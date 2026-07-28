from datetime import datetime, timedelta, timezone
import yfinance as yf
import pandas as pd
import requests
import sys, os
from concurrent.futures import ThreadPoolExecutor
from services.yf_pool import yf_executor
from config import settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402
from mcclellan import mcclellan_series  # noqa: E402
from market_regime import spy_trend_snapshot  # noqa: E402

# ── ÍNDICES ───────────────────────────────────────────────────────────────────

INDICES = [
    {"ticker": "^GSPC", "name": "S&P 500",     "short": "SPX"},
    {"ticker": "RSP",   "name": "S&P 500 Equal Weight", "short": "RSP"},
    {"ticker": "^NDX",  "name": "Nasdaq 100",  "short": "NDX"},
    {"ticker": "^DJI",  "name": "Dow Jones",   "short": "DJI"},
    {"ticker": "^RUT",  "name": "Russell 2000","short": "RUT"},
    {"ticker": "^VIX",  "name": "VIX",         "short": "VIX"},
]

def _fetch_ticker_fmp_fallback(item):
    """Respaldo cuando yfinance falla (bloqueo/rate-limit de Yahoo desde la IP
    del servidor, ver conversación 15/07/2026) — usa FMP, una API de verdad
    con clave, no un scraper como yfinance, así que no sufre el mismo tipo
    de bloqueo por IP de datacenter. Solo se llama cuando yfinance ya falló,
    no sustituye a yfinance como fuente principal (yfinance es gratis e
    ilimitado cuando funciona; FMP tiene cuota diaria de 250 peticiones)."""
    try:
        from config import settings
        if not settings.fmp_api_key:
            return None
        r = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": item["ticker"], "apikey": settings.fmp_api_key},
            timeout=6,
        )
        if r.status_code != 200:
            print(f"[Market] FMP fallback ({item['ticker']}): status HTTP {r.status_code}")
            return None
        data = r.json()
        if not data or not isinstance(data, list):
            return None
        q = data[0]
        price, change, pct = q.get("price"), q.get("change"), q.get("changesPercentage")
        if price is None:
            return None
        return {
            "ticker": item["short"], "name": item["name"],
            "price": round(price, 2), "change": round(change, 2) if change is not None else None,
            "pct": round(pct, 2) if pct is not None else None,
            "ok": True, "source": "fmp_fallback",
        }
    except Exception as e:
        print(f"[Market] FMP fallback ({item['ticker']}): error inesperado ({type(e).__name__}: {e})")
        return None

def _fetch_ticker(item):
    try:
        t    = yf.Ticker(item["ticker"])
        hist = t.history(period="5d", interval="1d").dropna()
        if len(hist) < 2:
            raise ValueError("Sin datos suficientes")
        prev = float(hist["Close"].iloc[-2])
        last = float(hist["Close"].iloc[-1])
        chg  = last - prev
        pct  = (chg / prev) * 100
        return {
            "ticker": item["short"],
            "name":   item["name"],
            "price":  round(last, 2),
            "change": round(chg, 2),
            "pct":    round(pct, 2),
            "ok":     True
        }
    except Exception as e:
        # yfinance falló (a menudo bloqueo/rate-limit de Yahoo, ver nota más
        # arriba) — antes de rendirse, un intento con FMP como respaldo.
        fallback = _fetch_ticker_fmp_fallback(item)
        if fallback:
            return fallback
        return {"ticker": item["short"], "name": item["name"], "price": None, "change": None, "pct": None, "ok": False, "error": str(e)}

def get_indices():
    from services.cache import cache, TTL
    cached = cache.get("market:indices")
    if cached: return cached
    results = []
    # max_workers bajado de 5 a 2 — una ráfaga de 5 peticiones simultáneas a
    # Yahoo desde una IP de datacenter que nunca las ha visto antes (recién
    # migrado a Hetzner) tiene más pinta de bot que las mismas peticiones
    # más espaciadas. No es una garantía, pero reduce la "firma" de ráfaga.
    futures = {yf_executor.submit(_fetch_ticker, item): item for item in INDICES}
    for future in futures:
        results.append(future.result())
    results.sort(key=lambda x: ["SPX","RSP","NDX","DJI","RUT","VIX"].index(x["ticker"]))
    ok_general = any(r["ok"] for r in results)
    from services.yf_health import log as _yf_log
    _yf_log("indices", ok_general, None if ok_general else "; ".join(r.get("error", "") for r in results if not r["ok"])[:250])
    result = {"data": results, "timestamp": get_timestamp(), "ok": ok_general}
    if ok_general:
        cache.set("market:indices", result, TTL["market"])
    else:
        # NO cachear un fallo total — si Yahoo está bloqueando/limitando
        # ahora mismo (ej. IP de datacenter recién vista), cachear ese
        # fallo significa quedarse "atascado" mostrando "Sin datos" los
        # próximos 5 minutos completos aunque el bloqueo ya se haya
        # levantado. Mejor dejar que la siguiente petición reintente.
        print(f"[Market] Índices: fallo total, sin cachear. Ejemplo de error: {results[0].get('error') if results else 'N/D'}")
    return result

# ── FEAR & GREED ──────────────────────────────────────────────────────────────

FEAR_GREED_COMPONENTS = [
    {"key": "market_momentum_sp500", "label": "Momentum del Mercado",        "desc": "S&P 500 vs media de 125 sesiones"},
    {"key": "stock_price_strength",  "label": "Fortaleza del Precio",        "desc": "Nuevos máximos vs mínimos (52 sem.)"},
    {"key": "stock_price_breadth",   "label": "Amplitud del Precio",         "desc": "Volumen alcista vs bajista (McClellan Vol.)"},
    {"key": "put_call_options",      "label": "Ratio Put/Call",              "desc": "Opciones de venta vs de compra"},
    {"key": "junk_bond_demand",      "label": "Demanda de Bonos Basura",     "desc": "Spread High Yield vs Investment Grade"},
    {"key": "market_volatility_vix", "label": "Volatilidad (VIX)",           "desc": "VIX vs su media de 50 sesiones"},
    {"key": "safe_haven_demand",     "label": "Demanda de Refugio",          "desc": "Rendimiento acciones vs bonos (20 días)"},
]

def get_fear_greed():
    import requests
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
                "Referer": "https://edition.cnn.com/markets/fear-and-greed",
                "Origin": "https://edition.cnn.com",
            },
            timeout=8,
        )
        if r.status_code == 200:
            data   = r.json()
            fg     = data["fear_and_greed"]
            score  = int(fg["score"])
            rating = str(fg["rating"]).replace("_", " ").title()
            prev   = int(fg.get("previous_close", score))
            week   = int(fg.get("previous_1_week", score))
            month  = fg.get("previous_1_month")
            year   = fg.get("previous_1_year")

            components = []
            for c in FEAR_GREED_COMPONENTS:
                node = data.get(c["key"])
                if node and node.get("score") is not None:
                    components.append({
                        "key": c["key"],
                        "label": c["label"],
                        "desc": c["desc"],
                        "score": round(float(node["score"]), 1),
                        "rating": str(node.get("rating", "")).replace("_", " ").title(),
                    })

            return {
                "score": score, "rating": rating,
                "prev": prev, "week_ago": week,
                "month_ago": int(month) if month is not None else None,
                "year_ago": int(year) if year is not None else None,
                "components": components,
                "timestamp": get_timestamp(), "ok": True,
            }
    except Exception:
        pass
    try:
        t     = yf.Ticker("^VIX")
        hist  = t.history(period="5d").dropna()
        vix   = float(hist["Close"].iloc[-1]) if len(hist) else 20
        score = max(0, min(100, int(100 - (vix - 10) * 3.5)))
        if score >= 75:   rating = "Extreme Greed"
        elif score >= 55: rating = "Greed"
        elif score >= 45: rating = "Neutral"
        elif score >= 25: rating = "Fear"
        else:             rating = "Extreme Fear"
        return {
            "score": score, "rating": rating + " (est.)",
            "prev": score, "week_ago": score, "month_ago": None, "year_ago": None,
            "components": [], "timestamp": get_timestamp(), "ok": True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "timestamp": get_timestamp()}

# ── FOREX ─────────────────────────────────────────────────────────────────────

FOREX_TICKERS = [
    {"ticker": "EURUSD=X",  "name": "Euro / Dólar",         "short": "EUR/USD"},
    {"ticker": "GBPUSD=X",  "name": "Libra / Dólar",        "short": "GBP/USD"},
    {"ticker": "JPY=X",     "name": "Dólar / Yen",          "short": "USD/JPY"},
    {"ticker": "CHF=X",     "name": "Dólar / Franco Suizo", "short": "USD/CHF"},
    {"ticker": "AUDUSD=X",  "name": "Dólar Aus. / Dólar",   "short": "AUD/USD"},
    {"ticker": "DX-Y.NYB",  "name": "Índice Dólar",         "short": "DXY"},
]

FOREX_FMP_MAP = {
    "EUR/USD": "EURUSD", "GBP/USD": "GBPUSD", "USD/JPY": "USDJPY",
    "USD/CHF": "USDCHF", "AUD/USD": "AUDUSD",
    # DXY (Índice Dólar) excluido a propósito — es un índice, no un par de
    # divisas normal, y el ticker de Yahoo (DX-Y.NYB) no tiene una
    # traducción obvia al símbolo de FMP. Mejor sin respaldo aquí que uno
    # adivinado que devuelva un dato incorrecto sin que se note.
}

def _fetch_fx_fmp_fallback(item):
    """Mismo respaldo que _fetch_ticker_fmp_fallback pero para forex — FMP
    usa el par sin barra ni sufijo (EURUSD, no EUR/USD ni EURUSD=X)."""
    simbolo_fmp = FOREX_FMP_MAP.get(item["short"])
    if not simbolo_fmp:
        return None
    try:
        from config import settings
        if not settings.fmp_api_key:
            return None
        r = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": simbolo_fmp, "apikey": settings.fmp_api_key},
            timeout=6,
        )
        if r.status_code != 200:
            print(f"[Market] FMP fallback forex ({item['short']}): status HTTP {r.status_code}")
            return None
        data = r.json()
        if not data or not isinstance(data, list):
            return None
        q = data[0]
        price, change, pct = q.get("price"), q.get("change"), q.get("changesPercentage")
        if price is None:
            return None
        return {
            "ticker": item["short"], "name": item["name"],
            "price": round(price, 4), "change": round(change, 4) if change is not None else None,
            "pct": round(pct, 2) if pct is not None else None,
            "ok": True, "source": "fmp_fallback",
        }
    except Exception as e:
        print(f"[Market] FMP fallback forex ({item['short']}): error inesperado ({type(e).__name__}: {e})")
        return None

def _fetch_fx(item):
    tickers_to_try = [item["ticker"]]
    alt = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X"}
    if item["short"] in alt and alt[item["short"]] != item["ticker"]:
        tickers_to_try.append(alt[item["short"]])
    for ticker in tickers_to_try:
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2:
                continue
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
            chg  = last - prev
            pct  = (chg / prev) * 100
            return {"ticker": item["short"], "name": item["name"], "price": round(last, 4), "change": round(chg, 4), "pct": round(pct, 2), "ok": True}
        except Exception:
            continue
    fallback = _fetch_fx_fmp_fallback(item)
    if fallback:
        return fallback
    return {"ticker": item["short"], "name": item["name"], "ok": False, "error": "Sin datos"}

def get_forex():
    from services.cache import cache, TTL
    cached = cache.get("market:forex")
    if cached: return cached
    results = []
    futures = {yf_executor.submit(_fetch_fx, item): item for item in FOREX_TICKERS}
    for future in futures:
        results.append(future.result())
    results.sort(key=lambda x: [i["short"] for i in FOREX_TICKERS].index(x["ticker"]))
    ok_general = any(r["ok"] for r in results)
    from services.yf_health import log as _yf_log
    _yf_log("forex", ok_general, None if ok_general else "; ".join(r.get("error", "") for r in results if not r["ok"])[:250])
    result = {"data": results, "timestamp": get_timestamp(), "ok": ok_general}
    if ok_general:
        cache.set("market:forex", result, TTL["market"])
    else:
        print(f"[Market] Forex: fallo total, sin cachear. Ejemplo de error: {results[0].get('error') if results else 'N/D'}")
    return result

# ── COMMODITIES

COMMODITY_TICKERS = [
    {"ticker": "GC=F", "name": "Oro",            "short": "GOLD",   "prefix": "$"},
    {"ticker": "SI=F", "name": "Plata",           "short": "SILVER", "prefix": "$"},
    {"ticker": "CL=F", "name": "Petróleo WTI",   "short": "WTI",    "prefix": "$"},
    {"ticker": "BZ=F", "name": "Petróleo Brent", "short": "BRENT",  "prefix": "$"},
    {"ticker": "NG=F", "name": "Gas Natural",     "short": "NATGAS", "prefix": "$"},
    {"ticker": "HG=F", "name": "Cobre",           "short": "COPPER", "prefix": "$"},
]

COMMODITY_FMP_MAP = {
    "GC=F": "GCUSD",  # Oro — confirmado en la documentación de FMP
    "SI=F": "SIUSD",  # Plata
    "CL=F": "CLUSD",  # Petróleo WTI — confirmado
    "BZ=F": "BZUSD",  # Petróleo Brent
    "NG=F": "NGUSD",  # Gas Natural
    "HG=F": "HGUSD",  # Cobre — confirmado
}

def _fetch_commodity_fmp_fallback(item):
    simbolo_fmp = COMMODITY_FMP_MAP.get(item["ticker"])
    if not simbolo_fmp:
        return None
    try:
        from config import settings
        if not settings.fmp_api_key:
            return None
        r = requests.get(
            "https://financialmodelingprep.com/stable/quote",
            params={"symbol": simbolo_fmp, "apikey": settings.fmp_api_key},
            timeout=6,
        )
        if r.status_code != 200:
            print(f"[Market] FMP fallback commodity ({item['short']}): status HTTP {r.status_code}")
            return None
        data = r.json()
        if not data or not isinstance(data, list):
            return None
        q = data[0]
        price, change, pct = q.get("price"), q.get("change"), q.get("changesPercentage")
        if price is None:
            return None
        return {
            "ticker": item["short"], "name": item["name"],
            "price": round(price, 4), "change": round(change, 4) if change is not None else None,
            "pct": round(pct, 2) if pct is not None else None,
            "prefix": item["prefix"], "ok": True, "source": "fmp_fallback",
        }
    except Exception as e:
        print(f"[Market] FMP fallback commodity ({item['short']}): error inesperado ({type(e).__name__}: {e})")
        return None

def _fetch_commodity(item):
    try:
        t    = yf.Ticker(item["ticker"])
        hist = t.history(period="5d", interval="1d").dropna()
        if len(hist) < 2:
            raise ValueError("Sin datos")
        prev = float(hist["Close"].iloc[-2])
        last = float(hist["Close"].iloc[-1])
        chg  = last - prev
        pct  = (chg / prev) * 100
        return {
            "ticker": item["short"],
            "name":   item["name"],
            "price":  round(last, 4),
            "change": round(chg, 4),
            "pct":    round(pct, 2),
            "prefix": item["prefix"],
            "ok":     True
        }
    except Exception as e:
        fallback = _fetch_commodity_fmp_fallback(item)
        if fallback:
            return fallback
        return {"ticker": item["short"], "name": item["name"], "ok": False, "error": str(e)}

def get_commodities():
    from services.cache import cache, TTL
    cached = cache.get("market:commodities")
    if cached: return cached
    results = []
    futures = {yf_executor.submit(_fetch_commodity, item): item for item in COMMODITY_TICKERS}
    for future in futures:
        results.append(future.result())
    results.sort(key=lambda x: [i["short"] for i in COMMODITY_TICKERS].index(x["ticker"]))
    ok_general = any(r["ok"] for r in results)
    from services.yf_health import log as _yf_log
    _yf_log("commodities", ok_general, None if ok_general else "; ".join(r.get("error", "") for r in results if not r["ok"])[:250])
    result = {"data": results, "timestamp": get_timestamp(), "ok": ok_general}
    if ok_general:
        cache.set("market:commodities", result, TTL["market"])
    else:
        print(f"[Market] Commodities: fallo total, sin cachear. Ejemplo de error: {results[0].get('error') if results else 'N/D'}")
    return result

# ── SECTOR

SECTOR_ETFS = [
    {"ticker": "XLK",  "name": "Tecnología"},
    {"ticker": "XLF",  "name": "Financiero"},
    {"ticker": "XLV",  "name": "Salud"},
    {"ticker": "XLE",  "name": "Energía"},
    {"ticker": "XLI",  "name": "Industrial"},
    {"ticker": "XLY",  "name": "Consumo Discr."},
    {"ticker": "XLP",  "name": "Consumo Básico"},
    {"ticker": "XLB",  "name": "Materiales"},
    {"ticker": "XLU",  "name": "Utilities"},
    {"ticker": "XLRE", "name": "Inmobiliario"},
    {"ticker": "XLC",  "name": "Comunicaciones"},
]

def _extract_sector_pct(item, df, period):
    """Extrae el % de cambio de un sector a partir del DataFrame combinado
    de yf.download() (una sola llamada para los 11 sectores, en vez de 11
    objetos Ticker() por separado) — ver conversación 16/07/2026 sobre
    reducir el número de peticiones reales a yfinance."""
    ticker = item["ticker"]
    try:
        if ticker not in df.columns.get_level_values(0):
            raise ValueError("Sin datos en el batch")
        close = df[ticker]["Close"].dropna()
        if period == "1w":
            if len(close) < 6: raise ValueError("Sin datos")
            prev, last = float(close.iloc[-6]), float(close.iloc[-1])
        elif period == "1m":
            if len(close) < 22: raise ValueError("Sin datos")
            prev, last = float(close.iloc[-22]), float(close.iloc[-1])
        else:
            if len(close) < 2: raise ValueError("Sin datos")
            prev, last = float(close.iloc[-2]), float(close.iloc[-1])
        pct = ((last - prev) / prev) * 100
        return {"ticker": ticker, "name": item["name"], "pct": round(pct, 2), "ok": True}
    except Exception as e:
        return {"ticker": ticker, "name": item["name"], "pct": 0, "ok": False, "error": str(e)}

def _fetch_sector(item, period="1d"):
    try:
        t = yf.Ticker(item["ticker"])
        if period == "1d":
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2: raise ValueError("Sin datos")
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
        elif period == "1w":
            hist = t.history(period="1mo", interval="1d").dropna()
            if len(hist) < 6: raise ValueError("Sin datos")
            prev = float(hist["Close"].iloc[-6])
            last = float(hist["Close"].iloc[-1])
        elif period == "1m":
            hist = t.history(period="3mo", interval="1d").dropna()
            if len(hist) < 22: raise ValueError("Sin datos")
            prev = float(hist["Close"].iloc[-22])
            last = float(hist["Close"].iloc[-1])
        else:
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2: raise ValueError("Sin datos")
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
        pct = ((last - prev) / prev) * 100
        return {"ticker": item["ticker"], "name": item["name"], "pct": round(pct, 2), "ok": True}
    except Exception as e:
        return {"ticker": item["ticker"], "name": item["name"], "pct": 0, "ok": False, "error": str(e)}

def get_sectors(period: str = "1d"):
    from services.cache import cache, TTL
    cached = cache.get(f"market:sectors:{period}")
    if cached: return cached

    def _download_and_extract():
        tickers = [item["ticker"] for item in SECTOR_ETFS]
        # Una sola llamada para los 11 sectores en vez de 11 objetos Ticker()
        # separados — threads=False porque ya la lanzamos dentro del pool
        # compartido (yf_executor), no queremos que yf.download abra su
        # propia concurrencia interna por encima de nuestro límite global.
        df = yf.download(tickers=tickers, period="3mo", interval="1d",
                          group_by="ticker", threads=False, progress=False)
        return [_extract_sector_pct(item, df, period) for item in SECTOR_ETFS]

    try:
        results = yf_executor.submit(_download_and_extract).result()
    except Exception as e:
        print(f"[Sectores] Batch download falló ({type(e).__name__}: {e}) — usando fallback ticker a ticker")
        futures = {yf_executor.submit(_fetch_sector, item, period): item for item in SECTOR_ETFS}
        results = [future.result() for future in futures]

    results.sort(key=lambda x: x["pct"], reverse=True)
    ok_general = any(r["ok"] for r in results)
    from services.yf_health import log as _yf_log
    _yf_log("sectors", ok_general, None if ok_general else "; ".join(r.get("error", "") for r in results if not r["ok"])[:250])
    result = {"data": results, "timestamp": get_timestamp(), "ok": ok_general}
    if ok_general:
        cache.set(f"market:sectors:{period}", result, TTL["sectors"])
    return result

# ── VIX

VIX_DIRECT = [
    {"ticker": "^VIX",   "label": "Spot"},
    {"ticker": "^VIX3M", "label": "3 meses"},
    {"ticker": "^VIX6M", "label": "6 meses"},
    {"ticker": "^VIX1Y", "label": "1 año"},
]

def _fetch_vix_point(item):
    try:
        t     = yf.Ticker(item["ticker"])
        hist  = t.history(period="5d").dropna()
        if len(hist) == 0:
            raise ValueError("Sin datos")
        price = round(float(hist["Close"].iloc[-1]), 2)
        return {"label": item["label"], "value": price, "ok": True}
    except Exception:
        return {"label": item["label"], "value": None, "ok": False}

def get_vix_term_structure():
    from services.cache import cache, TTL
    cached = cache.get("market:vix")
    if cached: return cached

    def _download_and_extract():
        tickers = [item["ticker"] for item in VIX_DIRECT]
        df = yf.download(tickers=tickers, period="5d", interval="1d",
                          group_by="ticker", threads=False, progress=False)
        out = []
        for item in VIX_DIRECT:
            try:
                if item["ticker"] not in df.columns.get_level_values(0):
                    raise ValueError("Sin datos en el batch")
                close = df[item["ticker"]]["Close"].dropna()
                if len(close) == 0:
                    raise ValueError("Sin datos")
                price = round(float(close.iloc[-1]), 2)
                out.append({"label": item["label"], "value": price, "ok": True})
            except Exception:
                out.append({"label": item["label"], "value": None, "ok": False})
        return out

    try:
        results = yf_executor.submit(_download_and_extract).result()
    except Exception as e:
        print(f"[VIX] Batch download falló ({type(e).__name__}: {e}) — usando fallback ticker a ticker")
        futures_map = {yf_executor.submit(_fetch_vix_point, item): item for item in VIX_DIRECT}
        results = [future.result() for future in futures_map]

    ordered = []
    for item in VIX_DIRECT:
        match = next((r for r in results if r["label"] == item["label"]), None)
        if match:
            ordered.append(match)

    valid = [r for r in ordered if r["ok"] and r["value"] is not None]
    from services.yf_health import log as _yf_log
    if len(valid) < 2:
        _yf_log("vix", False, "menos de 2 puntos validos del term structure")
        return {"data": [], "timestamp": get_timestamp(), "ok": False, "error": "Sin datos VIX"}
    _yf_log("vix", True, None)

    spot      = valid[0]["value"]
    last      = valid[-1]["value"]
    contango  = round(last - spot, 2)
    structure = "contango" if contango > 0 else "backwardation"

    result = {
        "data":      valid,
        "spot":      spot,
        "contango":  contango,
        "structure": structure,
        "timestamp": get_timestamp(),
        "ok":        True,
    }
    cache.set("market:vix", result, TTL["vix"])
    return result

# ── REDDIT

_BLACKLIST = {
    'A','I','IT','IS','AT','BE','BY','DO','FOR','GO','HE','IF','IN','ME',
    'MY','NO','OF','ON','OR','SO','TO','UP','US','WE','AND','ARE','BUT',
    'CAN','DID','GET','GOT','HAS','HAD','HER','HIM','HIS','HOW','ITS',
    'LET','MAY','NEW','NOT','NOW','OFF','OUR','OUT','OWN','PUT','RUN',
    'SAY','SHE','THE','TOO','TWO','USE','WAS','WAY','WHO','WHY','WITH',
    'YOU','YOLO','LMAO','FOMO','EPS','CEO','IPO','ETF','GDP','FED','ALL',
    'GOOD','BEST','NEXT','LAST','HIGH','LOW','MORE','MUCH','JUST','LIKE',
    'MAKE','MANY','MOST','MOVE','NEED','OVER','SOME','SUCH','THAN','THAT',
    'THEM','THEN','THEY','THIS','WHAT','WHEN','WILL','YEAR','HOLD','SELL',
    'BUY','LONG','SHORT','PUMP','DUMP','MOON','BEAR','BULL','CALLS','PUTS',
    'DD','TA','OTM','ITM','ATM','WSB','RH','TD','AI','ML','API','LOL',
    'WTF','OMG','GG','GE','F','T','X','V','D','C','K','M','R','S',
    'PRE','POST','AH','PM','AM','EST','PST','UTC','USD','EUR','CAD',
    'WELL','WORK','TAKE','GIVE','BACK','COME','WANT','SHOW','ONLY','VERY',
    # Palabras corrientísimas en estos foros que ADEMÁS son tickers reales,
    # así que el filtro por universo no las descarta: TECH (Bio-Techne),
    # OPEN (Opendoor), CASH (Pathward), REAL (The RealReal), TRUE (TrueCar).
    # En un hilo de bolsa, "tech" o "open" casi nunca hablan de esas
    # empresas -- si alguien las menciona de verdad, normalmente escribe
    # "$TECH", y el "$" sigue contando (salta el filtro, ver _extract_tickers).
    'TECH','OPEN','CASH','REAL','TRUE',
}

_UNIVERSO_TICKERS = None


def _universo_tickers() -> set:
    """Universo de tickers REALES conocidos, para separar una mención de
    verdad de una palabra corriente en mayúsculas.

    La lista negra de arriba solo puede enumerar las palabras que a alguien
    se le ocurrieron: sobre títulos reales de Reddit se colaban igualmente
    STOCK, JULY, CAPEX, BREAK, DOWN... Mientras StockTwits funcionaba,
    aportaba tickers buenos y ese ruido quedaba diluido; desde que
    StockTwits está tras un challenge de Cloudflare (verificado en el VPS,
    28/07/2026) Reddit es la única fuente y el ruido pasaría a dominar la
    tabla. Se valida contra el universo que el proyecto ya mantiene, en vez
    de seguir alargando la lista negra a mano para siempre."""
    global _UNIVERSO_TICKERS
    if _UNIVERSO_TICKERS is None:
        universo = set()
        try:
            from sp500_universe import SP500_SECTOR_MAP
            universo |= set(SP500_SECTOR_MAP.keys())
        except Exception as e:
            print(f"[RedditPulse] No se pudo cargar el universo S&P500: {type(e).__name__}: {e}")
        try:
            # WATCHLIST de Options Flow: S&P500 + una selección curada a mano
            # (mega caps, ETFs, nombres de la cartera RSU) -- añade los
            # tickers fuera del índice que sí se comentan en estos subreddits.
            from services.options_service import WATCHLIST
            universo |= set(WATCHLIST)
        except Exception as e:
            print(f"[RedditPulse] No se pudo cargar la watchlist de Options: {type(e).__name__}: {e}")
        _UNIVERSO_TICKERS = universo
    return _UNIVERSO_TICKERS


def _extract_tickers(text: str):
    import re as _re
    found = {}
    universo = _universo_tickers()
    for m in _re.finditer(r'\$([A-Z]{1,6})\b|\b([A-Z]{2,5})\b', text):
        con_dolar = bool(m.group(1))
        t = (m.group(1) or m.group(2) or '').strip()
        if not t or t in _BLACKLIST or not (2 <= len(t) <= 6):
            continue
        # Con "$" delante es inequívocamente un ticker (así se escriben en
        # estos foros); sin "$", solo cuenta si es un ticker real conocido --
        # si el universo no se pudo cargar, no se filtra nada, para no
        # vaciar el widget por un fallo de import.
        if not con_dolar and universo and t not in universo:
            continue
        found[t] = found.get(t, 0) + (2 if con_dolar else 1)
    return sorted(found.items(), key=lambda x: -x[1])[:30]

def _enrich_ticker(ticker, mention_count, max_mentions, st_tickers):
    try:
        tk          = yf.Ticker(ticker)
        info        = tk.fast_info
        price       = getattr(info, 'last_price', None)
        prev        = getattr(info, 'previous_close', None)
        change      = ((price - prev) / prev * 100) if price and prev and prev > 0 else 0.0
        hist        = tk.history(period='10d')
        vol_today   = float(hist['Volume'].iloc[-1]) if len(hist) > 0 else 0
        vol_avg     = float(hist['Volume'].mean())   if len(hist) > 0 else 1
        vol_ratio   = vol_today / vol_avg if vol_avg > 0 else 1.0
        hype_raw    = mention_count / max_mentions
        hype_stars  = max(1, min(5, round(hype_raw * 5)))
        smart_raw   = min(vol_ratio / 2, 1.0)
        smart_stars = max(1, min(5, round(smart_raw * 5)))
        in_st        = ticker in st_tickers
        hype_suffix  = " Reddit Top" if hype_raw > 0.5 else (" StockTwits" if in_st else "")
        smart_suffix = f" Vol ×{vol_ratio:.1f}" if vol_ratio > 1.5 else ""
        if change > 2:      health_num, health_lbl = 85, "Fuerte"
        elif change > 0:    health_num, health_lbl = 65, "Hold"
        elif change > -2:   health_num, health_lbl = 45, "Hold"
        else:               health_num, health_lbl = 30, "Débil"
        return {
            "ticker":      ticker,
            "price":       round(price, 2) if price else None,
            "change":      round(change, 2),
            "buzz":        round(hype_raw * 100),
            "health":      f"{health_num} {health_lbl}",
            "social_hype": "★" * hype_stars + "☆" * (5 - hype_stars) + hype_suffix,
            "smart_money": "★" * smart_stars + "☆" * (5 - smart_stars) + smart_suffix,
            "mentions":    mention_count,
            "ok":          True,
        }
    except Exception:
        return {
            "ticker": ticker, "price": None, "change": 0.0,
            "buzz": mention_count, "health": "50 Hold",
            "social_hype": "★★★☆☆", "smart_money": "★★☆☆☆",
            "mentions": mention_count, "ok": False,
        }

def _get_reddit_token() -> str | None:
    """Token OAuth de Reddit (client_credentials, sin contraseña de
    usuario) -- cacheado 55 min (dura 1h). None si no hay credenciales
    configuradas o si Reddit rechaza la petición (app aún sin aprobar,
    credenciales inválidas...) -- el llamador debe tratarlo igual que
    "Reddit no disponible", sin excepción."""
    from services.cache import cache
    if not settings.reddit_client_id or not settings.reddit_client_secret:
        return None
    cached = cache.get("market:reddit_token")
    if cached:
        return cached
    try:
        from requests.auth import HTTPBasicAuth
        r = requests.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=HTTPBasicAuth(settings.reddit_client_id, settings.reddit_client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": settings.reddit_user_agent},
            timeout=10,
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        if token:
            cache.set("market:reddit_token", token, 3300)
        return token
    except Exception:
        return None

REDDIT_SUBS = ['wallstreetbets', 'stocks', 'investing', 'options', 'StockMarket']


def _fetch_reddit_titles_via_rss():
    """Títulos de los posts "hot" de los subreddits de bolsa, vía el RSS
    público de Reddit.

    Sustituye al scraping con navegador headless (Playwright) que se montó
    el 23/07/2026. Aquel enfoque funcionó mientras el bloqueo de Reddit era
    un *challenge* JavaScript -- que un Chromium real resolvía. Verificado
    en producción el 28/07/2026 que ya NO es así: old.reddit.com devuelve
    HTTP 403 con título "Blocked" y el texto "Your request has been blocked
    due to a network policy" ANTES de servir página alguna. Es un bloqueo de
    RED por IP de datacenter, previo a cualquier JS, así que el navegador no
    aporta nada -- solo ~180MB de imagen y varios segundos por petición.

    El RSS, en cambio, sí responde 200 desde esa misma IP (verificado en el
    propio VPS). Y los 5 subreddits caben en UNA sola petición usando la
    sintaxis multi-subreddit de Reddit (`r/a+b+c`), lo que además esquiva el
    429 que aparecía al pedirlos uno a uno seguidos.

    Devuelve [] si falla -- el llamador ya trata la ausencia sin fabricar
    nada, mismo criterio que el resto del proyecto."""
    import time as _time
    import xml.etree.ElementTree as ET
    # limit=100 (el RSS sirve 25 por defecto): con solo 25 posts salían 3-4
    # tickers con 1-2 menciones cada uno, muy poco para llenar la tabla ahora
    # que StockTwits ya no aporta. Verificado que Reddit lo respeta y devuelve
    # los 100 en la misma petición única.
    url = f"https://www.reddit.com/r/{'+'.join(REDDIT_SUBS)}/hot/.rss?limit=100"
    cabeceras = {"User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/1.0)"}
    try:
        # Reddit limita el ritmo también en el RSS: dos peticiones seguidas
        # devuelven 429 (verificado). Con la caché de 5 min esto no debería
        # darse en producción, pero un reintento cubre la colisión puntual
        # (p.ej. dos workers pidiéndolo a la vez al caducar la caché) sin
        # insistir hasta hacerse pesado -- mismo criterio que el ritmo hacia
        # SEC EDGAR y el backoff de GDELT.
        r = None
        for intento, espera in enumerate((4, 10)):
            r = requests.get(url, headers=cabeceras, timeout=15)
            if r.status_code != 429:
                break
            if intento == 0:
                print(f"[RedditRSS] 429 (límite de ritmo) — reintento en {espera}s")
                _time.sleep(espera)
        if r.status_code != 200:
            print(f"[RedditRSS] HTTP {r.status_code} al pedir {len(REDDIT_SUBS)} subreddits")
            return []
        root = ET.fromstring(r.content)
        ns = {"a": "http://www.w3.org/2005/Atom"}
        titulos = [(e.findtext("a:title", "", ns) or "").strip() for e in root.findall("a:entry", ns)]
        titulos = [t for t in titulos if t]
        print(f"[RedditRSS] {len(titulos)} títulos de r/{'+'.join(REDDIT_SUBS)}")
        return titulos
    except Exception as e:
        print(f"[RedditRSS] Falló: {type(e).__name__}: {e}")
        return []

def get_reddit_pulse():
    from services.cache import cache, TTL
    cached = cache.get("market:reddit")
    if cached: return cached
    import requests as _req
    session = _req.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (compatible; MarketDashboard/2.0)",
        "Accept": "application/json",
    })
    ticker_mentions = {}
    sources = []
    reddit_ok = False
    st_tickers = []
    st_ok = False

    token = _get_reddit_token()
    if token:
        session.headers.update({"Authorization": f"Bearer {token}"})
        for sub in ['wallstreetbets', 'stocks', 'investing', 'options', 'StockMarket']:
            try:
                r = session.get(f'https://oauth.reddit.com/r/{sub}/hot?limit=30&t=day', timeout=10)
                if r.status_code != 200:
                    continue
                sources.append('Reddit')
                reddit_ok = True
                for post in r.json().get('data', {}).get('children', []):
                    p    = post.get('data', {})
                    text = f"{p.get('title','')} {p.get('selftext','')}".upper()
                    for ticker, count in _extract_tickers(text):
                        ticker_mentions[ticker] = ticker_mentions.get(ticker, 0) + count
                break
            except Exception:
                continue

    try:
        r = session.get('https://api.stocktwits.com/api/2/trending/symbols.json', timeout=8)
        if r.status_code == 200:
            symbols = r.json().get('symbols', [])[:20]
            for i, item in enumerate(symbols):
                t = item.get('symbol', '').upper()
                if t and 2 <= len(t) <= 6:
                    st_tickers.append(t)
                    weight = max(1, 20 - i)
                    ticker_mentions[t] = ticker_mentions.get(t, 0) + weight
            if st_tickers:
                sources.append('StockTwits')
                st_ok = True
    except Exception:
        pass

    # Sin OAuth (o si falló), el RSS público es la vía que SÍ responde desde
    # la IP del VPS -- ver _fetch_reddit_titles_via_rss para por qué se
    # abandonó el navegador headless.
    if not reddit_ok:
        titulos = _fetch_reddit_titles_via_rss()
        if titulos:
            sources.append('Reddit')
            for title in titulos:
                for ticker, count in _extract_tickers(title.upper()):
                    ticker_mentions[ticker] = ticker_mentions.get(ticker, 0) + count

    if not ticker_mentions:
        fallback = _reddit_fallback()
        # Cachear también el fallo (TTL más corto que el éxito, ver
        # TTL["reddit_fail"] en cache.py) -- sin esto, cada petición durante
        # una caída de Reddit/StockTwits relanzaba la cadena completa desde
        # cero para CADA usuario que abriera Market, sin ninguna caché
        # compartida de "esto está fallando ahora mismo".
        cache.set("market:reddit", fallback, TTL["reddit_fail"])
        return fallback

    top          = [t for t, _ in sorted(ticker_mentions.items(), key=lambda x: -x[1])[:15]]
    max_mentions = max(ticker_mentions.values())

    results = []
    futures_map = {yf_executor.submit(_enrich_ticker, t, ticker_mentions[t], max_mentions, st_tickers): t for t in top}
    for future in futures_map:
        results.append(future.result())

    results.sort(key=lambda x: -x["buzz"])
    result = {"data": results[:15], "sources": list(set(sources)), "timestamp": get_timestamp(), "ok": True}
    cache.set("market:reddit", result, TTL["reddit"])
    return result

def _reddit_fallback():
    # Antes devolvia 8 tickers fijos con buzz/health/social_hype inventados,
    # marcados "ok": True -- indistinguible de una respuesta real. Ante
    # ausencia de menciones reales, se admite la ausencia en vez de fabricar
    # datos con la misma forma que unos reales (sesion "eliminar fallbacks
    # fabricados", 22/07/2026).
    return {
        "ok": False,
        "error": "Sin menciones detectadas en Reddit/StockTwits en este momento",
        "data": [], "sources": [], "timestamp": get_timestamp(),
    }

# ── RESUMEN DE MERCADO DIARIO (antes "Nightly Briefing") ─────────────────────

BRIEFING_GIST_ID = "715ee0c4e571517c11fa65c5c2376c34"

def get_nightly_briefing():
    from services.cache import cache, TTL
    cached = cache.get("market:briefing")
    if cached: return cached
    import requests as _req
    import json as _json
    try:
        r = _req.get(
            f"https://api.github.com/gists/{BRIEFING_GIST_ID}",
            headers={"Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code != 200:
            raise ValueError(f"HTTP {r.status_code}")
        gist        = r.json()
        files       = gist.get("files", {})
        # IMPORTANTE: coger explícitamente "briefing.json" por nombre, no "el
        # primer fichero" — desde que daily_briefing.py también guarda
        # bias_history.json en el MISMO Gist, coger el primero a ciegas podía
        # devolver el fichero equivocado (alfabéticamente "bias_history.json"
        # va antes que "briefing.json").
        raw_content = files.get("briefing.json", {}).get("content", "")
        if not raw_content:
            raise ValueError("Briefing vacío")
        content   = raw_content
        date_str  = ""
        model_str = ""
        bias_str  = ""
        try:
            parsed    = _json.loads(raw_content)
            content   = parsed.get("text", raw_content)
            date_str  = parsed.get("date", "")
            model_str = parsed.get("model", "")
            bias_str  = parsed.get("bias", "")
            content   = content.replace("\\n", "\n").replace("\\*", "*")
        except Exception:
            pass
        updated_at  = gist.get("updated_at", "")
        updated_str = ""
        if updated_at:
            try:
                import pytz
                utc_dt      = datetime.strptime(updated_at[:19], "%Y-%m-%dT%H:%M:%S")
                madrid      = pytz.timezone("Europe/Madrid")
                mad_dt      = pytz.utc.localize(utc_dt).astimezone(madrid)
                updated_str = mad_dt.strftime("%d %b %Y · %H:%M")
            except Exception:
                updated_str = updated_at[:10]
        result = {"content": content, "date": date_str, "model": model_str, "bias": bias_str, "updated": updated_str, "timestamp": get_timestamp(), "ok": True}
        cache.set("market:briefing", result, TTL["briefing"])
        return result
    except Exception as e:
        return {"content": "", "date": "", "model": "", "updated": "", "timestamp": get_timestamp(), "ok": False, "error": str(e)}

# ── CREDIT SPREADS ────────────────────────────────────────────────────────────

FRED_SERIES = [
    {"id": "BAMLH0A0HYM2", "name": "HY OAS", "label": "High Yield"},
    {"id": "BAMLC0A0CM",   "name": "IG OAS",  "label": "Investment Grade"},
]

# Umbrales calibrados POR SEPARADO para cada serie — antes se usaba el mismo
# corte (>8/>5/>3) para las dos, y como el IG OAS rara vez supera el 2-2.5%
# (ronda 0.6-1% en entornos tranquilos, frente al 3-6% habitual del HY),
# salía "BAJO" prácticamente siempre sin que esa etiqueta significara nada.
# Referencia: media a 10 años del IG OAS ≈ 1.3%; el HY OAS por encima del
# 8% ha coincidido o precedido recesión en EE.UU. de forma consistente desde
# los años 90 (fuente: FRED, ICE BofA).
SPREAD_THRESHOLDS = {
    "BAMLH0A0HYM2": {"bajo": 3.5, "normal": 5.0, "elevado": 8.0},   # HY OAS
    "BAMLC0A0CM":   {"bajo": 1.0, "normal": 1.5, "elevado": 2.5},   # IG OAS
}

def _fetch_fred_series(series_id, api_key, limit=5):
    import requests as _req
    try:
        if api_key:
            url = (
                f"https://api.stlouisfed.org/fred/series/observations"
                f"?series_id={series_id}&api_key={api_key}&file_type=json"
                f"&limit={limit}&sort_order=desc"
            )
            r = _req.get(url, timeout=15)
            if r.status_code == 200:
                obs     = r.json().get("observations", [])
                history = []
                for o in reversed(obs):
                    try:
                        v = float(o["value"])
                        history.append({"date": o["date"], "value": round(v, 2)})
                    except Exception:
                        continue
                return history
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        r   = _req.get(url, timeout=15)
        if r.status_code == 200:
            history = []
            for line in r.text.strip().split("\n")[1:]:
                try:
                    parts = line.split(",")
                    v     = float(parts[1])
                    history.append({"date": parts[0], "value": round(v, 2)})
                except Exception:
                    continue
            return history
    except Exception:
        pass
    return []

# ── CAPE DE SHILLER (Yale) ─────────────────────────────────────────────────────
#
# Umbrales calibrados con referencias históricas reales, no inventados:
# mediana histórica del CAPE desde 1871 ≈ 17; el ratio superó 30 antes de los
# picos de 1929 (~33) y de la burbuja punto-com de 1999-2000 (>40); se mantuvo
# por debajo de 20 antes del crash de 1973-74 y por debajo de 30 antes de la
# crisis de 2008. Fuente: Shiller/Campbell (Yale), literatura académica citada
# en Wikipedia/CIBC/arXiv sobre el CAPE ratio.
CAPE_THRESHOLDS = {"bajo": 15, "normal": 25, "elevado": 30}

def get_shiller_cape() -> dict:
    from services.cache import cache
    cached = cache.get("market:shiller_cape")
    if cached: return cached
    try:
        import pandas as pd
        # La URL clásica (econ.yale.edu/~shiller/data/ie_data.xls, la página
        # personal antigua de Shiller en Yale) está CONGELADA desde septiembre
        # de 2023 — ya no se actualiza. La fuente activa ahora es
        # shillerdata.com, su web oficial actual ("Access ALL DATA FROM
        # PROFESSOR ROBERT J. Shiller"), que aloja el mismo fichero
        # actualizado en un CDN distinto.
        url = "https://img1.wsimg.com/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/907c87f4-4176-4a13-9487-abddeadceb1b/ie_data.xls"

        # Fichero .xls antiguo (no .xlsx) — necesita el motor xlrd. La hoja
        # "Data" tiene varias filas de texto descriptivo antes de la cabecera
        # real, así que se localiza buscando la fila que contiene "CAPE" en
        # vez de asumir un número de fila fijo (más resistente a que Shiller
        # cambie ligeramente el formato con el tiempo).
        raw = pd.read_excel(url, sheet_name="Data", header=None, engine="xlrd", nrows=15)
        header_row = None
        for i in range(len(raw)):
            # Coincidencia EXACTA de celda, no "contiene CAPE" — el título
            # descriptivo del propio fichero también incluye la palabra
            # "CAPE" dentro de una frase ("...and CAPE Ratio"), así que
            # buscar solo "contiene" detectaba esa fila en vez de la cabecera
            # real. Aquí se exige que una celda sea exactamente "CAPE".
            row_vals = raw.iloc[i].astype(str).str.strip().str.upper()
            if (row_vals == "CAPE").any():
                header_row = i
                break
        if header_row is None:
            raise ValueError("No se encontró la fila de cabecera con la celda exacta 'CAPE' en el fichero de Shiller")
        print(f"[ShillerCAPE] Fila de cabecera detectada: {header_row}")

        df = pd.read_excel(url, sheet_name="Data", header=header_row, engine="xlrd")
        df.columns = [str(c).strip() for c in df.columns]
        print(f"[ShillerCAPE] Columnas detectadas ({len(df.columns)}): {list(df.columns)}")

        # NO nos fiamos del NOMBRE de columna — la cabecera real de Shiller
        # está partida en dos filas fusionadas (p.ej. "P/E10 or" en una fila
        # y "CAPE" en la fila de abajo, que pandas lee como si fueran dos
        # columnas distintas al usar una sola fila de cabecera). Esto quiere
        # decir que la columna literalmente llamada "CAPE" puede en realidad
        # ser otra serie distinta (por los valores que da, todo apunta a que
        # es "Excess CAPE Yield", una métrica de rentabilidad, no el ratio).
        # En vez de perseguir el nombre exacto, se prueban las columnas
        # candidatas por NOMBRE y se valida cada una por el VALOR: el CAPE
        # real del S&P 500 nunca ha estado fuera de, aproximadamente, 3-50 en
        # 150 años, así que la columna correcta es la que tenga la mediana
        # dentro de ese rango con suficientes datos (arranca ~10 años después
        # del inicio de la serie, en torno a 1881, así que debe haber varios
        # cientos de valores como mínimo).
        candidate_names = ["CAPE", "P/E10 OR", "P/E10", "TR P/E10 OR", "TR CAPE"]
        cape_col, cape_raw = None, None

        def _try_column(col_name):
            series = pd.to_numeric(df[col_name], errors="coerce")
            valid  = series.dropna()
            if len(valid) < 400:
                return None
            median = float(valid.median())
            print(f"[ShillerCAPE]   Candidata '{col_name}': {len(valid)} valores, mediana={median:.2f}")
            if 3 <= median <= 50:
                return series
            return None

        for name in candidate_names:
            match = next((c for c in df.columns if c.upper() == name), None)
            if match:
                result_series = _try_column(match)
                if result_series is not None:
                    cape_col, cape_raw = match, result_series.reset_index(drop=True)
                    break

        # Último recurso: si ninguna de las columnas "candidatas por nombre"
        # cuadra, se escanean TODAS las columnas numéricas del fichero
        # buscando la que tenga una mediana plausible de CAPE.
        if cape_raw is None:
            print("[ShillerCAPE] Ninguna columna candidata por nombre encajó — escaneando todas las columnas por valor...")
            for col in df.columns:
                result_series = _try_column(col)
                if result_series is not None:
                    cape_col, cape_raw = col, result_series.reset_index(drop=True)
                    break

        if cape_raw is None:
            raise ValueError("No se encontró ninguna columna con valores plausibles de CAPE (mediana 3-50) en el fichero")

        print(f"[ShillerCAPE] Columna elegida tras validar por valor: '{cape_col}'")
        non_null = cape_raw.dropna()
        print(f"[ShillerCAPE] Columna '{cape_col}': {len(non_null)} valores no nulos de {len(cape_raw)} filas totales")
        print(f"[ShillerCAPE] Primeros 5 valores no nulos: {non_null.head(5).tolist()}")
        print(f"[ShillerCAPE] Últimos 5 valores no nulos: {non_null.tail(5).tolist()}")

        # IMPORTANTE: no se parsea la columna "Date" del fichero de Shiller —
        # su formato (AAAA.M) es ambiguo por cómo Excel recorta decimales
        # (1871.1 puede leerse como enero o como octubre según la fuente que
        # lo procese; hasta las herramientas de referencia en R tienen que
        # parchear esto a mano). Los datos son mensuales y consecutivos desde
        # enero de 1871 sin huecos (Shiller interpola específicamente para
        # garantizar esto), así que las fechas se generan por posición
        # secuencial — mucho más fiable que parsear una columna ambigua.
        dates = pd.date_range(start="1871-01-01", periods=len(cape_raw), freq="MS")

        history_full = list(zip(dates, cape_raw))
        history = [
            {"date": d.strftime("%Y-%m-%d"), "cape": round(float(v), 2)}
            for d, v in history_full if pd.notna(v)
        ]
        if not history:
            raise ValueError("Sin valores de CAPE válidos tras el parseo")

        cape_values = [h["cape"] for h in history]
        current   = history[-1]["cape"]
        mean_all  = round(sum(cape_values) / len(cape_values), 2)
        std_all   = round(float(pd.Series(cape_values).std()), 2)

        # Comprobación de cordura: el CAPE real nunca ha estado fuera de,
        # aproximadamente, 3-50 en 150 años de histórico. Si sale de ese
        # rango, algo del parseo está mal (columna equivocada, desalineación
        # de filas...) — mejor avisarlo claramente que servir un número falso
        # con la misma confianza que uno real.
        plausible = 3 <= current <= 50
        if not plausible:
            print(f"[ShillerCAPE] AVISO: CAPE actual = {current}, fuera del rango histórico plausible "
                  f"(3-50) — probable error de parseo (columna o fila equivocada). Revisar columnas arriba.")

        if current > CAPE_THRESHOLDS["elevado"]: level, level_color = "MUY ALTO", "#f23645"
        elif current > CAPE_THRESHOLDS["normal"]: level, level_color = "ELEVADO", "#ffb800"
        elif current > CAPE_THRESHOLDS["bajo"]:   level, level_color = "NORMAL",  "#90ee90"
        else:                                      level, level_color = "BAJO",    "#00ffad"

        result = {
            "ok":             True,
            "current":        current,
            "date":           history[-1]["date"],
            "mean":           mean_all,
            "std":            std_all,
            "deviation_pct":  round((current - mean_all) / mean_all * 100, 1),
            "level":          level,
            "level_color":    level_color,
            "thresholds":     CAPE_THRESHOLDS,
            "history":        history,
            "plausible":      plausible,
            "timestamp":      get_timestamp(),
        }
        # 24h — dato mensual, no hace falta refrescar más a menudo. El fichero
        # completo (150+ años) tampoco es barato de descargar/parsear cada vez.
        # Si el valor no parece plausible, NO se cachea 24h — así el próximo
        # intento (tras arreglar el parseo) no se queda atascado con el dato
        # malo hasta mañana.
        cache.set("market:shiller_cape", result, 86400 if plausible else 60)
        return result
    except Exception as e:
        print(f"[ShillerCAPE] ERROR: {type(e).__name__}: {e}")
        return {"ok": False, "error": str(e)}


def get_credit_spreads():
    from services.cache import cache, TTL
    cached = cache.get("market:spreads")
    if cached: return cached
    from config import settings
    api_key = getattr(settings, "fred_api_key", "")
    results = []
    for series in FRED_SERIES:
        # 260 sesiones (~1 año) para poder pintar el histórico real en el
        # gráfico — antes solo se pedían 5 puntos (bastaban para el valor
        # actual/anterior, pero no para un gráfico con sentido).
        history = _fetch_fred_series(series["id"], api_key, limit=260)
        th = SPREAD_THRESHOLDS.get(series["id"], {"bajo": 3.5, "normal": 5.0, "elevado": 8.0})
        if len(history) >= 2:
            current = history[-1]["value"]
            prev    = history[-2]["value"]
            change  = round(current - prev, 2)
            if current > th["elevado"]: level, level_color = "ALTO",    "#f23645"
            elif current > th["normal"]: level, level_color = "ELEVADO", "#ffb800"
            elif current > th["bajo"]:   level, level_color = "NORMAL",  "#90ee90"
            else:                        level, level_color = "BAJO",    "#00ffad"
            results.append({
                "id": series["id"], "name": series["name"], "label": series["label"],
                "current": current, "prev": prev, "change": change,
                "date": history[-1]["date"], "level": level, "level_color": level_color,
                "thresholds": th, "history": history[-260:],
                "ok": True,
            })
        else:
            results.append({
                "id": series["id"], "name": series["name"], "label": series["label"],
                "current": None, "thresholds": th, "history": [], "ok": False,
            })
    result = {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}
    cache.set("market:spreads", result, TTL["spreads"])
    return result

def get_fed_macro() -> dict:
    from services.cache import cache
    cached = cache.get('market:fed_macro')
    if cached: return cached

    import requests
    from concurrent.futures import ThreadPoolExecutor

    def _fred_csv(series_id):
        try:
            r = requests.get(
                f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}',
                timeout=10,
                headers={'User-Agent': 'RSU Terminal contact@rsu-terminal.com'}
            )
            if r.status_code != 200: return []
            lines = r.text.strip().split(chr(10))[1:]
            out = []
            for line in lines:
                parts = line.split(',')
                if len(parts) == 2 and parts[1] not in ('', '.'):
                    try:
                        out.append((parts[0], float(parts[1])))
                    except ValueError:
                        pass
            return out
        except Exception:
            return []

    def _fetch_balance():
        try:
            walcl = _fred_csv('WALCL')
            tga   = _fred_csv('WTREGEN')
            rrp   = _fred_csv('RRPONTSYD')
            if not walcl: return {}
            total    = walcl[-1][1]
            prev     = walcl[-2][1] if len(walcl) > 1 else total
            prev_mo  = walcl[-5][1] if len(walcl) > 5 else total
            w_change = total - prev
            m_change = total - prev_mo
            tga_val  = tga[-1][1] if tga else 0
            rrp_val  = (rrp[-1][1] * 1000) if rrp else 0
            net_liq  = total - tga_val - rrp_val
            if w_change < -10000:  status, color = 'QT',      '#f23645'
            elif w_change > 10000: status, color = 'QE',      '#00ffad'
            else:                  status, color = 'ESTABLE',  '#ffb800'
            history = [{'date': d, 'value': round(v / 1e6, 3)} for d, v in walcl[-24:]]
            def fmt(v): return f'${v/1e6:.2f}T' if v else 'N/D'
            return {
                'status': status, 'color': color,
                'total': fmt(total), 'total_num': total,
                'tga': fmt(tga_val), 'rrp': fmt(rrp_val),
                'net_liq': fmt(net_liq), 'net_liq_num': net_liq,
                'w_change': round(w_change / 1000, 1),
                'm_change': round(m_change / 1000, 1),
                'date': walcl[-1][0], 'history': history,
            }
        except Exception:
            return {}

    def _fetch_yields():
        try:
            yields = {}
            syms = {'Y3M': '^IRX', 'Y5Y': '^FVX', 'Y10Y': '^TNX', 'Y30Y': '^TYX'}
            for key, sym in syms.items():
                try:
                    h = yf.Ticker(sym).history(period='5d')
                    if not h.empty:
                        yields[key] = round(float(h['Close'].iloc[-1]), 3)
                except Exception:
                    pass
            # 2Y via yfinance — símbolo correcto
            for sym_2y in ['^TU', 'SHY']:
                try:
                    h2 = yf.Ticker(sym_2y).history(period='5d')
                    if not h2.empty:
                        v = float(h2['Close'].iloc[-1])
                        if 1.0 < v < 10.0:
                            yields['Y2Y'] = round(v, 3)
                            break
                except Exception:
                    pass
            # Sin fallback sintético: si ninguna fuente real trae el 2Y, se
            # deja ausente -- antes se aproximaba con Y3M + 0.47 (offset
            # histórico fijo), un número inventado con la misma forma que
            # uno real.

            dgs3m = _fred_csv('DGS3MO')
            if dgs3m and dgs3m[-1][1] > 0:
                yields['Y3M'] = round(dgs3m[-1][1], 3)

            # .get(key) sin default -- un yield ausente debe llegar como
            # None al JSON final, no como 0 (antes .get(key, 0) fabricaba
            # un "0%" silencioso para cualquier fuente que hubiera fallado).
            y10 = yields.get('Y10Y')
            y2  = yields.get('Y2Y')
            y3m = yields.get('Y3M')
            y5  = yields.get('Y5Y')
            y30 = yields.get('Y30Y')
            sp10_2  = round(y10 - y2, 3) if y10 and y2 else None
            sp10_3m = round(y10 - y3m, 3) if y10 and y3m else None
            dgs10 = _fred_csv('DGS10')
            history = [{'date': d, 'value': v} for d, v in dgs10[-90:]] if dgs10 else []
            return {
                'Y3M': y3m, 'Y2Y': y2, 'Y5Y': y5, 'Y10Y': y10, 'Y30Y': y30,
                'spread_10_2': sp10_2, 'spread_10_3m': sp10_3m,
                'inverted': sp10_2 is not None and sp10_2 < 0,
                'history': history,
            }
        except Exception:
            return {}

    def _fetch_indicators():
        try:
            series = {
                'fed_funds':    'FEDFUNDS',
                'cpi_yoy':      'CPIAUCSL',
                'unemployment': 'UNRATE',
                'core_pce':     'PCEPI',
            }
            out = {}
            for key, sid in series.items():
                data = _fred_csv(sid)
                if len(data) >= 13:
                    cur    = data[-1][1]
                    prev   = data[-2][1]
                    prev_y = data[-13][1]
                    yoy    = round((cur - prev_y) / prev_y * 100, 2) if prev_y else None
                    out[key] = {'value': cur, 'chg': round(cur - prev, 3), 'yoy': yoy, 'date': data[-1][0]}
                elif len(data) >= 2:
                    cur  = data[-1][1]
                    prev = data[-2][1]
                    out[key] = {'value': cur, 'chg': round(cur - prev, 3), 'yoy': None, 'date': data[-1][0]}
            return out
        except Exception:
            return {}

    try:
        f_b = yf_executor.submit(_fetch_balance)
        f_y = yf_executor.submit(_fetch_yields)
        f_i = yf_executor.submit(_fetch_indicators)
        balance    = f_b.result()
        yields     = f_y.result()
        indicators = f_i.result()
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    result = {
        'ok':         True,
        'balance':    balance,
        'yields':     yields,
        'indicators': indicators,
        'timestamp':  get_timestamp(),
    }
    cache.set('market:fed_macro', result, 1800)
    return result

# ── LIQUIDEZ (NET LIQUIDITY + M2 + OVERLAY SPX) ───────────────────────────────

def get_liquidity() -> dict:
    """
    Sigue la liquidez del sistema mediante dos métricas complementarias:
    - Net Liquidity = WALCL - TGA - RRP (táctica, semanal, mueve mercados en semanas/meses)
    - M2 Money Supply (semanal pero estructural, contexto de fondo de varios trimestres/años)
    Ambas se superponen contra el SPX para visualizar la correlación histórica.
    """
    from services.cache import cache
    cached = cache.get('market:liquidity')
    if cached: return cached

    import requests
    from concurrent.futures import ThreadPoolExecutor

    def _fred_csv(series_id, timeout=12):
        try:
            r = requests.get(
                f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}',
                timeout=timeout,
                headers={'User-Agent': 'RSU Terminal contact@rsu-terminal.com'}
            )
            if r.status_code != 200:
                print(f"[Liquidity] FRED {series_id}: status HTTP {r.status_code} (esperado 200)")
                return []
            lines = r.text.strip().split(chr(10))[1:]
            out = []
            for line in lines:
                parts = line.split(',')
                if len(parts) == 2 and parts[1] not in ('', '.'):
                    try:
                        out.append((parts[0], float(parts[1])))
                    except ValueError:
                        pass
            if not out:
                print(f"[Liquidity] FRED {series_id}: respuesta 200 OK pero 0 filas parseables (¿cambió el formato del CSV?)")
            return out
        except requests.exceptions.Timeout:
            print(f"[Liquidity] FRED {series_id}: TIMEOUT tras {timeout}s — problema de red/conectividad hacia fred.stlouisfed.org")
            return []
        except Exception as e:
            print(f"[Liquidity] FRED {series_id}: error inesperado ({type(e).__name__}: {e})")
            return []

    def _fetch_net_liquidity():
        try:
            walcl = _fred_csv('WALCL')
            tga   = _fred_csv('WTREGEN')
            rrp   = _fred_csv('RRPONTSYD')
            print(f"[Liquidity] WALCL: {len(walcl)} puntos · WTREGEN: {len(tga)} puntos · RRPONTSYD: {len(rrp)} puntos")
            if not walcl:
                print("[Liquidity] WALCL vacío — FRED no respondió o devolvió 0 filas parseables para esta serie. Net Liquidity quedará en N/D.")
                return {}

            # Indexar TGA y RRP por fecha para alinear correctamente con WALCL
            # (las tres series pueden no publicarse exactamente el mismo día)
            tga_map = dict(tga)
            rrp_map = dict(rrp)

            def _nearest(series_map, target_date, dates_sorted):
                if target_date in series_map:
                    return series_map[target_date]
                # buscar la fecha más cercana hacia atrás (último valor conocido)
                for d in reversed(dates_sorted):
                    if d <= target_date and d in series_map:
                        return series_map[d]
                return 0

            tga_dates = sorted(tga_map.keys())
            rrp_dates = sorted(rrp_map.keys())

            history = []
            for date, walcl_val in walcl[-104:]:  # ~2 años de histórico semanal
                tga_val = _nearest(tga_map, date, tga_dates)
                rrp_val = _nearest(rrp_map, date, rrp_dates) * 1000  # RRP viene en miles de millones distinta escala
                net_liq = walcl_val - tga_val - rrp_val
                history.append({'date': date, 'value': round(net_liq / 1e6, 3)})  # en Trillones

            current  = history[-1]['value'] if history else None
            prev     = history[-2]['value'] if len(history) > 1 else current
            prev_mo  = history[-5]['value'] if len(history) > 5 else current
            w_change = round((current - prev) * 1000, 1) if current is not None else None       # en Billions
            m_change = round((current - prev_mo) * 1000, 1) if current is not None else None     # en Billions

            return {
                'current': current,
                'w_change': w_change,
                'm_change': m_change,
                'date': history[-1]['date'] if history else None,
                'history': history,
            }
        except Exception as e:
            import traceback
            print(f"[Liquidity] _fetch_net_liquidity ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            return {}

    def _fetch_m2():
        try:
            m2 = _fred_csv('WM2NS')
            if not m2: return {}
            # WM2NS viene en miles de millones ($B); convertir a Trillones para consistencia visual
            history = [{'date': d, 'value': round(v / 1000, 3)} for d, v in m2[-104:]]
            current = history[-1]['value'] if history else None
            prev    = history[-2]['value'] if len(history) > 1 else current
            prev_y  = history[-53]['value'] if len(history) > 53 else current  # ~1 año atrás (semanal)
            yoy_pct = round((current - prev_y) / prev_y * 100, 2) if prev_y else None
            return {
                'current': current,
                'chg': round(current - prev, 3) if current is not None else None,
                'yoy_pct': yoy_pct,
                'date': history[-1]['date'] if history else None,
                'history': history,
            }
        except Exception as e:
            import traceback
            print(f"[Liquidity] _fetch_m2 ERROR: {type(e).__name__}: {e}")
            traceback.print_exc()
            return {}

    def _fetch_spx_overlay():
        try:
            spx_hist = yf.Ticker('^GSPC').history(period='2y', interval='1wk')
            if spx_hist.empty: return []
            out = []
            for idx, row in spx_hist.iterrows():
                out.append({'date': idx.strftime('%Y-%m-%d'), 'value': round(float(row['Close']), 2)})
            return out
        except Exception:
            return []

    try:
        f_nl  = yf_executor.submit(_fetch_net_liquidity)
        f_m2  = yf_executor.submit(_fetch_m2)
        f_spx = yf_executor.submit(_fetch_spx_overlay)
        net_liquidity = f_nl.result()
        m2            = f_m2.result()
        spx           = f_spx.result()
    except Exception as e:
        return {'ok': False, 'error': str(e)}

    if not net_liquidity and not m2:
        return {'ok': False, 'error': 'No se pudo obtener ningún dato de liquidez (FRED no respondió)'}

    # Correlación simple entre Net Liquidity y SPX, alineando por fecha más cercana
    # (no por coincidencia exacta de string — WALCL se publica miércoles, el SPX semanal
    # de yfinance puede anclar en lunes, así que una intersección exacta casi siempre da 0)
    correlation = None
    try:
        if net_liquidity.get('history') and spx:
            spx_vals    = {s['date']: s['value'] for s in spx}
            spx_dates   = sorted(spx_vals.keys())

            def _nearest_spx(target_date):
                best = None
                for d in spx_dates:
                    if d <= target_date:
                        best = d
                    else:
                        break
                return spx_vals.get(best) if best else None

            xs, ys = [], []
            for h in net_liquidity['history']:
                spx_v = _nearest_spx(h['date'])
                if spx_v is not None:
                    xs.append(h['value'])
                    ys.append(spx_v)

            n = len(xs)
            if n >= 10:
                mean_x, mean_y = sum(xs) / n, sum(ys) / n
                cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
                std_x = (sum((x - mean_x) ** 2 for x in xs)) ** 0.5
                std_y = (sum((y - mean_y) ** 2 for y in ys)) ** 0.5
                if std_x > 0 and std_y > 0:
                    correlation = round(cov / (std_x * std_y), 3)
    except Exception:
        correlation = None

    result = {
        'ok':            True,
        'net_liquidity': net_liquidity,
        'm2':            m2,
        'spx':           spx,
        'correlation':   correlation,
        'timestamp':     get_timestamp(),
    }

    # Solo cacheamos si AMBAS series principales tuvieron éxito. Un fallo parcial
    # (p.ej. WALCL con timeout puntual de red) no debe quedar "atascado" en caché
    # 30 minutos mostrando N/D — mejor reintentar en la próxima petición.
    if net_liquidity.get('current') is not None and m2.get('current') is not None:
        cache.set('market:liquidity', result, 1800)
    else:
        print("[Liquidity] Resultado parcial (Net Liquidity o M2 sin datos) — NO se cachea, se reintentará en la próxima petición")

    return result

# ── MARKET BREADTH ────────────────────────────────────────────────────────────

def _sanitize_breadth(obj):
    import math
    if isinstance(obj, dict):
        return {k: _sanitize_breadth(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize_breadth(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

SECTOR_ETFS_BREADTH = ['XLK', 'XLF', 'XLV', 'XLE', 'XLY', 'XLU', 'XLI', 'XLB', 'XLP', 'XLRE', 'XLC']

def _check_sector_above_sma50(etf_sym: str):
    try:
        etf_h = yf.Ticker(etf_sym).history(period="100d")
        if len(etf_h) >= 50:
            price = float(etf_h['Close'].iloc[-1])
            sma50 = float(etf_h['Close'].rolling(50).mean().iloc[-1])
            if sma50 == sma50:  # not NaN
                return price > sma50
    except Exception:
        pass
    return None

def _check_sectors_above_sma50_batch(tickers: list) -> list:
    """Version batcheada de _check_sector_above_sma50 — 1 sola llamada
    yf.download() para los 11 ETFs en vez de 11 objetos Ticker()
    separados. Devuelve una lista en el mismo orden que `tickers`, con
    True/False/None (None = sin datos suficientes, igual que antes)."""
    try:
        df = yf.download(tickers=tickers, period="100d", interval="1d",
                          group_by="ticker", threads=False, progress=False)
        out = []
        for sym in tickers:
            try:
                if sym not in df.columns.get_level_values(0):
                    out.append(None)
                    continue
                close = df[sym]["Close"].dropna()
                if len(close) < 50:
                    out.append(None)
                    continue
                price = float(close.iloc[-1])
                sma50 = float(close.rolling(50).mean().iloc[-1])
                out.append(price > sma50 if sma50 == sma50 else None)
            except Exception:
                out.append(None)
        return out
    except Exception as e:
        print(f"[MarketBreadth] Batch download falló ({type(e).__name__}: {e}) — usando fallback ticker a ticker")
        return [_check_sector_above_sma50(sym) for sym in tickers]


def get_market_breadth():
    """
    Amplitud de Mercado (unificado): SMA50/200, Golden/Death Cross, RSI(14) del
    SPY + Oscilador McClellan REAL (EMA19-EMA39 sobre avance/declive neto real
    del NYSE, no un proxy del propio índice) + % REAL del S&P 500 sobre su
    SMA50 (desde el scan nocturno de 500 tickers, no una muestra de 11 ETFs) +
    los datos de la Línea A/D (fusionados aquí — antes vivían en un widget
    aparte, /market/ad-line, que se mantiene por compatibilidad pero ya no se
    usa desde el frontend).
    """
    from services.cache import cache, TTL
    cached = cache.get("market:breadth")
    if cached:
        return cached

    try:
        spy_hist = yf.Ticker("SPY").history(period="2y")
        if len(spy_hist) < 50:
            raise ValueError("Histórico insuficiente")

        # Eliminar filas con Close NaN (puede pasar con datos parciales del día en curso,
        # especialmente fuera de horario de mercado) — si no se filtra, rolling().mean()
        # puede devolver NaN en la última posición aunque haya "suficientes" filas en total.
        spy_hist = spy_hist.dropna(subset=['Close'])
        if len(spy_hist) < 50:
            raise ValueError("Histórico insuficiente tras filtrar valores nulos")

        snap = spy_trend_snapshot(spy_hist['Close'])
        current, sma50, sma200 = snap["price"], snap["sma50"], snap["sma200"]

        # Verificación explícita: si por cualquier motivo el cálculo dio NaN,
        # tratarlo igual que un fallo de datos en vez de propagar NaN con ok=True
        # (NaN sobrevive silenciosamente la sanitización si no se detecta aquí primero).
        if current != current or sma50 != sma50:  # x != x es True solo si x es NaN
            raise ValueError("Cálculo de precio/SMA50 produjo NaN — datos de yfinance incompletos")

        deltas = spy_hist['Close'].diff()
        gains  = deltas.where(deltas > 0, 0).rolling(14).mean()
        losses = (-deltas.where(deltas < 0, 0)).rolling(14).mean()
        rs_last = gains.iloc[-1] / losses.iloc[-1] if losses.iloc[-1] not in (0, None) else None
        rsi = float(100 - (100 / (1 + rs_last))) if rs_last is not None and rs_last == rs_last else 50.0

        # ── AMPLITUD REAL — derivada del propio universo S&P 500 (scan nocturno) ──
        # Antes el McClellan y la Línea A/D dependían de ^ADV/^DEC de Yahoo, una
        # fuente que lleva tiempo devolviendo datos poco fiables (por eso salía
        # marcado [PROXY SPY] casi siempre). Ahora se calculan, cuando hay datos
        # suficientes, directamente sobre el histórico de precios de los 500
        # tickers que el Scanner ya descarga cada noche — es una fuente propia
        # y verificable, no depende de que un ticker compuesto externo funcione.
        breadth_hist = []
        try:
            from services.scanner_service import get_breadth_history
            breadth_hist = get_breadth_history()
        except Exception as e:
            print(f"[MarketBreadth] Scanner breadth_history no disponible: {e}")

        mcclellan, mcclellan_state = None, "N/D"
        mcclellan_week_ago = None
        pct_sma50_week_ago = None
        nh_nl_week_ago = None
        ad_history_out, current_adv, current_dec, current_net = [], 0, 0, 0
        ad_ok, ad_real_data, ad_source = False, False, "n/d"

        WEEK_LOOKBACK = 5  # sesiones de mercado ≈ 1 semana natural

        if len(breadth_hist) >= 40:
            net_series = pd.Series([h["advances"] - h["declines"] for h in breadth_hist])
            mc_series  = mcclellan_series(net_series)

            mcclellan = round(float(mc_series.iloc[-1]), 1)
            mcclellan_state = "ALCISTA" if mcclellan > 70 else ("BAJISTA" if mcclellan < -70 else "NEUTRO")
            if len(mc_series) > WEEK_LOOKBACK:
                mcclellan_week_ago = round(float(mc_series.iloc[-1 - WEEK_LOOKBACK]), 1)

            pct_series = [h.get("pct_above_sma50") for h in breadth_hist]
            if len(pct_series) > WEEK_LOOKBACK and pct_series[-1 - WEEK_LOOKBACK] is not None:
                pct_sma50_week_ago = pct_series[-1 - WEEK_LOOKBACK]

            nh_nl_series = [h.get("new_highs", 0) - h.get("new_lows", 0) for h in breadth_hist]
            if len(nh_nl_series) > WEEK_LOOKBACK:
                nh_nl_week_ago = nh_nl_series[-1 - WEEK_LOOKBACK]

            # Línea A/D acumulada para el gráfico — alinea cada sesión del
            # breadth_history con el cierre de SPY de ese mismo día
            spy_by_date = {idx.strftime("%Y-%m-%d"): float(row) for idx, row in spy_hist['Close'].items()}
            cum = 0.0
            for h in breadth_hist:
                net = h["advances"] - h["declines"]
                cum += net
                ad_history_out.append({
                    "date": h["date"],
                    "ad":   round(cum / 1000, 2),
                    "spy":  spy_by_date.get(h["date"]),
                    "adv":  h["advances"],
                    "dec":  h["declines"],
                    "net":  net,
                })
            last = breadth_hist[-1]
            current_adv = last["advances"]
            current_dec = last["declines"]
            current_net = current_adv - current_dec
            ad_ok = True
            ad_real_data = True
            # BUG CORREGIDO: antes esto compartía el mismo booleano ad_real_data=True
            # que la rama de abajo (Yahoo ^ADV/^DEC, NYSE de verdad, ~2800 valores),
            # y el frontend mostraba siempre "[NYSE REAL]" sin distinguir — pero esta
            # rama usa el scan nocturno del S&P 500 (525 tickers), no NYSE completo.
            # Detectado comparando avanzan+declinan (~486) contra "tickers evaluados"
            # de % S&P500 (~487) en la propia UI — prácticamente idénticos, confirma
            # que es el mismo universo, mal etiquetado como NYSE.
            ad_source = "sp500"

        else:
            # Fallback: Scanner sin histórico suficiente todavía (recién
            # desplegado — breadth_history tarda unos ~40 días de scans
            # nocturnos en acumularse) → cae al ^ADV/^DEC de Yahoo de siempre.
            print(f"[MarketBreadth] breadth_history insuficiente ({len(breadth_hist)} sesiones, "
                  f"hacen falta 40+) — usando fallback ^ADV/^DEC de Yahoo")
            ad_data = get_advance_decline()
            ad_ok = ad_data.get("ok", False)
            ad_real_data = ad_data.get("real_data", False)
            # get_advance_decline() ya no fabrica un proxy sintético -- o
            # devuelve datos reales de NYSE (^ADV/^DEC), o ok:False.
            ad_source = "nyse_yahoo" if ad_real_data else "n/d"
            ad_history_out = ad_data.get("history", [])
            current_adv = ad_data.get("current_adv", 0)
            current_dec = ad_data.get("current_dec", 0)
            current_net = ad_data.get("current_net", 0)
            if ad_data.get("ok") and len(ad_data.get("history", [])) >= 39:
                net_series = pd.Series([h["net"] for h in ad_data["history"]])
                mcclellan  = round(float(mcclellan_series(net_series).iloc[-1]), 1)
                mcclellan_state = "ALCISTA" if mcclellan > 70 else ("BAJISTA" if mcclellan < -70 else "NEUTRO")

        # ── % REAL del S&P 500 sobre SMA50 + New Highs/New Lows — mismo scan nocturno ──
        pct_above_sma50, sectors_checked, breadth_source = None, 0, "n/d"
        new_highs, new_lows, nh_nl, nh_nl_source = None, None, None, "n/d"
        try:
            from services.scanner_service import get_universe_stocks
            universe = get_universe_stocks()
            flagged = [v for v in universe.values() if v.get("above_sma50") is not None]
            if flagged:
                above = sum(1 for v in flagged if v["above_sma50"])
                pct_above_sma50 = round(above / len(flagged) * 100, 1)
                sectors_checked = len(flagged)
                breadth_source = "sp500"
            # NH-NL: preferir el universo ampliado (S&P 500 + Russell 2000, el
            # mismo breadth_hist que ya alimenta McClellan/ABI/A-D más arriba)
            # en vez de recalcular solo sobre las 500 grandes — a diferencia de
            # "% sobre SMA50" (que es explícitamente "del S&P 500" por nombre),
            # NH-NL se presenta como amplitud general, así que debe beneficiarse
            # de la misma cobertura ampliada que el resto de este widget.
            if breadth_hist:
                ultimo = breadth_hist[-1]
                new_highs = ultimo.get("new_highs")
                new_lows  = ultimo.get("new_lows")
                if new_highs is not None and new_lows is not None:
                    nh_nl = new_highs - new_lows
                    nh_nl_source = "sp500_r2k"
            if nh_nl is None and universe:
                new_highs = sum(1 for v in universe.values() if v.get("new_high"))
                new_lows  = sum(1 for v in universe.values() if v.get("new_low"))
                nh_nl = new_highs - new_lows
                nh_nl_source = "sp500"
        except Exception as e:
            print(f"[MarketBreadth] Scanner no disponible para % S&P500/NH-NL: {e}")

        # Fallback: si el Scanner todavía no ha corrido con el campo above_sma50
        # (primera vez tras el despliegue, antes del próximo scan nocturno de las
        # 22:15 UTC) o el Gist no está disponible, cae al proxy de 11 ETFs sectoriales
        # para no dejar el widget vacío — pero se marca claramente como proxy.
        # NH-NL no tiene un proxy razonable con solo 11 ETFs (la muestra es demasiado
        # pequeña para "nuevos máximos/mínimos"), así que ahí simplemente se deja en
        # null y el frontend lo muestra como N/D en vez de inventar un número.
        if pct_above_sma50 is None:
            above_count, total_checked = 0, 0
            results = yf_executor.submit(_check_sectors_above_sma50_batch, SECTOR_ETFS_BREADTH).result()
            for r in results:
                if r is not None:
                    total_checked += 1
                    if r:
                        above_count += 1
            pct_above_sma50 = round((above_count / total_checked * 100) if total_checked > 0 else 50.0, 1)
            sectors_checked = total_checked
            breadth_source = "etf_proxy"

        # ── Variaciones semanales (delta vs ~5 sesiones atrás) ──────────────────
        pct_sma50_wow = round(pct_above_sma50 - pct_sma50_week_ago, 1) if (pct_above_sma50 is not None and pct_sma50_week_ago is not None) else None
        nh_nl_wow     = (nh_nl - nh_nl_week_ago) if (nh_nl is not None and nh_nl_week_ago is not None) else None
        mcclellan_wow = round(mcclellan - mcclellan_week_ago, 1) if (mcclellan is not None and mcclellan_week_ago is not None) else None

        # ── Absolute Breadth Index (ABI) ────────────────────────────────────────
        # |avances - declives| / (avances + declives) — a diferencia del McClellan
        # (direccional: dice si el mercado tiende a subir o bajar), el ABI NO dice
        # hacia dónde va el mercado, solo CUÁNTA dispersión/actividad interna hay.
        # Lecturas muy altas (muchas acciones subiendo Y muchas bajando a la vez)
        # suelen asociarse a momentos de capitulación o cambio de régimen — Fosback
        # (creador del indicador) encontró que lecturas extremas han precedido
        # subidas de precio a 3-12 meses vista. Reutiliza current_adv/current_dec
        # y ad_history_out ya calculados arriba (mismo dato que el McClellan real y
        # la Línea A/D) — cero llamadas de red adicionales, funciona igual con datos
        # reales (breadth_source="sp500") o con el fallback de Yahoo.
        abi, abi_wow, abi_state = None, None, "N/D"
        total_issues = current_adv + current_dec
        if total_issues > 0:
            abi = round(abs(current_adv - current_dec) / total_issues * 100, 1)
            abi_state = "ALTA DISPERSIÓN" if abi >= 40 else ("BAJA ACTIVIDAD" if abi <= 15 else "NORMAL")
            if ad_history_out and len(ad_history_out) > WEEK_LOOKBACK:
                h_semana = ad_history_out[-1 - WEEK_LOOKBACK]
                total_semana = (h_semana.get("adv") or 0) + (h_semana.get("dec") or 0)
                if total_semana > 0:
                    abi_semana = abs(h_semana["adv"] - h_semana["dec"]) / total_semana * 100
                    abi_wow = round(abi - abi_semana, 1)

        golden_cross = (sma200 is not None) and (sma50 > sma200)
        above_sma200 = (sma200 is not None) and (current > sma200)

        result = {
            "ok": True,
            "price": round(current, 2),
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2) if sma200 is not None else None,
            "above_sma50": current > sma50,
            "above_sma200": above_sma200,
            "golden_cross": golden_cross,
            "rsi": round(rsi, 1),
            "rsi_state": "SOBRECOMPRA" if rsi > 70 else ("SOBREVENTA" if rsi < 30 else "NEUTRAL"),
            "trend": "ALCISTA" if (sma200 is not None and sma50 > sma200) else ("BAJISTA" if sma200 is not None else "N/D"),
            "strength": "FUERTE" if (sma200 is not None and current > sma50 and current > sma200) else "DÉBIL",
            "mcclellan": mcclellan,
            "mcclellan_state": mcclellan_state,
            "mcclellan_wow": mcclellan_wow,
            "abi": abi,
            "abi_wow": abi_wow,
            "abi_state": abi_state,
            "pct_above_sma50": pct_above_sma50,
            "pct_above_sma50_wow": pct_sma50_wow,
            "sectors_checked": sectors_checked,
            "breadth_source": breadth_source,  # "sp500" (real, 500 tickers) | "etf_proxy" (fallback, 11 ETFs)
            "new_highs": new_highs,
            "new_lows": new_lows,
            "nh_nl": nh_nl,
            "nh_nl_source": nh_nl_source,  # "sp500_r2k" (real, S&P 500 + Russell 2000) | "sp500" (fallback, solo S&P 500)
            "nh_nl_wow": nh_nl_wow,
            # Datos de Línea A/D fusionados (antes en el widget separado /market/ad-line)
            "ad_ok": ad_ok,
            "ad_real_data": ad_real_data,
            "ad_source": ad_source,  # "sp500" (scan nocturno, 525 tickers) | "nyse_yahoo" (^ADV/^DEC real) | "proxy_spy"
            "ad_history": ad_history_out,
            "current_adv": current_adv,
            "current_dec": current_dec,
            "current_net": current_net,
            "timestamp": get_timestamp(),
        }
        result = _sanitize_breadth(result)
        cache.set("market:breadth", result, TTL["market"])
        return result

    except Exception as e:
        print(f"[MarketBreadth] ERROR: {type(e).__name__}: {e}")
        return {
            "ok": False, "error": str(e),
            "price": None, "sma50": None, "sma200": None,
            "above_sma50": False, "above_sma200": False, "golden_cross": False,
            "rsi": 50.0, "rsi_state": "N/D", "trend": "N/D", "strength": "N/D",
            "mcclellan": None, "mcclellan_state": "N/D", "mcclellan_wow": None,
            "abi": None, "abi_wow": None, "abi_state": "N/D", "pct_above_sma50": None,
            "pct_above_sma50_wow": None,
            "sectors_checked": 0, "breadth_source": "n/d",
            "new_highs": None, "new_lows": None, "nh_nl": None, "nh_nl_source": "n/d", "nh_nl_wow": None,
            "ad_ok": False, "ad_real_data": False, "ad_source": "n/d", "ad_history": [],
            "current_adv": 0, "current_dec": 0, "current_net": 0,
            "timestamp": get_timestamp(),
        }


def get_advance_decline():
    """
    Línea Advance/Decline del NYSE (^ADV / ^DEC vía Yahoo Finance).

    Solo se usa como fallback dentro de get_market_breadth() cuando el
    scan nocturno de Scanner (breadth_hist, amplitud real del S&P 500)
    todavía no tiene 40+ sesiones acumuladas -- en la práctica, casi
    nunca (Scanner ya guarda 150 días). Pensado para el arranque en frío
    justo después de desplegar.

    ^ADV/^DEC están CAÍDOS en Yahoo (verificado 24/07/2026, 404 en yfinance
    para ambos, con y sin distintas variantes de símbolo) -- se deja el
    intento por si Yahoo los restaura algún día (código inofensivo si
    sigue fallando), pero SIN fallback sintético: antes, si Yahoo fallaba,
    se fabricaba un avance/declive falso a partir del % diario de SPY
    (adv = 250 + ratio*3000, clamped) marcado ok:True -- mismo patrón de
    "número fabricado con la misma forma que uno real" ya eliminado en
    Reddit Pulse/DXY/Yield 2Y/RS Rating CANSLIM (ver auditoría 22/07/2026).
    Sin datos reales, se devuelve ok:False -- el frontend ya lo maneja
    (la sección Línea A/D simplemente no se pinta si ad_ok es False).
    """
    from services.cache import cache, TTL
    cached = cache.get("market:ad_line")
    if cached:
        return cached

    ad_history = []

    # ── Capa 1: datos reales NYSE ──────────────────────────────────────────
    try:
        adv_hist = yf.Ticker("^ADV").history(period="6mo")
        dec_hist = yf.Ticker("^DEC").history(period="6mo")
        spy_hist = yf.Ticker("SPY").history(period="6mo")

        if len(adv_hist) > 20 and len(dec_hist) > 20:
            adv_hist.index = adv_hist.index.normalize()
            dec_hist.index = dec_hist.index.normalize()
            spy_hist.index = spy_hist.index.normalize()

            common_dates = adv_hist.index.intersection(dec_hist.index).intersection(spy_hist.index)
            common_dates = common_dates.sort_values()

            if len(common_dates) > 20:
                cumulative = 0
                for dt in common_dates:
                    adv_val = float(adv_hist.loc[dt, 'Close'])
                    dec_val = float(dec_hist.loc[dt, 'Close'])
                    net = adv_val - dec_val
                    cumulative += net
                    ad_history.append({
                        "date": dt.strftime('%Y-%m-%d'),
                        "ad": round(cumulative / 1000, 2),
                        "adv": int(adv_val),
                        "dec": int(dec_val),
                        "net": int(net),
                        "spy": round(float(spy_hist.loc[dt, 'Close']), 2),
                    })

                current = ad_history[-1]
                result = {
                    "ok": True,
                    "real_data": True,
                    "history": ad_history[-90:],
                    "current_ad": current["ad"],
                    "current_adv": current["adv"],
                    "current_dec": current["dec"],
                    "current_net": current["net"],
                    "spy_current": current["spy"],
                    "spy_change": round(current["spy"] - ad_history[-2]["spy"], 2) if len(ad_history) >= 2 else 0,
                    "timestamp": get_timestamp(),
                }
                result = _sanitize_breadth(result)
                cache.set("market:ad_line", result, TTL["market"])
                return result
    except Exception as e:
        print(f"[ADLine] Capa 1 (datos reales NYSE) falló: {type(e).__name__}: {e}")

    # Sin datos reales (^ADV/^DEC caídos) -- ok:False, no se fabrica un
    # avance/declive sintético. Ver docstring de la función.
    return {
        "ok": False, "real_data": False, "history": [],
        "current_ad": 0, "current_adv": 0, "current_dec": 0, "current_net": 0,
        "spy_current": 0, "spy_change": 0, "timestamp": get_timestamp(),
    }

# ── VIX NIVELES (gauge + histórico diario) ────────────────────────────────────

def get_vix_levels():
    """
    VIX spot con gráfico diario de 6 meses y gauge de 5 zonas:
    <12 Complacencia · 12-20 Normal · 20-25 Precaución · 25-35 Miedo · 35+ Pánico
    """
    from services.cache import cache, TTL
    cached = cache.get("market:vix_levels")
    if cached:
        return cached

    try:
        hist = yf.Ticker("^VIX").history(period="6mo")
        if hist.empty:
            raise ValueError("Sin histórico de VIX")

        current = float(hist['Close'].iloc[-1])
        prev    = float(hist['Close'].iloc[-2]) if len(hist) > 1 else current
        change  = current - prev
        pct     = (change / prev * 100) if prev else 0

        if current >= 35:    zone, color, label = "PÁNICO",       "#f23645", "Capitulación / posible suelo extremo"
        elif current >= 25:  zone, color, label = "MIEDO",        "#ff6b35", "Estrés de mercado elevado"
        elif current >= 20:  zone, color, label = "PRECAUCIÓN",   "#ff9800", "Volatilidad por encima de lo normal"
        elif current >= 12:  zone, color, label = "NORMAL",       "#00ffad", "Rango habitual de mercado tranquilo"
        else:                zone, color, label = "COMPLACENCIA", "#3b82f6", "Volatilidad muy baja — posible exceso de confianza"

        history = [
            {"date": d.strftime("%Y-%m-%d"), "value": round(float(v), 2)}
            for d, v in zip(hist.index[-130:], hist['Close'].iloc[-130:])
        ]

        result = {
            "ok": True,
            "current": round(current, 2),
            "prev": round(prev, 2),
            "change": round(change, 2),
            "pct": round(pct, 2),
            "zone": zone,
            "zone_color": color,
            "zone_label": label,
            "history": history,
            "timestamp": get_timestamp(),
        }
        result = _sanitize_breadth(result)
        cache.set("market:vix_levels", result, TTL["vix"])
        return result
    except Exception as e:
        return {"ok": False, "error": str(e), "timestamp": get_timestamp()}


# ── CRIPTOMONEDAS ──────────────────────────────────────────────────────────────

CRYPTO_TICKERS = [
    {"ticker": "BTC-USD", "symbol": "BTC", "name": "Bitcoin"},
    {"ticker": "ETH-USD", "symbol": "ETH", "name": "Ethereum"},
    {"ticker": "BNB-USD", "symbol": "BNB", "name": "BNB"},
    {"ticker": "SOL-USD", "symbol": "SOL", "name": "Solana"},
    {"ticker": "XRP-USD", "symbol": "XRP", "name": "XRP"},
    {"ticker": "ADA-USD", "symbol": "ADA", "name": "Cardano"},
]

def _fetch_crypto(item):
    try:
        hist = yf.Ticker(item["ticker"]).history(period="2d")
        if len(hist) >= 2:
            current = float(hist['Close'].iloc[-1])
            prev    = float(hist['Close'].iloc[-2])
            change  = current - prev
            pct     = (change / prev * 100) if prev else 0
            return {
                "ticker": item["symbol"], "name": item["name"],
                "price": round(current, 4 if current < 1 else 2),
                "change": round(change, 4 if current < 1 else 2),
                "pct": round(pct, 2),
                "ok": True,
            }
    except Exception:
        pass
    return {"ticker": item["symbol"], "name": item["name"], "ok": False}

def _extract_crypto_pct(item, df):
    try:
        if item["ticker"] not in df.columns.get_level_values(0):
            raise ValueError("Sin datos en el batch")
        close = df[item["ticker"]]["Close"].dropna()
        if len(close) < 2:
            raise ValueError("Sin datos")
        current = float(close.iloc[-1])
        prev = float(close.iloc[-2])
        change = current - prev
        pct = (change / prev * 100) if prev else 0
        return {
            "ticker": item["symbol"], "name": item["name"],
            "price": round(current, 4 if current < 1 else 2),
            "change": round(change, 4 if current < 1 else 2),
            "pct": round(pct, 2),
            "ok": True,
        }
    except Exception:
        return {"ticker": item["symbol"], "name": item["name"], "ok": False}


def get_crypto_prices():
    from services.cache import cache, TTL
    cached = cache.get("market:crypto")
    if cached:
        return cached

    def _download_and_extract():
        tickers = [item["ticker"] for item in CRYPTO_TICKERS]
        df = yf.download(tickers=tickers, period="2d", interval="1d",
                          group_by="ticker", threads=False, progress=False)
        return [_extract_crypto_pct(item, df) for item in CRYPTO_TICKERS]

    try:
        results = yf_executor.submit(_download_and_extract).result()
    except Exception as e:
        print(f"[Cripto] Batch download falló ({type(e).__name__}: {e}) — usando fallback ticker a ticker")
        results = list(yf_executor.map(_fetch_crypto, CRYPTO_TICKERS))

    result = {"ok": True, "data": results, "timestamp": get_timestamp()}
    result = _sanitize_breadth(result)
    cache.set("market:crypto", result, TTL["market"])
    return result


# Stablecoins excluidas del ranking de fuerza relativa — su % de cambio no
# representa momentum real (solo ruido de depeg), y contaminarían el top.
_STABLECOIN_SYMBOLS = {
    "usdt", "usdc", "dai", "busd", "tusd", "fdusd", "usde",
    "pyusd", "usdd", "frax", "gusd", "usdp", "eurt", "eurc",
}

def get_crypto_relative_strength(top_n: int = 5):
    """Top N criptomonedas por fuerza relativa (variación % a 30 días) sobre el
    universo REAL del mercado cripto — top 250 por capitalización vía CoinGecko
    (misma fuente que btc_stratum_service.py), no una lista curada a mano.
    """
    from services.cache import cache, TTL
    cache_key = f"market:crypto_rs:{top_n}"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        import requests
        r = requests.get(
            "https://api.coingecko.com/api/v3/coins/markets",
            params={
                "vs_currency": "usd",
                "order": "market_cap_desc",
                "per_page": 250,
                "page": 1,
                "price_change_percentage": "7d,30d",
                "sparkline": "false",
            },
            timeout=10,
        )
        data = r.json()
        if not isinstance(data, list):
            raise ValueError(f"Respuesta inesperada de CoinGecko: {data}")

        candidates = []
        for c in data:
            symbol = (c.get("symbol") or "").lower()
            if symbol in _STABLECOIN_SYMBOLS:
                continue
            pct_30d = c.get("price_change_percentage_30d_in_currency")
            price   = c.get("current_price")
            if pct_30d is None or price is None:
                continue
            # Filtro de precio: excluye memecoins/micro-caps de céntimo (ej. SHIB,
            # PEPE) que suelen dominar los rankings de % sin ser posiciones serias.
            if price <= 1.0:
                continue
            candidates.append({
                "ticker":          symbol.upper(),
                "name":            c.get("name", symbol.upper()),
                "price":           price,
                "pct_30d":         round(pct_30d, 2),
                "pct_7d":          round(c.get("price_change_percentage_7d_in_currency") or 0, 2),
                "market_cap_rank": c.get("market_cap_rank"),
            })

        ranked = sorted(candidates, key=lambda x: x["pct_30d"], reverse=True)
        for i, item in enumerate(ranked, start=1):
            item["rank"] = i

        result = {
            "ok":            True,
            "data":          ranked[:top_n],
            "universe_size": len(candidates),
            "source":        "CoinGecko · Top 250 por market cap",
            "timestamp":     get_timestamp(),
        }
    except Exception as e:
        result = {"ok": False, "error": str(e), "data": []}

    result = _sanitize_breadth(result)
    cache.set(cache_key, result, TTL["market"])
    return result


def get_crypto_fear_greed():
    """Crypto Fear & Greed Index vía alternative.me (independiente del Fear & Greed de acciones)."""
    from services.cache import cache, TTL
    cached = cache.get("market:crypto_fg")
    if cached:
        return cached

    import requests
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=2", timeout=8)
        if r.status_code == 200:
            data = r.json().get("data", [])
            if data:
                current = data[0]
                value = int(current["value"])
                classification = current["value_classification"]
                yesterday = int(data[1]["value"]) if len(data) > 1 else value
                result = {
                    "ok": True,
                    "value": value,
                    "classification": classification,
                    "yesterday": yesterday,
                    "change": value - yesterday,
                    "source": "alternative.me",
                    "timestamp": get_timestamp(),
                }
                cache.set("market:crypto_fg", result, TTL["market"])
                return result
    except Exception:
        pass

    return {
        "ok": False, "value": 50, "classification": "Neutral",
        "yesterday": 50, "change": 0, "source": "N/D", "timestamp": get_timestamp(),
    }

# ── COMPOSICIÓN SECTORIAL (breadth por sector, reutilizando el universo RS/RW) ─

def get_sector_composition():
    """
    Composición sectorial TEMÁTICA (29 cestas: BIOTECH, SEMIS, MAG7, SPACE...),
    con un universo de tickers propio (no limitado al S&P 500). Implementación
    completa en services/thematic_service.py — aquí solo se delega para no
    duplicar lógica ni cambiar el endpoint que ya consume el frontend.
    """
    from services.thematic_service import get_thematic_composition
    return get_thematic_composition()