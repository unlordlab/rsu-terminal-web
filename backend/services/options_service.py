import yfinance as yf
import requests
import pandas as pd
import numpy as np
import sqlite3
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

MASSIVE_KEY  = ""   # unused — placeholder for future provider
MASSIVE_BASE = "https://api.massive.com"
DB_PATH      = os.path.join(os.path.dirname(__file__), '..', 'options_flow.db')

# ── UNIVERSO ──────────────────────────────────────────────────────────────────

WATCHLIST = [
    # Mega caps
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","BRK-B","JPM",
    "LLY","V","UNH","XOM","MA","JNJ","PG","HD","MRK","COST","ABBV","CVX",
    "BAC","KO","CRM","PEP","WFC","NFLX","ORCL","AMD","ACN","ADBE","LIN",
    # Tech/Growth
    "PLTR","CRWD","PANW","NET","SNOW","ARM","SMCI","AXON","NBIS","RKLB",
    "COIN","HOOD","MSTR","UBER","ABNB","DXCM","ZS","OKTA","DASH","RIVN",
    "SOFI","MELI","NOW","ANET","FTNT","CPNG","SHOP","SQ","PYPL","APP",
    "CELH","DUOL","TTD","HUBS","DDOG","MDB","ZM","BILL","DOCN","GTLB",
    # Finance
    "GS","MS","BLK","SCHW","COF","AXP","SPGI","ICE","CME","MCO",
    # Defense/Industrial
    "LMT","RTX","NOC","GD","BA","CAT","DE","HON","ETN","EMR",
    "BWXT","HII","LDOS","AXON","KTOS","AVAV",
    # Energy/Materials
    "XOM","CVX","COP","SLB","OXY","FCX","NEM","ALB","MP","UUUU",
    # ETFs
    "SPY","QQQ","IWM","DIA","TLT","GLD","GDX","GDXJ","HYG","LQD",
    "XLK","XLF","XLE","XLV","XLY","XLP","XLI","XLB","XLRE","XLC","XLU",
    "ARKK","IBIT","MAGS","BOTZ","UFO","ITA","NLR",
    # RSU Portfolio
    "COHR","UMAC","LTRX","VVX","MIR","EQT","PLPC","ENS","PRIM","GLXY",
    "BWXT","UUUU","LEU","VIAV","TOST","URG","BOTZ","USAR",
]
WATCHLIST = list(dict.fromkeys(WATCHLIST))

# Mapa sector → tickers (para heatmap)
SECTOR_MAP = {
    "Tech":       ["AAPL","MSFT","NVDA","AVGO","AMD","ADBE","CRM","ORCL","ACN","NOW","ANET"],
    "Growth":     ["PLTR","CRWD","PANW","NET","SNOW","ARM","COIN","MELI","DDOG","TTD","HUBS","APP"],
    "Finance":    ["JPM","V","MA","BAC","WFC","GS","MS","BLK","SCHW","AXP","SPGI","COF"],
    "Defense":    ["LMT","RTX","NOC","GD","BA","BWXT","HII","KTOS","AVAV","AXON"],
    "Energy":     ["XOM","CVX","COP","SLB","OXY","LEU","UUUU","MP","ALB"],
    "ETFs":       ["SPY","QQQ","IWM","DIA","TLT","GLD","XLK","XLF","XLE","IBIT"],
    "Consumer":   ["AMZN","TSLA","META","GOOGL","NFLX","HD","KO","PEP","COST","PG"],
}

# ── DB ────────────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS options_flow (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_date       TEXT NOT NULL,
            scan_ts         TEXT NOT NULL,
            ticker          TEXT NOT NULL,
            strike          REAL,
            exp             TEXT,
            type            TEXT,
            action          TEXT,
            premium         REAL,
            premium_fmt     TEXT,
            volume          INTEGER,
            oi              INTEGER,
            vol_oi_ratio    REAL,
            score           INTEGER,
            signal          TEXT,
            price           REAL,
            strike_pct      TEXT,
            iv              REAL,
            underlying_price REAL,
            is_block        INTEGER DEFAULT 0,
            is_sweep        INTEGER DEFAULT 0,
            near_earnings   INTEGER DEFAULT 0
        )
    ''')
    # Añadir columnas nuevas si no existen (migracion segura)
    for col, typedef in [
        ("is_block",    "INTEGER DEFAULT 0"),
        ("is_sweep",    "INTEGER DEFAULT 0"),
        ("near_earnings","INTEGER DEFAULT 0"),
    ]:
        try:
            conn.execute(f"ALTER TABLE options_flow ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ticker ON options_flow(ticker)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_date   ON options_flow(scan_date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_signal ON options_flow(signal)')
    conn.commit()
    conn.close()

def save_flow_to_db(flow_items: list, scan_ts: str):
    init_db()
    scan_date = scan_ts[:10]
    conn      = sqlite3.connect(DB_PATH)
    inserted  = 0
    for item in flow_items:
        existing = conn.execute(
            'SELECT id FROM options_flow WHERE scan_date=? AND ticker=? AND strike=? AND exp=? AND action=?',
            (scan_date, item['ticker'], item['strike'], item['exp'], item['action'])
        ).fetchone()
        if existing: continue
        conn.execute('''
            INSERT INTO options_flow
            (scan_date,scan_ts,ticker,strike,exp,type,action,premium,premium_fmt,
             volume,oi,vol_oi_ratio,score,signal,price,strike_pct,iv,underlying_price,
             is_block,is_sweep,near_earnings)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ''', (
            scan_date, scan_ts,
            item['ticker'], item['strike'], item['exp'],
            item['type'], item['action'],
            item['premium'], item['premium_fmt'],
            item['volume'], item['oi'], item['vol_oi_ratio'],
            item['score'], item['signal'],
            item['price'], item['strike_pct'], item['iv'],
            item['price'],
            int(item.get('is_block', False)),
            int(item.get('is_sweep', False)),
            int(item.get('near_earnings', False)),
        ))
        inserted += 1
    conn.commit()
    conn.close()
    return inserted

def get_history_from_db(ticker: str = None, period: str = '1w') -> list:
    init_db()
    days_map = {'1w': 7, '2w': 14, '1m': 30, '3m': 90}
    days     = days_map.get(period, 7)
    from_dt  = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn  = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    if ticker:
        rows = conn.execute(
            'SELECT * FROM options_flow WHERE ticker=? AND scan_date>=? ORDER BY scan_ts DESC LIMIT 200',
            (ticker.upper(), from_dt)
        ).fetchall()
    else:
        rows = conn.execute(
            'SELECT * FROM options_flow WHERE scan_date>=? ORDER BY premium DESC LIMIT 500',
            (from_dt,)
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_db_stats() -> dict:
    init_db()
    conn  = sqlite3.connect(DB_PATH)
    total = conn.execute('SELECT COUNT(*) FROM options_flow').fetchone()[0]
    days  = conn.execute('SELECT COUNT(DISTINCT scan_date) FROM options_flow').fetchone()[0]
    last  = conn.execute('SELECT MAX(scan_ts) FROM options_flow').fetchone()[0]
    top   = conn.execute(
        'SELECT ticker, COUNT(*) as cnt FROM options_flow GROUP BY ticker ORDER BY cnt DESC LIMIT 10'
    ).fetchall()
    conn.close()
    return {
        "total_records": total,
        "scan_days":     days,
        "last_scan":     last or "Sin scans",
        "top_tickers":   [{"ticker": r[0], "count": r[1]} for r in top],
    }

def get_repeat_signals(days: int = 7, min_repeats: int = 2) -> list:
    init_db()
    from_dt = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    conn    = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT
            ticker, strike, exp, type, action,
            COUNT(DISTINCT scan_date) as repeat_count,
            SUM(premium) as total_premium,
            AVG(score) as avg_score,
            MAX(underlying_price) as last_price,
            MIN(scan_date) as first_seen,
            MAX(scan_date) as last_seen,
            GROUP_CONCAT(DISTINCT premium_fmt) as premiums,
            MAX(underlying_price) - MIN(underlying_price) as price_delta
        FROM options_flow
        WHERE scan_date >= ?
        GROUP BY ticker, strike, exp, type, action
        HAVING repeat_count >= ?
        ORDER BY repeat_count DESC, total_premium DESC
        LIMIT 50
    ''', (from_dt, min_repeats)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d['total_premium_fmt'] = _fmt_premium(d['total_premium'])
        d['avg_score']         = round(d['avg_score'], 1)
        d['price_delta']       = round(d.get('price_delta') or 0, 2)
        result.append(d)
    return result

def get_ticker_history_summary(ticker: str) -> dict:
    """Resumen de un ticker con prima ponderada y momentum de sentimiento."""
    init_db()
    from_dt = (datetime.now() - timedelta(days=90)).strftime('%Y-%m-%d')
    conn    = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT scan_date, type, action, strike, exp,
               premium, score, signal, underlying_price, strike_pct,
               is_block, is_sweep, near_earnings
        FROM options_flow
        WHERE ticker=? AND scan_date>=?
        ORDER BY scan_date DESC
    ''', (ticker.upper(), from_dt)).fetchall()
    conn.close()

    if not rows:
        return {"ok": False, "error": "Sin historial para " + ticker}

    current_price = 0.0
    try:
        tk = yf.Ticker(ticker.upper())
        fi = tk.fast_info
        current_price = float(getattr(fi, 'last_price', 0) or 0)
    except Exception:
        pass

    records   = [dict(r) for r in rows]
    bull_prem = sum(r['premium'] for r in records
                    if (r['type']=='call' and r['action']=='buy') or
                       (r['type']=='put'  and r['action']=='sell'))
    bear_prem = sum(r['premium'] for r in records
                    if (r['type']=='put'  and r['action']=='buy') or
                       (r['type']=='call' and r['action']=='sell'))

    total_prem = bull_prem + bear_prem
    # Net Premium Score normalizado [-1, +1]
    nps = (bull_prem - bear_prem) / total_prem if total_prem > 0 else 0.0

    # Agrupar por mes con prima ponderada
    weekly: dict = {}
    for r in records:
        week = r['scan_date'][:7]
        if week not in weekly:
            weekly[week] = {"bull_prem": 0, "bear_prem": 0, "bull_cnt": 0,
                            "bear_cnt": 0, "count": 0, "price": r['underlying_price']}
        is_bull = (r['type']=='call' and r['action']=='buy') or \
                  (r['type']=='put'  and r['action']=='sell')
        if is_bull:
            weekly[week]['bull_prem'] += r['premium']
            weekly[week]['bull_cnt']  += 1
        else:
            weekly[week]['bear_prem'] += r['premium']
            weekly[week]['bear_cnt']  += 1
        weekly[week]['count'] += 1

    weekly_list = []
    for k, v in sorted(weekly.items(), reverse=True):
        tp = v['bull_prem'] + v['bear_prem']
        nps_w = (v['bull_prem'] - v['bear_prem']) / tp if tp > 0 else 0
        weekly_list.append({
            "week":       k,
            "bull_prem":  _fmt_premium(v['bull_prem']),
            "bear_prem":  _fmt_premium(v['bear_prem']),
            "bull_cnt":   v['bull_cnt'],
            "bear_cnt":   v['bear_cnt'],
            "net_prem_score": round(nps_w * 100, 1),  # % de -100 a +100
            "count":      v['count'],
            "price":      v['price'],
        })

    # Momentum: sentimiento hoy vs ayer
    sentiment_momentum = _calc_sentiment_momentum(records)

    if abs(nps) >= 0.3:
        net_bias = "ALCISTA" if nps > 0 else "BAJISTA"
    else:
        net_bias = "NEUTRAL"

    return {
        "ok":              True,
        "ticker":          ticker.upper(),
        "current_price":   round(current_price, 2),
        "total_records":   len(records),
        "bull_premium":    _fmt_premium(bull_prem),
        "bear_premium":    _fmt_premium(bear_prem),
        "net_premium_score": round(nps * 100, 1),
        "net_bias":        net_bias,
        "sentiment_momentum": sentiment_momentum,
        "records":         records[:50],
        "weekly":          weekly_list,
    }

def _calc_sentiment_momentum(records: list) -> dict:
    """Compara bull_prem hoy vs ayer para detectar cambio de sentimiento."""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

    def prem_score(recs):
        bull = sum(r['premium'] for r in recs
                   if (r['type']=='call' and r['action']=='buy') or
                      (r['type']=='put'  and r['action']=='sell'))
        bear = sum(r['premium'] for r in recs
                   if (r['type']=='put'  and r['action']=='buy') or
                      (r['type']=='call' and r['action']=='sell'))
        tot = bull + bear
        return (bull - bear) / tot if tot > 0 else None

    today_recs = [r for r in records if r['scan_date'] == today]
    yest_recs  = [r for r in records if r['scan_date'] == yesterday]
    today_nps  = prem_score(today_recs)
    yest_nps   = prem_score(yest_recs)

    if today_nps is None or yest_nps is None:
        return {"available": False}

    delta = today_nps - yest_nps
    direction = "mejorando" if delta > 0.1 else "empeorando" if delta < -0.1 else "estable"
    return {
        "available":  True,
        "today_nps":  round(today_nps * 100, 1),
        "yest_nps":   round(yest_nps * 100, 1),
        "delta":      round(delta * 100, 1),
        "direction":  direction,
    }

# ── HELPERS ───────────────────────────────────────────────────────────────────

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

def _score_entry(vol, oi, premium, iv, exp_days, strike_pct_val) -> tuple:
    score  = 0
    signal = "LOW"

    # Prima (ponderación mayor — es el criterio principal)
    if premium >= 2_000_000: score += 4
    elif premium >= 1_000_000: score += 3
    elif premium >= 500_000: score += 2
    elif premium >= 100_000: score += 1

    # Vol/OI ratio
    vol_oi = vol / oi if oi > 0 else vol
    if vol_oi >= 5.0:   score += 3   # UNUSUAL
    elif vol_oi >= 2.0: score += 2
    elif vol_oi >= 0.5: score += 1

    # IV
    if iv >= 0.80:   score += 2
    elif iv >= 0.40: score += 1

    # Strike OTM sweet spot (5-25%)
    abs_pct = abs(strike_pct_val)
    if 5 <= abs_pct <= 25: score += 2
    elif abs_pct <= 5:     score += 1

    # Vencimiento
    if 14 <= exp_days <= 60:   score += 1

    # Señal
    is_unusual = (vol / oi >= 5.0) if oi > 0 else False
    if score >= 9 or (score >= 7 and is_unusual): signal = "UNUSUAL"
    elif score >= 7:   signal = "HIGH"
    elif score >= 4:   signal = "MEDIUM"
    else:              signal = "LOW"

    return score, signal, round(vol_oi, 2)

def _get_next_earnings(ticker: str) -> str | None:
    """Intenta obtener la próxima fecha de earnings de yfinance."""
    try:
        tk = yf.Ticker(ticker)
        cal = tk.calendar
        if cal is not None and not cal.empty:
            if 'Earnings Date' in cal.index:
                ed = cal.loc['Earnings Date'].values
                if len(ed) > 0:
                    return str(pd.Timestamp(ed[0]).date())
    except Exception:
        pass
    return None

def _classify_sentiment(calls_vol, puts_vol):
    if calls_vol + puts_vol == 0: return "neutral"
    ratio = calls_vol / (calls_vol + puts_vol)
    if ratio >= 0.65:  return "bullish"
    if ratio <= 0.35:  return "bearish"
    return "neutral"

def _classify_sentiment_by_premium(bull_prem, bear_prem):
    """Sentimiento por prima ponderada — más fiable que por volumen."""
    total = bull_prem + bear_prem
    if total == 0: return "neutral"
    ratio = bull_prem / total
    if ratio >= 0.60:  return "bullish"
    if ratio <= 0.40:  return "bearish"
    return "neutral"

def _detect_sweeps(entries_by_exp: dict) -> set:
    """
    Detecta sweep: 3+ entradas del mismo tipo en el mismo exp con vol/OI > 1.
    Retorna set de (ticker, exp, type).
    """
    sweeps = set()
    for key, entries in entries_by_exp.items():
        high_vol = [e for e in entries if e.get('vol_oi_ratio', 0) >= 1.0]
        if len(high_vol) >= 3:
            sweeps.add(key)
    return sweeps

# ── SCAN ENGINE ───────────────────────────────────────────────────────────────

def _process_chain(ticker: str, min_premium: float = 100_000, min_score: int = 4) -> dict:
    try:
        tk    = yf.Ticker(ticker)
        price = 0.0
        try:
            fi    = tk.fast_info
            price = _safe(getattr(fi, 'last_price', None))
        except Exception: pass
        if not price:
            hist  = tk.history(period="2d")
            price = float(hist['Close'].iloc[-1]) if not hist.empty else 0

        expirations = tk.options
        if not expirations: return {"ticker": ticker, "ok": False}

        # Intentar obtener next earnings
        next_earnings = _get_next_earnings(ticker)

        exps  = expirations[:5]
        today = datetime.now().date()

        calls_bought, puts_bought, calls_sold, puts_sold = [], [], [], []
        total_call_vol, total_put_vol = 0, 0
        bull_prem_total, bear_prem_total = 0, 0
        entries_by_exp: dict = {}   # para sweep detection

        for exp in exps:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                exp_days = (exp_date - today).days
                if exp_days < 7 or exp_days > 180: continue
                chain = tk.option_chain(exp)
            except Exception:
                continue

            # Earnings proximity
            near_earnings = False
            if next_earnings:
                try:
                    ed = datetime.strptime(next_earnings, '%Y-%m-%d').date()
                    near_earnings = (exp_date >= ed) and ((exp_date - ed).days <= 7)
                except Exception:
                    pass

            for opt_type, df in [('call', chain.calls), ('put', chain.puts)]:
                for _, row in df.iterrows():
                    vol     = _safe(row.get('volume', 0))
                    oi      = _safe(row.get('openInterest', 0))
                    price_o = _safe(row.get('lastPrice', 0))
                    strike  = _safe(row.get('strike', 0))
                    iv      = _safe(row.get('impliedVolatility', 0))

                    if vol < 10 or price_o < 0.10: continue

                    premium = vol * price_o * 100
                    if premium < min_premium: continue

                    strike_pct_val = (strike - price) / price * 100 if price > 0 else 0
                    strike_pct     = _pct_from_atm(strike, price)

                    score, signal, vol_oi = _score_entry(vol, oi, premium, iv, exp_days, strike_pct_val)
                    if score < min_score: continue

                    is_buy   = (vol / oi >= 0.3) if oi > 0 else True
                    # Block trade: prima alta, pocos contratos → institucional LEAPS
                    is_block = premium >= 500_000 and vol < 500

                    entry = {
                        "ticker":       ticker,
                        "strike":       round(strike, 2),
                        "strike_pct":   strike_pct,
                        "exp":          exp,
                        "exp_days":     exp_days,
                        "volume":       int(vol),
                        "oi":           int(oi),
                        "vol_oi_ratio": vol_oi,
                        "price":        round(price, 2),
                        "price_opt":    round(price_o, 2),
                        "premium":      premium,
                        "premium_fmt":  _fmt_premium(premium),
                        "iv":           round(iv * 100, 1),
                        "type":         opt_type,
                        "action":       "buy" if is_buy else "sell",
                        "score":        score,
                        "signal":       signal,
                        "color":        "bullish" if (opt_type=='call' and is_buy) or
                                                     (opt_type=='put'  and not is_buy)
                                                  else "bearish",
                        "is_block":     is_block,
                        "near_earnings": near_earnings,
                        "is_sweep":     False,   # se rellena después
                    }

                    # Acumular para sweep detection
                    sweep_key = (ticker, exp, opt_type)
                    entries_by_exp.setdefault(sweep_key, []).append(entry)

                    is_bull = (opt_type=='call' and is_buy) or (opt_type=='put' and not is_buy)
                    if opt_type == 'call':
                        total_call_vol += vol
                        if is_buy:
                            calls_bought.append(entry)
                            bull_prem_total += premium
                        else:
                            calls_sold.append(entry)
                            bear_prem_total += premium
                    else:
                        total_put_vol += vol
                        if is_buy:
                            puts_bought.append(entry)
                            bear_prem_total += premium
                        else:
                            puts_sold.append(entry)
                            bull_prem_total += premium

        # Marcar sweeps
        sweep_keys = _detect_sweeps(entries_by_exp)
        for lst in [calls_bought, puts_bought, calls_sold, puts_sold]:
            for e in lst:
                sk = (e['ticker'], e['exp'], e['type'])
                if sk in sweep_keys:
                    e['is_sweep'] = True

        # Net Premium Score normalizado
        total_prem = bull_prem_total + bear_prem_total
        net_prem_score = (bull_prem_total - bear_prem_total) / total_prem if total_prem > 0 else 0.0

        # Put/Call ratio por prima
        pc_ratio_prem = bear_prem_total / bull_prem_total if bull_prem_total > 0 else float('inf')

        return {
            "ticker":          ticker,
            "ok":              True,
            "price":           round(price, 2),
            # Sentimiento por volumen (legacy) + por prima (nuevo)
            "sentiment":       _classify_sentiment(total_call_vol, total_put_vol),
            "sentiment_prem":  _classify_sentiment_by_premium(bull_prem_total, bear_prem_total),
            "net_prem_score":  round(net_prem_score * 100, 1),   # -100 a +100
            "pc_ratio_prem":   round(pc_ratio_prem, 2),
            "bull_prem":       bull_prem_total,
            "bear_prem":       bear_prem_total,
            "total_call_prem": bull_prem_total + sum(e['premium'] for e in calls_sold),
            "total_put_prem":  bear_prem_total + sum(e['premium'] for e in puts_sold),
            "total_prem":      total_prem,
            "calls_bought":    sorted(calls_bought, key=lambda x: -x['score'])[:15],
            "puts_bought":     sorted(puts_bought,  key=lambda x: -x['score'])[:10],
            "calls_sold":      sorted(calls_sold,   key=lambda x: -x['score'])[:10],
            "puts_sold":       sorted(puts_sold,    key=lambda x: -x['score'])[:10],
            "next_earnings":   next_earnings,
        }
    except Exception as e:
        return {"ticker": ticker, "ok": False, "error": str(e)}

def get_options_flow(min_premium: float = 100_000, min_score: int = 4, tickers: list = None) -> dict:
    target  = tickers or WATCHLIST
    results = []
    scan_ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_process_chain, t, min_premium, min_score): t for t in target}
        for f in futures:
            r = f.result()
            if r.get('ok') and r['total_prem'] > 0:
                results.append(r)

    all_calls_bought, all_puts_bought = [], []
    all_calls_sold,   all_puts_sold   = [], []
    all_high_signal, all_unusual      = [], []

    for r in results:
        all_calls_bought.extend(r['calls_bought'])
        all_puts_bought.extend(r['puts_bought'])
        all_calls_sold.extend(r['calls_sold'])
        all_puts_sold.extend(r['puts_sold'])

    for item in all_calls_bought + all_puts_bought + all_calls_sold + all_puts_sold:
        if item['signal'] == 'UNUSUAL':
            all_unusual.append(item)
        elif item['signal'] == 'HIGH':
            all_high_signal.append(item)

    # Top por prima ponderada (bull_prem vs bear_prem)
    top_premium  = sorted(results, key=lambda x: -x['total_prem'])[:12]
    top_bullish  = sorted(results, key=lambda x: -x['net_prem_score'])[:8]
    top_bearish  = sorted(results, key=lambda x: x['net_prem_score'])[:8]

    # Heatmap sectorial
    sector_heat = _build_sector_heatmap(results)

    # Block trades
    all_blocks = [e for e in all_calls_bought + all_puts_bought + all_calls_sold + all_puts_sold
                  if e.get('is_block')]

    # Sweep trades
    all_sweeps = [e for e in all_calls_bought + all_puts_bought + all_calls_sold + all_puts_sold
                  if e.get('is_sweep')]

    # Near earnings
    near_earn  = [e for e in all_calls_bought + all_puts_bought + all_calls_sold + all_puts_sold
                  if e.get('near_earnings')]

    return {
        "ok":           True,
        "scanned":      len(target),
        "matched":      len(results),
        "scan_ts":      scan_ts,
        "calls_bought": sorted(all_calls_bought, key=lambda x: (-x['score'], -x['premium']))[:50],
        "puts_bought":  sorted(all_puts_bought,  key=lambda x: (-x['score'], -x['premium']))[:30],
        "calls_sold":   sorted(all_calls_sold,   key=lambda x: (-x['score'], -x['premium']))[:30],
        "puts_sold":    sorted(all_puts_sold,    key=lambda x: (-x['score'], -x['premium']))[:30],
        "high_signals": sorted(all_high_signal,  key=lambda x: -x['premium'])[:20],
        "unusual":      sorted(all_unusual,      key=lambda x: -x['premium'])[:15],
        "blocks":       sorted(all_blocks,       key=lambda x: -x['premium'])[:15],
        "sweeps":       sorted(all_sweeps,       key=lambda x: -x['premium'])[:15],
        "near_earnings":sorted(near_earn,        key=lambda x: -x['premium'])[:15],
        "top_premium":  [{"ticker": r['ticker'],
                          "premium_fmt": _fmt_premium(r['total_prem']),
                          "sentiment_prem": r['sentiment_prem'],
                          "net_prem_score": r['net_prem_score']} for r in top_premium],
        "top_bullish":  [{"ticker": r['ticker'],
                          "premium_fmt": _fmt_premium(r['bull_prem']),
                          "net_prem_score": r['net_prem_score']} for r in top_bullish],
        "top_bearish":  [{"ticker": r['ticker'],
                          "premium_fmt": _fmt_premium(r['bear_prem']),
                          "net_prem_score": r['net_prem_score']} for r in top_bearish],
        "sector_heat":  sector_heat,
        "timestamp":    datetime.now().strftime('%H:%M:%S'),
        "data_note":    "EOD Data · yfinance · Delayed",
    }

def _build_sector_heatmap(results: list) -> list:
    """Agrupa bull/bear premium por sector para el heatmap."""
    ticker_to_result = {r['ticker']: r for r in results}
    heat = []
    for sector, tickers in SECTOR_MAP.items():
        bull = 0.0
        bear = 0.0
        matched = []
        for t in tickers:
            r = ticker_to_result.get(t)
            if r:
                bull    += r.get('bull_prem', 0)
                bear    += r.get('bear_prem', 0)
                matched.append(t)
        total = bull + bear
        if total == 0: continue
        nps = (bull - bear) / total
        heat.append({
            "sector":   sector,
            "bull":     _fmt_premium(bull),
            "bear":     _fmt_premium(bear),
            "nps":      round(nps * 100, 1),
            "bias":     "bullish" if nps > 0.1 else "bearish" if nps < -0.1 else "neutral",
            "tickers":  matched,
        })
    return sorted(heat, key=lambda x: -abs(x['nps']))

def save_current_scan(flow_data: dict) -> dict:
    all_items = (
        flow_data.get('calls_bought', []) +
        flow_data.get('puts_bought',  []) +
        flow_data.get('calls_sold',   []) +
        flow_data.get('puts_sold',    [])
    )
    inserted = save_flow_to_db(all_items, flow_data['scan_ts'])
    return {"ok": True, "inserted": inserted, "total": len(all_items)}

def get_options_ticker(ticker: str) -> dict:
    try:
        result = _process_chain(ticker.upper(), min_premium=0, min_score=0)
        if not result.get('ok'):
            return {"ok": False, "error": result.get('error', 'Sin datos')}

        # Net Premium Score en lugar de conteo simple
        bull_prem = result['bull_prem']
        bear_prem = result['bear_prem']
        total_prem = bull_prem + bear_prem
        net_prem_score = (bull_prem - bear_prem) / total_prem if total_prem > 0 else 0.0

        # PC ratio por prima
        pc_ratio_prem = bear_prem / bull_prem if bull_prem > 0 else None

        # Sentimiento ponderado
        sentiment_prem = result['sentiment_prem']

        all_flow = []
        for item in result['calls_bought']:
            all_flow.append({**item, "order_type": "Buy Call"})
        for item in result['puts_sold']:
            all_flow.append({**item, "order_type": "Sell Put"})
        for item in result['puts_bought']:
            all_flow.append({**item, "order_type": "Buy Put"})
        for item in result['calls_sold']:
            all_flow.append({**item, "order_type": "Sell Call"})

        all_flow.sort(key=lambda x: -x['premium'])

        # Señales especiales
        unusual = [e for e in all_flow if e['signal'] == 'UNUSUAL']
        blocks  = [e for e in all_flow if e.get('is_block')]
        sweeps  = [e for e in all_flow if e.get('is_sweep')]

        return {
            "ok":              True,
            "ticker":          ticker.upper(),
            "price":           result['price'],
            "net_prem_score":  round(net_prem_score * 100, 1),
            "sentiment":       result['sentiment'],
            "sentiment_prem":  sentiment_prem,
            "pc_ratio_prem":   round(pc_ratio_prem, 2) if pc_ratio_prem else None,
            "bull_prem":       _fmt_premium(bull_prem),
            "bear_prem":       _fmt_premium(bear_prem),
            "flow":            all_flow[:40],
            "unusual":         unusual[:5],
            "blocks":          blocks[:5],
            "sweeps":          sweeps[:5],
            "next_earnings":   result.get('next_earnings'),
            "total_call_prem": _fmt_premium(result['total_call_prem']),
            "total_put_prem":  _fmt_premium(result['total_put_prem']),
            "timestamp":       datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}