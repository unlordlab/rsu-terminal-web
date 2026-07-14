import pandas as pd
import unicodedata
import time
import math
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import pytz
from config import settings

_price_cache: dict = {}
_CACHE_TTL = 60

def norm_col(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

# Sizing por nivel de conviccion: en vez de leer acciones exactas de la hoja,
# cada posicion se etiqueta Core/High/Lottery y el peso en $ sale de aplicar
# ese % fijo sobre settings.capital_total. Si una fila no tiene nivel valido,
# se cae al calculo antiguo (Cantidad/Inversion) para no romper nada.
TIER_WEIGHTS = {"CORE": 5.0, "HIGH": 3.0, "LOTTERY": 1.0}

def norm_tier(value) -> str | None:
    if value is None:
        return None
    key = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().strip().upper()
    return key if key in TIER_WEIGHTS else None

def clean_numeric(value):
    if pd.isna(value):
        return 0.0
    val_str = str(value).strip().replace("$", "").replace("%", "").replace(" ", "")
    if "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    try:
        return float(val_str)
    except Exception:
        return 0.0

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

def get_market_status():
    ny = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    wd = now.weekday()
    h = now.hour + now.minute / 60
    if wd >= 5:
        return "CLOSED", "#f23645"
    if 9.5 <= h < 16.0:
        return "OPEN", "#00ffad"
    if 4.0 <= h < 9.5 or 16.0 <= h < 20.0:
        return "PRE/POST", "#ff9800"
    return "CLOSED", "#f23645"

def _fetch_price_single(ticker: str) -> dict | None:
    now = time.time()
    cached = _price_cache.get(ticker)
    if cached and (now - cached["updated"]) < _CACHE_TTL:
        return cached
    try:
        import yfinance as yf
        tk_obj = yf.Ticker(ticker)
        # fast_info da precio intradiario real + previous_close oficial
        price = 0.0
        prev  = 0.0
        try:
            fi    = tk_obj.fast_info
            price = float(fi.last_price or 0)
            prev  = float(fi.previous_close or 0)
        except Exception:
            pass
        # Fallback a history si fast_info no devuelve datos
        if not price or not prev:
            hist = tk_obj.history(period="5d", interval="1d")
            if len(hist) >= 2:
                price = float(hist["Close"].iloc[-1])
                prev  = float(hist["Close"].iloc[-2])
            elif len(hist) == 1:
                price = float(hist["Close"].iloc[-1])
                prev  = price
        if not price:
            return None
        chg   = (price - prev) / prev * 100 if prev else 0.0
        entry = {"ticker": ticker, "price": round(price, 2),
                 "prev": round(prev, 2), "chg": round(chg, 2), "updated": now}
        _price_cache[ticker] = entry
        return entry
    except Exception:
        pass
    try:
        if settings.fmp_api_key:
            import requests
            # NOTA: /api/v3/quote-short/{ticker} es legacy (misma migración que
            # earnings-calendar, ver backend/services/earnings_service.py) — el
            # endpoint nuevo es /stable/quote-short?symbol=X, parámetro symbol
            # en la query en vez de en la ruta.
            r = requests.get(
                "https://financialmodelingprep.com/stable/quote-short",
                params={"symbol": ticker, "apikey": settings.fmp_api_key}, timeout=5
            )
            if r.status_code != 200:
                print(f"[Cartera] FMP quote-short ({ticker}): status HTTP {r.status_code} — {r.text[:150]}")
            data = r.json()
            if data and isinstance(data, list):
                price = float(data[0].get("price", 0))
                if price:
                    entry = {"ticker": ticker, "price": round(price, 2),
                             "prev": price, "chg": 0.0, "updated": now}
                    _price_cache[ticker] = entry
                    return entry
    except Exception as e:
        print(f"[Cartera] FMP quote-short ({ticker}): error inesperado ({type(e).__name__}: {e})")
    return None

def fetch_live_prices(tickers: list) -> dict:
    now = time.time()
    result = {}
    stale = []
    for t in tickers:
        cached = _price_cache.get(t)
        if cached and (now - cached["updated"]) < _CACHE_TTL:
            result[t] = cached
        else:
            stale.append(t)
    if stale:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(_fetch_price_single, t): t for t in stale}
            for fut, t in futures.items():
                try:
                    r = fut.result(timeout=10)
                    if r:
                        result[t] = r
                except Exception:
                    pass
    return result

_sector_cache: dict = {}
_SECTOR_TTL = 6 * 3600  # el sector/industria no cambia casi nunca, cache larga

def _fetch_sector_single(ticker: str) -> dict:
    now = time.time()
    cached = _sector_cache.get(ticker)
    if cached and (now - cached["updated"]) < _SECTOR_TTL:
        return cached
    entry = {"ticker": ticker, "sector": "Sin clasificar", "industry": "", "updated": now}
    try:
        import yfinance as yf
        info = yf.Ticker(ticker).get_info()
        sector   = info.get("sector")
        industry = info.get("industry") or ""
        if not sector:
            # Los ETFs/fondos no tienen sector GICS — usamos su categoría como
            # sustituto en vez de dejarlos todos apilados en "Sin clasificar".
            quote_type = (info.get("quoteType") or "").upper()
            category   = info.get("category") or info.get("fundFamily") or ""
            if quote_type == "ETF" and category:
                sector = f"ETF · {category}"
            elif quote_type == "ETF":
                sector = "ETF (sin categoría)"
            elif quote_type == "CRYPTOCURRENCY":
                sector = "Cripto"
        entry["sector"]   = sector or "Sin clasificar"
        entry["industry"] = industry
    except Exception:
        pass
    _sector_cache[ticker] = entry
    return entry

def fetch_sectors(tickers: list) -> dict:
    now = time.time()
    result = {}
    stale = []
    for t in tickers:
        cached = _sector_cache.get(t)
        if cached and (now - cached["updated"]) < _SECTOR_TTL:
            result[t] = cached
        else:
            stale.append(t)
    if stale:
        with ThreadPoolExecutor(max_workers=4) as ex:
            futures = {ex.submit(_fetch_sector_single, t): t for t in stale}
            for fut, t in futures.items():
                try:
                    result[t] = fut.result(timeout=10)
                except Exception:
                    pass
    return result


_sparkline_cache: dict = {}
_SPARKLINE_TTL = 900  # 15 min

def _fetch_sparkline_single(ticker: str, days: int) -> dict | None:
    key = f"{ticker}:{days}"
    now = time.time()
    cached = _sparkline_cache.get(key)
    if cached and (now - cached["updated"]) < _SPARKLINE_TTL:
        return cached
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period=f"{days}d", interval="1d")
        if hist.empty:
            return None
        closes = [round(float(v), 4) for v in hist["Close"].tolist()]
        entry = {"ticker": ticker, "closes": closes, "updated": now}
        _sparkline_cache[key] = entry
        return entry
    except Exception:
        return None

def fetch_sparklines(tickers: list, days: int = 30) -> dict:
    result = {}
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures = {ex.submit(_fetch_sparkline_single, t, days): t for t in tickers}
        for fut, t in futures.items():
            try:
                r = fut.result(timeout=10)
                if r:
                    result[t] = r
            except Exception:
                pass
    return result


_history_cache: dict = {"updated": 0, "data": None}
_HISTORY_TTL = 900  # 15 min — reconstruir el histórico es costoso (N llamadas yfinance)

def get_portfolio_history(abiertas_rows: list, days: int = 180) -> list:
    """Reconstruye la curva de valor de la cartera (posiciones abiertas actuales)
    desde la fecha de entrada más antigua hasta hoy, usando precios históricos.
    Devuelve [{fecha, valor, invertido}] en orden cronológico.
    Nota: requiere 'shares' > 0 por posición (columna Cantidad rellenada en el
    Excel); si no hay shares, el valor histórico no se puede ponderar por posición
    y se devuelve una lista vacía en vez de datos engañosos.
    """
    now = time.time()
    positions = [r for r in abiertas_rows if r.get("shares", 0) > 0]
    if not positions:
        return []

    cache_key = tuple(sorted((r["ticker"], r["shares"]) for r in positions))
    cached = _history_cache.get("data")
    if cached and _history_cache.get("key") == cache_key and (now - _history_cache["updated"]) < _HISTORY_TTL:
        return cached

    try:
        import yfinance as yf
    except Exception:
        return []

    def _hist_for(ticker):
        try:
            return ticker, yf.Ticker(ticker).history(period=f"{days}d", interval="1d")["Close"]
        except Exception:
            return ticker, None

    series = {}
    with ThreadPoolExecutor(max_workers=6) as ex:
        for ticker, s in ex.map(_hist_for, [p["ticker"] for p in positions]):
            if s is not None and not s.empty:
                s.index = s.index.tz_localize(None)
                series[ticker] = s

    if not series:
        return []

    all_dates = sorted(set().union(*[s.index for s in series.values()]))
    if not all_dates:
        return []

    entry_dates = {}
    for p in positions:
        try:
            entry_dates[p["ticker"]] = datetime.strptime(p["fecha"], "%d/%m/%Y")
        except Exception:
            entry_dates[p["ticker"]] = all_dates[0]

    result = []
    for d in all_dates:
        total_val = 0.0
        total_inv = 0.0
        for p in positions:
            ticker = p["ticker"]
            if d < entry_dates.get(ticker, all_dates[0]):
                continue  # posición aún no abierta en esta fecha
            s = series.get(ticker)
            if s is None:
                continue
            px_series = s[s.index <= d]
            if px_series.empty:
                continue
            px = float(px_series.iloc[-1])
            total_val += px * p["shares"]
            total_inv += p.get("inv", 0.0)
        if total_val > 0:
            result.append({
                "fecha":     d.strftime("%Y-%m-%d"),
                "valor":     round(total_val, 2),
                "invertido": round(total_inv, 2),
            })

    _history_cache.update({"updated": now, "key": cache_key, "data": result})
    return result


def simulate_tier_capital(df, col_fecha, col_estado, col_compra, col_actual, col_venta, col_tier, capital_total):
    """Recorre TODAS las operaciones (abiertas + cerradas) en orden cronológico y
    dimensiona cada posición Core/High/Lottery como % de un capital que:
      - empieza en `capital_total`,
      - se incrementa/reduce con el P&L REALIZADO de cada posición al cerrarse,
      - nunca permite que el capital comprometido en posiciones abiertas supere
        el capital disponible en ese momento (si el tamaño objetivo del nivel no
        cabe, se recorta al disponible).
    Devuelve {indice_fila_df: inversion_real} — None si la fila no tiene nivel
    válido o no se puede dimensionar (para que el llamador caiga al cálculo
    antiguo Cantidad/Inversión en ese caso).
    """
    if capital_total <= 0 or not col_tier:
        return {}

    order = df.sort_values(col_fecha, ascending=True)
    equity = capital_total
    open_committed = 0.0
    inv_by_idx = {}

    for idx, row in order.iterrows():
        tier = norm_tier(row.get(col_tier))
        compra = float(row[col_compra]) if row[col_compra] else 0.0
        if not tier or compra <= 0:
            inv_by_idx[idx] = None
            continue

        desired   = capital_total * TIER_WEIGHTS[tier] / 100
        available = max(0.0, equity - open_committed)
        actual_inv = round(min(desired, available), 2)
        inv_by_idx[idx] = actual_inv
        open_committed += actual_inv

        estado = str(row[col_estado]).upper()
        if "CERRADA" in estado or "CLOSED" in estado:
            venta = float(row.get(col_venta, 0) or 0) if col_venta else 0.0
            actual_px = venta if venta > 0 else (float(row.get(col_actual, 0) or 0) if col_actual else 0.0) or compra
            pnl_dollar = (actual_px - compra) / compra * actual_inv if compra > 0 else 0.0
            equity += pnl_dollar
            open_committed -= actual_inv  # libera el capital comprometido al cerrar

    return {
        "inv_by_idx": inv_by_idx,
        "equity_final":     round(equity, 2),
        "open_committed":   round(open_committed, 2),
        "pnl_realizado":    round(equity - capital_total, 2),
        "capital_disponible": round(max(0.0, equity - open_committed), 2),
    }


def get_cartera():
    try:
        url = settings.url_cartera
        if not url:
            raise ValueError("URL_CARTERA no configurada")

        df_raw = pd.read_csv(url).dropna(how="all")
        df_raw.columns = [c.strip() for c in df_raw.columns]

        col_map = {norm_col(c): c for c in df_raw.columns}

        def find_col(*candidates):
            for c in candidates:
                key = norm_col(c)
                if key in col_map:
                    return col_map[key]
            return None

        col_fecha    = find_col("Fecha")
        col_ticker   = find_col("Ticker", "Symbol")
        col_estado   = find_col("Estado")
        col_cantidad = find_col("Cantidad", "Shares", "Acciones", "Qty")
        col_compra   = find_col("Precio Compra", "Compra", "Precio de Compra")
        col_actual   = find_col("Precio Actual", "Actual", "Current Price", "Precio")
        col_venta    = find_col("Precio Venta", "Venta", "Precio de Venta")
        col_inversion = find_col("Inversión", "Inversion", "Capital")
        col_valor    = find_col("Valor Actual", "Valor", "Market Value")
        col_comis    = find_col("Comisiones", "Comision", "Fees")
        col_comment  = find_col("Comentarios", "Comentario", "Notes")
        col_tier     = find_col("Nivel", "Tamaño", "Tamano", "Tier", "Categoria", "Conviccion", "Convicción")
        col_cierre   = find_col("Fecha Cierre", "Fecha Venta", "Fecha Salida", "Close Date", "Fecha Cerrada")

        if not col_fecha or not col_ticker or not col_estado or not col_compra:
            raise ValueError(f"Columnas mínimas no encontradas. Disponibles: {list(df_raw.columns)}")

        df = df_raw.copy()

        for col in [c for c in [col_compra, col_actual, col_venta, col_inversion,
                                  col_valor, col_comis, col_cantidad] if c]:
            df[col] = df[col].apply(clean_numeric)

        df[col_estado] = df[col_estado].astype(str).str.strip().str.upper()
        df[col_ticker] = df[col_ticker].astype(str).str.strip()

        def parse_dates_flexible(series):
            """La hoja mezcla fechas DD/MM/AAAA (entradas antiguas) y MM/DD/AAAA
            (entradas más recientes). Probamos primero día-primero (convención
            habitual); para las que resulten inválidas (ej. "06/29/2026" → día=06,
            mes=29 no existe), reintentamos mes-primero antes de descartar la fila.
            """
            raw = series.astype(str)
            parsed = pd.to_datetime(raw, dayfirst=True, errors="coerce")
            need_retry = parsed.isna() & series.notna()
            if need_retry.any():
                retry = pd.to_datetime(raw[need_retry], dayfirst=False, errors="coerce")
                parsed.loc[need_retry] = retry
            return parsed

        df[col_fecha] = parse_dates_flexible(df[col_fecha])
        if col_cierre:
            df[col_cierre] = parse_dates_flexible(df[col_cierre])

        n_before = len(df)
        df = df.dropna(subset=[col_fecha, col_ticker])
        n_after = len(df)
        if n_before != n_after:
            print(f"[Cartera] {n_before - n_after} fila(s) descartada(s) por fecha o ticker inválido tras ambos intentos de parseo")
        df = df[~df[col_ticker].str.upper().isin(["NAN", "NONE", ""])]

        sim = simulate_tier_capital(df, col_fecha, col_estado, col_compra, col_actual,
                                     col_venta, col_tier, settings.capital_total)
        inv_by_idx = sim.get("inv_by_idx", {}) if sim else {}

        abiertas = df[df[col_estado].str.contains("ABIERTA|OPEN", case=False, na=False)].copy()
        cerradas = df[df[col_estado].str.contains("CERRADA|CLOSED", case=False, na=False)].copy()

        # Enriquecer abiertas con precios live + sector
        live_prices = {}
        sectors = {}
        if not abiertas.empty:
            tickers_open = abiertas[col_ticker].unique().tolist()
            live_prices = fetch_live_prices(tickers_open)
            sectors = fetch_sectors(tickers_open)

        def calc_pnl(compra, actual):
            if compra and compra > 0 and actual and actual > 0:
                return round((actual - compra) / compra * 100, 2)
            return 0.0

        def df_to_rows(d, total_inv_ref=1, is_open=False):
            rows = []
            for idx, row in d.sort_values(col_fecha, ascending=False).iterrows():
                ticker  = row[col_ticker]
                compra  = float(row[col_compra]) if row[col_compra] else 0.0
                cantidad = float(row[col_cantidad]) if col_cantidad and row.get(col_cantidad) else 0.0

                tier = norm_tier(row.get(col_tier)) if col_tier else None

                # Inversión: prioridad = simulación cronológica Core/High/Lottery
                # (capital real disponible, ver simulate_tier_capital) > columna
                # Inversión > Cantidad*compra.
                sim_inv = inv_by_idx.get(idx)
                if sim_inv is not None:
                    inv = sim_inv
                else:
                    inv = float(row[col_inversion]) if col_inversion and row.get(col_inversion) else 0.0
                    if inv == 0 and cantidad > 0 and compra > 0:
                        inv = round(cantidad * compra, 2)

                # Shares: si viene de nivel o inversión, se derivan del precio de compra;
                # si la hoja ya trae Cantidad explícita, esa manda (más precisa).
                shares = cantidad if cantidad > 0 else (round(inv / compra, 4) if compra > 0 else 0.0)

                # Precio actual: live > sheet > compra
                live = live_prices.get(ticker, {}) if is_open else {}
                live_px = live.get("price", 0.0)

                sheet_px = float(row[col_actual]) if col_actual and row.get(col_actual) else 0.0

                # Para cerradas, usar precio de venta si existe
                if not is_open and col_venta:
                    venta_px = float(row.get(col_venta, 0) or 0)
                    actual = venta_px if venta_px > 0 else (sheet_px if sheet_px > 0 else compra)
                else:
                    actual = live_px if live_px > 0 else (sheet_px if sheet_px > 0 else compra)

                actual = round(actual, 2)

                # Valor actual y P&L
                val_act = round(shares * actual, 2) if shares > 0 and actual > 0 else inv
                pnl = calc_pnl(compra, actual)
                pnl_usd = round(val_act - inv, 2)

                peso = round(inv / total_inv_ref * 100, 1) if total_inv_ref > 0 else 0.0

                comment = str(row[col_comment])[:60] if col_comment and col_comment in row.index else ""
                if comment.lower() in ("nan", "none", ""):
                    comment = ""

                sec = sectors.get(ticker, {}) if is_open else {}

                # Fecha de cierre real (si la hoja la tiene y está rellenada);
                # si no, cae a la fecha de apertura para no romper filas antiguas.
                fecha_cierre = None
                if not is_open and col_cierre and pd.notna(row.get(col_cierre)):
                    fecha_cierre = row[col_cierre].strftime("%d/%m/%Y")
                fecha_display = fecha_cierre if fecha_cierre else row[col_fecha].strftime("%d/%m/%Y")

                rows.append({
                    # Identificador único por fila (no por ticker) — imprescindible
                    # para no confundir operaciones duplicadas del mismo ticker
                    # (varios lotes abiertos/cerrados) al actualizar precios live.
                    "id":       f"{ticker}-{idx}",
                    "ticker":   ticker,
                    "fecha":    row[col_fecha].strftime("%d/%m/%Y"),
                    "fecha_cierre":  fecha_cierre,
                    "fecha_display": fecha_display,
                    "compra":   round(compra, 2),
                    "actual":   actual,
                    "pnl":      pnl,
                    "pnl_usd":  pnl_usd,
                    "inv":      inv,
                    "val_act":  val_act,
                    "shares":   round(shares, 4),
                    "peso":     peso,
                    "chg_hoy":  live.get("chg"),
                    "estado":   row[col_estado],
                    "comment":  comment,
                    "sector":   sec.get("sector", "Sin clasificar"),
                    "industry": sec.get("industry", ""),
                    "tier":     tier,
                })
            return rows

        # Calcular totales para métricas
        abiertas_rows = df_to_rows(abiertas, 1, is_open=True)
        total_inv = sum(r["inv"] for r in abiertas_rows)
        # Recalcular con total_inv correcto
        abiertas_rows = df_to_rows(abiertas, total_inv or 1, is_open=True)

        cerradas_rows = df_to_rows(cerradas, total_inv or 1, is_open=False)

        # Para "Últimas salidas" ordenamos por fecha de CIERRE real (fecha_display
        # ya cae a la fecha de apertura si no hay fecha de cierre en la hoja),
        # no por fecha de apertura como el resto de la tabla de cerradas.
        def _parse_dmy(s):
            try:
                return datetime.strptime(s, "%d/%m/%Y")
            except Exception:
                return datetime.min
        recent_closed = sorted(cerradas_rows, key=lambda r: _parse_dmy(r["fecha_display"]), reverse=True)[:5]

        # Métricas
        metrics = {}
        if abiertas_rows:
            total_val   = sum(r["val_act"] for r in abiertas_rows)
            total_comis = df[col_comis].apply(clean_numeric).sum() if col_comis else 0
            pnl_neto    = (total_val - total_inv) - total_comis
            pnl_pct     = (pnl_neto / total_inv * 100) if total_inv > 0 else 0
            val_pct     = ((total_val - total_inv) / total_inv * 100) if total_inv > 0 else 0
            metrics = {
                "total_inv":   round(total_inv, 2),
                "total_val":   round(total_val, 2),
                "pnl_neto":    round(pnl_neto, 2),
                "pnl_pct":     round(pnl_pct, 2),
                "val_pct":     round(val_pct, 2),
                "total_comis": round(total_comis, 2),
            }
            if sim and sim.get("inv_by_idx"):
                metrics["capital_inicial"]     = round(settings.capital_total, 2)
                metrics["pnl_realizado_acum"]  = sim["pnl_realizado"]
                metrics["capital_disponible"]  = sim["capital_disponible"]

        closed_stats = {}
        if cerradas_rows:
            ganadas  = len([r for r in cerradas_rows if r["pnl"] > 0])
            perdidas = len([r for r in cerradas_rows if r["pnl"] <= 0])
            win_rate = ganadas / len(cerradas_rows) * 100
            closed_stats = {
                "total":    len(cerradas_rows),
                "ganadas":  ganadas,
                "perdidas": perdidas,
                "win_rate": round(win_rate, 1),
                "avg_pnl":  round(sum(r["pnl"] for r in cerradas_rows), 2),
            }

        mkt_status, mkt_color = get_market_status()

        history = []
        try:
            history = get_portfolio_history(abiertas_rows)
        except Exception:
            history = []

        return _sanitize({
            "ok":           True,
            "metrics":      metrics,
            "closed_stats": closed_stats,
            "abiertas":     abiertas_rows,
            "cerradas":     cerradas_rows,
            "recent":       abiertas_rows[:5],
            "recent_closed": recent_closed,
            "history":      history,
            "mkt_status":   mkt_status,
            "mkt_color":    mkt_color,
            "last_update":  datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        })

    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "detail": traceback.format_exc()}


def get_live_prices_for_ws(tickers: list) -> list:
    prices = fetch_live_prices(tickers)
    return list(prices.values())