import re
import html as _html
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
import yfinance as yf

# ── SOURCES ───────────────────────────────────────────────────────────────────

SOURCES = [
    {"id":"reuters",      "label":"REUTERS",     "url":"https://feeds.reuters.com/reuters/topNews"},
    {"id":"wsj",          "label":"WSJ",         "url":"https://feeds.a.dj.com/rss/RSSMarketsMain.xml"},
    {"id":"cnbc",         "label":"CNBC",        "url":"https://www.cnbc.com/id/20910258/device/rss/rss.html"},
    {"id":"marketwatch",  "label":"MKTWATCH",    "url":"https://feeds.content.dowjones.io/public/rss/mw_topstories"},
    {"id":"yahoofinance", "label":"YAHOO FIN",   "url":"https://finance.yahoo.com/rss/topstories"},
    {"id":"benzinga",     "label":"BENZINGA",    "url":"https://www.benzinga.com/feed"},
    {"id":"seekingalpha", "label":"SEKALPHA",    "url":"https://seekingalpha.com/market_currents.xml"},
    {"id":"zerohedge",    "label":"ZEROHEDGE",   "url":"https://feeds.feedburner.com/zerohedge/feed"},
    {"id":"investing",    "label":"INVESTING",   "url":"https://www.investing.com/rss/news.rss"},
    {"id":"reddit",       "label":"REDDIT",      "url":"https://www.reddit.com/r/investing+stocks+options/new.rss"},
    {"id":"fed",          "label":"FED",         "url":"https://www.federalreserve.gov/feeds/press_all.xml", "fmt":"atom"},
    {"id":"macroalf",     "label":"MACRO ALF",   "url":"https://themacrocompass.substack.com/feed"},
    {"id":"blockworks",   "label":"BLOCKWORKS",  "url":"https://blockworks.co/feed"},
    {"id":"valuewalk",    "label":"VALUEWALK",   "url":"https://www.valuewalk.com/feed"},
    {"id":"gurufocus",    "label":"GURUFOCUS",   "url":"https://www.gurufocus.com/term/news/rss"},
]

PRICE_TICKERS = {
    "S&P 500": "^GSPC", "NASDAQ": "^IXIC", "DOW": "^DJI", "VIX": "^VIX",
    "EUR/USD": "EURUSD=X", "BTC/USD": "BTC-USD", "ETH/USD": "ETH-USD",
    "GOLD": "GC=F", "OIL WTI": "CL=F", "10Y UST": "^TNX",
}

HIGH_KW = [
    "fed","federal reserve","fomc","rate hike","rate cut","recession","crash","collapse",
    "default","bankrupt","bailout","systemic","inflation surge","cpi","ppi","nonfarm",
    "crisis","emergency","plunge","surge","circuit breaker","black swan","contagion",
]
MED_KW = [
    "earnings","guidance","downgrade","upgrade","merger","acquisition","ipo","spac",
    "sec","investigation","layoffs","gdp","unemployment","retail sales","pmi",
    "dividend","buyback","activist","short","target price",
]

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

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _strip_html(text: str) -> str:
    if not text: return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = _html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def _classify_impact(text: str) -> str:
    t = text.lower()
    if any(k in t for k in HIGH_KW): return "HIGH"
    if any(k in t for k in MED_KW):  return "MED"
    return "LOW"

def _sentiment(text: str) -> str:
    t = text.lower()
    pos = sum(1 for w in ["surge","rally","gain","rise","soar","beat","record","high","growth","strong","bull"] if w in t)
    neg = sum(1 for w in ["plunge","crash","fall","drop","sink","miss","low","weak","bear","crisis","collapse"] if w in t)
    if pos > neg: return "bullish"
    if neg > pos: return "bearish"
    return "neutral"

def _sector(text: str) -> str:
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
        "title":    _strip_html(title)[:200],
        "desc":     desc[:300],
        "url":      link,
        "source":   src['label'],
        "source_id": src['id'],
        "impact":   _classify_impact(text),
        "sentiment": _sentiment(text),
        "sector":   _sector(text),
        "mins_ago": mins,
        "pub":      pub,
    }

def _fetch_source(src: dict) -> list:
    if not src.get('url'):
        return []
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; RSUTerminal/2.0)",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }
    try:
        r = requests.get(src['url'], headers=headers, timeout=8)
        if r.status_code == 200:
            return _parse_rss(r.text, src)
    except Exception:
        pass
    return []

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
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = {ex.submit(_fetch, name, ticker): name for name, ticker in PRICE_TICKERS.items()}
        for f in as_completed(futures):
            r = f.result()
            if r: result.append(r)
    result.sort(key=lambda x: list(PRICE_TICKERS.keys()).index(x['name']))
    return result

# ── MAIN ──────────────────────────────────────────────────────────────────────

def get_newsfeed(sources: list = None, impact: str = None, sector: str = None, limit: int = 50) -> dict:
    active_sources = [s for s in SOURCES if not sources or s['id'] in sources]

    all_items = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_source, src): src for src in active_sources}
        for f in as_completed(futures):
            all_items.extend(f.result())

    # Deduplicar por título
    seen   = set()
    unique = []
    for item in all_items:
        key = item['title'][:60].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # Filtros
    if impact:
        unique = [i for i in unique if i['impact'] == impact.upper()]
    if sector:
        unique = [i for i in unique if i['sector'] == sector.upper()]

    # Ordenar por tiempo
    unique.sort(key=lambda x: x['mins_ago'])

    # Stats
    high = sum(1 for i in unique if i['impact'] == 'HIGH')
    med  = sum(1 for i in unique if i['impact'] == 'MED')
    low  = sum(1 for i in unique if i['impact'] == 'LOW')
    bull = sum(1 for i in unique if i['sentiment'] == 'bullish')
    bear = sum(1 for i in unique if i['sentiment'] == 'bearish')

    return {
        "ok":        True,
        "items":     unique[:limit],
        "total":     len(unique),
        "stats":     {"high": high, "med": med, "low": low, "bullish": bull, "bearish": bear},
        "sources":   [{"id": s['id'], "label": s['label']} for s in SOURCES],
        "timestamp": datetime.now().strftime('%H:%M:%S'),
    }

def get_newsfeed_prices() -> list:
    return _get_prices()
    