from datetime import datetime, timedelta, timezone
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor

def get_timestamp():
    cet = timezone(timedelta(hours=1))
    return datetime.now(cet).strftime('%H:%M:%S')

# ── ÍNDICES ───────────────────────────────────────────────────────────────────

INDICES = [
    {"ticker": "^GSPC",  "name": "S&P 500",    "short": "SPX"},
    {"ticker": "^NDX",   "name": "Nasdaq 100",  "short": "NDX"},
    {"ticker": "^DJI",   "name": "Dow Jones",   "short": "DJI"},
    {"ticker": "^RUT",   "name": "Russell 2000","short": "RUT"},
    {"ticker": "^VIX",   "name": "VIX",         "short": "VIX"},
]

def _fetch_ticker(item: dict) -> dict:
    try:
        t = yf.Ticker(item["ticker"])
        hist = t.history(period="2d", interval="1d")
        if len(hist) < 2:
            raise ValueError("Sin datos suficientes")
        prev_close = float(hist["Close"].iloc[-2])
        last_close = float(hist["Close"].iloc[-1])
        change     = last_close - prev_close
        pct        = (change / prev_close) * 100
        return {
            "ticker": item["short"],
            "name":   item["name"],
            "price":  round(last_close, 2),
            "change": round(change, 2),
            "pct":    round(pct, 2),
            "ok":     True,
        }
    except Exception as e:
        return {
            "ticker": item["short"],
            "name":   item["name"],
            "price":  None,
            "change": None,
            "pct":    None,
            "ok":     False,
            "error":  str(e),
        }

def get_indices() -> dict:
    results = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(_fetch_ticker, item): item for item in INDICES}
        for future in futures:
            results.append(future.result())
    results.sort(key=lambda x: ["SPX","NDX","DJI","RUT","VIX"].index(x["ticker"]))
    return {
        "data":      results,
        "timestamp": get_timestamp(),
        "ok":        any(r["ok"] for r in results),
    }

# ── FEAR & GREED ──────────────────────────────────────────────────────────────

def get_fear_greed() -> dict:
    import requests
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        )
        r.raise_for_status()
        data  = r.json()
        score = int(data["fear_and_greed"]["score"])
        rating = data["fear_and_greed"]["rating"].replace("_", " ").title()
        prev  = int(data["fear_and_greed"]["previous_close"])
        week  = int(data["fear_and_greed"]["previous_1_week"])
        return {
            "score":    score,
            "rating":   rating,
            "prev":     prev,
            "week_ago": week,
            "timestamp": get_timestamp(),
            "ok":       True,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "timestamp": get_timestamp()}
