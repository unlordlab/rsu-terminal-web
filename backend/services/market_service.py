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
        vix   = float(hi
