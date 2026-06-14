import yfinance as yf
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import os

FMP_KEY     = os.getenv("fmp_api_key", "")
FINNHUB_KEY = os.getenv("finnhub_api_key", "")

WATCHLIST = [
    "NVDA","AAPL","MSFT","AMZN","META","GOOGL","TSLA","AMD","AVGO","NFLX",
    "HOOD","PLTR","CRWD","COIN","MSTR","ARM","SMCI","SOFI","RKLB","NBIS",
    "JPM","GS","MS","BAC","V","MA","PYPL","SQ","SHOP","MELI",
    "SPY","QQQ","IWM",
]

def _get_timestamp():
    from services.market_service import get_timestamp
    return get_timestamp()

# ── FUENTE 1: FMP ─────────────────────────────────────────────────────────────

def _get_fmp_earnings() -> list:
    try:
        today   = datetime.now().strftime('%Y-%m-%d')
        future  = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        url     = f"https://financialmodelingprep.com/api/v3/earning_calendar?from={today}&to={future}&apikey={FMP_KEY}"
        r       = requests.get(url, timeout=8)
        data    = r.json()
        results = []
        for item in data[:50]:
            ticker = item.get('symbol','')
            if not ticker: continue
            results.append({
                "ticker":   ticker,
                "date":     item.get('date',''),
                "time":     item.get('time',''),  # BMO/AMC
                "eps_est":  item.get('epsEstimated'),
                "rev_est":  item.get('revenueEstimated'),
                "source":   "FMP",
            })
        return results
    except Exception:
        return []

# ── FUENTE 2: Finnhub ─────────────────────────────────────────────────────────

def _get_finnhub_earnings() -> list:
    try:
        today  = datetime.now().strftime('%Y-%m-%d')
        future = (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')
        url    = f"https://finnhub.io/api/v1/calendar/earnings?from={today}&to={future}&token={FINNHUB_KEY}"
        r      = requests.get(url, timeout=8)
        data   = r.json().get('earningsCalendar', [])
        results = []
        for item in data[:50]:
            ticker = item.get('symbol','')
            if not ticker: continue
            results.append({
                "ticker":    ticker,
                "date":      item.get('date',''),
                "time":      item.get('hour',''),  # bmo/amc
                "eps_est":   item.get('epsEstimate'),
                "eps_actual": item.get('epsActual'),
                "rev_est":   item.get('revenueEstimate'),
                "source":    "Finnhub",
            })
        return results
    except Exception:
        return []

# ── FUENTE 3: yfinance individual ─────────────────────────────────────────────

def _get_yf_earnings(ticker: str) -> dict:
    try:
        tk   = yf.Ticker(ticker)
        cal  = tk.calendar
        if cal is None or cal.empty:
            return {}
        date_col = cal.columns[0] if hasattr(cal, 'columns') else None
        if date_col is None:
            return {}
        eps_est  = cal.loc['EPS Estimate', date_col] if 'EPS Estimate' in cal.index else None
        rev_est  = cal.loc['Revenue Estimate', date_col] if 'Revenue Estimate' in cal.index else None
        date_val = str(date_col)[:10] if date_col else ''
        return {
            "ticker":  ticker,
            "date":    date_val,
            "eps_est": float(eps_est) if eps_est else None,
            "rev_est": float(rev_est) if rev_est else None,
            "source":  "yfinance",
        }
    except Exception:
        return {}

# ── SURPRISE HISTÓRICO: yfinance ──────────────────────────────────────────────

def _get_surprise(ticker: str) -> list:
    try:
        tk   = yf.Ticker(ticker)
        hist = tk.quarterly_earnings
        if hist is None or hist.empty:
            return []
        results = []
        for date, row in hist.tail(4).iterrows():
            actual   = row.get('Actual', None)
            estimate = row.get('Estimate', None)
            if actual is None or estimate is None:
                continue
            surprise = ((actual - estimate) / abs(estimate) * 100) if estimate != 0 else 0
            results.append({
                "quarter":  str(date),
                "actual":   round(float(actual), 2),
                "estimate": round(float(estimate), 2),
                "surprise": round(float(surprise), 1),
            })
        return results[::-1]  # más reciente primero
    except Exception:
        return []

# ── MAIN ──────────────────────────────────────────────────────────────────────

def get_earnings_calendar() -> dict:
    # Combinar FMP + Finnhub
    fmp_data     = _get_fmp_earnings()
    finnhub_data = _get_finnhub_earnings()

    # Merge por ticker+date, priorizando FMP
    merged = {}
    for item in finnhub_data + fmp_data:
        key = item['ticker'] + '_' + item['date']
        merged[key] = item

    # Filtrar solo watchlist o tickers conocidos + ordenar por fecha
    items = list(merged.values())
    items.sort(key=lambda x: x.get('date',''))

    # Añadir info de precio actual
    def enrich(item):
        try:
            tk    = yf.Ticker(item['ticker'])
            fi    = tk.fast_info
            price = round(float(getattr(fi, 'last_price', 0) or 0), 2)
            item['price'] = price
        except Exception:
            item['price'] = None
        return item

    # Solo enriquecer los primeros 20 para no tardar demasiado
    with ThreadPoolExecutor(max_workers=8) as ex:
        items[:20] = list(ex.map(enrich, items[:20]))

    # Formatear tiempo BMO/AMC
    def fmt_time(t):
        t = (t or '').lower()
        if 'bmo' in t or 'before' in t: return 'BMO 🌅'
        if 'amc' in t or 'after'  in t: return 'AMC 🌙'
        return t.upper() or '—'

    formatted = []
    today = datetime.now().strftime('%Y-%m-%d')
    for item in items[:30]:
        date    = item.get('date','')
        is_today = date == today
        days_out = (datetime.strptime(date, '%Y-%m-%d') - datetime.now()).days if date else 99
        formatted.append({
            "ticker":   item.get('ticker',''),
            "date":     date,
            "date_fmt": 'HOY' if is_today else date[5:] if date else '—',
            "is_today": is_today,
            "days_out": days_out,
            "time":     fmt_time(item.get('time','')),
            "eps_est":  item.get('eps_est'),
            "eps_actual": item.get('eps_actual'),
            "rev_est":  item.get('rev_est'),
            "price":    item.get('price'),
            "source":   item.get('source',''),
        })

    return {
        "ok":        True,
        "data":      formatted,
        "total":     len(formatted),
        "timestamp": datetime.now().strftime('%H:%M:%S'),
    }

def get_earnings_ticker(ticker: str) -> dict:
    surprise = _get_surprise(ticker.upper())
    yf_next  = _get_yf_earnings(ticker.upper())
    finnhub  = next((x for x in _get_finnhub_earnings() if x['ticker'] == ticker.upper()), {})

    next_date = yf_next.get('date') or finnhub.get('date','')
    eps_est   = yf_next.get('eps_est') or finnhub.get('eps_est')

    return {
        "ok":        True,
        "ticker":    ticker.upper(),
        "next_date": next_date,
        "eps_est":   eps_est,
        "surprise_history": surprise,
        "timestamp": datetime.now().strftime('%H:%M:%S'),
    }