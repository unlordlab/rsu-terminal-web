"""
Servicio de Watchlist + Alertas de precio.

Guarda en users.db (misma base SQLite que users_service.py, sin ORM nuevo,
mismo estilo que el resto del proyecto). Dos tablas nuevas: watchlist y alerts.

Disponible para cualquier usuario registrado (tier free incluido) por ahora.
El día que se quiera limitar a tiers de pago, basta con cambiar la
dependencia del router (`rl` -> `paid`) en main.py — no hace falta tocar
nada de este fichero.
"""
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.db')

# Límites razonables para evitar abuso mientras es gratis para todos.
MAX_WATCHLIST_ITEMS = 50
MAX_ACTIVE_ALERTS   = 30

VALID_CONDITIONS = ("above", "below")
VALID_METRICS    = ("price", "rvol", "ema_touch")
EMA_PERIODS      = (10, 20, 50, 200)
EMA_TOUCH_TOLERANCE_PCT = 0.5  # % de proximidad al valor de la EMA para considerar que el precio la "toca"


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS watchlist (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            ticker     TEXT NOT NULL,
            added_at   TEXT NOT NULL,
            UNIQUE(user_id, ticker)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            ticker           TEXT NOT NULL,
            condition        TEXT NOT NULL,                  -- 'above' | 'below' | 'touch'
            target_price     REAL NOT NULL,                  -- valor objetivo: $ si metric='price', xVeces si metric='rvol', periodo de EMA si metric='ema_touch'
            status           TEXT NOT NULL DEFAULT 'active',  -- active | triggered | cancelled
            created_at       TEXT NOT NULL,
            triggered_at     TEXT,
            triggered_price  REAL,
            seen             INTEGER NOT NULL DEFAULT 1       -- 0 = disparada y sin ver (campanita)
        )
    ''')
    # metric se añadió después del lanzamiento inicial (solo alertas de precio).
    # ALTER TABLE ADD COLUMN no tiene "IF NOT EXISTS" en SQLite, así que se
    # envuelve en try/except para que sea idempotente en bases ya existentes.
    try:
        conn.execute("ALTER TABLE alerts ADD COLUMN metric TEXT NOT NULL DEFAULT 'price'")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    # ema_period: qué EMA vigilar (10/20/50/200) — solo relevante si metric='ema_touch'.
    try:
        conn.execute("ALTER TABLE alerts ADD COLUMN ema_period INTEGER")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    conn.commit()
    conn.close()


# ── WATCHLIST ────────────────────────────────────────────────────────────────

def add_to_watchlist(user_id: int, ticker: str) -> dict:
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "Ticker vacío"}
    conn = _conn()
    try:
        count = conn.execute("SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (user_id,)).fetchone()[0]
        if count >= MAX_WATCHLIST_ITEMS:
            return {"ok": False, "error": f"Límite de {MAX_WATCHLIST_ITEMS} tickers en watchlist alcanzado"}
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (user_id, ticker, added_at) VALUES (?, ?, ?)",
            (user_id, ticker, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        return {"ok": True, "ticker": ticker}
    finally:
        conn.close()


def remove_from_watchlist(user_id: int, ticker: str) -> dict:
    ticker = (ticker or "").strip().upper()
    conn = _conn()
    try:
        conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ?", (user_id, ticker))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def get_watchlist_tickers(user_id: int) -> list:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT ticker, added_at FROM watchlist WHERE user_id = ? ORDER BY added_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_watchlist(user_id: int) -> dict:
    """Watchlist enriquecida con precio en vivo. Reutiliza fetch_live_prices()
    de cartera_service (mismo caché de 60s, mismo patrón de fetch por lotes
    con ThreadPoolExecutor) en vez de duplicar lógica de precios."""
    items = get_watchlist_tickers(user_id)
    if not items:
        return {"ok": True, "data": []}
    from services.cartera_service import fetch_live_prices
    tickers = [i["ticker"] for i in items]
    prices  = fetch_live_prices(tickers)
    data = []
    for i in items:
        p = prices.get(i["ticker"])
        data.append({
            "ticker":   i["ticker"],
            "added_at": i["added_at"],
            "price":    p["price"] if p else None,
            "chg":      p["chg"]   if p else None,
            "ok":       p is not None,
        })
    return {"ok": True, "data": data}


# ── ALERTAS ──────────────────────────────────────────────────────────────────

def create_alert(user_id: int, ticker: str, condition: str, target_price: float, metric: str = "price", ema_period: int = None) -> dict:
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "Ticker vacío"}
    if metric not in VALID_METRICS:
        return {"ok": False, "error": "Métrica inválida (usa 'price', 'rvol' o 'ema_touch')"}

    if metric == "ema_touch":
        try:
            ema_period = int(ema_period)
        except (TypeError, ValueError):
            ema_period = None
        if ema_period not in EMA_PERIODS:
            return {"ok": False, "error": f"Periodo de EMA inválido (usa uno de {EMA_PERIODS})"}
        condition = "touch"
        target_price = float(ema_period)  # sin uso numérico real aquí — el periodo real vive en ema_period; se replica por compatibilidad con la columna NOT NULL
    else:
        if condition not in VALID_CONDITIONS:
            return {"ok": False, "error": "Condición inválida (usa 'above' o 'below')"}
        try:
            target_price = float(target_price)
        except (TypeError, ValueError):
            return {"ok": False, "error": "Valor objetivo inválido"}
        if target_price <= 0:
            return {"ok": False, "error": "Valor objetivo debe ser mayor que 0"}
        ema_period = None

    conn = _conn()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND status = 'active'", (user_id,)
        ).fetchone()[0]
        if count >= MAX_ACTIVE_ALERTS:
            return {"ok": False, "error": f"Límite de {MAX_ACTIVE_ALERTS} alertas activas alcanzado"}
        cur = conn.execute(
            "INSERT INTO alerts (user_id, ticker, condition, target_price, status, created_at, seen, metric, ema_period) "
            "VALUES (?, ?, ?, ?, 'active', ?, 1, ?, ?)",
            (user_id, ticker, condition, target_price, datetime.now(timezone.utc).isoformat(), metric, ema_period)
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


def delete_alert(user_id: int, alert_id: int) -> dict:
    conn = _conn()
    try:
        conn.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def get_alerts(user_id: int) -> dict:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM alerts WHERE user_id = ? ORDER BY "
            "CASE status WHEN 'triggered' THEN 0 WHEN 'active' THEN 1 ELSE 2 END, created_at DESC",
            (user_id,)
        ).fetchall()
        return {"ok": True, "data": [dict(r) for r in rows]}
    finally:
        conn.close()


def mark_alerts_seen(user_id: int) -> dict:
    conn = _conn()
    try:
        conn.execute("UPDATE alerts SET seen = 1 WHERE user_id = ? AND status = 'triggered'", (user_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def clear_triggered_alerts(user_id: int) -> dict:
    """Borra en bloque todas las alertas ya disparadas del usuario (botón
    'Limpiar disparadas' en el frontend). No toca las activas."""
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM alerts WHERE user_id = ? AND status = 'triggered'", (user_id,))
        conn.commit()
        return {"ok": True, "deleted": cur.rowcount}
    finally:
        conn.close()


def get_unseen_triggered_count(user_id: int) -> int:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND status = 'triggered' AND seen = 0", (user_id,)
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


# ── RVOL EN VIVO (para alertas metric='rvol') ─────────────────────────────────
# Caché propio y corto (5 min): el RVOL no hace falta tenerlo al segundo, y así
# no se dispara una descarga de yfinance por cada alerta activa en cada ciclo.
_rvol_cache: dict = {}
_RVOL_CACHE_TTL = 300

def _fetch_rvol_single(ticker: str):
    import time
    now = time.time()
    cached = _rvol_cache.get(ticker)
    if cached and (now - cached["updated"]) < _RVOL_CACHE_TTL:
        return cached["rvol"]
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="30d")
        if len(hist) < 6:
            return None
        vol_today = float(hist["Volume"].iloc[-1])
        vol_avg   = float(hist["Volume"].iloc[:-1].tail(20).mean())
        if vol_avg <= 0:
            return None
        rvol = round(vol_today / vol_avg, 2)
        _rvol_cache[ticker] = {"rvol": rvol, "updated": now}
        return rvol
    except Exception:
        return None


def fetch_live_rvol(tickers: list) -> dict:
    """{ticker: rvol_float}. Tickers sin dato válido no aparecen en el dict."""
    from concurrent.futures import ThreadPoolExecutor
    result = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_fetch_rvol_single, t): t for t in tickers}
        for fut, t in futures.items():
            try:
                r = fut.result(timeout=15)
                if r is not None:
                    result[t] = r
            except Exception:
                pass
    return result


# ── EMA EN VIVO (para alertas metric='ema_touch') ─────────────────────────────
#
# Calcular una EMA200 desde cero (con histórico completo) en cada ciclo de 90s
# para cada alerta activa sería caro y redundante — los cierres de días ya
# pasados no cambian en todo el día de hoy. Así que la EMA se calcula en dos
# capas:
#  1. Base de AYER: histórico real, cacheada una vez al día por (ticker, periodo).
#  2. EMA "en vivo" de HOY: se combina esa base cacheada con el precio actual,
#     exactamente el mismo cálculo que hace cualquier plataforma de gráficos
#     para el último punto de una EMA en un gráfico diario — barato, sin
#     volver a descargar histórico en cada ciclo.
_ema_cache: dict = {}

def _get_ema_baseline(ticker: str, period: int):
    key = (ticker, period)
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    cached = _ema_cache.get(key)
    if cached and cached["date"] == today:
        return cached["ema"]
    try:
        import yfinance as yf
        # Margen amplio para que la EMA esté "calentada" — sobre todo
        # relevante para la EMA200, que necesita bastante histórico previo
        # para converger a un valor estable y no arrastrar sesgo de arranque.
        lookback_days = max(period * 3, 260)
        hist = yf.Ticker(ticker).history(period=f"{lookback_days}d")
        closes = hist["Close"].dropna()
        if len(closes) < period:
            return None
        # Cierres hasta AYER — si el histórico ya trae la vela de hoy (p.ej.
        # tras el cierre de mercado), se excluye para no contarla dos veces
        # al combinarla más abajo con el precio en vivo.
        if closes.index[-1].strftime('%Y-%m-%d') == today:
            closes = closes.iloc[:-1]
        if len(closes) < period:
            return None
        ema_value = float(closes.ewm(span=period, adjust=False).mean().iloc[-1])
        _ema_cache[key] = {"ema": ema_value, "date": today}
        return ema_value
    except Exception:
        return None


def _get_live_ema(ticker: str, period: int, live_price: float):
    baseline = _get_ema_baseline(ticker, period)
    if baseline is None or live_price is None:
        return None
    k = 2 / (period + 1)
    return live_price * k + baseline * (1 - k)


# ── COMPROBACIÓN DE ALERTAS (llamada desde el bucle en segundo plano) ────────

def check_all_active_alerts() -> list:
    """Revisa TODAS las alertas activas de TODOS los usuarios de una vez,
    agrupando por ticker para pedir cada precio/RVOL una sola vez sin importar
    cuántos usuarios tengan una alerta puesta en el mismo ticker. Pensada
    para llamarse periódicamente desde un bucle en segundo plano (ver
    routers/ws.py, alerts_check_loop()) — mismo patrón que ya usáis para el
    broadcast de precios en tiempo real."""
    conn = _conn()
    try:
        rows = conn.execute("SELECT * FROM alerts WHERE status = 'active'").fetchall()
        active = [dict(r) for r in rows]
    finally:
        conn.close()

    if not active:
        return []

    price_alerts = [a for a in active if a.get("metric", "price") == "price"]
    rvol_alerts  = [a for a in active if a.get("metric") == "rvol"]
    ema_alerts   = [a for a in active if a.get("metric") == "ema_touch"]

    from services.cartera_service import fetch_live_prices
    prices = {}
    if price_alerts:
        prices.update(fetch_live_prices(list({a["ticker"] for a in price_alerts})))
    if ema_alerts:
        # Las alertas de EMA también necesitan el precio en vivo — se piden
        # solo los tickers que todavía no se hayan pedido para price_alerts,
        # reutilizando el mismo caché de 60s de fetch_live_prices.
        missing = [t for t in {a["ticker"] for a in ema_alerts} if t not in prices]
        if missing:
            prices.update(fetch_live_prices(missing))

    rvols = {}
    if rvol_alerts:
        rvols = fetch_live_rvol(list({a["ticker"] for a in rvol_alerts}))

    triggered = []
    conn = _conn()
    try:
        now_iso = datetime.now(timezone.utc).isoformat()

        def _check(a, current_value):
            if current_value is None:
                return
            hit = (a["condition"] == "above" and current_value >= a["target_price"]) or \
                  (a["condition"] == "below" and current_value <= a["target_price"])
            if hit:
                conn.execute(
                    "UPDATE alerts SET status = 'triggered', triggered_at = ?, "
                    "triggered_price = ?, seen = 0 WHERE id = ?",
                    (now_iso, current_value, a["id"])
                )
                a["triggered_at"]    = now_iso
                a["triggered_price"] = current_value
                triggered.append(a)

        def _check_ema_touch(a):
            p = prices.get(a["ticker"])
            if not p or p.get("price") is None:
                return
            live_price = p["price"]
            period = a.get("ema_period")
            if not period:
                return
            ema_value = _get_live_ema(a["ticker"], period, live_price)
            if not ema_value:
                return
            distance_pct = abs(live_price - ema_value) / ema_value * 100
            if distance_pct <= EMA_TOUCH_TOLERANCE_PCT:
                conn.execute(
                    "UPDATE alerts SET status = 'triggered', triggered_at = ?, "
                    "triggered_price = ?, seen = 0 WHERE id = ?",
                    (now_iso, live_price, a["id"])
                )
                a["triggered_at"]    = now_iso
                a["triggered_price"] = live_price
                triggered.append(a)

        for a in price_alerts:
            p = prices.get(a["ticker"])
            _check(a, p["price"] if p else None)
        for a in rvol_alerts:
            _check(a, rvols.get(a["ticker"]))
        for a in ema_alerts:
            _check_ema_touch(a)

        if triggered:
            conn.commit()
    finally:
        conn.close()
    return triggered


init_db()