import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import warnings
warnings.filterwarnings('ignore')

# ── S&P 500 UNIVERSE ──────────────────────────────────────────────────────────

SP500_TICKERS = [
    "MMM","AOS","ABT","ABBV","ACN","ADBE","AMD","AES","AFL","APD","ABNB",
    "AKAM","ALB","ARE","ALGN","ALLE","LNT","ALL","GOOGL","MO","AMZN","AMCR",
    "AEE","AAL","AEP","AXP","AIG","AMT","AWK","AMP","AME","AMGN","APH","ADI",
    "ANSS","AON","APA","AAPL","AMAT","APTV","ACGL","ADM","ANET","AJG","AIZ",
    "T","ATO","ADSK","ADP","AZO","AVB","AVY","AXON","BKR","BALL","BAC","BK",
    "BBWI","BAX","BDX","BBY","BIIB","BLK","BX","BA","BKNG","BWA","BSX","BMY",
    "AVGO","BR","BRO","BLDR","BG","CDNS","CPT","CPB","COF","CAH","KMX","CCL",
    "CARR","CAT","CBOE","CBRE","CDW","CNC","SCHW","CHTR","CVX","CMG","CB",
    "CI","CINF","CTAS","CSCO","C","CFG","CLX","CME","CMS","KO","CTSH","CL",
    "CMCSA","CMA","CAG","COP","ED","STZ","CEG","COO","CPRT","GLW","CPAY",
    "CTVA","CSGP","COST","CTRA","CCI","CSX","CMI","CVS","DHR","DRI","DVA",
    "DAY","DE","DAL","XRAY","DVN","DXCM","FANG","DLR","DFS","DG","DLTR","D",
    "DPZ","DOV","DOW","DHI","DTE","DUK","DD","EMN","ETN","EBAY","ECL","EIX",
    "EW","EA","ELV","LLY","EMR","ENPH","ETR","EOG","EPAM","EQT","EFX","EQIX",
    "EQR","ESS","EL","ETSY","EG","EVRG","ES","EXC","EXPE","EXPD","EXR","XOM",
    "FFIV","FDS","FICO","FAST","FRT","FDX","FIS","FITB","FSLR","FE","FI","F",
    "FTNT","FTV","FOXA","FOX","BEN","FCX","GRMN","IT","GE","GEHC","GEN","GIS",
    "GPC","GILD","GPN","GL","GS","HAL","HIG","HAS","HCA","DOC","HSIC","HSY",
    "HES","HPE","HLT","HOLX","HD","HON","HRL","HST","HWM","HPQ","HUBB","HUM",
    "HBAN","HII","IBM","IEX","IDXX","ITW","INCY","IR","PODD","INTC","ICE",
    "IFF","IP","IPG","INTU","ISRG","IVZ","INVH","IQV","IRM","JBHT","JBL",
    "JKHY","J","JNJ","JCI","JPM","JNPR","K","KVUE","KDP","KEY","KEYS","KMB",
    "KIM","KMI","KLAC","KHC","KR","LHX","LH","LRCX","LW","LVS","LDOS","LEN",
    "LIN","LYV","LKQ","LMT","L","LOW","LULU","LYB","MTB","MRO","MPC","MKTX",
    "MAR","MMC","MLM","MAS","META","MET","MTD","MGM","MCHP","MU","MSFT","MAA",
    "MRNA","MHK","MOH","TAP","MDLZ","MPWR","MNST","MCO","MS","MOS","MSI","MSCI",
    "NDAQ","NTAP","NFLX","NEM","NWSA","NWS","NEE","NKE","NI","NDSN","NSC",
    "NTRS","NOC","NCLH","NRG","NUE","NVDA","NVR","NXPI","ORLY","OXY","ODFL",
    "OMC","ON","OKE","ORCL","OTIS","PCAR","PKG","PANW","PH","PAYX","PAYC",
    "PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PXD","PNC","POOL","PPG",
    "PPL","PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","QRVO","PWR",
    "QCOM","DGX","RL","RJF","RTX","O","REG","REGN","RF","RSG","RMD","RVTY",
    "ROK","ROL","ROP","ROST","RCL","SPGI","CRM","SBAC","SLB","STX","SRE","NOW",
    "SHW","SPG","SWKS","SJM","SNA","SOLV","SO","LUV","SWK","SBUX","STT","STLD",
    "STE","SYK","SYF","SNPS","SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT",
    "TEL","TDY","TFX","TER","TSLA","TXN","TXT","TMO","TJX","TSCO","TT","TDG",
    "TRV","TRMB","TFC","TYL","TSN","USB","UBER","UDR","ULTA","UNP","UAL","UPS",
    "URI","UNH","UHS","VLO","VTR","VLTO","VRSN","VRSK","VZ","VRTX","VTRS",
    "VICI","V","VMC","WRB","GWW","WAB","WBA","WMT","DIS","WBD","WM","WAT",
    "WEC","WFC","WELL","WST","WDC","WRK","WY","WHR","WMB","WTW","WYNN","XEL",
    "XYL","YUM","ZBRA","ZBH","ZTS"
]

# ── HELPERS ───────────────────────────────────────────────────────────────────

def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if not np.isnan(v) and not np.isinf(v) else default
    except Exception:
        return default

def _get_timestamp():
    return datetime.now().strftime('%H:%M:%S')

# ── IBD RATINGS ───────────────────────────────────────────────────────────────

def _rs_rating(perf_12m: float, universe_perfs: list) -> int:
    if not universe_perfs:
        return 50
    rank = sum(1 for p in universe_perfs if p < perf_12m)
    return max(1, min(99, int(rank / len(universe_perfs) * 99) + 1))

def _eps_rating(eps_growth_q: float) -> int:
    if eps_growth_q >= 100: return 99
    if eps_growth_q >= 50:  return 90
    if eps_growth_q >= 25:  return 80
    if eps_growth_q >= 15:  return 70
    if eps_growth_q >= 5:   return 60
    if eps_growth_q >= 0:   return 50
    return 30

def _smr_rating(sales_g: float, roe: float, margins: float) -> str:
    score = 0
    if sales_g >= 25:  score += 3
    elif sales_g >= 15: score += 2
    elif sales_g >= 5:  score += 1
    if roe >= 20:      score += 3
    elif roe >= 15:    score += 2
    elif roe >= 10:    score += 1
    if margins >= 15:  score += 2
    elif margins >= 5: score += 1
    if score >= 7: return 'A'
    if score >= 5: return 'B'
    if score >= 3: return 'C'
    if score >= 1: return 'D'
    return 'E'

def _acc_dis_rating(hist: pd.DataFrame) -> str:
    if len(hist) < 20:
        return 'C'
    recent = hist.tail(20)
    up_vol   = recent[recent['Close'] > recent['Close'].shift(1)]['Volume'].sum()
    down_vol = recent[recent['Close'] < recent['Close'].shift(1)]['Volume'].sum()
    total    = up_vol + down_vol
    if total == 0:
        return 'C'
    ratio = up_vol / total
    if ratio >= 0.65: return 'A'
    if ratio >= 0.55: return 'B'
    if ratio >= 0.45: return 'C'
    if ratio >= 0.35: return 'D'
    return 'E'

def _trend_template(hist: pd.DataFrame, price: float) -> dict:
    if len(hist) < 200:
        return {"passed": False, "score": 0, "conditions": {}}
    closes = hist['Close']
    ma50   = float(closes.tail(50).mean())
    ma150  = float(closes.tail(150).mean())
    ma200  = float(closes.tail(200).mean())
    ma200_20ago = float(closes.tail(220).head(20).mean()) if len(closes) >= 220 else ma200
    low_52w  = float(closes.tail(252).min())
    high_52w = float(closes.tail(252).max())

    c1 = bool(price > ma150 and price > ma200)
    c2 = bool(ma150 > ma200)
    c3 = bool(ma200 > ma200_20ago)
    c4 = bool(ma50 > ma150 and ma50 > ma200)
    c5 = bool(price > ma50)
    c6 = bool(price >= low_52w * 1.25)
    c7 = bool(price >= high_52w * 0.75)

    conditions = {
        "Precio > MA150 y MA200":    c1,
        "MA150 > MA200":             c2,
        "MA200 en tendencia alcista": c3,
        "MA50 > MA150 y MA200":      c4,
        "Precio > MA50":             c5,
        ">=25% sobre minimo 52s":    c6,
        "<=25% bajo maximo 52s":     c7,
    }
    score  = sum(1 for v in conditions.values() if v)
    passed = bool(score >= 6)

    return {
        "passed":     passed,
        "score":      score,
        "total":      7,
        "conditions": conditions,
        "ma50":       round(ma50, 2),
        "ma150":      round(ma150, 2),
        "ma200":      round(ma200, 2),
        "low_52w":    round(low_52w, 2),
        "high_52w":   round(high_52w, 2),
    }

# ── ANÁLISIS INDIVIDUAL ───────────────────────────────────────────────────────

def analyze_ticker(ticker: str) -> dict:
    try:
        tk   = yf.Ticker(ticker.upper())
        hist = tk.history(period="2y")
        if len(hist) < 50:
            return {"ok": False, "error": "Histórico insuficiente"}

        info = {}
        try:
            info = tk.info or {}
        except Exception:
            pass

        price      = _safe_float(hist['Close'].iloc[-1])
        prev_close = _safe_float(hist['Close'].iloc[-2])
        chg_pct    = ((price - prev_close) / prev_close * 100) if prev_close else 0

        perf_12m   = ((price / _safe_float(hist['Close'].iloc[-252], price)) - 1) * 100 if len(hist) >= 252 else 0
        perf_6m    = ((price / _safe_float(hist['Close'].iloc[-126], price)) - 1) * 100 if len(hist) >= 126 else 0
        perf_3m    = ((price / _safe_float(hist['Close'].iloc[-63], price)) - 1) * 100 if len(hist) >= 63 else 0

        vol_today  = _safe_float(hist['Volume'].iloc[-1])
        vol_avg    = _safe_float(hist['Volume'].tail(50).mean(), 1)
        vol_ratio  = vol_today / vol_avg if vol_avg > 0 else 1.0

        sales_g    = _safe_float(info.get('revenueGrowth', 0)) * 100
        roe        = _safe_float(info.get('returnOnEquity', 0)) * 100
        margins    = _safe_float(info.get('profitMargins', 0)) * 100
        eps_g      = _safe_float(info.get('earningsGrowth', 0)) * 100
        mktcap     = _safe_float(info.get('marketCap', 0))
        name       = info.get('shortName', ticker.upper())
        sector     = info.get('sector', 'N/A')
        industry   = info.get('industry', 'N/A')

        eps_r   = _eps_rating(eps_g)
        smr_r   = _smr_rating(sales_g, roe, margins)
        acc_dis = _acc_dis_rating(hist)
        trend   = _trend_template(hist, price)

        rs_est  = min(99, max(1, int(50 + perf_12m / 2)))

        composite = int((
            rs_est * 0.4 +
            eps_r  * 0.3 +
            (100 if smr_r in ['A','B'] else 60 if smr_r == 'C' else 30) * 0.2 +
            (100 if acc_dis in ['A','B'] else 60 if acc_dis == 'C' else 30) * 0.1
        ))
        composite = max(1, min(99, composite))

        canslim_score = int(
            (1 if eps_g >= 25 else 0) * 15 +
            (1 if sales_g >= 25 else 0) * 15 +
            (1 if rs_est >= 80 else 0) * 20 +
            (1 if trend['passed'] else 0) * 20 +
            (1 if acc_dis in ['A','B'] else 0) * 10 +
            (1 if vol_ratio >= 1.5 else 0) * 10 +
            (1 if mktcap > 1e9 else 0) * 10
        )

        closes = hist['Close'].tolist()[-60:]
        dates  = [d.strftime('%Y-%m-%d') for d in hist.index.tolist()[-60:]]

        return {
            "ok":        True,
            "ticker":    ticker.upper(),
            "name":      name,
            "sector":    sector,
            "industry":  industry,
            "price":     round(price, 2),
            "chg_pct":   round(chg_pct, 2),
            "mktcap":    mktcap,
            "perf": {
                "3m":  round(perf_3m, 2),
                "6m":  round(perf_6m, 2),
                "12m": round(perf_12m, 2),
            },
            "ibd": {
                "rs":        rs_est,
                "eps":       eps_r,
                "composite": composite,
                "smr":       smr_r,
                "acc_dis":   acc_dis,
            },
            "fundamentals": {
                "eps_growth":   round(eps_g, 2),
                "sales_growth": round(sales_g, 2),
                "roe":          round(roe, 2),
                "margins":      round(margins, 2),
            },
            "volume": {
                "today": int(vol_today),
                "avg":   int(vol_avg),
                "ratio": round(vol_ratio, 2),
            },
            "trend":         trend,
            "canslim_score": canslim_score,
            "chart": {
                "dates":  dates,
                "closes": [round(c, 2) for c in closes],
            },
            "timestamp": _get_timestamp(),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── SCANNER S&P 500 ───────────────────────────────────────────────────────────

def _scan_single(ticker: str, spy_perf: float) -> dict | None:
    try:
        tk   = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if len(hist) < 100:
            return None

        price = _safe_float(hist['Close'].iloc[-1])
        if price < 10:
            return None

        vol_avg = _safe_float(hist['Volume'].tail(50).mean(), 1)
        if vol_avg < 200_000:
            return None

        perf_12m = ((price / _safe_float(hist['Close'].iloc[0], price)) - 1) * 100

        try:
            fi     = tk.fast_info
            mktcap = _safe_float(getattr(fi, 'market_cap', 0))
        except Exception:
            mktcap = 0

        if mktcap > 0 and mktcap < 500_000_000:
            return None

        closes = hist['Close']
        ma50   = float(closes.tail(50).mean())
        ma150  = float(closes.tail(150).mean()) if len(closes) >= 150 else ma50
        ma200  = float(closes.tail(200).mean()) if len(closes) >= 200 else ma150

        trend_ok = bool(price > ma50 and price > ma150 and ma50 > ma150)

        vol_today = _safe_float(hist['Volume'].iloc[-1])
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0
        acc_dis   = _acc_dis_rating(hist)

        rs_est   = min(99, max(1, int(50 + perf_12m / 2)))
        low_52w  = float(closes.tail(252).min())
        high_52w = float(closes.tail(252).max())

        score = 0
        if rs_est >= 80:          score += 25
        if trend_ok:              score += 25
        if acc_dis in ['A','B']:  score += 20
        if vol_ratio >= 1.5:      score += 15
        if perf_12m >= 20:        score += 15

        if score < 40:
            return None

        return {
            "ticker":    ticker,
            "price":     round(price, 2),
            "perf_12m":  round(perf_12m, 2),
            "rs":        rs_est,
            "acc_dis":   acc_dis,
            "vol_ratio": round(vol_ratio, 2),
            "trend":     trend_ok,
            "ma50":      round(ma50, 2),
            "ma150":     round(ma150, 2),
            "ma200":     round(ma200, 2),
            "high_52w":  round(high_52w, 2),
            "low_52w":   round(low_52w, 2),
            "score":     score,
        }
    except Exception:
        return None


def scan_canslim(min_score: int = 40, max_results: int = 30) -> dict:
    try:
        spy  = yf.Ticker("SPY")
        hist = spy.history(period="1y")
        spy_perf = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100 if len(hist) > 0 else 0
    except Exception:
        spy_perf = 0

    candidates = []
    tickers    = SP500_TICKERS[:200]

    with ThreadPoolExecutor(max_workers=12) as ex:
        futures = {ex.submit(_scan_single, t, spy_perf): t for t in tickers}
        for future in futures:
            result = future.result()
            if result and result['score'] >= min_score:
                candidates.append(result)

    candidates.sort(key=lambda x: -x['score'])

    return {
        "ok":         True,
        "candidates": candidates[:max_results],
        "total":      len(candidates),
        "scanned":    len(tickers),
        "timestamp":  _get_timestamp(),
    }