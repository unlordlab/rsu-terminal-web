import yfinance as yf
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import json

MASSIVE_KEY = "0328d4QbyOxYeB1x8G4dl4PyfhemDqZW"
MASSIVE_BASE = "https://api.massive.com"

WATCHLIST = [
    "NVDA","AAPL","MSFT","AMZN","META","GOOGL","TSLA","AMD","AVGO","NFLX",
    "SPY","QQQ","IWM","GLD","TLT","HYG","XLK","XLF","XLE","XLV",
    "HOOD","MSTR","PLTR","CRWD","PANW","NET","UBER","ABNB","COIN","RKLB",
    "SOFI","MELI","NOW","ZS","SNOW","ARM","SMCI","AXON","NBIS","VIAV",
]

def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if not np.isnan(v) and not np.isinf(v) else default
    except Exception:
        return default

def _fmt_premium(val: float) -> str:
    if val >= 1_000_000: return f"${val/1_000_000:.1f}M"
    if val >= 1_000:     return f"${val/1_000:.0f}K"
    return f"${val:.0f}"

def _pct_from_atm(strike: float, price: float) -> str:
    if price <= 0: return ""
    pct = (strike - price) / price * 100
    return f"{pct:+.0f}%"

def _classify_sentiment(calls_vol: float, puts_vol: float) -> str:
    if calls_vol + puts_vol == 0: return "neutral"
    ratio = calls_vol / (calls_vol + puts_vol)
    if ratio >= 0.65:  return "bullish"
    if ratio <= 0.35:  return "bearish"
    return "neutral"

def _process_chain(ticker: str, min_premium: float = 50_000) -> dict:
    try:
        tk     = yf.Ticker(ticker)
        price  = None
        try:
            fi    = tk.fast_info
            price = _safe(getattr(fi, 'last_price', None))
        except Exception:
            pass
        if not price:
            hist  = tk.history(period="2d")
            price = float(hist['Close'].iloc[-1]) if not hist.empty else 0

        expirations = tk.options
        if not expirations:
            return {"ticker": ticker, "ok": False}

        # Tomar los próximos 4 vencimientos
        exps = expirations[:4]

        calls_bought, puts_bought, calls_sold, puts_sold = [], [], [], []
        total_call_vol, total_put_vol = 0, 0
        total_call_prem, total_put_prem = 0, 0

        for exp in exps:
            try:
                chain = tk.option_chain(exp)
            except Exception:
                continue

            for _, row in chain.calls.iterrows():
                vol     = _safe(row.get('volume', 0))
                oi      = _safe(row.get('openInterest', 0))
                price_c = _safe(row.get('lastPrice', 0))
                strike  = _safe(row.get('strike', 0))
                iv      = _safe(row.get('impliedVolatility', 0))
                premium = vol * price_c * 100
                if premium < min_premium or vol < 10: continue

                total_call_vol  += vol
                total_call_prem += premium

                # Heurística: vol >> OI → compra nueva; vol << OI → posición existente
                is_buy = vol > oi * 0.5 if oi > 0 else True
                entry = {
                    "ticker":    ticker,
                    "strike":    round(strike, 2),
                    "strike_pct": _pct_from_atm(strike, price),
                    "exp":       exp,
                    "volume":    int(vol),
                    "oi":        int(oi),
                    "price":     round(price_c, 2),
                    "premium":   premium,
                    "premium_fmt": _fmt_premium(premium),
                    "iv":        round(iv * 100, 1),
                    "type":      "call",
                    "action":    "buy" if is_buy else "sell",
                }
                if is_buy:
                    calls_bought.append(entry)
                else:
                    calls_sold.append(entry)

            for _, row in chain.puts.iterrows():
                vol     = _safe(row.get('volume', 0))
                oi      = _safe(row.get('openInterest', 0))
                price_p = _safe(row.get('lastPrice', 0))
                strike  = _safe(row.get('strike', 0))
                iv      = _safe(row.get('impliedVolatility', 0))
                premium = vol * price_p * 100
                if premium < min_premium or vol < 10: continue

                total_put_vol  += vol
                total_put_prem += premium

                is_buy = vol > oi * 0.5 if oi > 0 else False
                entry = {
                    "ticker":    ticker,
                    "strike":    round(strike, 2),
                    "strike_pct": _pct_from_atm(strike, price),
                    "exp":       exp,
                    "volume":    int(vol),
                    "oi":        int(oi),
                    "price":     round(price_p, 2),
                    "premium":   premium,
                    "premium_fmt": _fmt_premium(premium),
                    "iv":        round(iv * 100, 1),
                    "type":      "put",
                    "action":    "buy" if is_buy else "sell",
                }
                if is_buy:
                    puts_bought.append(entry)
                else:
                    puts_sold.append(entry)

        sentiment = _classify_sentiment(total_call_vol, total_put_vol)

        return {
            "ticker":       ticker,
            "ok":           True,
            "price":        round(price, 2),
            "total_call_vol":  int(total_call_vol),
            "total_put_vol":   int(total_put_vol),
            "total_call_prem": total_call_prem,
            "total_put_prem":  total_put_prem,
            "total_prem":      total_call_prem + total_put_prem,
            "sentiment":    sentiment,
            "calls_bought": sorted(calls_bought, key=lambda x: -x['premium'])[:10],
            "puts_bought":  sorted(puts_bought,  key=lambda x: -x['premium'])[:10],
            "calls_sold":   sorted(calls_sold,   key=lambda x: -x['premium'])[:10],
            "puts_sold":    sorted(puts_sold,    key=lambda x: -x['premium'])[:10],
        }
    except Exception as e:
        return {"ticker": ticker, "ok": False, "error": str(e)}

def get_options_flow(min_premium: float = 50_000, tickers: list = None) -> dict:
    target  = tickers or WATCHLIST
    results = []

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = {ex.submit(_process_chain, t, min_premium): t for t in target}
        for f in futures:
            r = f.result()
            if r.get('ok'):
                results.append(r)

    # Agregados globales
    all_calls_bought, all_puts_bought = [], []
    all_calls_sold,   all_puts_sold   = [], []

    for r in results:
        all_calls_bought.extend(r['calls_bought'])
        all_puts_bought.extend(r['puts_bought'])
        all_calls_sold.extend(r['calls_sold'])
        all_puts_sold.extend(r['puts_sold'])

    # Top rankings
    top_premium = sorted(results, key=lambda x: -x['total_prem'])[:10]
    top_bullish  = sorted(results, key=lambda x: -x['total_call_prem'])[:8]
    top_bearish  = sorted(results, key=lambda x: -x['total_put_prem'])[:8]

    return {
        "ok":           True,
        "scanned":      len(results),
        "calls_bought": sorted(all_calls_bought, key=lambda x: -x['premium'])[:50],
        "puts_bought":  sorted(all_puts_bought,  key=lambda x: -x['premium'])[:30],
        "calls_sold":   sorted(all_calls_sold,   key=lambda x: -x['premium'])[:30],
        "puts_sold":    sorted(all_puts_sold,    key=lambda x: -x['premium'])[:30],
        "top_premium":  [{"ticker": r['ticker'], "premium_fmt": _fmt_premium(r['total_prem']), "sentiment": r['sentiment']} for r in top_premium],
        "top_bullish":  [{"ticker": r['ticker'], "premium_fmt": _fmt_premium(r['total_call_prem'])} for r in top_bullish],
        "top_bearish":  [{"ticker": r['ticker'], "premium_fmt": _fmt_premium(r['total_put_prem'])} for r in top_bearish],
        "timestamp":    datetime.now().strftime('%H:%M:%S'),
        "date":         datetime.now().strftime('%Y-%m-%d'),
        "data_note":    "EOD Data · yfinance · Delayed",
    }

def get_options_ticker(ticker: str) -> dict:
    try:
        result = _process_chain(ticker.upper(), min_premium=0)
        if not result.get('ok'):
            return {"ok": False, "error": result.get('error', 'Sin datos')}

        # Historial via Massive (contratos más activos)
        history = _get_massive_history(ticker.upper())

        # Net Score: calls_bought - puts_bought (simplificado)
        net_score = len(result['calls_bought']) - len(result['puts_bought'])

        all_flow = []
        for item in result['calls_bought']:
            all_flow.append({**item, "order_type": "Buy Call",  "color": "bullish"})
        for item in result['puts_sold']:
            all_flow.append({**item, "order_type": "Sell Put",  "color": "bullish"})
        for item in result['puts_bought']:
            all_flow.append({**item, "order_type": "Buy Put",   "color": "bearish"})
        for item in result['calls_sold']:
            all_flow.append({**item, "order_type": "Sell Call", "color": "bearish"})

        all_flow.sort(key=lambda x: -x['premium'])

        return {
            "ok":        True,
            "ticker":    ticker.upper(),
            "price":     result['price'],
            "net_score": net_score,
            "sentiment": result['sentiment'],
            "flow":      all_flow[:30],
            "history":   history,
            "total_call_prem": _fmt_premium(result['total_call_prem']),
            "total_put_prem":  _fmt_premium(result['total_put_prem']),
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def _get_massive_history(ticker: str) -> list:
    try:
        # Obtener contratos disponibles
        r = requests.get(
            f"{MASSIVE_BASE}/v3/reference/options/contracts",
            params={"underlying_ticker": ticker, "limit": 20, "apiKey": MASSIVE_KEY},
            timeout=8
        )
        if r.status_code != 200: return []
        contracts = r.json().get('results', [])
        if not contracts: return []

        history = []
        today   = datetime.now().strftime('%Y-%m-%d')
        from_d  = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        for contract in contracts[:5]:
            cticker = contract['ticker']
            try:
                agg = requests.get(
                    f"{MASSIVE_BASE}/v2/aggs/ticker/{cticker}/range/1/day/{from_d}/{today}",
                    params={"limit": 10, "apiKey": MASSIVE_KEY},
                    timeout=8
                )
                if agg.status_code != 200: continue
                data = agg.json()
                if data.get('status') in ('NOT_AUTHORIZED', 'ERROR'): continue
                results = data.get('results', [])
                for bar in results:
                    vol     = bar.get('v', 0)
                    price_v = bar.get('vw', bar.get('c', 0))
                    premium = vol * price_v * 100
                    if premium < 10_000: continue
                    ts = datetime.fromtimestamp(bar['t'] / 1000)
                    history.append({
                        "date":      ts.strftime('%Y-%m-%d'),
                        "ticker":    cticker,
                        "strike":    contract['strike_price'],
                        "exp":       contract['expiration_date'],
                        "type":      contract['contract_type'],
                        "volume":    int(vol),
                        "premium":   premium,
                        "premium_fmt": _fmt_premium(premium),
                    })
            except Exception:
                continue

        history.sort(key=lambda x: x['date'], reverse=True)
        return history[:20]
    except Exception:
        return []