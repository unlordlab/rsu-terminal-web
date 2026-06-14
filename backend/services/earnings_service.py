import yfinance as yf
import requests
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import os
from dotenv import load_dotenv
load_dotenv()

FMP_KEY     = os.getenv("fmp_api_key", "")
FINNHUB_KEY = os.getenv("finnhub_api_key", "")

def _get_timestamp():
    from services.market_service import get_timestamp
    return get_timestamp()

# ── FUENTE 1: FMP ─────────────────────────────────────────────────────────────

def _get_fmp_earnings(from_date: str, to_date: str) -> list:
    try:
        url  = f"https://financialmodelingprep.com/api/v3/earning_calendar?from={from_date}&to={to_date}&apikey={FMP_KEY}"
        r    = requests.get(url, timeout=8)
        data = r.json()
        if not isinstance(data, list): return []
        results = []
        for item in data[:80]:
            ticker = item.get('symbol', '')
            if not ticker: continue
            results.append({
                "ticker":  ticker,
                "date":    item.get('date', ''),
                "time":    item.get('time', ''),
                "eps_est": item.get('epsEstimated'),
                "rev_est": item.get('revenueEstimated'),
                "source":  "FMP",
            })
        return results
    except Exception:
        return []

# ── FUENTE 2: Finnhub ─────────────────────────────────────────────────────────

def _get_finnhub_earnings(from_date: str, to_date: str) -> list:
    try:
        url  = f"https://finnhub.io/api/v1/calendar/earnings?from={from_date}&to={to_date}&token={FINNHUB_KEY}"
        r    = requests.get(url, timeout=8)
        data = r.json().get('earningsCalendar', [])
        results = []
        for item in data[:80]:
            ticker = item.get('symbol', '')
            if not ticker: continue
            results.append({
                "ticker":     ticker,
                "date":       item.get('date', ''),
                "time":       item.get('hour', ''),
                "eps_est":    item.get('epsEstimate'),
                "eps_actual": item.get('epsActual'),
                "rev_est":    item.get('revenueEstimate'),
                "source":     "Finnhub",
            })
        return results
    except Exception:
        return []

# ── FUENTE 3: yfinance individual ─────────────────────────────────────────────

def _get_yf_earnings(ticker: str) -> dict:
    try:
        tk  = yf.Ticker(ticker)
        cal = tk.calendar
        if cal is None or cal.empty:
            return {}
        date_col = cal.columns[0] if hasattr(cal, 'columns') else None
        if date_col is None:
            return {}
        eps_est = cal.loc['EPS Estimate', date_col] if 'EPS Estimate' in cal.index else None
        rev_est = cal.loc['Revenue Estimate', date_col] if 'Revenue Estimate' in cal.index else None
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

def _get_surprise(ticker: str) -> list:
    try:
        tk = yf.Ticker(ticker)
        results = []

        # Intento 1: earnings_history (yfinance moderno)
        try:
            hist = tk.earnings_history
            if hist is not None and not hist.empty:
                for _, row in hist.tail(4).iterrows():
                    actual   = row.get('epsActual', None)
                    estimate = row.get('epsEstimate', None)
                    date     = str(row.name)[:10] if hasattr(row, 'name') else ''
                    if actual is None or estimate is None: continue
                    actual   = float(actual)
                    estimate = float(estimate)
                    surprise = ((actual - estimate) / abs(estimate) * 100) if estimate != 0 else 0
                    results.append({
                        "quarter":  date,
                        "actual":   round(actual, 2),
                        "estimate": round(estimate, 2),
                        "surprise": round(surprise, 1),
                    })
                if results:
                    return results[::-1]
        except Exception:
            pass

        # Intento 2: quarterly_earnings
        try:
            hist = tk.quarterly_earnings
            if hist is not None and not hist.empty:
                for date, row in hist.tail(4).iterrows():
                    actual   = row.get('Actual', None)
                    estimate = row.get('Estimate', None)
                    if actual is None or estimate is None: continue
                    actual   = float(actual)
                    estimate = float(estimate)
                    surprise = ((actual - estimate) / abs(estimate) * 100) if estimate != 0 else 0
                    results.append({
                        "quarter":  str(date)[:10],
                        "actual":   round(actual, 2),
                        "estimate": round(estimate, 2),
                        "surprise": round(surprise, 1),
                    })
                if results:
                    return results[::-1]
        except Exception:
            pass

        # Intento 3: Finnhub earnings
        try:
            url = f"https://finnhub.io/api/v1/stock/earnings?symbol={ticker}&token={FINNHUB_KEY}"
            r   = requests.get(url, timeout=8)
            data = r.json()
            if isinstance(data, list) and data:
                for item in data[:4]:
                    actual   = item.get('actual')
                    estimate = item.get('estimate')
                    if actual is None or estimate is None: continue
                    actual   = float(actual)
                    estimate = float(estimate)
                    surprise = ((actual - estimate) / abs(estimate) * 100) if estimate != 0 else 0
                    results.append({
                        "quarter":  item.get('period', '')[:10],
                        "actual":   round(actual, 2),
                        "estimate": round(estimate, 2),
                        "surprise": round(surprise, 1),
                    })
                return results
        except Exception:
            pass

        return []
    except Exception:
        return []

# ── MAIN ──────────────────────────────────────────────────────────────────────

def get_earnings_calendar() -> dict:
    now     = datetime.now()
    weekday = now.weekday()  # 0=lunes, 5=sábado, 6=domingo
    if weekday == 5:
        start = now + timedelta(days=2)
    elif weekday == 6:
        start = now + timedelta(days=1)
    else:
        start = now

    from_date = start.strftime('%Y-%m-%d')
    to_date   = (start + timedelta(days=14)).strftime('%Y-%m-%d')

    fmp_data     = _get_fmp_earnings(from_date, to_date)
    finnhub_data = _get_finnhub_earnings(from_date, to_date)

    merged = {}
    for item in finnhub_data + fmp_data:
        key = item['ticker'] + '_' + item['date']
        merged[key] = item

    items = list(merged.values())
    items.sort(key=lambda x: x.get('date', ''))

    def enrich(item):
        try:
            tk    = yf.Ticker(item['ticker'])
            fi    = tk.fast_info
            price = round(float(getattr(fi, 'last_price', 0) or 0), 2)
            item['price'] = price
        except Exception:
            item['price'] = None
        return item

    with ThreadPoolExecutor(max_workers=8) as ex:
        items[:20] = list(ex.map(enrich, items[:20]))

    def fmt_time(t):
        t = (t or '').lower()
        if 'bmo' in t or 'before' in t: return 'BMO 🌅'
        if 'amc' in t or 'after'  in t: return 'AMC 🌙'
        return t.upper() or '—'

    formatted = []
    today = now.strftime('%Y-%m-%d')
    for item in items[:30]:
        date     = item.get('date', '')
        is_today = date == today
        try:
            days_out = (datetime.strptime(date, '%Y-%m-%d') - now).days
        except Exception:
            days_out = 99
        formatted.append({
            "ticker":     item.get('ticker', ''),
            "date":       date,
            "date_fmt":   'HOY' if is_today else date[5:] if date else '—',
            "is_today":   is_today,
            "days_out":   days_out,
            "time":       fmt_time(item.get('time', '')),
            "eps_est":    item.get('eps_est'),
            "eps_actual": item.get('eps_actual'),
            "rev_est":    item.get('rev_est'),
            "price":      item.get('price'),
            "source":     item.get('source', ''),
        })

    return {
        "ok":        True,
        "data":      formatted,
        "total":     len(formatted),
        "from_date": from_date,
        "to_date":   to_date,
        "timestamp": datetime.now().strftime('%H:%M:%S'),
    }

def get_earnings_ticker(ticker: str) -> dict:
    now      = datetime.now()
    weekday  = now.weekday()
    if weekday == 5:   start = now + timedelta(days=2)
    elif weekday == 6: start = now + timedelta(days=1)
    else:              start = now
    from_date = start.strftime('%Y-%m-%d')
    to_date   = (start + timedelta(days=30)).strftime('%Y-%m-%d')

    surprise = _get_surprise(ticker.upper())
    yf_next  = _get_yf_earnings(ticker.upper())
    finnhub  = next((x for x in _get_finnhub_earnings(from_date, to_date) if x['ticker'] == ticker.upper()), {})

    next_date = yf_next.get('date') or finnhub.get('date', '')
    eps_est   = yf_next.get('eps_est') or finnhub.get('eps_est')

    return {
        "ok":               True,
        "ticker":           ticker.upper(),
        "next_date":        next_date,
        "eps_est":          eps_est,
        "surprise_history": surprise,
        "timestamp":        datetime.now().strftime('%H:%M:%S'),
    }