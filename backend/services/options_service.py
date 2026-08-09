import yfinance as yf
import requests
import pandas as pd
import numpy as np
import sqlite3
import os
import sys
import time
import math
from datetime import datetime, timedelta
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402
from sp500_universe import SP500_SECTOR_MAP  # noqa: E402

MASSIVE_KEY  = ""   # unused — placeholder for future provider
MASSIVE_BASE = "https://api.massive.com"
DB_PATH      = os.path.join(os.path.dirname(__file__), '..', 'options_flow.db')

# Una cadena de opciones no se puede recuperar después: yfinance solo sirve la
# de HOY, así que lo que no se guardó esa noche se perdió para siempre. Por eso
# la retención es larga -- 3 años -- en vez del mínimo que harían falta: la
# lectura más profunda de todo el módulo mira 90 días (get_history_from_db,
# get_repeat_signals y get_ticker_history_summary), así que sobra muchísimo
# margen. No es para ahorrar disco (~150 filas/día, unos pocos MB al año), es
# para que la tabla tenga un techo en vez de crecer indefinidamente.
# Ver auditoría Options Flow #17.
RETENTION_DAYS = 1095

# Umbral de prima para los tickers que están en la Cartera del usuario. El
# general son $100.000, pensado para filtrar ruido en un universo de ~570
# valores; en una acción de pocos dólares esa cifra no se alcanza casi nunca,
# así que sobre las posiciones propias el módulo se quedaba mudo. Ver
# auditoría Options Flow #8.
MIN_PREMIUM_CARTERA = 25_000

# ── Foto diaria de Open Interest, independiente del filtro de flujo ───────────
#
# El ranking de "Large OI Increase/Decrease" se calculaba cruzando la tabla de
# flujo consigo misma, y ahí solo hay contratos que superaron el filtro de
# volumen, prima y score. Medido sobre datos reales: de 158 contratos guardados
# un día, solo 33 estaban también el día anterior — el 21%. Es decir, el
# indicador solo podía ver contratos que resultaron "inusuales" LOS DOS DÍAS,
# que es justo lo contrario de lo que debe cazar: un contrato cuyo OI se dispara
# sin que su prima llame la atención era invisible. Ver auditoría #15.
#
# Se guarda aparte y con su propio criterio: solo hace falta OI, no prima ni
# volumen. Dos topes para que la tabla no crezca sin control:
# Ventana, en días, para considerar que un vencimiento está pegado a la fecha
# de resultados -- a un lado o al otro. Más allá de una semana, el vencimiento
# deja de ser una apuesta al evento y pasa a ser una posición ordinaria que
# resulta que lo incluye (una LEAP también cubre los resultados, y no significa
# nada). Ver auditoría #10.
DIAS_EARNINGS = 7

MIN_OI_SNAPSHOT = 100            # por debajo, un cambio porcentual es ruido
MAX_OI_SNAPSHOT_POR_TICKER = 50  # los de mayor OI; acota las filas por escaneo
# Retención corta y a propósito distinta de la del flujo: el ranking solo
# compara las dos últimas sesiones, así que no hace falta guardar años. Con el
# tope de arriba son ~29.000 filas por sesión en el peor caso.
RETENTION_OI_DAYS = 45

_SESION_CACHE: dict = {"fecha": None, "ts": 0.0}


def _fecha_sesion() -> str:
    """Fecha de la última SESIÓN REAL de mercado, no la del reloj del proceso.

    `datetime.now()` sin zona es UTC dentro del contenedor. El cron dispara a
    las 23:00 UTC, pero GitHub Actions se retrasa con frecuencia: pasada la
    medianoche UTC el scan se archivaría bajo el día siguiente aunque describa
    la sesión anterior. Y en un festivo el cron corre igual (va de lunes a
    viernes) y vuelve a descargar el cierre del día previo, así que fechar esas
    filas en el festivo desplazaría una sesión todo el histórico.

    Se resuelve como ya se resolvió en RS/RW #6 y CANSLIM: la fecha sale DEL
    DATO, del índice del propio benchmark, que por definición solo contiene
    sesiones reales -- así no hace falta ningún calendario de festivos. Si SPY
    no responde se cae a la fecha en horario de Nueva York, que sigue siendo
    mejor que UTC, en vez de fabricar una fecha.
    """
    ahora = time.time()
    if _SESION_CACHE["fecha"] and (ahora - _SESION_CACHE["ts"]) < 3600:
        return _SESION_CACHE["fecha"]
    fecha = None
    try:
        hist = yf.Ticker("SPY").history(period="5d")
        if not hist.empty:
            fecha = hist.index[-1].strftime("%Y-%m-%d")
    except Exception as e:
        print(f"[OptionsFlow] No se pudo leer la última sesión de SPY: {type(e).__name__}: {e}")
    if not fecha:
        from zoneinfo import ZoneInfo
        fecha = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    _SESION_CACHE["fecha"] = fecha
    _SESION_CACHE["ts"]    = ahora
    return fecha


def purgar_antiguos(days: int = RETENTION_DAYS) -> int:
    """Borra las filas más antiguas que `days`. Se llama al final de cada
    escaneo -- mismo patrón que insider_service.py::_cleanup_old_transactions."""
    try:
        corte = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        conn  = sqlite3.connect(DB_PATH)
        cur   = conn.execute('DELETE FROM options_flow WHERE scan_date < ?', (corte,))
        borradas = cur.rowcount or 0
        # La foto de OI tiene su propia retención, mucho más corta: solo se usa
        # para comparar las dos últimas sesiones y son muchas más filas por día.
        corte_oi = (datetime.now() - timedelta(days=RETENTION_OI_DAYS)).strftime('%Y-%m-%d')
        cur_oi = conn.execute('DELETE FROM oi_snapshot WHERE scan_date < ?', (corte_oi,))
        borradas_oi = cur_oi.rowcount or 0
        conn.commit()
        conn.close()
        if borradas_oi:
            print(f"[OptionsFlow] Purgadas {borradas_oi} filas de la foto de OI "
                  f"con más de {RETENTION_OI_DAYS} días")
        return borradas
    except Exception as e:
        print(f"[OptionsFlow] Purga fallida: {type(e).__name__}: {e}")
        return 0

# ── UNIVERSO ──────────────────────────────────────────────────────────────────

WATCHLIST = [
    # Mega caps
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","BRK-B","JPM",
    "LLY","V","UNH","XOM","MA","JNJ","PG","HD","MRK","COST","ABBV","CVX",
    "BAC","KO","CRM","PEP","WFC","NFLX","ORCL","AMD","ACN","ADBE","LIN",
    # Tech/Growth
    "PLTR","CRWD","PANW","NET","SNOW","ARM","SMCI","AXON","NBIS","RKLB",
    "COIN","HOOD","MSTR","UBER","ABNB","DXCM","ZS","OKTA","DASH","RIVN",
    "SOFI","MELI","NOW","ANET","FTNT","CPNG","SHOP","PYPL","APP",
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
] + list(SP500_SECTOR_MAP.keys())
# El bloque de arriba (mega caps/tech-growth/finanzas/defensa/energía/ETFs/
# cartera RSU) es curación deliberada para Options Flow, no un intento de
# replicar el S&P500 -- se mantiene tal cual. El S&P500 completo ya no es un
# export estático (antes desactualizado, ver sesión 19): viene en vivo de
# shared/sp500_universe.py, la fuente única del universo.
# AVISO DE ESCALA: el S&P500 completo casi cuadriplica el tamaño de
# WATCHLIST (~149 curados -> 570 tickers reales tras dedup, verificado
# 23/07/2026) — el escaneo de opciones es mucho más pesado por ticker que
# una simple descarga de precio (hasta 5 llamadas a option_chain() por
# ticker, cada una con decenas de filas que iterar). Sesión 35: se subió
# max_workers de 10 a 15 y se añadieron reintentos por vencimiento en
# _process_chain(), y el disparo diario pasó a un cron de GitHub Actions
# (sin límite de tiempo de una petición en vivo) -- si el escaneo sigue
# tardando demasiado o fallando por rate-limit de Yahoo, este es el primer
# sitio a revisar.
WATCHLIST = list(dict.fromkeys(WATCHLIST))


def universo_scan() -> list:
    """WATCHLIST más los tickers de la Cartera que no estuvieran ya dentro.

    El bloque curado de arriba se escribió a mano y la Cartera ha ido cambiando
    desde entonces: medido el 06/08/2026, **9 de las 46 posiciones abiertas no
    estaban en el universo** (AMKR, ATI, FUTU, KOID, NXT, PL, POWL, SPCX,
    UROY). No es que no pasaran el filtro de prima: es que nunca se miraban,
    así que sobre una quinta parte de la cartera el módulo no podía decir nada
    ni aunque hubiera actividad enorme. Ver auditoría Options Flow #8.

    Se resuelve en tiempo de escaneo, no al importar: la Cartera cambia cuando
    el usuario abre o cierra una posición, y una lista congelada al arrancar el
    proceso volvería a quedarse vieja. Si la Cartera no está disponible,
    `get_cartera_tickers()` devuelve un conjunto vacío y el escaneo sigue con el
    universo de siempre — nunca falla por esto."""
    try:
        from services.cartera_service import get_cartera_tickers
        de_cartera = sorted(get_cartera_tickers())
    except Exception as e:
        print(f"[OptionsFlow] No se pudo leer Cartera para el universo: {type(e).__name__}: {e}")
        de_cartera = []
    universo = list(dict.fromkeys(WATCHLIST + de_cartera))
    nuevos = [t for t in de_cartera if t not in WATCHLIST]
    if nuevos:
        print(f"[OptionsFlow] {len(nuevos)} tickers de Cartera añadidos al universo: {nuevos}")
    return universo

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
            near_earnings   INTEGER DEFAULT 0,
            bid             REAL,
            ask             REAL,
            price_opt       REAL
        )
    ''')
    # Añadir columnas nuevas si no existen (migracion segura)
    #
    # bid/ask/price_opt (28/07/2026): ya se descargaban en option_chain y se
    # usaban para clasificar compra/venta (Lee-Ready, ver _process_chain),
    # pero se tiraban al guardar. Son IRRECUPERABLES: yfinance da la cadena
    # de "ahora"; en cuanto pasa el día esa foto desaparece y no existe
    # ninguna fuente gratuita de histórico de cadenas de opciones (los
    # proveedores que sí lo venden cobran miles al año, precisamente porque
    # no se puede reconstruir). Guardarlos cuesta cero llamadas extra.
    # Con bid/ask se puede recalcular a posteriori el spread, revisar la
    # clasificación de dirección con otro criterio, o estimar el precio
    # medio real de ejecución -- nada de eso es posible con lo guardado
    # hasta ahora. price_opt es el lastPrice del propio contrato: el INSERT
    # guardaba el precio del SUBYACENTE dos veces (en price y en
    # underlying_price) y el del contrato en ninguna.
    # Ver DATOS_IRREPRODUCIBLES_PLAN.md, nivel 1.1.
    for col, typedef in [
        ("is_block",    "INTEGER DEFAULT 0"),
        ("is_sweep",    "INTEGER DEFAULT 0"),
        ("near_earnings","INTEGER DEFAULT 0"),
        ("bid",         "REAL"),
        ("ask",         "REAL"),
        ("price_opt",   "REAL"),
        # "cubre" (el vencimiento es posterior a los resultados, así que la
        # opción sigue viva durante el anuncio) o "antes" (vence justo antes,
        # así que NO recoge el movimiento). Ver auditoría #10.
        ("earnings_rel", "TEXT"),
    ]:
        try:
            conn.execute(f"ALTER TABLE options_flow ADD COLUMN {col} {typedef}")
        except Exception:
            pass
    conn.execute('CREATE INDEX IF NOT EXISTS idx_ticker ON options_flow(ticker)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_date   ON options_flow(scan_date)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_signal ON options_flow(signal)')
    # Cobertura de cada escaneo. Sin esto, un escaneo que se deje la mitad de
    # los tickers por el camino -- caída de red, límite del proveedor, un fallo
    # suyo -- produce pocas entradas y llega a la pantalla como un día
    # tranquilo, que es lo contrario de lo que pasó. Guardar cuántos se pidieron
    # y cuántos respondieron es lo que permite distinguir "no hubo actividad"
    # de "no hubo datos". Ver auditoría Options Flow #7.
    conn.execute('''
        CREATE TABLE IF NOT EXISTS oi_snapshot (
            scan_date TEXT NOT NULL,
            ticker    TEXT NOT NULL,
            strike    REAL NOT NULL,
            exp       TEXT NOT NULL,
            type      TEXT NOT NULL,
            oi        INTEGER NOT NULL,
            PRIMARY KEY (scan_date, ticker, strike, exp, type)
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_oisnap_date ON oi_snapshot(scan_date)')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS scan_log (
            scan_date   TEXT PRIMARY KEY,
            scan_ts     TEXT NOT NULL,
            pedidos     INTEGER NOT NULL,
            respondidos INTEGER NOT NULL,
            con_flujo   INTEGER NOT NULL,
            entradas    INTEGER,
            oi_cero     INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def save_flow_to_db(flow_items: list, scan_ts: str, scan_date: str = None):
    """`scan_date` es la fecha de la SESIÓN que describen los datos; `scan_ts`
    es cuándo corrió el proceso. Antes la primera se derivaba de la segunda
    (`scan_ts[:10]`), que es el reloj UTC del contenedor -- ver _fecha_sesion()
    y auditoría Options Flow #11."""
    init_db()
    if not scan_date:
        scan_date = scan_ts[:10]
    conn      = sqlite3.connect(DB_PATH)
    inserted  = 0
    for item in flow_items:
        # `type` va en la clave: una call y una put pueden compartir strike,
        # vencimiento y acción perfectamente, y sin esta columna se
        # consideraban la misma fila -- la segunda se descartaba en silencio.
        # Ver auditoría Options Flow #6.
        existing = conn.execute(
            'SELECT id FROM options_flow WHERE scan_date=? AND ticker=? AND strike=? AND exp=? AND type=? AND action=?',
            (scan_date, item['ticker'], item['strike'], item['exp'], item['type'], item['action'])
        ).fetchone()
        if existing: continue
        conn.execute('''
            INSERT INTO options_flow
            (scan_date,scan_ts,ticker,strike,exp,type,action,premium,premium_fmt,
             volume,oi,vol_oi_ratio,score,signal,price,strike_pct,iv,underlying_price,
             is_block,is_sweep,near_earnings,bid,ask,price_opt,earnings_rel)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
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
            item.get('bid'), item.get('ask'), item.get('price_opt'),
            item.get('earnings_rel'),
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
        "earnings_rel":  item.get("earnings_rel"),
        "en_cartera":    item["ticker"] in cartera_tickers if cartera_tickers is not None else False,
        "es_repetida":   clave in repetidos if repetidos is not None else False,
    }

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
            "earnings_rel":  r["earnings_rel"] if "earnings_rel" in r.keys() else None,
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
    from services.cartera_service import get_cartera_tickers
    cartera_tickers = get_cartera_tickers()
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

    # Cobertura del escaneo que produjo estos datos. Va junto al sesgo del día
    # a propósito: si el escaneo se dejó medio universo, ese sesgo está
    # calculado sobre media muestra y el usuario tiene que poder saberlo antes
    # de leerlo. None en los días anteriores a que existiera el registro.
    return {
        "ok":                 True,
        "scan_date":          ultima_fecha,
        "cobertura":          get_scan_log(ultima_fecha),
        "dia_bias_pct":       dia_bias_pct,
        "dia_bias_label":     dia_bias_label,
        "calls_bought":       [_entrada_simple(e, "Buy Call",  cartera_tickers, repetidos) for e in grupos["Buy Call"]][:25],
        "puts_sold":          [_entrada_simple(e, "Sell Put",  cartera_tickers, repetidos) for e in grupos["Sell Put"]][:25],
        "puts_bought":        [_entrada_simple(e, "Buy Put",   cartera_tickers, repetidos) for e in grupos["Buy Put"]][:20],
        "calls_sold":         [_entrada_simple(e, "Sell Call", cartera_tickers, repetidos) for e in grupos["Sell Call"]][:20],
        "large_oi_increase":  oi_changes["increase"],
        "large_oi_decrease":  oi_changes["decrease"],
        # Aviso cuando la comparación de OI todavía va por el camino antiguo
        # (sesgado) porque aún no hay dos sesiones con foto completa.
        "oi_nota":            oi_changes.get("nota"),
        "oi_comparados":      oi_changes.get("contratos_comparados"),
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

    # Fuente: la foto de OI, no la tabla de flujo. La tabla de flujo solo tiene
    # contratos que superaron el filtro de volumen/prima/score, así que cruzarla
    # consigo misma solo encontraba los que fueron "inusuales" LOS DOS DÍAS
    # -- medido, el 21% de un día ya filtrado. Ver auditoría #15.
    tabla = 'oi_snapshot'
    fechas = conn.execute(
        'SELECT DISTINCT scan_date FROM oi_snapshot ORDER BY scan_date DESC LIMIT 2'
    ).fetchall()
    if len(fechas) < 2:
        # Respaldo para el periodo de transición: la foto empieza a acumularse
        # desde el primer escaneo tras este cambio, así que hasta que haya dos
        # sesiones se sigue usando la tabla de flujo -- con su sesgo, pero es
        # mejor que una pantalla vacía. Se avisa en la respuesta.
        tabla = 'options_flow'
        fechas = conn.execute(
            'SELECT DISTINCT scan_date FROM options_flow ORDER BY scan_date DESC LIMIT 2'
        ).fetchall()
    if len(fechas) < 2:
        conn.close()
        return {"increase": [], "decrease": [], "nota": "Hace falta al menos 2 días de histórico guardado para comparar OI"}

    fecha_hoy, fecha_prev = fechas[0][0], fechas[1][0]

    rows = conn.execute(f'''
        SELECT h.ticker, h.strike, h.exp, h.type, h.oi as oi_hoy, p.oi as oi_prev
        FROM {tabla} h
        JOIN {tabla} p
          ON h.ticker=p.ticker AND h.strike=p.strike AND h.exp=p.exp AND h.type=p.type
        WHERE h.scan_date=? AND p.scan_date=? AND p.oi >= ?
        GROUP BY h.ticker, h.strike, h.exp, h.type
    ''', (fecha_hoy, fecha_prev, MIN_OI_SNAPSHOT)).fetchall()
    conn.close()

    cambios = []
    for r in rows:
        pct = (r["oi_hoy"] - r["oi_prev"]) / r["oi_prev"] * 100
        if abs(pct) < 1:  # ruido, ignorar cambios triviales
            continue
        cambios.append({
            "ticker": r["ticker"], "strike": r["strike"], "exp": r["exp"],
            "type": r["type"], "daily_pct": round(pct, 1),
            "oi_prev": r["oi_prev"], "oi_hoy": r["oi_hoy"],
        })

    incrementos = sorted([c for c in cambios if c["daily_pct"] > 0], key=lambda x: -x["daily_pct"])[:limit]
    descensos   = sorted([c for c in cambios if c["daily_pct"] < 0], key=lambda x: x["daily_pct"])[:limit]
    salida = {"increase": incrementos, "decrease": descensos,
              "contratos_comparados": len(rows), "fuente": tabla}
    if tabla == 'options_flow':
        salida["nota"] = ("Comparación limitada: todavía no hay dos sesiones con foto completa de "
                          "Open Interest, así que solo se comparan contratos que además destacaron "
                          "por prima. Se corrige solo tras el segundo escaneo.")
    return salida

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
        SELECT scan_date, type, action, strike, exp, oi, premium, premium_fmt, near_earnings, earnings_rel
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

    from services.cartera_service import get_cartera_tickers
    en_cartera = ticker.upper() in get_cartera_tickers()
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
            "earnings_rel":  r["earnings_rel"] if "earnings_rel" in r.keys() else None,
            "es_repetida":   clave in repetidos,
            "premium_fmt": r["premium_fmt"],
        })

    return {
        "ok": True, "ticker": ticker.upper(), "period": period, "en_cartera": en_cartera,
        "total": len(entradas), "net_score": net_score, "entradas": entradas,
    }

def run_and_save_scan() -> dict:
    """Ejecuta un escaneo completo del WATCHLIST y lo persiste. Desde la
    sesión 35, lo dispara un cron de GitHub Actions
    (.github/workflows/options_scan.yml) llamando a POST /scan-now a hora
    fija cada tarde tras el cierre de mercado -- antes corría desde un
    loop programado dentro del propio proceso del backend (ver ws.py),
    cuya hora real dependía de cuándo se había reiniciado el contenedor.
    Sigue disponible también para disparo manual. El escaneo es pesado
    (~570 tickers -- curados + S&P500 completo -- x hasta 5 vencimientos),
    no algo para disparar cada vez que alguien abre la página."""
    data = get_options_flow()
    if not data.get("ok"):
        print(f"[OptionsFlow] Escaneo fallido: {data.get('error', 'desconocido')}")
        return {"ok": False}
    resultado = save_current_scan(data)
    print(f"[OptionsFlow] Escaneo guardado: {resultado['inserted']}/{resultado['total']} entradas nuevas "
          f"(sesión {data.get('scan_date')})")
    purgadas = purgar_antiguos()
    if purgadas:
        print(f"[OptionsFlow] Purgadas {purgadas} filas con más de {RETENTION_DAYS} días")
    resultado["purgadas"] = purgadas
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

    # Agrupar por MES (scan_date[:7] es AAAA-MM) con prima ponderada.
    #
    # Antes todo esto se llamaba "weekly"/"week" -- variable, clave del dict
    # y campo de la respuesta de la API -- mientras el comentario de encima
    # ya decía "agrupar por mes". El cálculo siempre fue correcto; lo que
    # engañaba era el nombre, y llegaba hasta la API. Renombrado a mensual.
    # Ver auditoría de Options Flow, hallazgo #16.
    mensual: dict = {}
    for r in records:
        mes = r['scan_date'][:7]
        if mes not in mensual:
            mensual[mes] = {"bull_prem": 0, "bear_prem": 0, "bull_cnt": 0,
                            "bear_cnt": 0, "count": 0, "price": r['underlying_price']}
        is_bull = (r['type']=='call' and r['action']=='buy') or \
                  (r['type']=='put'  and r['action']=='sell')
        if is_bull:
            mensual[mes]['bull_prem'] += r['premium']
            mensual[mes]['bull_cnt']  += 1
        else:
            mensual[mes]['bear_prem'] += r['premium']
            mensual[mes]['bear_cnt']  += 1
        mensual[mes]['count'] += 1

    mensual_list = []
    for k, v in sorted(mensual.items(), reverse=True):
        tp = v['bull_prem'] + v['bear_prem']
        nps_w = (v['bull_prem'] - v['bear_prem']) / tp if tp > 0 else 0
        mensual_list.append({
            "month":      k,
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
        "monthly":         mensual_list,
    }

def _calc_sentiment_momentum(records: list) -> dict:
    """Cambio de sentimiento entre los dos escaneos MÁS RECIENTES que existan.

    Antes comparaba `hoy` contra `datetime.now() - 1 día`, o sea el día natural
    anterior. El cron solo corre de lunes a viernes, así que un lunes comparaba
    contra el domingo -- que nunca tiene scan -- y devolvía "sin datos"; lo
    mismo tras cualquier festivo o fallo puntual del escaneo. En la práctica el
    indicador estaba apagado buena parte de la semana sin decirlo.

    Ahora se toman las dos fechas de sesión presentes en los propios datos, sin
    suponer nada sobre el calendario. Se devuelven ambas fechas para que la UI
    pueda decir contra qué se está comparando en vez de dar por hecho "ayer".
    Ver auditoría Options Flow #12.
    """
    fechas = sorted({r['scan_date'] for r in records if r.get('scan_date')}, reverse=True)
    if len(fechas) < 2:
        return {"available": False}
    fecha_actual, fecha_previa = fechas[0], fechas[1]

    def prem_score(recs):
        bull = sum(r['premium'] for r in recs
                   if (r['type']=='call' and r['action']=='buy') or
                      (r['type']=='put'  and r['action']=='sell'))
        bear = sum(r['premium'] for r in recs
                   if (r['type']=='put'  and r['action']=='buy') or
                      (r['type']=='call' and r['action']=='sell'))
        tot = bull + bear
        return (bull - bear) / tot if tot > 0 else None

    today_nps = prem_score([r for r in records if r['scan_date'] == fecha_actual])
    yest_nps  = prem_score([r for r in records if r['scan_date'] == fecha_previa])

    if today_nps is None or yest_nps is None:
        return {"available": False}

    delta = today_nps - yest_nps
    direction = "mejorando" if delta > 0.1 else "empeorando" if delta < -0.1 else "estable"
    try:
        dias_entre = (datetime.strptime(fecha_actual, '%Y-%m-%d')
                      - datetime.strptime(fecha_previa, '%Y-%m-%d')).days
    except Exception:
        dias_entre = None
    return {
        "available":     True,
        "today_nps":     round(today_nps * 100, 1),
        "yest_nps":      round(yest_nps * 100, 1),
        "delta":         round(delta * 100, 1),
        "direction":     direction,
        "fecha_actual":  fecha_actual,
        "fecha_previa":  fecha_previa,
        "dias_entre":    dias_entre,
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

RISK_FREE_RATE = 0.045  # aproximado -- gamma es poco sensible a r, no
                         # compensa una descarga de red solo por esto

def _norm_pdf(x: float) -> float:
    return math.exp(-x * x / 2) / math.sqrt(2 * math.pi)

def _norm_cdf(x: float) -> float:
    """N(x), normal acumulada. `math.erf` es de la librería estándar -- no
    hace falta scipy, que no es dependencia del proyecto."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))

def _d1(S: float, K: float, T: float, sigma: float, r: float = RISK_FREE_RATE) -> float:
    return (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))

def _bs_gamma(S: float, K: float, T: float, sigma: float, r: float = RISK_FREE_RATE) -> float:
    """Gamma de Black-Scholes -- idéntica para call y put al mismo
    strike/vencimiento. T en años, sigma = IV en decimal (0.30, no 30)."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    return _norm_pdf(_d1(S, K, T, sigma, r)) / (S * sigma * math.sqrt(T))

def _bs_delta(S: float, K: float, T: float, sigma: float, es_call: bool,
              r: float = RISK_FREE_RATE) -> float:
    """Delta de Black-Scholes. Call: N(d1), entre 0 y +1. Put: N(d1)-1,
    entre -1 y 0. A diferencia de gamma, el signo distingue call de put por
    sí solo -- por eso el DEX no necesita ningún convenio de inventario de
    dealer para tener sentido (ver docstring de get_gamma_exposure)."""
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return 0.0
    nd1 = _norm_cdf(_d1(S, K, T, sigma, r))
    return nd1 if es_call else nd1 - 1.0

def _fmt_gex(val: float) -> str:
    """Como _fmt_premium() pero con signo -- GEX puede ser negativo."""
    sign = "+" if val >= 0 else "-"
    v = abs(val)
    if v >= 1_000_000_000: return f"{sign}${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:     return f"{sign}${v/1_000_000:.1f}M"
    if v >= 1_000:         return f"{sign}${v/1_000:.0f}K"
    return f"{sign}${v:.0f}"

_GEX_MAX_EXPIRACIONES = 8   # techo de llamadas a option_chain() por petición
_GEX_MAX_STRIKES      = 40  # strikes pintados, los más cercanos al spot

def get_gamma_exposure(ticker: str, max_dte: int = 50,
                       strike_range: float = None) -> dict:
    """GEX y DEX por strike, con calls y puts separadas.

    GEX (Gamma Exposure) = gamma × OI × 100 × spot² × 0.01. Fórmula
    verificada contra SpotGamma/SqueezeMetrics, quien acuñó el término. El
    signo sale de un CONVENIO de inventario de dealer (calls = dealer largo
    gamma, puts = dealer corto), porque los datos públicos de OI no dicen si
    el dealer está comprado o vendido en cada contrato. Es una estimación
    ampliamente usada, no una observación directa -- el tooltip
    "options-gex" lo dice explícitamente y debe seguir diciéndolo. GEX neto
    positivo → los dealers tienden a amortiguar el movimiento (venden en
    subidas, compran en caídas); negativo → tienden a amplificarlo.

    DEX (Delta Exposure) = delta × OI × 100 × spot. **No necesita ningún
    convenio de dealer**: el signo lo da la propia delta (call positiva, put
    negativa), así que esto es literalmente la exposición direccional del
    open interest, no una inferencia sobre quién está al otro lado. Es una
    afirmación más fuerte que la del GEX y conviene no mezclarlas.

    `max_dte` (días hasta vencimiento) y `strike_range` (± en unidades de
    precio, no en porcentaje ni en número de strikes) replican los dos
    controles de la herramienta de tradingedge.club. `strike_range=None`
    calcula un rango automático del ±12% del spot -- un ±15 fijo es
    razonable para un subyacente de $130 y absurdo para uno de $5 o de $900.

    NO usa _process_chain() -- necesita el open interest de TODA la cadena
    (incluidos contratos sin volumen hoy pero con mucho OI acumulado), no
    solo los que pasarían el filtro de volumen/prima del escaneo de flujo,
    que descartaría justo lo que más pesa aquí."""
    try:
        max_dte = max(1, min(int(max_dte or 50), 365))
        tk    = yf.Ticker(ticker.upper())
        price = 0.0
        try:
            fi    = tk.fast_info
            price = _safe(getattr(fi, 'last_price', None))
        except Exception: pass
        if not price:
            hist  = tk.history(period="2d")
            price = float(hist['Close'].iloc[-1]) if not hist.empty else 0
        if not price:
            return {"ok": False, "error": f"Sin precio para {ticker}"}

        expirations = tk.options
        if not expirations:
            return {"ok": False, "error": f"Sin cadena de opciones para {ticker}"}

        # ±12% del spot por defecto: un ±15 fijo (el valor del PDF, para un
        # subyacente de ~$130) no significa lo mismo en un ticker de $5 que
        # en uno de $900.
        rango = float(strike_range) if strike_range else round(price * 0.12, 2)
        if rango <= 0:
            rango = round(price * 0.12, 2)
        k_min, k_max = price - rango, price + rango

        today = datetime.now().date()
        por_strike: dict = {}
        oi_call = oi_put = 0
        exp_days_min, exp_days_max = None, None

        # Filtrar por días hasta vencimiento ANTES de recortar el número de
        # vencimientos -- tickers con vencimientos diarios (SPY, QQQ...)
        # tienen sus primeros vencimientos cronológicos todos muy cortos, así
        # que recortar antes de filtrar dejaba la cadena vacía para justo los
        # subyacentes con más liquidez de opciones del mercado.
        valid_exps = []
        for exp in expirations:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                exp_days = (exp_date - today).days
                if 0 <= exp_days <= max_dte:
                    valid_exps.append((exp, exp_days))
            except Exception:
                continue

        for exp, exp_days in valid_exps[:_GEX_MAX_EXPIRACIONES]:
            chain = None
            for attempt in range(3):   # mismo patrón de reintentos que _process_chain
                try:
                    chain = tk.option_chain(exp)
                    break
                except Exception:
                    if attempt < 2: time.sleep(1.5)
            if chain is None: continue

            # Un vencimiento de hoy (0 DTE) tiene T=0 y las griegas se van a
            # infinito. Se le da medio día en vez de descartarlo: en tickers
            # con vencimiento diario es donde más gamma hay concentrada.
            T = max(exp_days, 0.5) / 365.0
            for es_call, df in [(True, chain.calls), (False, chain.puts)]:
                for _, row in df.iterrows():
                    oi     = _safe(row.get('openInterest', 0))
                    iv     = _safe(row.get('impliedVolatility', 0))
                    strike = _safe(row.get('strike', 0))
                    if oi <= 0 or iv <= 0 or strike <= 0: continue
                    if not (k_min <= strike <= k_max): continue

                    gamma = _bs_gamma(price, strike, T, iv)
                    delta = _bs_delta(price, strike, T, iv, es_call)
                    # GEX: el signo es el convenio de dealer (call larga,
                    # put corta). DEX: el signo ya viene en la propia delta.
                    gex = (1 if es_call else -1) * gamma * oi * 100 * price ** 2 * 0.01
                    dex = delta * oi * 100 * price

                    s = por_strike.setdefault(strike, {"gex_call": 0.0, "gex_put": 0.0,
                                                       "dex_call": 0.0, "dex_put": 0.0})
                    if es_call:
                        s["gex_call"] += gex; s["dex_call"] += dex; oi_call += oi
                    else:
                        s["gex_put"]  += gex; s["dex_put"]  += dex; oi_put  += oi

            exp_days_min = exp_days if exp_days_min is None else min(exp_days_min, exp_days)
            exp_days_max = exp_days if exp_days_max is None else max(exp_days_max, exp_days)

        if not por_strike:
            return {"ok": False,
                    "error": f"Sin OI/IV suficiente para {ticker.upper()} con "
                             f"Max DTE {max_dte} y rango ±{rango}"}

        filas = []
        for k, v in por_strike.items():
            gex_net = v["gex_call"] + v["gex_put"]
            dex_net = v["dex_call"] + v["dex_put"]
            filas.append({
                "strike":   k,
                "gex_call": round(v["gex_call"], 0), "gex_put": round(v["gex_put"], 0),
                "dex_call": round(v["dex_call"], 0), "dex_put": round(v["dex_put"], 0),
                "gex":      round(gex_net, 0), "gex_fmt": _fmt_gex(gex_net),
                "dex":      round(dex_net, 0), "dex_fmt": _fmt_gex(dex_net),
            })
        # Si el rango deja demasiados strikes, se conservan los más cercanos
        # al spot (no los de mayor GEX: la forma del perfil alrededor del
        # precio es justo lo que se está mirando, y quitarle los huecos
        # intermedios la falsearía).
        filas.sort(key=lambda x: abs(x["strike"] - price))
        filas = filas[:_GEX_MAX_STRIKES]
        filas.sort(key=lambda x: x["strike"])

        total_gex = sum(f["gex"] for f in filas)
        total_dex = sum(f["dex"] for f in filas)
        regimen   = "POSITIVO" if total_gex > 0 else "NEGATIVO"

        return {
            "ok":            True,
            "ticker":        ticker.upper(),
            "price":         round(price, 2),
            "total_gex":     round(total_gex, 0),
            "total_gex_fmt": _fmt_gex(total_gex),
            "total_dex":     round(total_dex, 0),
            "total_dex_fmt": _fmt_gex(total_dex),
            "regimen":       regimen,
            "by_strike":     filas,
            "max_dte":       max_dte,
            "strike_range":  rango,
            "oi_call":       int(oi_call),
            "oi_put":        int(oi_put),
            # Ratio sobre OPEN INTEREST (no sobre volumen ni sobre prima) y
            # solo dentro del rango de strikes pedido -- se dice explícito
            # porque "call/put ratio" a secas es ambiguo y cada web usa una
            # base distinta.
            "call_put_ratio": round(oi_call / oi_put, 2) if oi_put > 0 else None,
            "exp_days_range": [exp_days_min, exp_days_max] if exp_days_min is not None else None,
            "timestamp":     get_timestamp(),
        }
    except Exception as e:
        return {"ok": False, "ticker": ticker.upper(), "error": str(e)}

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
        # Mayor open interest visto en toda la cadena, ANTES de cualquier
        # filtro. Sirve para distinguir un modo de fallo que si no es invisible:
        # el proveedor devuelve la cadena entera con openInterest = 0, todo cae
        # por el mínimo de OI y el ticker parece tranquilo cuando en realidad
        # llegó vacío. Ocurrió de verdad el 06/08/2026.
        oi_max = 0.0
        # Foto de OI de TODA la cadena, recogida antes del filtro de flujo (ver
        # MIN_OI_SNAPSHOT). Es lo que alimenta el ranking de cambios de OI, que
        # antes solo veía los contratos que además destacaban por prima.
        oi_snap: list = []
        bull_prem_total, bear_prem_total = 0, 0
        entries_by_exp: dict = {}   # para sweep detection

        for exp in exps:
            try:
                exp_date = datetime.strptime(exp, '%Y-%m-%d').date()
                exp_days = (exp_date - today).days
                if exp_days < 7 or exp_days > 180: continue
            except Exception:
                continue

            # Reintentos con backoff corto -- option_chain() es la llamada más
            # expuesta a fallos transitorios de red; antes un solo fallo
            # perdía el vencimiento entero sin reintentar.
            chain = None
            for attempt in range(3):
                try:
                    chain = tk.option_chain(exp)
                    break
                except Exception:
                    if attempt < 2:
                        time.sleep(1.5)
            if chain is None:
                continue

            # Proximidad a resultados. Antes solo se marcaban los vencimientos
            # POSTERIORES al anuncio, pero la etiqueta de la pantalla decía
            # «vencimiento cerca de la fecha de earnings», que sugiere cercanía
            # en cualquier dirección. Ver auditoría #10.
            #
            # Y no son lo mismo, son casi lo contrario:
            #   CUBRE  -> el vencimiento cae DESPUÉS del anuncio, así que la
            #             opción sigue viva durante el evento. Es la apuesta a
            #             resultados clásica: IV inflada antes, desplome después.
            #   ANTES  -> el vencimiento cae ANTES del anuncio, así que la
            #             opción NO recoge el movimiento. Suele ser subida
            #             previa o evitar deliberadamente el evento.
            #
            # Se marcan las dos y se distingue cuál es, en vez de mezclarlas
            # bajo un único booleano que no dice de qué caso habla.
            #
            # LÍMITE CONOCIDO: más arriba se descartan los vencimientos a menos
            # de 7 días, así que si los resultados caen dentro de esa semana el
            # caso "antes" no puede detectarse -- esos vencimientos ni siquiera
            # entran en el bucle. Ampliar la ventana de vencimientos es una
            # decisión aparte (metería 0DTE en todo el módulo), así que se deja
            # dicho en vez de resuelto a medias.
            near_earnings = False
            earnings_rel  = None
            if next_earnings:
                try:
                    ed   = datetime.strptime(next_earnings, '%Y-%m-%d').date()
                    dias = (exp_date - ed).days
                    if 0 <= dias <= DIAS_EARNINGS:
                        near_earnings, earnings_rel = True, "cubre"
                    elif -DIAS_EARNINGS <= dias < 0:
                        near_earnings, earnings_rel = True, "antes"
                except Exception:
                    pass

            for opt_type, df in [('call', chain.calls), ('put', chain.puts)]:
                for _, row in df.iterrows():
                    vol     = _safe(row.get('volume', 0))
                    oi      = _safe(row.get('openInterest', 0))
                    price_o = _safe(row.get('lastPrice', 0))
                    strike  = _safe(row.get('strike', 0))
                    iv      = _safe(row.get('impliedVolatility', 0))
                    bid     = _safe(row.get('bid', 0))
                    ask     = _safe(row.get('ask', 0))

                    if oi > oi_max: oi_max = oi
                    if oi >= MIN_OI_SNAPSHOT and strike > 0:
                        oi_snap.append((strike, exp, opt_type, int(oi)))
                    if vol < MIN_VOLUME or oi < MIN_OI or price_o < 0.10: continue

                    premium = vol * price_o * 100
                    if premium < min_premium: continue

                    strike_pct_val = (strike - price) / price * 100 if price > 0 else 0
                    strike_pct     = _pct_from_atm(strike, price)

                    score, signal, vol_oi = _score_entry(vol, oi, premium, iv, exp_days, strike_pct_val, baseline)
                    if score < min_score: continue

                    # Dirección por precio vs. bid/ask (Lee-Ready simplificado):
                    # el último cruce por encima del punto medio del spread
                    # indica agresor comprador. vol/OI mide actividad nueva
                    # frente a posiciones existentes, no dirección -- con
                    # spread inválido (contratos ilíquidos, bid/ask a 0) se
                    # cae a ese heurístico como red de seguridad.
                    if bid > 0 and ask > bid:
                        is_buy = price_o >= (bid + ask) / 2
                    else:
                        is_buy = (vol / oi >= 0.3) if oi > 0 else True
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
                        # Se guardan CRUDOS, no como spread ya calculado: si
                        # mañana se quiere revisar la clasificación de
                        # dirección con otro criterio, o estimar el precio de
                        # ejecución, hará falta bid y ask por separado -- el
                        # spread siempre se puede derivar, al revés no.
                        # 0 significa "Yahoo no dio cotización para este
                        # contrato" (pasa en los muy ilíquidos), y hay que
                        # poder distinguirlo de un spread real de 0.
                        "bid":          round(bid, 4) if bid else None,
                        "ask":          round(ask, 4) if ask else None,
                        "type":         opt_type,
                        "action":       "buy" if is_buy else "sell",
                        "score":        score,
                        "signal":       signal,
                        "color":        "bullish" if (opt_type=='call' and is_buy) or
                                                     (opt_type=='put'  and not is_buy)
                                                  else "bearish",
                        "is_block":     is_block,
                        "near_earnings": near_earnings,
                        "earnings_rel":  earnings_rel,
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
            "oi_max":          oi_max,
            # Solo los de mayor OI: acota las filas por escaneo sin perder los
            # contratos que de verdad mueven la aguja.
            "oi_snapshot":     sorted(oi_snap, key=lambda x: -x[3])[:MAX_OI_SNAPSHOT_POR_TICKER],
            "calls_bought":    sorted(calls_bought, key=lambda x: -x['score'])[:15],
            "puts_bought":     sorted(puts_bought,  key=lambda x: -x['score'])[:10],
            "calls_sold":      sorted(calls_sold,   key=lambda x: -x['score'])[:10],
            "puts_sold":       sorted(puts_sold,    key=lambda x: -x['score'])[:10],
            "next_earnings":   next_earnings,
        }
    except Exception as e:
        return {"ticker": ticker, "ok": False, "error": str(e)}

def get_options_flow(min_premium: float = 100_000, min_score: int = 4, tickers: list = None) -> dict:
    target  = tickers or universo_scan()
    results = []
    # scan_ts = cuándo corrió el proceso. scan_date = qué sesión describen los
    # datos. No son lo mismo y antes la segunda se derivaba de la primera.
    scan_ts   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    scan_date = _fecha_sesion()

    # Umbral rebajado para lo que el usuario TIENE en cartera. Entrar en el
    # universo no basta: el corte de prima actúa ANTES de puntuar, así que una
    # posición de $3 por acción se descarta aunque su actividad en opciones sea
    # extraordinaria PARA ELLA. Con el umbral general nunca aparecería, y sobre
    # las posiciones propias es justo donde más interesa que el módulo hable.
    #
    # No descuadra el sesgo del día porque ese cálculo va PONDERADO POR PRIMA:
    # junto a entradas de decenas de millones, unas cuantas de $25-100K no
    # mueven la aguja. Y las filas quedan marcadas con `en_cartera`, así que
    # siempre se puede distinguir de dónde salió cada una.
    try:
        from services.cartera_service import get_cartera_tickers
        de_cartera = get_cartera_tickers()
    except Exception:
        de_cartera = set()

    from services.yf_pool import yf_executor
    futures = {
        yf_executor.submit(_process_chain, t,
                           MIN_PREMIUM_CARTERA if t in de_cartera else min_premium,
                           min_score): t
        for t in target
    }
    # Tres cuentas distintas, y la diferencia entre ellas es justo la
    # información que faltaba: cuántos se pidieron, a cuántos se les pudo leer
    # la cadena, y cuántos de esos traían algo. `respondidos` bajo significa
    # problema de datos; `con_flujo` bajo con `respondidos` alto significa,
    # ahora sí, un día tranquilo de verdad.
    respondidos = 0
    oi_cero     = 0
    oi_filas: list = []
    for f in futures:
        r = f.result()
        if r.get('ok'):
            respondidos += 1
            # Cadena leída pero con TODO el open interest a cero: el dato llegó
            # vacío, no es que no hubiera actividad. Sin contarlo, un día así se
            # confunde con uno tranquilo aunque la cobertura sea del 99%.
            if not r.get('oi_max'):
                oi_cero += 1
            # La foto de OI se recoge de TODOS los que respondan, no solo de los
            # que tengan flujo destacable. Recogerla solo de `results` sería
            # repetir el sesgo que este cambio viene a corregir: un contrato con
            # OI disparado en un ticker por lo demás tranquilo es exactamente el
            # caso que el ranking debe encontrar.
            for strike, exp, tipo, oi in r.get('oi_snapshot', []):
                oi_filas.append((r['ticker'], strike, exp, tipo, oi))
            if r['total_prem'] > 0:
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
        "scan_date":    scan_date,
        "respondidos":  respondidos,
        "oi_cero":      oi_cero,
        "oi_filas":     oi_filas,
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
    inserted = save_flow_to_db(all_items, flow_data['scan_ts'], flow_data.get('scan_date'))
    guardar_oi_snapshot(flow_data.get('scan_date') or flow_data['scan_ts'][:10],
                        flow_data.get('oi_filas', []))
    guardar_scan_log(
        scan_date   = flow_data.get('scan_date') or flow_data['scan_ts'][:10],
        scan_ts     = flow_data['scan_ts'],
        pedidos     = flow_data.get('scanned', 0),
        respondidos = flow_data.get('respondidos', 0),
        con_flujo   = flow_data.get('matched', 0),
        entradas    = inserted,
        oi_cero     = flow_data.get('oi_cero'),
    )
    return {"ok": True, "inserted": inserted, "total": len(all_items)}


def guardar_oi_snapshot(scan_date: str, filas: list) -> int:
    """Guarda la foto de Open Interest de la sesión. `filas` son tuplas
    (ticker, strike, exp, type, oi). Idempotente por la clave primaria."""
    if not filas:
        return 0
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        conn.executemany(
            'INSERT OR REPLACE INTO oi_snapshot (scan_date, ticker, strike, exp, type, oi) '
            'VALUES (?,?,?,?,?,?)',
            [(scan_date, t, s, e, tp, oi) for (t, s, e, tp, oi) in filas]
        )
        conn.commit()
        conn.close()
        print(f"[OptionsFlow] Foto de OI guardada: {len(filas)} contratos de la sesión {scan_date}")
        return len(filas)
    except Exception as e:
        print(f"[OptionsFlow] No se pudo guardar la foto de OI: {type(e).__name__}: {e}")
        return 0


COBERTURA_MINIMA = 0.80   # por debajo de esto, el escaneo se marca incompleto


def guardar_scan_log(scan_date: str, scan_ts: str, pedidos: int,
                     respondidos: int, con_flujo: int, entradas: int,
                     oi_cero: int = None) -> None:
    """Deja constancia de la cobertura del escaneo. Se sobrescribe si se
    repite el mismo día (REPLACE): un segundo escaneo manual del mismo día
    describe mejor la realidad que el primero."""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        conn.execute(
            'INSERT OR REPLACE INTO scan_log '
            '(scan_date, scan_ts, pedidos, respondidos, con_flujo, entradas, oi_cero) '
            'VALUES (?,?,?,?,?,?,?)',
            (scan_date, scan_ts, pedidos, respondidos, con_flujo, entradas, oi_cero)
        )
        conn.commit()
        conn.close()
        pct = (respondidos / pedidos * 100) if pedidos else 0
        aviso = "  <-- INCOMPLETO" if pedidos and respondidos / pedidos < COBERTURA_MINIMA else ""
        print(f"[OptionsFlow] Cobertura {respondidos}/{pedidos} ({pct:.0f}%), "
              f"{con_flujo} con flujo, {entradas} entradas nuevas{aviso}")
    except Exception as e:
        print(f"[OptionsFlow] No se pudo guardar el registro del escaneo: {type(e).__name__}: {e}")


def get_scan_log(scan_date: str = None) -> dict | None:
    """Cobertura del escaneo de una fecha (por defecto, el más reciente).
    None si no hay registro -- los escaneos anteriores a este cambio no lo
    tienen, y esa ausencia se dice tal cual en vez de inventar un 100%."""
    try:
        init_db()
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        if scan_date:
            row = conn.execute('SELECT * FROM scan_log WHERE scan_date=?', (scan_date,)).fetchone()
        else:
            row = conn.execute('SELECT * FROM scan_log ORDER BY scan_date DESC LIMIT 1').fetchone()
        conn.close()
        if not row:
            return None
        d = dict(row)
        d["cobertura_pct"] = round(d["respondidos"] / d["pedidos"] * 100, 1) if d["pedidos"] else None
        # Dos formas distintas de que un escaneo no sirva, y hay que detectar
        # las dos. La primera es no poder leer los valores. La segunda es
        # leerlos y que vengan vacíos: cadenas con TODO el open interest a
        # cero, que caen por el mínimo de OI y dejan el día en blanco con una
        # cobertura aparentemente perfecta.
        d["cobertura_baja"] = bool(d["pedidos"] and d["respondidos"] / d["pedidos"] < COBERTURA_MINIMA)
        d["oi_cero_pct"] = (round(d["oi_cero"] / d["respondidos"] * 100, 1)
                            if d.get("oi_cero") is not None and d["respondidos"] else None)
        d["datos_vacios"] = bool(d["oi_cero_pct"] is not None and d["oi_cero_pct"] > 50)
        d["incompleto"] = d["cobertura_baja"] or d["datos_vacios"]
        return d
    except Exception:
        return None

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