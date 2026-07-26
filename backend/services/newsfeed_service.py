import re
import html as _html
import requests
import xml.etree.ElementTree as ET
import sys, os
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf
from config import settings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

# ── SOURCES ───────────────────────────────────────────────────────────────────

SOURCES = [
    {"id":"reuters",      "label":"REUTERS",     "url":"https://feeds.reuters.com/reuters/topNews"},
    {"id":"wsj",          "label":"WSJ",         "url":"https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
    {"id":"cnbc",         "label":"CNBC",        "url":"https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"id":"marketwatch",  "label":"MKTWATCH",    "url":"https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"id":"yahoofinance", "label":"YAHOO FIN",   "url":"https://finance.yahoo.com/rss/topstories"},
    {"id":"benzinga",     "label":"BENZINGA",    "url":"https://www.benzinga.com/feed"},
    {"id":"zerohedge",    "label":"ZEROHEDGE",   "url":"https://feeds.feedburner.com/zerohedge/feed"},
    {"id":"investing",    "label":"INVESTING",   "url":"https://www.investing.com/rss/news.rss"},
    {"id":"reddit",       "label":"REDDIT",      "url":"https://www.reddit.com/r/investing+stocks+options/new.rss"},
    {"id":"fed",          "label":"FED",         "url":"https://www.federalreserve.gov/feeds/press_all.xml", "fmt":"atom"},
    {"id":"macroalf",     "label":"MACRO ALF",   "url":"https://themacrocompass.substack.com/feed"},
    {"id":"blockworks",   "label":"BLOCKWORKS",  "url":"https://blockworks.co/feed"},
    {"id":"valuewalk",    "label":"VALUEWALK",   "url":"https://www.valuewalk.com/feed"},
    {"id":"gurufocus",    "label":"GURUFOCUS",   "url":"https://www.gurufocus.com/term/news/rss"},
]

# URL de la web de cada fuente — para hipervínculo directo al clicar el label
SOURCE_URLS = {
    "reuters":      "https://www.reuters.com/markets/",
    "wsj":          "https://www.wsj.com/news/markets",
    "cnbc":         "https://www.cnbc.com/markets/",
    "marketwatch":  "https://www.marketwatch.com/",
    "yahoofinance": "https://finance.yahoo.com/",
    "benzinga":     "https://www.benzinga.com/",
    "zerohedge":    "https://www.zerohedge.com/",
    "investing":    "https://www.investing.com/news/",
    "reddit":       "https://www.reddit.com/r/investing/",
    "fed":          "https://www.federalreserve.gov/newsevents/pressreleases.htm",
    "macroalf":     "https://themacrocompass.substack.com/",
    "blockworks":   "https://blockworks.co/news",
    "valuewalk":    "https://www.valuewalk.com/",
    "gurufocus":    "https://www.gurufocus.com/news/",
    "finnhub":      "https://finnhub.io/",
}

PRICE_TICKERS = {
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX",
    "EUR/USD": "EURUSD=X", "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
    "GOLD": "GC=F", "OIL WTI": "CL=F", "10Y UST": "^TNX",
}

HIGH_KW = [
    "fed","federal reserve","fomc","rate hike","rate cut","recession","crash","collapse",
    "default","bankrupt","bailout","systemic","inflation surge","cpi","ppi","nonfarm",
    "crisis","emergency","plunge","circuit breaker","black swan","contagion",
    "tariff","sanction","executive order","nuclear","war","attack",
    # "surge" y "plunge" se tratan aparte con contexto — ver _classify_impact()
]
MED_KW = [
    "earnings","guidance","downgrade","upgrade","merger","acquisition","ipo","spac",
    "sec","investigation","layoffs","gdp","unemployment","retail sales","pmi",
    "dividend","buyback","activist","short","target price","inflation","interest rate",
]

# Palabras que anulan una keyword HIGH/MED si aparecen justo antes de ella (negación básica)
NEGATION_PREFIXES = ["no ", "not ", "avoids ", "avoid ", "no sign", "no risk", "eases ", "ease ",
                     "rules out", "denies ", "deny ", "end of ", "ends ", "survived ", "survives ",
                     "low ", "falling ", "fading ", "cooling ", "subdued "]

# Keywords de impacto que son sensibles al contexto (no clasificar como HIGH si van con
# sujetos que las anulan, p.ej. "surge in unemployment" no es bullish)
CONTEXT_HIGH_SURGE  = ["market","stock","share","equity","price","rally","s&p","nasdaq","dow","index"]
CONTEXT_HIGH_PLUNGE = ["market","stock","share","equity","price","s&p","nasdaq","dow","index","yield","oil","gold"]

SECTORS_MAP = {
    "TECH":    ["nvidia","apple","microsoft","google","meta","tesla","amd","chip","ai","cloud","software","semiconductor"],
    "FINANCE": ["jpmorgan","goldman","bank","federal reserve","interest rate","yield","treasury","fomc","bonds","credit"],
    "ENERGY":  ["oil","gas","opec","crude","wti","brent","energy","xom","cvx"],
    "HEALTH":  ["pharma","fda","drug","biotech","clinical","vaccine","pfizer","merck"],
    "MACRO":   ["gdp","cpi","jobs","unemployment","recession","inflation","economy","fomc"],
    "CRYPTO":  ["bitcoin","btc","ethereum","eth","crypto","blockchain","solana","defi"],
    "POLICY":  ["trump","white house","congress","tariff","sanction","executive order"],
    "DEFENSE": ["military","war","ukraine","russia","china","taiwan","missile","pentagon"],
}

# Mapeo de categorías de Finnhub a sectores RSU (Nivel 2)
FINNHUB_CATEGORY_TO_SECTOR = {
    "technology":  "TECH",
    "crypto":      "CRYPTO",
    "forex":       "FINANCE",
    "merger":      "FINANCE",
    "general":     "GENERAL",
    "top news":    "MACRO",
}

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    # 2ª pasada: un payload doblemente codificado (&amp;lt;img...) sobrevive
    # al primer strip (el parser XML aún lo ve como &lt;...&gt;) y solo se
    # convierte en HTML real tras el unescape de arriba -- sin esto, salía
    # de aquí como etiqueta viva. Defensa en profundidad; el esc() del
    # frontend (core/ui.js) es la que realmente bloquea la ejecución.
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()

def _is_negated(text: str, keyword: str) -> bool:
    """
    Comprueba si una keyword aparece precedida de un prefijo de negación
    en una ventana de ~5 palabras. Cubre casos como:
      "no signs of recession", "avoids crash", "not a crisis", "rules out rate cut"
    """
    idx = text.find(keyword)
    if idx == -1:
        return False
    window = text[max(0, idx - 40):idx]
    return any(neg in window for neg in NEGATION_PREFIXES)

def _classify_impact(text: str, finnhub_related: list = None) -> str:
    """
    Nivel 1: clasificación con detección de negación y contexto para keywords ambiguas.
    Nivel 2: si se pasan related articles de Finnhub, los usa para reforzar la clasificación.
    """
    t = text.lower()

    # "surge" solo es HIGH si se refiere a activos de mercado, no a datos macro negativos
    # "plunge" igual — "plunge in yields" puede ser bueno o malo, pero en activos es impacto alto
    if "surge" in t and not _is_negated(t, "surge"):
        if any(ctx in t for ctx in CONTEXT_HIGH_SURGE):
            return "HIGH"
    if "plunge" in t and not _is_negated(t, "plunge"):
        if any(ctx in t for ctx in CONTEXT_HIGH_PLUNGE):
            return "HIGH"

    # Keywords HIGH con detección de negación
    for kw in HIGH_KW:
        if kw in t and not _is_negated(t, kw):
            return "HIGH"

    # Nivel 2: si Finnhub dice que hay artículos relacionados con símbolos de alto impacto
    # (Fed, mercado, macro) — tratar como MED mínimo aunque las keywords no aparezcan
    if finnhub_related:
        macro_symbols = {"SPY","QQQ","TLT","GLD","DXY","VIX","ES","NQ"}
        if any(r.get('symbol','') in macro_symbols for r in finnhub_related):
            return "MED"

    for kw in MED_KW:
        if kw in t and not _is_negated(t, kw):
            return "MED"

    return "LOW"

def _sentiment(text: str) -> str:
    """
    Nivel 1: sentimiento con desambiguación de palabras en contexto negativo.
    Palabras como 'high' y 'low' son ambiguas — 'high unemployment' es bearish,
    'stock hits high' es bullish. Las excluimos del conteo simple y las evaluamos
    solo si hay contexto de activos/mercados junto a ellas.
    """
    t = text.lower()

    # Palabras positivas netas (sin 'high' que es ambigua; 'surge' se evalúa con contexto abajo)
    pos_words = ["rally","gain","rise","soar","beat","record","growth","strong","bull",
                 "recover","rebound","outperform","upgrade","beat expectations"]
    # Palabras negativas netas (sin 'low' que es ambigua)
    neg_words = ["plunge","crash","fall","drop","sink","miss","weak","bear","collapse","selloff",
                 "tumble","underperform","downgrade","miss expectations","layoffs","bankrupt"]

    pos = sum(1 for w in pos_words if w in t and not _is_negated(t, w))
    neg = sum(1 for w in neg_words if w in t and not _is_negated(t, w))

    # "surge" es positivo SOLO si va con activos de mercado, no con datos macro negativos
    if "surge" in t and not _is_negated(t, "surge"):
        if any(ctx in t for ctx in ["stock","share","price","market","equity","s&p","nasdaq"]):
            pos += 1
        elif any(ctx in t for ctx in ["unemployment","jobless","layoff","inflation","deficit","debt"]):
            neg += 1  # surge en datos negativos = señal bearish

    # 'high' en contexto de precio/mercado es positivo; en contexto macro (unemployment, inflation) es negativo
    if "high" in t:
        if any(ctx in t for ctx in ["stock","share","price","market","record","52-week"]):
            pos += 1
        elif any(ctx in t for ctx in ["unemployment","inflation","rate","deficit","debt","risk"]):
            neg += 1

    # 'low' es el inverso
    if "low" in t:
        if any(ctx in t for ctx in ["unemployment","inflation","rate","volatility"]):
            pos += 1
        elif any(ctx in t for ctx in ["stock","share","price","market","52-week"]):
            neg += 1

    if pos > neg: return "bullish"
    if neg > pos: return "bearish"
    return "neutral"

def _sector(text: str, finnhub_category: str = None) -> str:
    """
    Nivel 2: si viene una categoría de Finnhub, la usamos como señal primaria.
    Si no, fallback a keyword matching.
    """
    # Nivel 2: categoría de Finnhub como señal de mayor precisión
    if finnhub_category:
        mapped = FINNHUB_CATEGORY_TO_SECTOR.get(finnhub_category.lower())
        if mapped and mapped != "GENERAL":
            return mapped

    # Nivel 1: keyword matching como fallback
    t = text.lower()
    for sec, kws in SECTORS_MAP.items():
        if any(k in t for k in kws):
            return sec
    return "GENERAL"

def _mins_ago(pub_str: str) -> int:
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(pub_str)
        diff = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return max(0, int(diff.total_seconds() / 60))
    except Exception:
        pass
    try:
        # Formato ISO 8601 (usado por Atom y algunos RSS modernos)
        dt = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
        diff = datetime.now(timezone.utc) - dt.astimezone(timezone.utc)
        return max(0, int(diff.total_seconds() / 60))
    except Exception:
        return 999

def _parse_rss(content: str, src: dict) -> list:
    items = []
    try:
        root = ET.fromstring(content)
        ns   = {'atom': 'http://www.w3.org/2005/Atom'}
        fmt  = src.get('fmt', 'rss')

        if fmt == 'atom':
            entries = root.findall('.//atom:entry', ns) or root.findall('.//{http://www.w3.org/2005/Atom}entry')
            for e in entries[:10]:
                def _t(tag): return (e.findtext(f'{{http://www.w3.org/2005/Atom}}{tag}') or '').strip()
                title = _t('title')
                link  = e.find('{http://www.w3.org/2005/Atom}link')
                link  = link.get('href','') if link is not None else ''
                pub   = _t('updated') or _t('published')
                desc  = _strip_html(_t('summary') or _t('content'))
                if title:
                    items.append(_build(title, desc, link, src, pub))
        else:
            for item in root.findall('.//item')[:10]:
                def _t(tag): return (item.findtext(tag) or '').strip()
                title = _t('title')
                link  = _t('link')
                pub   = _t('pubDate')
                desc  = _strip_html(_t('description') or _t('summary'))
                if title:
                    items.append(_build(title, desc, link, src, pub))
    except Exception:
        pass
    return items

def _build(title: str, desc: str, link: str, src: dict, pub: str) -> dict:
    text   = title + ' ' + desc
    mins   = _mins_ago(pub) if pub else 999
    return {
        "title":      _strip_html(title)[:200],
        "desc":       desc[:300],
        "url":        link,
        "source":     src['label'],
        "source_id":  src['id'],
        "source_url": SOURCE_URLS.get(src['id'], ''),
        "impact":     _classify_impact(text),
        "sentiment":  _sentiment(text),
        "sector":     _sector(text),
        "mins_ago":   mins,
        "pub":        pub,
    }

def _fetch_source(src: dict) -> tuple:
    """Devuelve (items, source_id, ok) para poder rastrear qué fuentes funcionan."""
    if not src.get('url'):
        return [], src['id'], False
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/2.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        r = requests.get(src['url'], headers=headers, timeout=8)
        if r.status_code == 200:
            items = _parse_rss(r.text, src)
            return items, src['id'], len(items) > 0
        return [], src['id'], False
    except Exception:
        return [], src['id'], False

# ── FINNHUB NEWS ──────────────────────────────────────────────────────────────

def _fetch_finnhub_news() -> tuple:
    """
    Noticias de mercado de Finnhub — mayor calidad y sentimiento real que RSS.
    Usa la key de Finnhub ya configurada en el proyecto (misma que Research).
    """
    key = settings.finnhub_api_key
    if not key:
        return [], False
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": key},
            timeout=8
        )
        if r.status_code != 200:
            return [], False
        items = []
        src = {"id": "finnhub", "label": "FINNHUB"}
        for art in r.json()[:15]:
            headline = art.get('headline', '')
            summary  = art.get('summary', '')
            url      = art.get('url', '')
            ts       = art.get('datetime', 0)
            category = art.get('category', '')   # Nivel 2: categoría nativa de Finnhub
            related  = art.get('related', [])    # Nivel 2: símbolos relacionados (lista o string)
            if not headline:
                continue
            # Calcular mins_ago desde Unix timestamp
            try:
                dt   = datetime.fromtimestamp(ts, tz=timezone.utc)
                mins = max(0, int((datetime.now(timezone.utc) - dt).total_seconds() / 60))
            except Exception:
                mins = 999

            # Normalizar 'related' — puede ser string "AAPL,MSFT" o lista
            if isinstance(related, str):
                related = [{"symbol": s.strip()} for s in related.split(',') if s.strip()]
            elif not isinstance(related, list):
                related = []

            text   = headline + ' ' + summary
            item   = {
                "title":      headline[:200],
                "desc":       summary[:300],
                "url":        url,
                "source":     "FINNHUB",
                "source_id":  "finnhub",
                "source_url": SOURCE_URLS.get("finnhub", ""),
                "impact":     _classify_impact(text, finnhub_related=related),
                "sentiment":  _sentiment(text),
                "sector":     _sector(text, finnhub_category=category),
                "mins_ago":   mins,
                "pub":        str(ts),
            }
            items.append(item)
        return items, len(items) > 0
    except Exception:
        return [], False

# ── TRUMP / TRUTH SOCIAL ──────────────────────────────────────────────────────

def get_trump_feed(limit: int = 15) -> dict:
    """
    Posts de Trump vía trumpstruth.org — archivo público de Truth Social.
    Usa el RSS oficial del archivo (https://www.trumpstruth.org/feed).
    Etiquetado explícitamente como archivo, no como fuente oficial de Truth Social.
    """
    from services.cache import cache
    cached = cache.get("newsfeed:trump")
    if cached: return cached

    url = "https://www.trumpstruth.org/feed"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/2.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return {"ok": False, "error": f"trumpstruth.org status {r.status_code}", "posts": []}

        root  = ET.fromstring(r.text)
        posts = []
        for item in root.findall('.//item')[:limit]:
            def _t(tag): return (item.findtext(tag) or '').strip()
            title   = _strip_html(_t('title'))
            content = _strip_html(_t('description') or _t('content:encoded') or _t('summary'))
            link    = _t('link')
            pub     = _t('pubDate')
            mins    = _mins_ago(pub)

            # Clasificar impacto del post por keywords financieras/política
            text = (title + ' ' + content).lower()
            impact = _classify_impact(text)

            posts.append({
                "title":    title[:300] if title else content[:300],
                "content":  content[:500],
                "url":      link,
                "mins_ago": mins,
                "pub":      pub,
                "impact":   impact,
                "sector":   _sector(text),
            })

        posts.sort(key=lambda x: x['mins_ago'])
        result = {
            "ok":        True,
            "posts":     posts,
            "total":     len(posts),
            "source":    "trumpstruth.org (archivo público de Truth Social)",
            "timestamp": get_timestamp(),
        }
        cache.set("newsfeed:trump", result, 300)  # cache 5 min
        return result

    except Exception as e:
        return {"ok": False, "error": str(e), "posts": []}

# ── PRICES ────────────────────────────────────────────────────────────────────

def _get_prices() -> list:
    result = []
    def _fetch(name, ticker):
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="2d", interval="1d")
            if len(hist) < 2: return None
            prev  = float(hist['Close'].iloc[-2])
            last  = float(hist['Close'].iloc[-1])
            chg   = (last - prev) / prev * 100
            return {"name": name, "price": round(last, 4), "chg": round(chg, 2)}
        except Exception:
            return None
    from services.yf_pool import yf_executor
    futures = {yf_executor.submit(_fetch, name, ticker): name for name, ticker in PRICE_TICKERS.items()}
    for f in as_completed(futures):
        r = f.result()
        if r: result.append(r)
    result.sort(key=lambda x: list(PRICE_TICKERS.keys()).index(x['name']))
    return result

# ── MAIN ──────────────────────────────────────────────────────────────────────

def _fetch_all_items() -> tuple:
    """
    Parte costosa de get_newsfeed — los 15 fetches HTTP en paralelo.
    Separada para poder cachearla independientemente de los filtros,
    de modo que todos los usuarios comparten el mismo ciclo de fetch.
    """
    from services.cache import cache
    cached = cache.get("newsfeed:raw")
    if cached:
        return cached['items'], cached['source_status'], cached['all_source_defs']

    active_sources = SOURCES
    source_status  = {}
    all_items      = []

    with ThreadPoolExecutor(max_workers=12) as ex:
        rss_futures    = {ex.submit(_fetch_source, src): src for src in active_sources}
        finnhub_future = ex.submit(_fetch_finnhub_news)

        for f in as_completed(rss_futures):
            items, src_id, ok = f.result()
            all_items.extend(items)
            source_status[src_id] = ok

        fh_items, fh_ok = finnhub_future.result()
        all_items.extend(fh_items)
        source_status['finnhub'] = fh_ok

    # Deduplicar por título
    seen   = set()
    unique = []
    for item in all_items:
        key = item['title'][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    unique.sort(key=lambda x: x['mins_ago'])

    all_source_defs = SOURCES + [{"id": "finnhub", "label": "FINNHUB"}]

    # Caché de 5 minutos — coincide con el auto-refresh del frontend.
    # Solo cacheamos si hay al menos algunas noticias (no guardamos un estado vacío
    # por fallo de red que quedaría pegado 5 minutos).
    if len(unique) > 5:
        cache.set("newsfeed:raw", {
            "items":           unique,
            "source_status":   source_status,
            "all_source_defs": all_source_defs,
        }, 300)

    return unique, source_status, all_source_defs

def get_newsfeed(sources: list = None, impact: str = None, sector: str = None, limit: int = 50) -> dict:
    unique, source_status, all_source_defs = _fetch_all_items()

    # Filtros aplicados en memoria sobre los datos ya cacheados — sin coste de red
    filtered = unique
    if impact:
        filtered = [i for i in filtered if i['impact'] == impact.upper()]
    if sector:
        filtered = [i for i in filtered if i['sector'] == sector.upper()]

    # Stats sobre el conjunto completo (no solo la página filtrada)
    high = sum(1 for i in unique if i['impact'] == 'HIGH')
    med  = sum(1 for i in unique if i['impact'] == 'MED')
    low  = sum(1 for i in unique if i['impact'] == 'LOW')
    bull = sum(1 for i in unique if i['sentiment'] == 'bullish')
    bear = sum(1 for i in unique if i['sentiment'] == 'bearish')

    return {
        "ok":      True,
        "items":   filtered[:limit],
        "total":   len(unique),
        "stats":   {"high": high, "med": med, "low": low, "bullish": bull, "bearish": bear},
        "sources": [{"id": s['id'], "label": s['label'],
                     "ok": source_status.get(s['id'], False),
                     "url": SOURCE_URLS.get(s['id'], '')} for s in all_source_defs],
        "timestamp": get_timestamp(),
    }

def get_newsfeed_prices() -> list:
    return _get_prices()