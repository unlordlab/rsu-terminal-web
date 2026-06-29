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
            r = requests.get(
                f"https://financialmodelingprep.com/api/v3/quote-short/{ticker}",
                params={"apikey": settings.fmp_api_key}, timeout=5
            )
            data = r.json()
            if data and isinstance(data, list):
                price = float(data[0].get("price", 0))
                if price:
                    entry = {"ticker": ticker, "price": round(price, 2),
                             "prev": price, "chg": 0.0, "updated": now}
                    _price_cache[ticker] = entry
                    return entry
    except Exception:
        pass
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

        if not col_fecha or not col_ticker or not col_estado or not col_compra:
            raise ValueError(f"Columnas mínimas no encontradas. Disponibles: {list(df_raw.columns)}")

        df = df_raw.copy()

        for col in [c for c in [col_compra, col_actual, col_venta, col_inversion,
                                  col_valor, col_comis, col_cantidad] if c]:
            df[col] = df[col].apply(clean_numeric)

        df[col_estado] = df[col_estado].astype(str).str.strip().str.upper()
        df[col_ticker] = df[col_ticker].astype(str).str.strip()

        # La hoja mezcla fechas DD/MM/AAAA (entradas antiguas) y MM/DD/AAAA (entradas
        # más recientes). Probamos primero día-primero (convención habitual); para las
        # que resulten inválidas (ej. "06/29/2026" → día=06, mes=29 no existe),
        # reintentamos mes-primero antes de descartar la fila. Así no perdemos en
        # silencio las operaciones más recientes solo porque cambiaron el formato.
        fecha_raw = df[col_fecha].astype(str)
        parsed = pd.to_datetime(fecha_raw, dayfirst=True, errors="coerce")
        need_retry = parsed.isna() & df[col_fecha].notna()
        if need_retry.any():
            retry = pd.to_datetime(fecha_raw[need_retry], dayfirst=False, errors="coerce")
            parsed.loc[need_retry] = retry
        df[col_fecha] = parsed

        n_before = len(df)
        df = df.dropna(subset=[col_fecha, col_ticker])
        n_after = len(df)
        if n_before != n_after:
            print(f"[Cartera] {n_before - n_after} fila(s) descartada(s) por fecha o ticker inválido tras ambos intentos de parseo")
        df = df[~df[col_ticker].str.upper().isin(["NAN", "NONE", ""])]

        abiertas = df[df[col_estado].str.contains("ABIERTA|OPEN", case=False, na=False)].copy()
        cerradas = df[df[col_estado].str.contains("CERRADA|CLOSED", case=False, na=False)].copy()

        # Enriquecer abiertas con precios live
        live_prices = {}
        if not abiertas.empty:
            tickers_open = abiertas[col_ticker].unique().tolist()
            live_prices = fetch_live_prices(tickers_open)

        def calc_pnl(compra, actual):
            if compra and compra > 0 and actual and actual > 0:
                return round((actual - compra) / compra * 100, 2)
            return 0.0

        def df_to_rows(d, total_inv_ref=1, is_open=False):
            rows = []
            for _, row in d.sort_values(col_fecha, ascending=False).iterrows():
                ticker  = row[col_ticker]
                compra  = float(row[col_compra]) if row[col_compra] else 0.0
                cantidad = float(row[col_cantidad]) if col_cantidad and row.get(col_cantidad) else 0.0

                # Inversión
                inv = float(row[col_inversion]) if col_inversion and row.get(col_inversion) else 0.0
                if inv == 0 and cantidad > 0 and compra > 0:
                    inv = round(cantidad * compra, 2)

                # Shares
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

                rows.append({
                    "ticker":   ticker,
                    "fecha":    row[col_fecha].strftime("%d/%m/%Y"),
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
                })
            return rows

        # Calcular totales para métricas
        abiertas_rows = df_to_rows(abiertas, 1, is_open=True)
        total_inv = sum(r["inv"] for r in abiertas_rows)
        # Recalcular con total_inv correcto
        abiertas_rows = df_to_rows(abiertas, total_inv or 1, is_open=True)

        cerradas_rows = df_to_rows(cerradas, total_inv or 1, is_open=False)

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

        return _sanitize({
            "ok":           True,
            "metrics":      metrics,
            "closed_stats": closed_stats,
            "abiertas":     abiertas_rows,
            "cerradas":     cerradas_rows,
            "recent":       abiertas_rows[:5],
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