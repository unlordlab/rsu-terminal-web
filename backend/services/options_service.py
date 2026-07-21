import yfinance as yf
import requests
import pandas as pd
import numpy as np
import sqlite3
import os
import sys
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

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
    # Ampliación (14/07/2026) — S&P 500 completo vía export de TradingView.
    # AVISO DE ESCALA: esto casi cuadriplica el tamaño de WATCHLIST (149 ->
    # 568 tickers) — el escaneo de opciones es mucho más pesado por ticker
    # que una simple descarga de precio (hasta 5 llamadas a option_chain()
    # por ticker, cada una con decenas de filas que iterar). Si el escaneo
    # diario empieza a tardar demasiado o a fallar por rate-limit de Yahoo,
    # este es el primer sitio a revisar — considera reducir max_workers en
    # get_options_flow() o recortar esta lista.
    "A", "ABT", "ACGL", "ADI", "ADM", "ADP", "ADSK", "AEE", "AEP", "AES",
    "AFL", "AIG", "AIZ", "AJG", "AKAM", "ALGN", "ALL", "ALLE", "AMAT", "AMCR",
    "AME", "AMGN", "AMP", "AMT", "AON", "AOS", "APA", "APD", "APH", "APO",
    "APTV", "ARE", "ARES", "ATO", "AVB", "AVY", "AWK", "AZO", "BALL", "BAX",
    "BBY", "BDX", "BEN", "BG", "BIIB", "BKNG", "BKR", "BLDR", "BMY", "BNY",
    "BR", "BRO", "BSX", "BX", "BXP", "C", "CAH", "CARR", "CASY", "CB",
    "CBOE", "CBRE", "CCI", "CCL", "CDNS", "CDW", "CEG", "CF", "CFG", "CHD",
    "CHRW", "CHTR", "CI", "CIEN", "CINF", "CL", "CLX", "CMCSA", "CMG", "CMI",
    "CMS", "CNC", "CNP", "COO", "COR", "CPAY", "CPRT", "CPT", "CRH", "CRL",
    "CSCO", "CSGP", "CSX", "CTAS", "CTSH", "CTVA", "CVNA", "CVS", "D", "DAL",
    "DD", "DECK", "DELL", "DG", "DGX", "DHI", "DHR", "DIS", "DLR", "DLTR",
    "DOC", "DOV", "DOW", "DPZ", "DRI", "DTE", "DUK", "DVA", "DVN", "EA",
    "EBAY", "ECHO", "ECL", "ED", "EFX", "EG", "EIX", "EL", "ELV", "EME",
    "EOG", "EQIX", "EQR", "ERIE", "ES", "ESS", "ETR", "EVRG", "EW", "EXC",
    "EXE", "EXPD", "EXPE", "EXR", "F", "FANG", "FAST", "FDS", "FDX", "FDXF",
    "FE", "FFIV", "FICO", "FIS", "FISV", "FITB", "FIX", "FLEX", "FOX", "FRT",
    "FSLR", "FTV", "GDDY", "GE", "GEHC", "GEN", "GEV", "GILD", "GIS", "GL",
    "GLW", "GM", "GNRC", "GOOG", "GPC", "GPN", "GRMN", "GWW", "HAL", "HAS",
    "HBAN", "HCA", "HIG", "HLT", "HONA", "HPE", "HPQ", "HRL", "HSIC", "HST",
    "HSY", "HUBB", "HUM", "HWM", "IBKR", "IBM", "IDXX", "IEX", "IFF", "INCY",
    "INTC", "INTU", "INVH", "IP", "IQV", "IR", "IRM", "ISRG", "IT", "ITW",
    "IVZ", "J", "JBHT", "JBL", "JCI", "JKHY", "KDP", "KEY", "KEYS", "KHC",
    "KIM", "KKR", "KLAC", "KMB", "KMI", "KR", "KVUE", "L", "LEN", "LH",
    "LHX", "LII", "LITE", "LNT", "LOW", "LRCX", "LULU", "LUV", "LVS", "LYB",
    "LYV", "MAA", "MAR", "MAS", "MCD", "MCHP", "MCK", "MDLZ", "MDT", "MET",
    "MGM", "MKC", "MLM", "MMM", "MNST", "MO", "MOS", "MPC", "MPWR", "MRNA",
    "MRSH", "MRVL", "MSCI", "MSI", "MTB", "MTD", "MU", "NCLH", "NDAQ", "NDSN",
    "NEE", "NI", "NKE", "NRG", "NSC", "NTAP", "NTRS", "NUE", "NVR", "NWS",
    "NXPI", "O", "ODFL", "OKE", "OMC", "ON", "ORLY", "OTIS", "PAYX", "PCAR",
    "PCG", "PEG", "PFE", "PFG", "PGR", "PH", "PHM", "PKG", "PLD", "PM",
    "PNC", "PNR", "PNW", "PODD", "PPG", "PPL", "PRU", "PSA", "PSKY", "PSX",
    "PTC", "PWR", "Q", "QCOM", "RCL", "REG", "REGN", "RF", "RJF", "RL",
    "RMD", "ROK", "ROL", "ROP", "ROST", "RSG", "RVTY", "SBAC", "SBUX", "SHW",
    "SJM", "SNA", "SNDK", "SNPS", "SO", "SOLV", "SPG", "SRE", "STE", "STLD",
    "STT", "STX", "STZ", "SW", "SWK", "SWKS", "SYF", "SYK", "SYY", "T",
    "TAP", "TDG", "TDY", "TECH", "TEL", "TER", "TFC", "TGT", "TJX", "TKO",
    "TMO", "TMUS", "TPL", "TPR", "TRGP", "TRMB", "TROW", "TRV", "TSCO", "TSN",
    "TT", "TTWO", "TXN", "TXT", "TYL", "UAL", "UDR", "UHS", "ULTA", "UNP",
    "UPS", "URI", "USB", "VEEV", "VICI", "VLO", "VLTO", "VMC", "VRSK", "VRSN",
    "VRT", "VRTX", "VST", "VTR", "VTRS", "VZ", "WAB", "WAT", "WBD", "WDAY",
    "WDC", "WEC", "WELL", "WM", "WMB", "WMT", "WRB", "WSM", "WST", "WTW",
    "WY", "WYNN", "XEL", "XYL", "XYZ", "YUM", "ZBH", "ZBRA", "ZTS",
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

# ── VERSIÓN SIMPLIFICADA — "sin ruido", solo lo que pide Marc ──────────────────
# Motivo de tenerla aparte de get_options_flow/get_options_ticker (que se
# dejan intactas, siguen usándose en /repeats y /ticker-summary): esas
# devuelven un batiburrillo de score/signal/sector heatmap/blocks/sweeps que
# hacía la sección difícil de leer. Estas tres funciones nuevas devuelven
# exactamente la estructura del PDF de referencia (Trading Edge Flow) —
# Calls Bought / Puts Sold / Puts Bought / Calls Sold / Large OI Increase /
# Large OI Decrease, y nada más.

def _obtener_contratos_repetidos(days: int = 7, min_repeats: int = 2) -> set:
    """Igual que get_repeat_signals pero devuelve solo las claves (ticker,
    strike, exp, type, action) como conjunto, para marcar con icono 🔁 las
    entradas que son repetición de días anteriores — no una tabla aparte,
    solo un icono en las tablas que ya existen (mejora #1 pedida por Marc)."""
    try:
        señales = get_repeat_signals(days=days, min_repeats=min_repeats)
        return {(s["ticker"], s["strike"], s["exp"], s["type"], s["action"]) for s in señales}
    except Exception as e:
        print(f"[OptionsFlow] No se pudieron calcular contratos repetidos: {e}")
        return set()

def _entrada_simple(item: dict, order_type: str, cartera_tickers: set = None, repetidos: set = None) -> dict:
    tipo, accion = {
        "Buy Call": ("call", "buy"), "Sell Put": ("put", "sell"),
        "Buy Put": ("put", "buy"), "Sell Call": ("call", "sell"),
    }[order_type]
    clave = (item["ticker"], item["strike"], item["exp"], tipo, accion)
    return {
        "ticker":        item["ticker"],
        "order_type":    order_type,
        "strike":        item["strike"],
        "strike_pct":    item["strike_pct"],
        "exp":           item["exp"],
        "oi":            item["oi"],
        "premium":       item["premium"],
        "premium_fmt":   item["premium_fmt"],
        "near_earnings": bool(item.get("near_earnings")),
        "en_cartera":    item["ticker"] in cartera_tickers if cartera_tickers is not None else False,
        "es_repetida":   clave in repetidos if repetidos is not None else False,
    }

def _obtener_tickers_cartera() -> set:
    """Tickers actualmente en posición abierta en Cartera — para el icono de
    cruce en Options Flow (#4 de las mejoras pedidas). Falla en silencio a
    conjunto vacío si Cartera no está disponible por lo que sea; no debe
    tumbar Options Flow si Cartera tiene un problema puntual."""
    try:
        from services.cartera_service import get_cartera
        data = get_cartera()
        return {r["ticker"] for r in data.get("abiertas", [])}
    except Exception as e:
        print(f"[OptionsFlow] No se pudo leer Cartera para el cruce de tickers: {e}")
        return set()

def get_options_flow_simple() -> dict:
    """Lee del último escaneo GUARDADO en la base de datos — no hace un
    escaneo en vivo de ~150 tickers en cada carga de página. Antes esta
    función llamaba a get_options_flow() (escaneo en vivo) cada vez que
    alguien abría /options, lo cual era lento y quedaba en blanco sin aviso
    si Yahoo empezaba a limitar peticiones a mitad de escaneo — el mismo
    tipo de fallo silencioso que ya vimos con GDELT y el calendario
    económico. Ahora lee de lo que ya guardó run_and_save_scan()."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    ultima_fecha = conn.execute('SELECT MAX(scan_date) FROM options_flow').fetchone()[0]
    if not ultima_fecha:
        conn.close()
        return {"ok": False, "error": "Todavía no se ha guardado ningún escaneo — usa POST /api/v1/options/scan-now para forzar el primero, o espera al escaneo automático diario."}

    rows = conn.execute(
        'SELECT * FROM options_flow WHERE scan_date=? ORDER BY premium DESC',
        (ultima_fecha,)
    ).fetchall()
    conn.close()

    ORDER_TYPE = {("call","buy"): "Buy Call", ("put","sell"): "Sell Put",
                  ("put","buy"): "Buy Put", ("call","sell"): "Sell Call"}
    grupos = {"Buy Call": [], "Sell Put": [], "Buy Put": [], "Sell Call": []}
    premio_por_ticker: dict = {}
    bull_por_ticker: dict = {}
    bear_por_ticker: dict = {}
    bull_total, bear_total = 0.0, 0.0

    for r in rows:
        ot = ORDER_TYPE.get((r["type"], r["action"]))
        if not ot:
            continue
        grupos[ot].append({
            "ticker": r["ticker"], "order_type": ot,
            "strike": r["strike"], "strike_pct": r["strike_pct"],
            "exp": r["exp"], "oi": r["oi"],
            "premium": r["premium"], "premium_fmt": r["premium_fmt"],
            "near_earnings": r["near_earnings"],
        })
        premio_por_ticker[r["ticker"]] = premio_por_ticker.get(r["ticker"], 0) + r["premium"]
        if ot in ("Buy Call", "Sell Put"):
            bull_por_ticker[r["ticker"]] = bull_por_ticker.get(r["ticker"], 0) + r["premium"]
            bull_total += r["premium"]
        else:
            bear_por_ticker[r["ticker"]] = bear_por_ticker.get(r["ticker"], 0) + r["premium"]
            bear_total += r["premium"]

    top_premium = sorted(premio_por_ticker.items(), key=lambda x: -x[1])[:6]
    top_bullish = sorted(bull_por_ticker.items(), key=lambda x: -x[1])[:6]
    top_bearish = sorted(bear_por_ticker.items(), key=lambda x: -x[1])[:6]

    oi_changes      = get_oi_changes(limit=15)
    cartera_tickers = _obtener_tickers_cartera()
    repetidos       = _obtener_contratos_repetidos()

    # Sesgo del día — un único número, sin gráficos ni heatmaps (mejora #3):
    # % de la prima total del día que es alcista (Calls Bought + Puts Sold)
    # frente a bajista (Puts Bought + Calls Sold).
    total_dia = bull_total + bear_total
    if total_dia > 0:
        dia_bias_pct = round(bull_total / total_dia * 100, 1)
        if dia_bias_pct >= 60:   dia_bias_label = "ALCISTA"
        elif dia_bias_pct <= 40: dia_bias_label = "BAJISTA"
        else:                    dia_bias_label = "NEUTRAL"
    else:
        dia_bias_pct, dia_bias_label = None, "SIN DATOS"

    return {
        "ok":                 True,
        "scan_date":          ultima_fecha,
        "dia_bias_pct":       dia_bias_pct,
        "dia_bias_label":     dia_bias_label,
        "calls_bought":       [_entrada_simple(e, "Buy Call",  cartera_tickers, repetidos) for e in grupos["Buy Call"]][:25],
        "puts_sold":          [_entrada_simple(e, "Sell Put",  cartera_tickers, repetidos) for e in grupos["Sell Put"]][:25],
        "puts_bought":        [_entrada_simple(e, "Buy Put",   cartera_tickers, repetidos) for e in grupos["Buy Put"]][:20],
        "calls_sold":         [_entrada_simple(e, "Sell Call", cartera_tickers, repetidos) for e in grupos["Sell Call"]][:20],
        "large_oi_increase":  oi_changes["increase"],
        "large_oi_decrease":  oi_changes["decrease"],
        "top_premium":        [{"ticker": t, "premium_fmt": _fmt_premium(p)} for t, p in top_premium],
        "top_bullish":        [{"ticker": t} for t, _ in top_bullish],
        "top_bearish":        [{"ticker": t} for t, _ in top_bearish],
    }

def get_oi_changes(limit: int = 15) -> dict:
    """Compara el Open Interest del último scan guardado contra el scan
    anterior, contrato a contrato (ticker+strike+exp+type), y devuelve los
    mayores incrementos/descensos en %. Requiere al menos 2 días distintos
    de escaneo guardados — con solo 1 día no hay nada contra lo que comparar,
    devuelve listas vacías en vez de fallar."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    fechas = conn.execute(
        'SELECT DISTINCT scan_date FROM options_flow ORDER BY scan_date DESC LIMIT 2'
    ).fetchall()
    if len(fechas) < 2:
        conn.close()
        return {"increase": [], "decrease": [], "nota": "Hace falta al menos 2 días de histórico guardado para comparar OI"}

    fecha_hoy, fecha_prev = fechas[0][0], fechas[1][0]

    rows = conn.execute('''
        SELECT h.ticker, h.strike, h.exp, h.type, h.oi as oi_hoy, p.oi as oi_prev
        FROM options_flow h
        JOIN options_flow p
          ON h.ticker=p.ticker AND h.strike=p.strike AND h.exp=p.exp AND h.type=p.type
        WHERE h.scan_date=? AND p.scan_date=? AND p.oi > 0
        GROUP BY h.ticker, h.strike, h.exp, h.type
    ''', (fecha_hoy, fecha_prev)).fetchall()
    conn.close()

    cambios = []
    for r in rows:
        pct = (r["oi_hoy"] - r["oi_prev"]) / r["oi_prev"] * 100
        if abs(pct) < 1:  # ruido, ignorar cambios triviales
            continue
        cambios.append({
            "ticker": r["ticker"], "strike": r["strike"], "exp": r["exp"],
            "type": r["type"], "daily_pct": round(pct, 1),
        })

    incrementos = sorted([c for c in cambios if c["daily_pct"] > 0], key=lambda x: -x["daily_pct"])[:limit]
    descensos   = sorted([c for c in cambios if c["daily_pct"] < 0], key=lambda x: x["daily_pct"])[:limit]
    return {"increase": incrementos, "decrease": descensos}

def get_ticker_flow_simple(ticker: str, period: str = "1w") -> dict:
    """Historial plano de un ticker — la tabla que pide Marc al buscar/clicar
    un ticker: fecha, tipo de orden, strike, exp, OI, prima. Con un 'net
    score' simple (recuento de señales alcistas menos bajistas, no
    ponderado por prima — igual que el +2 del PDF de referencia)."""
    init_db()
    days_map = {"1w": 7, "2w": 14, "1m": 30, "3m": 90, "4m": 120}
    days     = days_map.get(period, 7)
    from_dt  = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute('''
        SELECT scan_date, type, action, strike, exp, oi, premium, premium_fmt, near_earnings
        FROM options_flow
        WHERE ticker=? AND scan_date>=?
        ORDER BY scan_date DESC, premium DESC
        LIMIT 200
    ''', (ticker.upper(), from_dt)).fetchall()
    conn.close()

    if not rows:
        conn2  = sqlite3.connect(DB_PATH)
        total  = conn2.execute('SELECT COUNT(*) FROM options_flow').fetchone()[0]
        conn2.close()
        if total == 0:
            return {"ok": False, "error": "Todavía no se ha guardado ningún escaneo — usa POST /api/v1/options/scan-now para forzar el primero, o espera al escaneo automático diario."}
        return {"ok": False, "error": f"Sin señales de {ticker.upper()} en este periodo (no significa que no haya operado opciones, solo que no hubo actividad lo bastante inusual para registrarse). Prueba un periodo más largo."}

    en_cartera = ticker.upper() in _obtener_tickers_cartera()
    repetidos  = _obtener_contratos_repetidos()
    ORDER_TYPE = {("call","buy"): "Buy Call", ("put","sell"): "Sell Put",
                  ("put","buy"): "Buy Put", ("call","sell"): "Sell Call"}
    entradas, net_score = [], 0
    for r in rows:
        ot = ORDER_TYPE.get((r["type"], r["action"]), f"{r['action']} {r['type']}")
        net_score += 1 if ot in ("Buy Call", "Sell Put") else -1
        clave = (ticker.upper(), r["strike"], r["exp"], r["type"], r["action"])
        entradas.append({
            "fecha":         r["scan_date"],
            "order_type":    ot,
            "strike":        r["strike"],
            "exp":           r["exp"],
            "oi":            r["oi"],
            "near_earnings": bool(r["near_earnings"]),
            "es_repetida":   clave in repetidos,
            "premium_fmt": r["premium_fmt"],
        })

    return {
        "ok": True, "ticker": ticker.upper(), "period": period, "en_cartera": en_cartera,
        "total": len(entradas), "net_score": net_score, "entradas": entradas,
    }

def run_and_save_scan() -> dict:
    """Ejecuta un escaneo completo del WATCHLIST y lo persiste — pensado para
    correr una vez al día desde un loop programado (ver ws.py), no manualmente
    desde el frontend. El escaneo es pesado (~150 tickers x 5 vencimientos),
    no algo para disparar cada vez que alguien abre la página."""
    data = get_options_flow()
    if not data.get("ok"):
        print(f"[OptionsFlow] Escaneo fallido: {data.get('error', 'desconocido')}")
        return {"ok": False}
    resultado = save_current_scan(data)
    print(f"[OptionsFlow] Escaneo guardado: {resultado['inserted']}/{resultado['total']} entradas nuevas")
    return resultado

# ────────────────────────────────────────────────────────────────────────────

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

MIN_VOLUME = 200   # antes 10 — muy por debajo del estándar de la industria (Barchart usa 500);
                    # 200 es un punto medio razonable dado que escaneamos tickers más pequeños
                    # que los universos de los scanners comerciales, no una copia exacta de Barchart
MIN_OI     = 100    # no existía ningún mínimo antes — sin esto, un contrato con OI=5 y vol=20
                     # da un ratio Vol/OI de 4 (parece "muy inusual") siendo en realidad ilíquido

def _ticker_baseline(ticker: str, dias: int = 30) -> dict:
    """Media histórica de prima e IV del propio ticker, de sus escaneos guardados
    anteriores — usado para puntuar por CUÁNTO SE DESVÍA una entrada de lo normal
    PARA ESE TICKER CONCRETO, en vez de un umbral absoluto igual para todos
    (mismo criterio que ya usa el filtro Large OI Increase/Decrease, aplicado
    ahora también al scoring). $500K en una small-cap y $500K en NVDA no
    significan lo mismo — este es el ajuste que corrige eso.

    LIMITACIÓN HONESTA: la media se calcula sobre las entradas que YA pasaron
    el filtro en escaneos anteriores (lo único que se guarda), no sobre el
    volumen total diario de cada ticker (eso requeriría una tabla de
    seguimiento nueva, ver conversación). Es una aproximación razonable, no
    una media de volumen total — mejora con cada día que se acumula histórico,
    y para tickers sin historial todavía (recién añadidos, o su primer día)
    simplemente no aporta ajuste, cae al criterio absoluto de siempre."""
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        from_dt = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
        rows = conn.execute(
            'SELECT premium, iv FROM options_flow WHERE ticker=? AND scan_date>=? AND scan_date<?',
            (ticker, from_dt, datetime.now().strftime('%Y-%m-%d'))
        ).fetchall()
        conn.close()
        if len(rows) < 5:  # muy poco histórico para que la media signifique algo — no ajustar
            return {"avg_premium": None, "iv_values": []}
        avg_premium = sum(r["premium"] for r in rows) / len(rows)
        iv_values   = sorted(r["iv"] for r in rows if r["iv"] is not None)
        return {"avg_premium": avg_premium, "iv_values": iv_values}
    except Exception:
        return {"avg_premium": None, "iv_values": []}

def _iv_percentile(iv_actual: float, iv_values_historicos: list) -> float | None:
    """Percentil de la IV de hoy dentro del propio histórico del ticker (0-100).
    Ej: 80 significa que la IV de hoy es más alta que el 80% de sus lecturas
    de los últimos 30 días — más informativo que un umbral fijo de IV, porque
    lo que es 'alto' varía muchísimo entre una biotecnológica y una utility."""
    if not iv_values_historicos or iv_actual is None:
        return None
    por_debajo = sum(1 for v in iv_values_historicos if v <= iv_actual)
    return round(por_debajo / len(iv_values_historicos) * 100, 1)

def _score_entry(vol, oi, premium, iv, exp_days, strike_pct_val, baseline: dict = None) -> tuple:
    score  = 0
    signal = "LOW"
    baseline = baseline or {"avg_premium": None, "iv_values": []}

    # Prima — relativa al propio histórico del ticker cuando hay suficiente
    # (5+ entradas en 30 días), si no cae al umbral absoluto de siempre.
    if baseline["avg_premium"]:
        ratio = premium / baseline["avg_premium"]
        if ratio >= 5:    score += 4
        elif ratio >= 3:  score += 3
        elif ratio >= 1.5: score += 2
        elif ratio >= 1:  score += 1
    else:
        if premium >= 2_000_000: score += 4
        elif premium >= 1_000_000: score += 3
        elif premium >= 500_000: score += 2
        elif premium >= 100_000: score += 1

    # Vol/OI ratio
    vol_oi = vol / oi if oi > 0 else vol
    if vol_oi >= 5.0:   score += 3   # UNUSUAL
    elif vol_oi >= 2.0: score += 2
    elif vol_oi >= 0.5: score += 1

    # IV — percentil dentro del propio histórico del ticker cuando hay
    # suficiente, si no cae al umbral absoluto de siempre (60%/40% biotech
    # vs utility no significan lo mismo, ver _iv_percentile).
    iv_pct = _iv_percentile(iv, baseline["iv_values"])
    if iv_pct is not None:
        if iv_pct >= 90:   score += 2
        elif iv_pct >= 70: score += 1
    else:
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
        # Histórico propio del ticker — una sola consulta por ticker, no por
        # contrato (serían cientos de consultas repetidas a la BD si no)
        baseline = _ticker_baseline(ticker)

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

                    if vol < MIN_VOLUME or oi < MIN_OI or price_o < 0.10: continue

                    premium = vol * price_o * 100
                    if premium < min_premium: continue

                    strike_pct_val = (strike - price) / price * 100 if price > 0 else 0
                    strike_pct     = _pct_from_atm(strike, price)

                    score, signal, vol_oi = _score_entry(vol, oi, premium, iv, exp_days, strike_pct_val, baseline)
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
        "timestamp":    get_timestamp(),
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
            "timestamp":       get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}