from datetime import datetime, timedelta, timezone
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

def get_timestamp():
    cet = timezone(timedelta(hours=1))
    return datetime.now(cet).strftime('%H:%M:%S')

# ── ÍNDICES ───────────────────────────────────────────────────────────────────

INDICES = [
    {"ticker": "^GSPC", "name": "S&P 500",     "short": "SPX"},
    {"ticker": "^NDX",  "name": "Nasdaq 100",  "short": "NDX"},
    {"ticker": "^DJI",  "name": "Dow Jones",   "short": "DJI"},
    {"ticker": "^RUT",  "name": "Russell 2000","short": "RUT"},
    {"ticker": "^VIX",  "name": "VIX",         "short": "VIX"},
]

def _fetch_ticker(item):
    try:
        t = yf.Ticker(item["ticker"])
        hist = t.history(period="2d", interval="1d")
        if len(hist) < 2:
            raise ValueError("Sin datos suficientes")
        prev  = float(hist["Close"].iloc[-2])
        last  = float(hist["Close"].iloc[-1])
        chg   = last - prev
        pct   = (chg / prev) * 100
        return {"ticker": item["short"], "name": item["name"], "price": round(last, 2), "change": round(chg, 2), "pct": round(pct, 2), "ok": True}
    except Exception as e:
        return {"ticker": item["short"], "name": item["name"], "price": None, "change": None, "pct": None, "ok": False, "error": str(e)}

def get_indices():
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch_ticker, item): item for item in INDICES}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: ["SPX","NDX","DJI","RUT","VIX"].index(x["ticker"]))
    return {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}

# ── FEAR & GREED ──────────────────────────────────────────────────────────────

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
            return {"score": score, "rating": rating, "prev": prev, "week_ago": week, "timestamp": get_timestamp(), "ok": True}
    except Exception:
        pass
    try:
        t     = yf.Ticker("^VIX")
        hist  = t.history(period="2d")
        vix   = float(hist["Close"].iloc[-1]) if len(hist) else 20
        score = max(0, min(100, int(100 - (vix - 10) * 3.5)))
        if score >= 75:   rating = "Extreme Greed"
        elif score >= 55: rating = "Greed"
        elif score >= 45: rating = "Neutral"
        elif score >= 25: rating = "Fear"
        else:             rating = "Extreme Fear"
        return {"score": score, "rating": rating + " (est.)", "prev": score, "week_ago": score, "timestamp": get_timestamp(), "ok": True}
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

def _fetch_fx(item):
    tickers_to_try = [item["ticker"]]
    alt = {"EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X", "USD/CHF": "USDCHF=X", "AUD/USD": "AUDUSD=X"}
    if item["short"] in alt and alt[item["short"]] != item["ticker"]:
        tickers_to_try.append(alt[item["short"]])
    for ticker in tickers_to_try:
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d")
            hist = hist.dropna()
            if len(hist) < 2:
                continue
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
            chg  = last - prev
            pct  = (chg / prev) * 100
            return {"ticker": item["short"], "name": item["name"], "price": round(last, 4), "change": round(chg, 4), "pct": round(pct, 2), "ok": True}
        except Exception:
            continue
    return {"ticker": item["short"], "name": item["name"], "ok": False, "error": "Sin datos"}

def get_forex():
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_fetch_fx, item): item for item in FOREX_TICKERS}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: [i["short"] for i in FOREX_TICKERS].index(x["ticker"]))
    return {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}

# ── COMMODITIES ───────────────────────────────────────────────────────────────

COMMODITY_TICKERS = [
    {"ticker": "GC=F", "name": "Oro",            "short": "GOLD",   "prefix": "$"},
    {"ticker": "SI=F", "name": "Plata",           "short": "SILVER", "prefix": "$"},
    {"ticker": "CL=F", "name": "Petróleo WTI",   "short": "WTI",    "prefix": "$"},
    {"ticker": "BZ=F", "name": "Petróleo Brent", "short": "BRENT",  "prefix": "$"},
    {"ticker": "NG=F", "name": "Gas Natural",     "short": "NATGAS", "prefix": "$"},
    {"ticker": "HG=F", "name": "Cobre",           "short": "COPPER", "prefix": "$"},
]

def _fetch_commodity(item):
    try:
        t    = yf.Ticker(item["ticker"])
        hist = t.history(period="2d", interval="1d")
        if len(hist) < 2:
            raise ValueError("Sin datos")
        prev = float(hist["Close"].iloc[-2])
        last = float(hist["Close"].iloc[-1])
        chg  = last - prev
        pct  = (chg / prev) * 100
        return {"ticker": item["short"], "name": item["name"], "price": round(last, 4), "change": round(chg, 4), "pct": round(pct, 2), "prefix": item["prefix"], "ok": True}
    except Exception as e:
        return {"ticker": item["short"], "name": item["name"], "ok": False, "error": str(e)}

def get_commodities():
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_fetch_commodity, item): item for item in COMMODITY_TICKERS}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: [i["short"] for i in COMMODITY_TICKERS].index(x["ticker"]))
    return {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}
    # ── SECTOR PERFORMANCE ────────────────────────────────────────────────────────

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

def _fetch_sector(item):
    try:
        t    = yf.Ticker(item["ticker"])
        hist = t.history(period="5d", interval="1d").dropna()
        if len(hist) < 2:
            raise ValueError("Sin datos")
        prev = float(hist["Close"].iloc[-2])
        last = float(hist["Close"].iloc[-1])
        pct  = ((last - prev) / prev) * 100
        return {"ticker": item["ticker"], "name": item["name"], "pct": round(pct, 2), "ok": True}
    except Exception as e:
        return {"ticker": item["ticker"], "name": item["name"], "pct": 0, "ok": False, "error": str(e)}

def get_sectors():
    results = []
    with ThreadPoolExecutor(max_workers=11) as ex:
        futures = {ex.submit(_fetch_sector, item): item for item in SECTOR_ETFS}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: x["pct"], reverse=True)
    return {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}

    # ── CALENDARIO ECONÓMICO ──────────────────────────────────────────────────────

EVENT_TRANSLATIONS = {
    # Ya existentes...
    "Nonfarm Payrolls": "Nóminas No Agrícolas",
    "Unemployment Rate": "Tasa de Desempleo",
    "CPI": "IPC (Inflación)",
    "Core CPI": "IPC Subyacente",
    "PPI": "IPP (Precios Productor)",
    "GDP": "PIB",
    "GDP Growth Rate": "Crecimiento del PIB",
    "Retail Sales": "Ventas al Por Menor",
    "ISM Manufacturing PMI": "PMI Manufacturero ISM",
    "ISM Services PMI": "PMI Servicios ISM",
    "Fed Interest Rate Decision": "Decisión de Tipos de la Fed",
    "FOMC Statement": "Declaración FOMC",
    "FOMC Minutes": "Actas FOMC",
    "Initial Jobless Claims": "Solicitudes de Desempleo",
    "Building Permits": "Permisos de Construcción",
    "Housing Starts": "Inicio de Viviendas",
    "Trade Balance": "Balanza Comercial",
    "Crude Oil Inventories": "Inventarios de Petróleo",
    "Natural Gas Storage": "Almacenamiento Gas Natural",
    "ECB Interest Rate Decision": "Decisión Tipos BCE",
    "ECB Press Conference": "Rueda de Prensa BCE",
    "ADP Nonfarm Employment": "Empleo ADP",
    "JOLTS Job Openings": "Vacantes JOLTS",
    "Michigan Consumer Sentiment": "Sentimiento Michigan",
    "CB Consumer Confidence": "Confianza Consumidor CB",
    "Durable Goods Orders": "Pedidos Bienes Duraderos",
    "PCE Price Index": "Índice Precios PCE",
    "Core PCE": "PCE Subyacente",
    # Nuevas entradas UK y globales
    "Revised Industrial Production": "Producción Industrial Revisada",
    "Industrial Production": "Producción Industrial",
    "Manufacturing Production": "Producción Manufacturera",
    "Construction Output": "Producción en Construcción",
    "Index of Services": "Índice de Servicios",
    "Consumer Inflation Expectations": "Expectativas de Inflación",
    "M2 Money Supply": "Oferta Monetaria M2",
    "New Loans": "Nuevos Préstamos",
    "ECOFIN Meetings": "Reunión ECOFIN",
    "CB Leading Index": "Índice Adelantado CB",
    "UoM Consumer Sentiment": "Sentimiento Consumidor UoM",
    "Prelim UoM Consumer Sentiment": "Sentimiento Consumidor UoM (Prel.)",
    "Prelim UoM Inflation Expectations": "Expectativas Inflación UoM (Prel.)",
    "German Buba President": "Presidente Bundesbank",
    "Buba President": "Presidente Bundesbank",
    "Existing Home Sales": "Ventas Viviendas Existentes",
    "New Home Sales": "Ventas Viviendas Nuevas",
    "Pending Home Sales": "Ventas Viviendas Pendientes",
    "Empire State Manufacturing": "Índice Manufacturero Empire State",
    "Philadelphia Fed": "Fed Filadelfia",
    "Flash Manufacturing PMI": "PMI Manufacturero Flash",
    "Flash Services PMI": "PMI Servicios Flash",
    "Composite PMI": "PMI Compuesto",
    "Current Account": "Cuenta Corriente",
    "Consumer Price Index": "Índice de Precios al Consumo",
    "Producer Price Index": "Índice de Precios al Productor",
    "Import Prices": "Precios de Importación",
    "Export Prices": "Precios de Exportación",
    "Capacity Utilization": "Utilización de Capacidad",
    "Average Hourly Earnings": "Salario por Hora Promedio",
    "Labor Force Participation": "Tasa de Participación Laboral",
    "Continuing Jobless Claims": "Solicitudes Continuas de Desempleo",
    "Wholesale Inventories": "Inventarios al Por Mayor",
    "Business Inventories": "Inventarios Empresariales",
    "Factory Orders": "Órdenes de Fábrica",
    "Chicago PMI": "PMI de Chicago",
    "Richmond Fed": "Fed Richmond",
    "Dallas Fed": "Fed Dallas",
    "Kansas Fed": "Fed Kansas",
}

def translate_event(name):
    for en, es in EVENT_TRANSLATIONS.items():
        if en.lower() in name.lower():
            return es
    return name

def get_economic_calendar():
    import requests
    events = []
    try:
        now = datetime.now(timezone(timedelta(hours=1))).replace(tzinfo=None)
        r = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            for item in data:
                try:
                    date_str  = item.get('date', '')
                    event_dt  = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S') if date_str else now
                    if event_dt.date() < now.date():
                        continue
                    if event_dt.weekday() >= 5:
                        continue
                    impact = item.get('impact', 'Low')
                    if impact not in ['High', 'Medium', 'Low']:
                        impact = 'Low'
                    try:
                        import pytz
                        et     = pytz.timezone('America/New_York')
                        madrid = pytz.timezone('Europe/Madrid')
                        et_dt  = et.localize(event_dt)
                        mad_dt = et_dt.astimezone(madrid)
                        hour   = mad_dt.hour
                        minute = mad_dt.minute
                        event_dt = mad_dt.replace(tzinfo=None)
                    except Exception:
                        hour   = (event_dt.hour + 6) % 24
                        minute = event_dt.minute
                    if event_dt.date() == now.date():
                        date_display = "HOY"
                        date_color   = "#00ffad"
                    elif event_dt.date() == (now + timedelta(days=1)).date():
                        date_display = "MAÑANA"
                        date_color   = "#3b82f6"
                    else:
                        date_display = event_dt.strftime('%d %b').upper()
                        date_color   = "#888"
                    events.append({
                        "date":         date_display,
                        "date_color":   date_color,
                        "time":         f"{hour:02d}:{minute:02d}",
                        "event":        translate_event(item.get('title', 'Evento')),
                        "impact":       impact,
                        "country":      item.get('country', 'US').upper()[:2],
                        "actual":       item.get('actual', '-') or '-',
                        "forecast":     item.get('forecast', '-') or '-',
                        "previous":     item.get('previous', '-') or '-',
                    })
                except Exception:
                    continue
    except Exception as e:
        return {"data": [], "timestamp": get_timestamp(), "ok": False, "error": str(e)}

    events = events[:20]
    return {"data": events, "timestamp": get_timestamp(), "ok": True}
   # ── VIX TERM STRUCTURE ────────────────────────────────────────────────────────

VIX_CHAIN = [
    {"ticker": "^VIX",   "label": "VIX Spot",  "months": 0},
    {"ticker": "VIXY",   "label": "1M (VIXY)", "months": 1},
    {"ticker": "VIXM",   "label": "5M (VIXM)", "months": 5},
    {"ticker": "VXZ",    "label": "5M (VXZ)",  "months": 5},
    {"ticker": "SVXY",   "label": "Inv 1M",    "months": 1},
    {"ticker": "^VIX3M", "label": "VIX 3M",   "months": 3},
    {"ticker": "^VIX6M", "label": "VIX 6M",   "months": 6},
    {"ticker": "^VIX1Y", "label": "VIX 1Y",   "months": 12},
]

VIX_DIRECT = [
    {"ticker": "^VIX",   "label": "Spot"},
    {"ticker": "^VIX3M", "label": "3 meses"},
    {"ticker": "^VIX6M", "label": "6 meses"},
    {"ticker": "^VIX1Y", "label": "1 año"},
]

def _fetch_vix_point(item):
    try:
        t    = yf.Ticker(item["ticker"])
        hist = t.history(period="5d").dropna()
        if len(hist) == 0:
            raise ValueError("Sin datos")
        price = round(float(hist["Close"].iloc[-1]), 2)
        return {"label": item["label"], "value": price, "ok": True}
    except Exception:
        return {"label": item["label"], "value": None, "ok": False}

def get_vix_term_structure():
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures_map = {ex.submit(_fetch_vix_point, item): item for item in VIX_DIRECT}
        for future in futures_map:
            results.append(future.result())

    results.sort(key=lambda x: VIX_DIRECT[[i["ticker"] for i in VIX_DIRECT].index(
        next(i["ticker"] for i in VIX_DIRECT if i["label"] == x["label"])
    )]["label"] if x["ok"] else "z")

    ordered = []
    for item in VIX_DIRECT:
        match = next((r for r in results if r["label"] == item["label"]), None)
        if match:
            ordered.append(match)

    valid = [r for r in ordered if r["ok"] and r["value"] is not None]

    if len(valid) < 2:
        return {"data": [], "timestamp": get_timestamp(), "ok": False, "error": "Sin datos VIX"}

    spot      = valid[0]["value"]
    last      = valid[-1]["value"]
    contango  = round(last - spot, 2)
    structure = "contango" if contango > 0 else "backwardation"

    return {
        "data":      valid,
        "spot":      spot,
        "contango":  contango,
        "structure": structure,
        "timestamp": get_timestamp(),
        "ok":        True,
    }