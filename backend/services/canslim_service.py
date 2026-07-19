"""
CAN SLIM Service — RSU Terminal
Universo: S&P 500 completo (503 tickers)
Fixes: NaN sanitization, RS real percentile, N+I criteria, Market widget
"""
import pandas as pd
import numpy as np
import yfinance as yf
import math
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
    "PYPL","PNR","PEP","PFE","PCG","PM","PSX","PNW","PNC","POOL","PPG",
    "PPL","PFG","PG","PGR","PLD","PRU","PEG","PTC","PSA","PHM","PWR",
    "QCOM","DGX","RL","RJF","RTX","O","REG","REGN","RF","RSG","RMD","RVTY",
    "ROK","ROL","ROP","ROST","RCL","SPGI","CRM","SBAC","SLB","STX","SRE","NOW",
    "SHW","SPG","SWKS","SJM","SNA","SOLV","SO","LUV","SWK","SBUX","STT","STLD",
    "STE","SYK","SYF","SNPS","SYY","TMUS","TROW","TTWO","TPR","TRGP","TGT",
    "TEL","TDY","TFX","TER","TSLA","TXN","TXT","TMO","TJX","TSCO","TT","TDG",
    "TRV","TRMB","TFC","TYL","TSN","USB","UBER","UDR","ULTA","UNP","UAL","UPS",
    "URI","UNH","UHS","VLO","VTR","VLTO","VRSN","VRSK","VZ","VRTX","VTRS",
    "VICI","V","VMC","WRB","GWW","WAB","WBA","WMT","DIS","WBD","WM","WAT",
    "WEC","WFC","WELL","WST","WDC","WY","WHR","WMB","WTW","WYNN","XEL",
    "XYL","YUM","ZBRA","ZBH","ZTS",
]

# ── SANITIZE NaN ──────────────────────────────────────────────────────────────

def _sanitize(obj):
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj

def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if not math.isnan(v) and not math.isinf(v) else default
    except Exception:
        return default

def _get_timestamp():
    return datetime.now().strftime('%H:%M:%S')

# ── IBD RATINGS ───────────────────────────────────────────────────────────────

def _rs_rating_real(perf_12m: float, universe_perfs: list) -> int:
    """RS real: percentil en el universo escaneado."""
    if not universe_perfs:
        return max(1, min(99, int(50 + perf_12m / 2)))
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
    if sales_g >= 25:   score += 3
    elif sales_g >= 15: score += 2
    elif sales_g >= 5:  score += 1
    if roe >= 20:       score += 3
    elif roe >= 15:     score += 2
    elif roe >= 10:     score += 1
    if margins >= 15:   score += 2
    elif margins >= 5:  score += 1
    if score >= 7: return 'A'
    if score >= 5: return 'B'
    if score >= 3: return 'C'
    if score >= 1: return 'D'
    return 'E'

def _acc_dis_rating(hist: pd.DataFrame) -> str:
    if len(hist) < 20:
        return 'C'
    recent = hist.tail(20)
    up_vol   = recent.loc[recent['Close'] > recent['Open'], 'Volume'].sum()
    down_vol = recent.loc[recent['Close'] < recent['Open'], 'Volume'].sum()
    total    = up_vol + down_vol
    if total == 0:
        return 'C'
    ratio = up_vol / total
    if ratio >= 0.70: return 'A'
    if ratio >= 0.58: return 'B'
    if ratio >= 0.45: return 'C'
    if ratio >= 0.35: return 'D'
    return 'E'

def _trend_template(hist: pd.DataFrame, price: float) -> dict:
    """Minervini Trend Template — 7 condiciones."""
    n = len(hist)
    closes = hist['Close']

    ma50  = float(closes.tail(50).mean())  if n >= 50  else price
    ma150 = float(closes.tail(150).mean()) if n >= 150 else ma50
    ma200 = float(closes.tail(200).mean()) if n >= 200 else ma150

    # 200 MA trend (slope over last 20 days)
    if n >= 220:
        ma200_20ago = float(closes.iloc[-220:-20].tail(200).mean())
        ma200_rising = ma200 > ma200_20ago
    else:
        # Antes: True por defecto -- sesgo optimista, daba por buena una
        # condición que en realidad no se puede verificar por falta de
        # histórico (típico en salidas a bolsa recientes). El resto de
        # condiciones del Trend Template exigen datos reales para pasar;
        # esta debe tratarse igual: si no se puede comprobar, no se
        # concede. Ver conversación 19/07/2026.
        ma200_rising = False

    high_52w = float(closes.tail(252).max()) if n >= 252 else float(closes.max())
    low_52w  = float(closes.tail(252).min()) if n >= 252 else float(closes.min())

    pct_from_high = ((price - high_52w) / high_52w * 100) if high_52w > 0 else -100

    conditions = {
        "Precio > MA150 y MA200":    bool(price > ma150 and price > ma200),
        "MA150 > MA200":             bool(ma150 > ma200),
        "MA200 subiendo (20d)":      bool(ma200_rising),
        "MA50 > MA150 y MA200":      bool(ma50 > ma150 and ma50 > ma200),
        "Precio > MA50":             bool(price > ma50),
        ">30% sobre mínimo 52s":     bool(price >= low_52w * 1.30),
        "< 25% del máximo 52s":      bool(pct_from_high >= -25),
    }

    score  = sum(conditions.values())
    passed = score >= 5

    return {
        "passed":      passed,
        "score":       score,
        "conditions":  conditions,
        "ma50":        round(ma50, 2),
        "ma150":       round(ma150, 2),
        "ma200":       round(ma200, 2),
        "high_52w":    round(high_52w, 2),
        "low_52w":     round(low_52w, 2),
        "pct_from_high": round(pct_from_high, 1),
    }

# ── MARKET ANALYZER ───────────────────────────────────────────────────────────

def get_market_status() -> dict:
    """
    Análisis del mercado general (M en CAN SLIM).
    Usa SPY + VIX + amplitud para determinar el estado del mercado.
    """
    try:
        # SPY
        spy = yf.Ticker("SPY")
        spy_hist = spy.history(period="1y")
        if spy_hist.empty:
            raise ValueError("Sin datos SPY")

        spy_price  = _safe(spy_hist['Close'].iloc[-1])
        spy_prev   = _safe(spy_hist['Close'].iloc[-2])
        spy_chg    = (spy_price - spy_prev) / spy_prev * 100 if spy_prev else 0
        spy_ma50   = float(spy_hist['Close'].tail(50).mean())
        spy_ma200  = float(spy_hist['Close'].tail(200).mean()) if len(spy_hist) >= 200 else spy_ma50
        spy_high52 = float(spy_hist['Close'].tail(252).max())
        spy_pct_from_high = (spy_price - spy_high52) / spy_high52 * 100

        spy_above_ma50  = spy_price > spy_ma50
        spy_above_ma200 = spy_price > spy_ma200

        spy_perf_3m  = _safe(((spy_price / spy_hist['Close'].iloc[-63]) - 1) * 100 if len(spy_hist) >= 63 else 0)
        spy_perf_1m  = _safe(((spy_price / spy_hist['Close'].iloc[-21]) - 1) * 100 if len(spy_hist) >= 21 else 0)
        spy_perf_1w  = _safe(((spy_price / spy_hist['Close'].iloc[-5])  - 1) * 100 if len(spy_hist) >= 5  else 0)

        # VIX
        vix_level = 0.0
        try:
            vix = yf.Ticker("^VIX")
            vix_hist = vix.history(period="5d")
            if not vix_hist.empty:
                vix_level = _safe(vix_hist['Close'].iloc[-1])
        except Exception:
            pass

        # QQQ para tech breadth
        qqq_above_ma50 = False
        try:
            qqq = yf.Ticker("QQQ")
            qqq_hist = qqq.history(period="100d")
            if not qqq_hist.empty:
                qqq_price  = _safe(qqq_hist['Close'].iloc[-1])
                qqq_ma50   = float(qqq_hist['Close'].tail(50).mean())
                qqq_above_ma50 = qqq_price > qqq_ma50
        except Exception:
            pass

        # Score del mercado 0-100
        score = 0
        if spy_above_ma50:   score += 25
        if spy_above_ma200:  score += 20
        if qqq_above_ma50:   score += 15
        if vix_level < 20:   score += 20
        elif vix_level < 30: score += 10
        if spy_perf_3m > 0:  score += 10
        if spy_perf_1m > 0:  score += 10

        # Estado del mercado
        if score >= 80:
            status = "CONFIRMED UPTREND"
            status_es = "TENDENCIA ALCISTA CONFIRMADA"
            color = "#00ffad"
            can_buy = True
        elif score >= 60:
            status = "UPTREND UNDER PRESSURE"
            status_es = "TENDENCIA ALCISTA BAJO PRESIÓN"
            color = "#ff9800"
            can_buy = True
        elif score >= 40:
            status = "RALLY ATTEMPT"
            status_es = "INTENTO DE RECUPERACIÓN"
            color = "#ffb800"
            can_buy = False
        elif score >= 20:
            status = "MARKET IN CORRECTION"
            status_es = "MERCADO EN CORRECCIÓN"
            color = "#f23645"
            can_buy = False
        else:
            status = "DISTRIBUTION PHASE"
            status_es = "FASE DE DISTRIBUCIÓN"
            color = "#f23645"
            can_buy = False

        return _sanitize({
            "ok":            True,
            "status":        status,
            "status_es":     status_es,
            "score":         score,
            "color":         color,
            "can_buy":       can_buy,
            "spy": {
                "price":         round(spy_price, 2),
                "chg_pct":       round(spy_chg, 2),
                "above_ma50":    spy_above_ma50,
                "above_ma200":   spy_above_ma200,
                "ma50":          round(spy_ma50, 2),
                "ma200":         round(spy_ma200, 2),
                "pct_from_high": round(spy_pct_from_high, 1),
                "perf_1w":       round(spy_perf_1w, 2),
                "perf_1m":       round(spy_perf_1m, 2),
                "perf_3m":       round(spy_perf_3m, 2),
            },
            "vix":           round(vix_level, 2),
            "vix_risk":      "ALTO" if vix_level >= 30 else "MEDIO" if vix_level >= 20 else "BAJO",
            "timestamp":     _get_timestamp(),
        })

    except Exception as e:
        return {"ok": False, "error": str(e)}

# ── ANALYZE TICKER ────────────────────────────────────────────────────────────

def analyze_ticker(ticker: str, universe_perfs: list = None) -> dict:
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

        price      = _safe(hist['Close'].iloc[-1])
        prev_close = _safe(hist['Close'].iloc[-2])
        chg_pct    = ((price - prev_close) / prev_close * 100) if prev_close else 0

        perf_12m = _safe(((price / hist['Close'].iloc[-252]) - 1) * 100 if len(hist) >= 252 else 0)
        perf_6m  = _safe(((price / hist['Close'].iloc[-126]) - 1) * 100 if len(hist) >= 126 else 0)
        perf_3m  = _safe(((price / hist['Close'].iloc[-63])  - 1) * 100 if len(hist) >= 63  else 0)

        vol_today = _safe(hist['Volume'].iloc[-1])
        vol_avg   = _safe(hist['Volume'].tail(50).mean(), 1)
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0

        # Fundamentales
        eps_g   = _safe(info.get('earningsGrowth',  0)) * 100
        sales_g = _safe(info.get('revenueGrowth',   0)) * 100
        roe     = _safe(info.get('returnOnEquity',  0)) * 100
        margins = _safe(info.get('profitMargins',   0)) * 100
        mktcap  = _safe(info.get('marketCap',       0))
        name    = str(info.get('shortName', ticker.upper()))
        sector  = str(info.get('sector',   'N/A'))
        industry= str(info.get('industry', 'N/A'))

        # ── Participación institucional real via major_holders ────────────────
        inst_pct        = 0.0
        inst_pct_source = "N/A"
        inst_holders    = []
        inst_data_ok    = False

        try:
            major = tk.major_holders
            if major is not None and not major.empty:
                # Nuevo formato yfinance: columnas Value/Description o index-based
                # Intentar ambos formatos
                df = major.reset_index()
                for idx in range(len(df)):
                    row_vals = [str(v).lower() for v in df.iloc[idx].tolist()]
                    row_str  = ' '.join(row_vals)
                    if 'institution' in row_str and 'float' not in row_str:
                        # Buscar el valor numérico en la fila
                        for v in df.iloc[idx].tolist():
                            v_str = str(v).replace('%', '').strip()
                            try:
                                parsed = float(v_str)
                                if 0 < parsed <= 100:
                                    inst_pct        = parsed
                                    inst_pct_source = "major_holders"
                                    inst_data_ok    = True
                                    break
                            except Exception:
                                continue
                        if inst_data_ok:
                            break
        except Exception:
            pass

        # Fallback: info['institutionPercentHeld']
        if not inst_data_ok:
            raw = _safe(info.get('institutionPercentHeld', 0)) * 100
            if raw > 0:
                inst_pct        = raw
                inst_pct_source = "info"
                inst_data_ok    = True

        # Top holders institucionales
        try:
            holders_df = tk.institutional_holders
            if holders_df is not None and not holders_df.empty:
                for _, row in holders_df.head(5).iterrows():
                    holder_name = str(row.get('Holder', row.get('Name', 'N/A')))
                    shares      = _safe(row.get('Shares', 0))
                    pct_out     = _safe(row.get('% Out', row.get('pctHeld', 0))) * 100
                    inst_holders.append({
                        "name":    holder_name,
                        "shares":  int(shares),
                        "pct_out": round(pct_out, 2),
                    })
        except Exception:
            pass

        # ── RS rating ────────────────────────────────────────────────────────
        rs_r = _rs_rating_real(perf_12m, universe_perfs or [])

        # ── IBD Ratings ───────────────────────────────────────────────────────
        eps_r   = _eps_rating(eps_g)
        smr_r   = _smr_rating(sales_g, roe, margins)
        acc_dis = _acc_dis_rating(hist)
        trend   = _trend_template(hist, price)

        smr_num   = 100 if smr_r in ['A','B'] else 60 if smr_r == 'C' else 30
        acc_num   = 100 if acc_dis in ['A','B'] else 60 if acc_dis == 'C' else 30
        composite = int(rs_r * 0.35 + eps_r * 0.30 + smr_num * 0.20 + acc_num * 0.15)
        composite = max(1, min(99, composite))

        # ── CAN SLIM criteria ─────────────────────────────────────────────────
        pct_from_high    = trend['pct_from_high']
        near_new_high    = pct_from_high >= -15

        # I: sponsorship — solo penaliza si tenemos dato y es bajo
        # Si no hay dato (inst_data_ok=False), no penaliza
        inst_sponsorship = (inst_pct > 40) if inst_data_ok else None  # None = sin dato

        can_slim_letters = {
            "C — EPS crecimiento >25%":         bool(eps_g >= 25),
            "A — Ventas anuales >25%":           bool(sales_g >= 25),
            "N — Near new high (<15% del máx)":  bool(near_new_high),
            "S — RS Rating >80":                 bool(rs_r >= 80),
            "L — Leader (Trend Template)":       bool(trend['passed']),
            "I — Sponsorship institucional":     bool(inst_sponsorship) if inst_sponsorship is not None else None,
            "M — (ver estado mercado)":          True,
        }

        # ── Score técnico (lo que puede evaluar sin fundamentales) ───────────
        tech_score = sum([
            25 if rs_r >= 80       else (15 if rs_r >= 70 else 0),
            25 if trend['passed']  else (10 if trend['score'] >= 4 else 0),
            20 if acc_dis in ['A','B'] else (10 if acc_dis == 'C' else 0),
            15 if near_new_high    else 0,
            15 if vol_ratio >= 1.5 else (8 if vol_ratio >= 1.0 else 0),
        ])
        tech_score = min(100, tech_score)

        # ── Score fundamental ─────────────────────────────────────────────────
        # Sin dato → no penaliza (tratado como ausente, no como "0% malo").
        # ROE y Márgenes antes NO comprobaban esto (a diferencia de EPS y
        # Sales, que sí) -- un ticker sin dato de ROE en yfinance (frecuente
        # fuera de EE.UU. o en salidas a bolsa recientes) se puntuaba como
        # 0% de ROE real, la peor nota posible, en vez de excluirse del
        # cálculo. Ver conversación 19/07/2026.
        eps_has_data     = abs(eps_g)   > 0.1
        sales_has_data   = abs(sales_g) > 0.1
        roe_has_data     = abs(roe)     > 0.1
        margins_has_data = abs(margins) > 0.1

        sub_scores  = []
        max_posible = 0
        if eps_has_data:
            sub_scores.append(30 if eps_g >= 25 else (15 if eps_g >= 10 else 0))
            max_posible += 30
        if sales_has_data:
            sub_scores.append(30 if sales_g >= 25 else (15 if sales_g >= 10 else 0))
            max_posible += 30
        if roe_has_data:
            sub_scores.append(20 if roe >= 15 else (10 if roe >= 8 else 0))
            max_posible += 20
        if margins_has_data:
            sub_scores.append(20 if margins >= 10 else (10 if margins >= 3 else 0))
            max_posible += 20

        # Reescalado a /100 proporcional a las submétricas realmente
        # disponibles -- mismo patrón que usa el RSU Score de Research
        # cuando faltan categorías enteras.
        fund_score = int(sum(sub_scores) / max_posible * 100) if max_posible > 0 else 0
        fund_score = min(100, fund_score)

        # Si no hay NINGÚN dato fundamental, marcar como sin dato
        fund_data_available = len(sub_scores) > 0

        # Score CAN SLIM unificado (60% técnico + 40% fundamental)
        # Si no hay fundamentales, usar solo técnico con disclaimer
        if fund_data_available:
            canslim_score = int(tech_score * 0.60 + fund_score * 0.40)
        else:
            canslim_score = int(tech_score * 0.80)  # sin fundamentales, reducido

        canslim_score = max(0, min(100, canslim_score))

        # ── Chart ─────────────────────────────────────────────────────────────
        hist60     = hist.tail(60)
        closes_60  = [round(_safe(c), 2) for c in hist60['Close'].tolist()]
        dates_60   = [d.strftime('%Y-%m-%d') for d in hist60.index.tolist()]
        ma50_line  = []
        ma200_line = []
        for i in range(len(hist60)):
            idx = len(hist) - len(hist60) + i
            slice50  = hist['Close'].iloc[max(0, idx-49):idx+1]
            slice200 = hist['Close'].iloc[max(0, idx-199):idx+1]
            ma50_line.append(round(float(slice50.mean()), 2) if len(slice50) >= 10 else None)
            ma200_line.append(round(float(slice200.mean()), 2) if len(slice200) >= 50 else None)

        return _sanitize({
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
                "rs":        rs_r,
                "eps":       eps_r,
                "composite": composite,
                "smr":       smr_r,
                "acc_dis":   acc_dis,
            },
            "fundamentals": {
                "eps_growth":        round(eps_g, 2),
                "sales_growth":      round(sales_g, 2),
                "roe":               round(roe, 2),
                "margins":           round(margins, 2),
                "inst_pct":          round(inst_pct, 1),
                "inst_pct_source":   inst_pct_source,
                "inst_data_ok":      inst_data_ok,
                "inst_holders":      inst_holders,
                "fund_data_available": fund_data_available,
            },
            "volume": {
                "today": int(vol_today),
                "avg":   int(vol_avg),
                "ratio": round(vol_ratio, 2),
            },
            "scores": {
                "tech":         tech_score,
                "fundamental":  fund_score,
                "combined":     canslim_score,
                "fund_available": fund_data_available,
            },
            "trend":            trend,
            "can_slim_letters": can_slim_letters,
            "canslim_score":    canslim_score,
            "near_new_high":    near_new_high,
            "pct_from_high":    round(pct_from_high, 1),
            "chart": {
                "dates":   dates_60,
                "closes":  closes_60,
                "ma50":    ma50_line,
                "ma200":   ma200_line,
            },
            "timestamp": _get_timestamp(),
        })

    except Exception as e:
        import traceback
        return {"ok": False, "error": str(e), "detail": traceback.format_exc()}

# ── SCANNER S&P 500 COMPLETO ──────────────────────────────────────────────────

def _scan_single(ticker: str) -> dict | None:
    try:
        tk   = yf.Ticker(ticker)
        hist = tk.history(period="1y")
        if len(hist) < 100:
            return None

        price = _safe(hist['Close'].iloc[-1])
        if price < 5:
            return None

        vol_avg = _safe(hist['Volume'].tail(50).mean(), 1)
        if vol_avg < 100_000:
            return None

        perf_12m = _safe(((price / hist['Close'].iloc[0]) - 1) * 100)

        try:
            fi     = tk.fast_info
            mktcap = _safe(getattr(fi, 'market_cap', 0))
        except Exception:
            mktcap = 0

        closes  = hist['Close']
        ma50    = float(closes.tail(50).mean())
        ma150   = float(closes.tail(150).mean()) if len(closes) >= 150 else ma50
        ma200   = float(closes.tail(200).mean()) if len(closes) >= 200 else ma150

        trend_ok = bool(price > ma50 and price > ma150 and ma50 > ma150)

        vol_today = _safe(hist['Volume'].iloc[-1])
        vol_ratio = vol_today / vol_avg if vol_avg > 0 else 1.0
        acc_dis   = _acc_dis_rating(hist)

        high_52w = float(closes.tail(252).max())
        low_52w  = float(closes.tail(252).min())
        pct_from_high = (price - high_52w) / high_52w * 100 if high_52w > 0 else -100

        return {
            "ticker":      ticker,
            "price":       round(price, 2),
            "perf_12m":    round(perf_12m, 2),
            "acc_dis":     acc_dis,
            "vol_ratio":   round(vol_ratio, 2),
            "trend":       trend_ok,
            "ma50":        round(ma50, 2),
            "ma150":       round(ma150, 2),
            "ma200":       round(ma200, 2),
            "high_52w":    round(high_52w, 2),
            "low_52w":     round(low_52w, 2),
            "pct_from_high": round(pct_from_high, 1),
            "mktcap":      mktcap,
        }
    except Exception:
        return None


def scan_canslim(min_score: int = 40, max_results: int = 50) -> dict:
    """Escanea el S&P 500 completo con RS real calculado contra el universo."""
    tickers = list(dict.fromkeys(SP500_TICKERS))   # 503 sin duplicados

    # Paso 1: datos básicos en paralelo
    raw_results = []
    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(_scan_single, t): t for t in tickers}
        for future in futures:
            result = future.result()
            if result:
                raw_results.append(result)

    # Paso 2: RS real = percentil dentro del universo escaneado
    perfs = [r['perf_12m'] for r in raw_results]
    for r in raw_results:
        rank = sum(1 for p in perfs if p < r['perf_12m'])
        r['rs'] = max(1, min(99, int(rank / len(perfs) * 99) + 1)) if perfs else 50

    # Paso 3: Score con RS real
    candidates = []
    for r in raw_results:
        near_new_high = r['pct_from_high'] >= -15
        score = 0
        if r['rs'] >= 80:            score += 25
        if r['trend']:               score += 25
        if r['acc_dis'] in ['A','B']:score += 20
        if r['vol_ratio'] >= 1.5:    score += 15
        if r['perf_12m'] >= 20:      score += 10
        if near_new_high:            score += 5

        if score >= min_score:
            r['score'] = score
            r['near_new_high'] = near_new_high
            candidates.append(r)

    candidates.sort(key=lambda x: -x['score'])

    return _sanitize({
        "ok":         True,
        "candidates": candidates[:max_results],
        "total":      len(candidates),
        "scanned":    len(tickers),
        "universe_perfs": perfs[:10],   # muestra de percentiles para debug
        "timestamp":  _get_timestamp(),
    })