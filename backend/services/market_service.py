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
        return {"ticker": item["short"], "name": item["name"], "price": None, "change": None, "pct": None, "ok": False, "error": str(e)}

def get_indices():
    from services.cache import cache, TTL
    cached = cache.get("market:indices")
    if cached: return cached
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch_ticker, item): item for item in INDICES}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: ["SPX","NDX","DJI","RUT","VIX"].index(x["ticker"]))
    result = {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}
    cache.set("market:indices", result, TTL["market"])
    return result

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
        hist  = t.history(period="5d").dropna()
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
    return {"ticker": item["short"], "name": item["name"], "ok": False, "error": "Sin datos"}

def get_forex():
    from services.cache import cache, TTL
    cached = cache.get("market:forex")
    if cached: return cached
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_fetch_fx, item): item for item in FOREX_TICKERS}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: [i["short"] for i in FOREX_TICKERS].index(x["ticker"]))
    result = {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}
    cache.set("market:forex", result, TTL["market"])
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
        return {"ticker": item["short"], "name": item["name"], "ok": False, "error": str(e)}

def get_commodities():
    from services.cache import cache, TTL
    cached = cache.get("market:commodities")
    if cached: return cached
    results = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_fetch_commodity, item): item for item in COMMODITY_TICKERS}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: [i["short"] for i in COMMODITY_TICKERS].index(x["ticker"]))
    result = {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}
    cache.set("market:commodities", result, TTL["market"])
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
    results = []
    with ThreadPoolExecutor(max_workers=11) as ex:
        futures = {ex.submit(_fetch_sector, item, period): item for item in SECTOR_ETFS}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: x["pct"], reverse=True)
    result = {"data": results, "timestamp": get_timestamp(), "ok": any(r["ok"] for r in results)}
    cache.set(f"market:sectors:{period}", result, TTL["sectors"])
    return result

# ── CALENDARIO

EVENT_TRANSLATIONS = {
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
    "Revised Industrial Production": "Producción Industrial Revisada",
    "Industrial Production": "Producción Industrial",
    "Manufacturing Production": "Producción Manufacturera",
    "Construction Output": "Producción en Construcción",
    "Index of Services": "Índice de Servicios",
    "Consumer Inflation Expectations": "Expectativas de Inflación",
    "M2 Money Supply": "Oferta Monetaria M2",
    "New Loans": "Nuevos Préstamos",
    "CB Leading Index": "Índice Adelantado CB",
    "UoM Consumer Sentiment": "Sentimiento Consumidor UoM",
    "Prelim UoM Consumer Sentiment": "Sentimiento Consumidor UoM (Prel.)",
    "Prelim UoM Inflation Expectations": "Expectativas Inflación UoM (Prel.)",
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
    from services.cache import cache, TTL
    cached = cache.get("market:calendar")
    if cached: return cached
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
                    date_str = item.get('date', '')
                    event_dt = datetime.strptime(date_str[:19], '%Y-%m-%dT%H:%M:%S') if date_str else now
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
                        "date":       date_display,
                        "date_color": date_color,
                        "time":       f"{hour:02d}:{minute:02d}",
                        "event":      translate_event(item.get('title', 'Evento')),
                        "impact":     impact,
                        "country":    item.get('country', 'US').upper()[:2],
                        "actual":     item.get('actual', '-') or '-',
                        "forecast":   item.get('forecast', '-') or '-',
                        "previous":   item.get('previous', '-') or '-',
                    })
                except Exception:
                    continue
    except Exception as e:
        return {"data": [], "timestamp": get_timestamp(), "ok": False, "error": str(e)}
    result = {"data": events[:20], "timestamp": get_timestamp(), "ok": True}
    cache.set("market:calendar", result, TTL["calendar"])
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
    results = []
    with ThreadPoolExecutor(max_workers=4) as ex:
        futures_map = {ex.submit(_fetch_vix_point, item): item for item in VIX_DIRECT}
        for future in futures_map:
            results.append(future.result())

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
}

def _extract_tickers(text: str):
    import re as _re
    found = {}
    for m in _re.finditer(r'\$([A-Z]{1,6})\b|\b([A-Z]{2,5})\b', text):
        t = (m.group(1) or m.group(2) or '').strip()
        if t and t not in _BLACKLIST and 2 <= len(t) <= 6:
            found[t] = found.get(t, 0) + (2 if m.group(1) else 1)
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

    for sub in ['wallstreetbets', 'stocks', 'investing', 'options', 'StockMarket']:
        try:
            r = session.get(f'https://www.reddit.com/r/{sub}/hot.json?limit=30&t=day', timeout=10)
            if r.status_code != 200:
                continue
            sources.append('Reddit')
            for post in r.json().get('data', {}).get('children', []):
                p    = post.get('data', {})
                text = f"{p.get('title','')} {p.get('selftext','')}".upper()
                for ticker, count in _extract_tickers(text):
                    ticker_mentions[ticker] = ticker_mentions.get(ticker, 0) + count
            break
        except Exception:
            continue

    st_tickers = []
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
    except Exception:
        pass

    if not ticker_mentions:
        return _reddit_fallback()

    top          = [t for t, _ in sorted(ticker_mentions.items(), key=lambda x: -x[1])[:15]]
    max_mentions = max(ticker_mentions.values())

    results = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        futures_map = {ex.submit(_enrich_ticker, t, ticker_mentions[t], max_mentions, st_tickers): t for t in top}
        for future in futures_map:
            results.append(future.result())

    results.sort(key=lambda x: -x["buzz"])
    result = {"data": results[:15], "sources": list(set(sources)), "timestamp": get_timestamp(), "ok": True}
    cache.set("market:reddit", result, TTL["reddit"])
    return result

def _reddit_fallback():
    fallback = [
        {"ticker":"NVDA","price":None,"change":0.8, "buzz":98,"health":"85 Fuerte","social_hype":"★★★★★ Reddit Top","smart_money":"★★★★☆ Vol ×2.3","mentions":98},
        {"ticker":"TSLA","price":None,"change":-0.4,"buzz":95,"health":"72 Fuerte","social_hype":"★★★★★ Reddit Top","smart_money":"★★★☆☆ Vol ×1.8","mentions":95},
        {"ticker":"AAPL","price":None,"change":0.2, "buzz":88,"health":"80 Fuerte","social_hype":"★★★★☆",           "smart_money":"★★★★☆ Vol ×1.5","mentions":88},
        {"ticker":"META","price":None,"change":1.1, "buzz":85,"health":"78 Fuerte","social_hype":"★★★★☆",           "smart_money":"★★★☆☆",         "mentions":85},
        {"ticker":"PLTR","price":None,"change":2.3, "buzz":80,"health":"65 Hold",  "social_hype":"★★★★★ Reddit Top","smart_money":"★★★☆☆",         "mentions":80},
        {"ticker":"AMD", "price":None,"change":-0.9,"buzz":75,"health":"60 Hold",  "social_hype":"★★★★☆ Reddit Top","smart_money":"★★★☆☆",         "mentions":75},
        {"ticker":"GME", "price":None,"change":3.2, "buzz":72,"health":"40 Hold",  "social_hype":"★★★★★ Reddit Top","smart_money":"★☆☆☆☆",         "mentions":72},
        {"ticker":"MSFT","price":None,"change":0.1, "buzz":70,"health":"82 Fuerte","social_hype":"★★★☆☆",           "smart_money":"★★★★★ Vol ×1.9","mentions":70},
    ]
    return {"data": fallback, "sources": ["Fallback"], "timestamp": get_timestamp(), "ok": True}

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
        raw_content = None
        for fname, fdata in files.items():
            raw_content = fdata.get("content", "")
            break
        if not raw_content:
            raise ValueError("Briefing vacío")
        content   = raw_content
        date_str  = ""
        model_str = ""
        try:
            parsed    = _json.loads(raw_content)
            content   = parsed.get("text", raw_content)
            date_str  = parsed.get("date", "")
            model_str = parsed.get("model", "")
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
        result = {"content": content, "date": date_str, "model": model_str, "updated": updated_str, "timestamp": get_timestamp(), "ok": True}
        cache.set("market:briefing", result, TTL["briefing"])
        return result
    except Exception as e:
        return {"content": "", "date": "", "model": "", "updated": "", "timestamp": get_timestamp(), "ok": False, "error": str(e)}

# ── CREDIT SPREADS ────────────────────────────────────────────────────────────

FRED_SERIES = [
    {"id": "BAMLH0A0HYM2", "name": "HY OAS", "label": "High Yield"},
    {"id": "BAMLC0A0CM",   "name": "IG OAS",  "label": "Investment Grade"},
]

def _fetch_fred_series(series_id, api_key, limit=130):
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

def get_credit_spreads():
    from services.cache import cache, TTL
    cached = cache.get("market:spreads")
    if cached: return cached
    from config import settings
    api_key = getattr(settings, "fred_api_key", "")
    results = []
    for series in FRED_SERIES:
        history = _fetch_fred_series(series["id"], api_key)
        if len(history) >= 2:
            current = history[-1]["value"]
            prev    = history[-2]["value"]
            change  = round(current - prev, 2)
            if current > 8:   level, level_color = "ALTO",    "#f23645"
            elif current > 5: level, level_color = "ELEVADO", "#ffb800"
            elif current > 3: level, level_color = "NORMAL",  "#90ee90"
            else:             level, level_color = "BAJO",    "#00ffad"
            results.append({
                "id": series["id"], "name": series["name"], "label": series["label"],
                "current": current, "prev": prev, "change": change,
                "date": history[-1]["date"], "level": level, "level_color": level_color,
                "history": history[-130:], "ok": True,
            })
        else:
            results.append({"id": series["id"], "name": series["name"], "label": series["label"], "current": None, "ok": False})
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
            # Fallback 2Y: usar ^IRX (3M) que yfinance sí devuelve bien
            if not yields.get('Y2Y'):
                irx_val = yields.get('Y3M', 0)
                if irx_val > 0:
                    # 2Y históricamente ~0.3-0.5% sobre el 3M
                    yields['Y2Y'] = round(irx_val + 0.47, 3)

            dgs3m = _fred_csv('DGS3MO')
            if dgs3m and dgs3m[-1][1] > 0:
                yields['Y3M'] = round(dgs3m[-1][1], 3)

            y10 = yields.get('Y10Y', 0)
            y2  = yields.get('Y2Y', 0)
            y3m = yields.get('Y3M', 0)
            y5  = yields.get('Y5Y', 0)
            y30 = yields.get('Y30Y', 0)
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
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_b = ex.submit(_fetch_balance)
            f_y = ex.submit(_fetch_yields)
            f_i = ex.submit(_fetch_indicators)
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
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_nl  = ex.submit(_fetch_net_liquidity)
            f_m2  = ex.submit(_fetch_m2)
            f_spx = ex.submit(_fetch_spx_overlay)
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

def get_market_breadth():
    """
    Market Breadth: SMA50/200, Golden/Death Cross, RSI(14), Oscilador McClellan
    (proxy EMA19-EMA39), % sectores S&P sobre SMA50.
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

        current = float(spy_hist['Close'].iloc[-1])
        sma50   = float(spy_hist['Close'].rolling(50).mean().iloc[-1])
        sma200  = float(spy_hist['Close'].rolling(200).mean().iloc[-1]) if len(spy_hist) >= 200 else None

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

        close = spy_hist['Close']
        ema19 = float(close.ewm(span=19, adjust=False).mean().iloc[-1])
        ema39 = float(close.ewm(span=39, adjust=False).mean().iloc[-1])
        mcclellan = round((ema19 - ema39) / current * 1000, 2)

        # % sectores sobre SMA50 — en paralelo
        above_count, total_checked = 0, 0
        with ThreadPoolExecutor(max_workers=6) as ex:
            results = list(ex.map(_check_sector_above_sma50, SECTOR_ETFS_BREADTH))
        for r in results:
            if r is not None:
                total_checked += 1
                if r:
                    above_count += 1
        pct_above_sma50 = round((above_count / total_checked * 100) if total_checked > 0 else 50.0, 1)

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
            "mcclellan_state": "ALCISTA" if mcclellan > 20 else ("BAJISTA" if mcclellan < -20 else "NEUTRO"),
            "pct_above_sma50": pct_above_sma50,
            "sectors_checked": total_checked,
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
            "mcclellan": 0.0, "mcclellan_state": "N/D", "pct_above_sma50": 50.0,
            "sectors_checked": 0, "timestamp": get_timestamp(),
        }


def get_advance_decline():
    """
    Línea Advance/Decline del NYSE (^ADV / ^DEC vía Yahoo Finance).
    Fallback: proxy sintético basado en SPY si Yahoo no devuelve datos.
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

    # ── Capa 2: proxy sintético ─────────────────────────────────────────────
    try:
        spy_hist = yf.Ticker("SPY").history(period="6mo")
        # Igual que en Market Breadth: filas con Close NaN pueden colarse en datos
        # parciales/recientes de yfinance. Sin filtrarlas, una división por un Close
        # nulo o NaN produce inf/NaN, y `int(NaN)` lanza ValueError, abortando todo
        # el cálculo de las ~124 filas en vez de solo la fila problemática.
        spy_hist = spy_hist.dropna(subset=['Close'])
        print(f"[ADLine] Capa 2 (proxy SPY): {len(spy_hist)} puntos obtenidos (tras filtrar nulos)")
        if len(spy_hist) > 20:
            cumulative = 0
            for i in range(1, len(spy_hist)):
                prev_close = spy_hist['Close'].iloc[i - 1]
                if prev_close == 0 or prev_close != prev_close:  # cero o NaN
                    continue  # saltar esta fila puntual, no abortar todo el cálculo
                day_change = spy_hist['Close'].iloc[i] - prev_close
                ratio = day_change / prev_close
                if ratio != ratio or ratio in (float('inf'), float('-inf')):  # NaN o Inf
                    continue
                adv = int(250 + ratio * 3000)
                adv = max(50, min(450, adv))
                dec = 500 - adv
                net = adv - dec
                cumulative += net
                ad_history.append({
                    "date": spy_hist.index[i].strftime('%Y-%m-%d'),
                    "ad": round(cumulative / 1000, 2),
                    "adv": adv,
                    "dec": dec,
                    "net": net,
                    "spy": round(float(spy_hist['Close'].iloc[i]), 2),
                })
            if not ad_history:
                raise ValueError("Todas las filas de SPY fueron descartadas por datos inválidos")
            current = ad_history[-1]
            result = {
                "ok": True,
                "real_data": False,
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
        print(f"[ADLine] Capa 2 (proxy SPY) también falló: {type(e).__name__}: {e}")

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

def get_crypto_prices():
    from services.cache import cache, TTL
    cached = cache.get("market:crypto")
    if cached:
        return cached

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(_fetch_crypto, CRYPTO_TICKERS))

    result = {"ok": True, "data": results, "timestamp": get_timestamp()}
    result = _sanitize_breadth(result)
    cache.set("market:crypto", result, TTL["market"])
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
    Agrega por sector el universo S&P 500 ya calculado por el módulo RS/RW
    (mismo Gist, sin llamadas nuevas a APIs): tamaño de la cesta, % de nombres
    en el percentil líder (RS_Pct >= 80) y momentum medio del sector (RS_Mom),
    usado este último como señal de "acelerando/desacelerando" — es el dato de
    momentum YA calculado hoy por el scan, no un histórico simulado.
    """
    try:
        from services.cache import cache, TTL
        cached = cache.get("market:sector_composition")
        if cached:
            return cached

        from services.rsrw_service import get_universe_dataframe, SP500_SECTOR_MAP, GICS_MAP
        result = get_universe_dataframe()
        if not result:
            return {"ok": False, "error": "Universo RS/RW no disponible (Gist sin datos todavía)"}

        df, meta = result

        # Respaldo: si el Gist no trae un sector válido para un ticker (viene
        # vacío/None y por tanto cae a "Otros"), usamos el propio mapeo estático
        # SP500_SECTOR_MAP del RS/RW (el mismo que usa el motor de scan) como
        # segunda fuente, por ticker. Evita que todo el universo colapse en
        # "Otros" cuando el campo sector del Gist viene incompleto.
        fallback_map = {t: GICS_MAP.get(sec, sec) for t, sec in SP500_SECTOR_MAP.items()}
        n_fallback = [0]

        def _resolve_sector(row):
            sec = row.get("Sector")
            if sec and str(sec).strip() not in ("", "nan", "None", "Otros"):
                return sec
            fb = fallback_map.get(str(row.name).strip().upper())
            if fb:
                n_fallback[0] += 1
                return fb
            return sec or "Otros"

        df["Sector"] = df.apply(_resolve_sector, axis=1)
        if n_fallback[0]:
            print(f"[Sector Composition] {n_fallback[0]} ticker(s) resueltos vía SP500_SECTOR_MAP (el Gist no traía sector válido para ellos)")

        df = df.dropna(subset=["Sector", "RS_Pct"])
        if df.empty:
            return {"ok": False, "error": "Sin datos de sector en el universo"}

        grouped = []
        for sector, g in df.groupby("Sector"):
            basket = len(g)
            if basket == 0:
                continue
            leaders     = int((g["RS_Pct"] >= 80).sum())
            avg_score   = round(float(g["RS_Pct"].mean()), 1)
            avg_mom     = round(float(g["RS_Mom"].mean()), 2) if "RS_Mom" in g.columns and g["RS_Mom"].notna().any() else None
            grouped.append({
                "sector":      sector,
                "basket":      basket,
                "leaders":     leaders,
                "leaders_pct": round(leaders / basket * 100, 0) if basket else 0,
                "avg_score":   avg_score,
                "avg_momentum": avg_mom,
            })

        if not grouped:
            return {"ok": False, "error": "Sin sectores con datos suficientes"}

        grouped.sort(key=lambda r: r["avg_score"], reverse=True)
        for i, r in enumerate(grouped):
            r["rank"] = i + 1

        with_mom = [r for r in grouped if r["avg_momentum"] is not None]
        accelerating = sorted(with_mom, key=lambda r: r["avg_momentum"], reverse=True)[:5]
        decelerating = sorted(with_mom, key=lambda r: r["avg_momentum"])[:5]

        result = {
            "ok":              True,
            "sectors":         grouped,
            "strongest":       grouped[0],
            "weakest":         grouped[-1],
            "sectors_tracked": len(grouped),
            "universe_size":   int(len(df)),
            "accelerating":    accelerating,
            "decelerating":    decelerating,
            "freshness":       meta.get("generated_at", ""),
            "timestamp":       get_timestamp(),
        }
        cache.set("market:sector_composition", result, TTL.get("market", 300))
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}