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
VALID_METRICS    = ("price", "rvol")


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
            condition        TEXT NOT NULL,                  -- 'above' | 'below'
            target_price     REAL NOT NULL,                  -- valor objetivo: $ si metric='price', xVeces si metric='rvol'
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

def create_alert(user_id: int, ticker: str, condition: str, target_price: float, metric: str = "price") -> dict:
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "Ticker vacío"}
    if condition not in VALID_CONDITIONS:
        return {"ok": False, "error": "Condición inválida (usa 'above' o 'below')"}
    if metric not in VALID_METRICS:
        return {"ok": False, "error": "Métrica inválida (usa 'price' o 'rvol')"}
    try:
        target_price = float(target_price)
    except (TypeError, ValueError):
        return {"ok": False, "error": "Valor objetivo inválido"}
    if target_price <= 0:
        return {"ok": False, "error": "Valor objetivo debe ser mayor que 0"}

    conn = _conn()
    try:
        count = conn.execute(
            "SELECT COUNT(*) FROM alerts WHERE user_id = ? AND status = 'active'", (user_id,)
        ).fetchone()[0]
        if count >= MAX_ACTIVE_ALERTS:
            return {"ok": False, "error": f"Límite de {MAX_ACTIVE_ALERTS} alertas activas alcanzado"}
        cur = conn.execute(
            "INSERT INTO alerts (user_id, ticker, condition, target_price, status, created_at, seen, metric) "
            "VALUES (?, ?, ?, ?, 'active', ?, 1, ?)",
            (user_id, ticker, condition, target_price, datetime.now(timezone.utc).isoformat(), metric)
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

    prices = {}
    if price_alerts:
        from services.cartera_service import fetch_live_prices
        prices = fetch_live_prices(list({a["ticker"] for a in price_alerts}))

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

        for a in price_alerts:
            p = prices.get(a["ticker"])
            _check(a, p["price"] if p else None)
        for a in rvol_alerts:
            _check(a, rvols.get(a["ticker"]))

        if triggered:
            conn.commit()
    finally:
        conn.close()
    return triggered


init_db()