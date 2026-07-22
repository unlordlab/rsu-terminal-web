import pandas as pd
import numpy as np
import yfinance as yf
import sys, os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

VENTANA = 10

# ── FILTRO DE ESTRÉS DE CRÉDITO (BAA10Y) ────────────────────────────────────
# Motivación real, con datos del propio backtest: las señales VERDE de 2008
# que peor salieron (16/09, 23/09, 30/09 — hasta -25.77% a 60d) se dispararon
# ya con el crédito roto (post-Lehman), mientras que las de enero-julio 2008
# (crisis subprime en curso pero crédito aún no en pánico sistémico) dieron
# resultados razonables.
#
# SERIE: se probó primero con el HY OAS de ICE BofA (BAMLH0A0HYM2), pero se
# confirmó por tres vías independientes (CSV anónimo, endpoint /data/, API
# oficial con API key válida) que FRED solo distribuye programáticamente los
# últimos ~3 años de esa serie — es un índice propietario de ICE Data
# Services con licencia restringida para redistribución vía API/descarga,
# aunque el gráfico interactivo en su web sí muestre el histórico completo.
# No es arreglable con reintentos ni con una key mejor.
#
# Se usa en su lugar BAA10Y (diferencial entre el bono corporativo Baa de
# Moody's y el Treasury a 10 años) — mide el mismo concepto (prima de riesgo
# de crédito exigida a deuda de peor calidad) y es dato público de la Fed sin
# restricción de licencia, con histórico completo desde 1986.
#
# Umbrales (escala BAA10Y, distinta de la de HY OAS): "elevado" ≥3.0% y
# "crítico" ≥4.0% — calibrados con picos históricos reales: 2008 GFC ~6.16%
# (dic-2008), COVID mar-2020 ~3.94%, crisis de deuda europea 2011 ~3.5%,
# energía/China 2015-16 ~3.5%. Deliberadamente NO bloquea VERDE por completo
# — solo lo degrada a VERDE-VOL (igual tratamiento que "sin volumen") —
# porque los suelos reales de 2008-09 y COVID ocurrieron precisamente con el
# spread todavía cerca de su pico; un veto total habría descartado también
# esas oportunidades. Umbrales provisionales — re-evaluar con el backtest ya
# corriendo con datos reales de BAA10Y.
CREDIT_SPREAD_ELEVADO = 3.0
CREDIT_SPREAD_CRITICO = 4.0

def _parsear_csv_fred(texto):
    """Parsea el CSV de FRED a (fechas, valores) — tolerante a las dos
    variantes de formato que usan /data/{id}.csv y /graph/fredgraph.csv
    (cabecera y nombre de columna difieren, pero ambas son 'fecha,valor')."""
    fechas, valores = [], []
    for line in texto.strip().split("\n")[1:]:  # saltar cabecera
        parts = line.split(",")
        if len(parts) != 2:
            continue
        try:
            v = float(parts[1])
        except ValueError:
            continue  # FRED marca los días sin dato con "."
        fechas.append(parts[0])
        valores.append(v)
    return fechas, valores

def _fetch_hy_spread_history():
    """
    Histórico completo del BAA10Y vía FRED.

    CONFIRMADO EN PRODUCCIÓN (dos intentos, dos endpoints distintos —
    /graph/fredgraph.csv y /data/{id}.csv): ambas rutas de descarga CSV
    anónima de FRED (sin API key) truncan a los últimos ~3 años sin avisar,
    aunque devuelvan 200 OK con datos aparentemente válidos. No es un bug de
    parseo — es una limitación real del acceso anónimo. La única vía fiable
    para histórico completo es la API oficial con una API key (gratuita,
    instantánea: https://fred.stlouisfed.org/docs/api/api_key.html).

    Si settings.fred_api_key está configurada, se usa la API oficial (JSON,
    sin límite de rango). Si no, se cae al CSV como mejor esfuerzo — con el
    aviso de "cobertura parcial" ya implementado en el backtest para que se
    note en vez de fallar en silencio.
    """
    import requests
    from config import settings
    api_key = getattr(settings, "fred_api_key", "")

    if api_key:
        try:
            url = (
                "https://api.stlouisfed.org/fred/series/observations"
                f"?series_id=BAA10Y&api_key={api_key}&file_type=json"
                "&observation_start=1996-01-01&sort_order=asc&limit=100000"
            )
            url_log = url.replace(api_key, api_key[:4] + "..." + api_key[-4:])
            print(f"[CreditStressGate] Pidiendo: {url_log}")
            r = requests.get(url, timeout=20)
            print(f"[CreditStressGate] FRED API respondió: HTTP {r.status_code}")
            if r.status_code == 200:
                body = r.json()
                obs = body.get("observations", [])
                print(f"[CreditStressGate] FRED API: 'count' del body = {body.get('count')}, observations recibidas = {len(obs)}"
                      + (f", primera = {obs[0]}, última = {obs[-1]}" if obs else ""))
                fechas, valores = [], []
                for o in obs:
                    try:
                        valores.append(float(o["value"]))
                        fechas.append(o["date"])
                    except (ValueError, KeyError):
                        continue  # "." = sin dato ese día
                if valores:
                    print(f"[CreditStressGate] FRED API (con key) BAA10Y: {len(valores)} puntos ({fechas[0]} → {fechas[-1]})")
                    return pd.Series(valores, index=pd.to_datetime(fechas)).sort_index()
                print("[CreditStressGate] FRED API: 200 OK pero 0 observaciones parseables")
            else:
                print(f"[CreditStressGate] FRED API: status HTTP {r.status_code} — cuerpo: {r.text[:300]}")
        except requests.exceptions.Timeout:
            print("[CreditStressGate] FRED API: TIMEOUT")
        except Exception as e:
            print(f"[CreditStressGate] FRED API: error inesperado ({type(e).__name__}: {e})")
        # Si la API con key falla, no tiene sentido probar el CSV (misma
        # limitación de rango) — se cae directo a "sin datos".
        return None

    print("[CreditStressGate] Sin FRED_API_KEY configurada — usando CSV anónimo (limitado a ~3 años, confirmado). "
          "Consigue una key gratis en https://fred.stlouisfed.org/docs/api/api_key.html y añádela como FRED_API_KEY en .env para histórico completo.")
    try:
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAA10Y",
            timeout=15,
            headers={'User-Agent': 'RSU Terminal contact@rsu-terminal.com'}
        )
        if r.status_code != 200:
            print(f"[CreditStressGate] CSV anónimo: status HTTP {r.status_code}")
            return None
        fechas, valores = _parsear_csv_fred(r.text)
        if not valores:
            print("[CreditStressGate] CSV anónimo: 200 OK pero 0 filas parseables")
            return None
        print(f"[CreditStressGate] CSV anónimo BAA10Y: {len(valores)} puntos ({fechas[0]} → {fechas[-1]}) — cobertura limitada, ver nota arriba")
        return pd.Series(valores, index=pd.to_datetime(fechas)).sort_index()
    except requests.exceptions.Timeout:
        print("[CreditStressGate] CSV anónimo: TIMEOUT")
        return None
    except Exception as e:
        print(f"[CreditStressGate] CSV anónimo: error inesperado ({type(e).__name__}: {e})")
        return None

def _fetch_hy_spread_cached():
    """Envoltorio con caché (6h — FRED publica el BAA10Y una vez al día, con
    retraso de un día) para no golpear FRED en cada carga de la página.

    La caché compartida (L2, SQLite) serializa a JSON — una Series de pandas
    no es JSON-serializable, así que se convierte a una lista plana de
    [fecha_iso, valor] alrededor de la caché en vez de guardar la Series
    directamente (que se rompería en cuanto hubiera más de un worker o un
    reinicio, sirviendo un string inservible en vez de la Series real)."""
    from services.cache import cache
    from config import settings
    tiene_key = bool(getattr(settings, "fred_api_key", ""))
    # La clave incluye si hay API key o no — si algún día se añade/quita la
    # key, el cambio de sufijo invalida automáticamente la caché vieja sin
    # depender de acordarse de subir el número de versión a mano (ya se nos
    # olvidó una vez: la key se añadió pero el resultado limitado del CSV,
    # cacheado 6h antes de añadirla, se siguió sirviendo igual).
    cache_key = f"algoritmo:hy_spread_history:v7:{'key' if tiene_key else 'nokey'}"
    cached = cache.get(cache_key)
    if cached is not None:
        try:
            fechas  = [row[0] for row in cached]
            valores = [row[1] for row in cached]
            return pd.Series(valores, index=pd.to_datetime(fechas)).sort_index()
        except Exception:
            pass  # caché corrupta/formato antiguo — recalcular
    serie = _fetch_hy_spread_history()
    if serie is not None:
        cache.set(cache_key, [[d.strftime('%Y-%m-%d'), v] for d, v in serie.items()], 3600 * 6)
    return serie

def _credit_stress_gate(hy_spread_series, fecha=None, ventana_tendencia=10):
    """
    Devuelve (valor, nivel, empeorando) del BAA10Y en o antes de `fecha` (o el
    último dato disponible si fecha=None, para el cálculo en vivo).
    nivel ∈ {'normal','elevado','critico'}, o (None, None, None) si no hay dato.

    "empeorando" = True si el spread ha subido en los últimos `ventana_tendencia`
    días — no solo el NIVEL importa, importa la DIRECCIÓN. Confirmado con datos
    reales del propio backtest: dos señales en "elevado" (16/09 y 23/09/2008,
    con el crédito rompiéndose activamente tras la caída de Lehman) fueron un
    desastre (-18% a -26% a 60d), mientras que otras igual de "elevado" pero con
    el crédito ya sanando (jul-2009, sep-2011 — recuperación tras la fase aguda
    de sus respectivas crisis) fueron excelentes (+12% a +20%). El nivel
    absoluto no distingue estos dos casos — la tendencia sí.
    """
    if hy_spread_series is None or hy_spread_series.empty:
        return None, None, None
    serie = hy_spread_series[hy_spread_series.index <= fecha] if fecha is not None else hy_spread_series
    if serie.empty:
        return None, None, None
    valor = float(serie.iloc[-1])
    if valor >= CREDIT_SPREAD_CRITICO:
        nivel = "critico"
    elif valor >= CREDIT_SPREAD_ELEVADO:
        nivel = "elevado"
    else:
        nivel = "normal"
    if len(serie) > ventana_tendencia:
        valor_hace_n = float(serie.iloc[-(ventana_tendencia + 1)])
        empeorando = valor > valor_hace_n
    else:
        empeorando = False  # sin histórico suficiente para juzgar tendencia — no penalizar por defecto
    return round(valor, 2), nivel, empeorando

def _fmt_fecha(d):
    """Formato de fecha estándar de la UI: día/mes/año (dd/mm/yyyy)."""
    return d.strftime('%d/%m/%Y') if d is not None else None

def _safe_float(val, default=0.0):
    try:
        v = float(val)
        return v if not np.isnan(v) and not np.isinf(v) else default
    except Exception:
        return default

def _calcular_rsi(prices, period=14):
    delta = prices.diff()
    gain  = delta.clip(lower=0)
    loss  = (-delta).clip(lower=0)
    avg_g = gain.ewm(com=period-1, min_periods=period).mean()
    avg_l = loss.ewm(com=period-1, min_periods=period).mean()
    rs    = avg_g / avg_l.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def _calcular_atr(df, periodo=14):
    high  = df['High']
    low   = df['Low']
    close = df['Close'].shift(1)
    tr    = pd.concat([high - low, (high - close).abs(), (low - close).abs()], axis=1).max(axis=1)
    return tr.ewm(span=periodo, min_periods=periodo).mean()

def _calcular_medias_moviles(df):
    c = df['Close']
    return {
        'price':   _safe_float(c.iloc[-1]),
        'ema_21':  _safe_float(c.ewm(span=21).mean().iloc[-1]),
        'sma_50':  _safe_float(c.tail(50).mean()),
        'sma_200': _safe_float(c.tail(200).mean()) if len(c) >= 200 else _safe_float(c.mean()),
    }

def _detectar_ftd(df):
    if len(df) < 10:
        return None
    closes  = df['Close']
    volumes = df['Volume']
    avg_vol = volumes.rolling(50).mean()
    for i in range(len(df)-1, max(len(df)-20, 3), -1):
        chg       = (float(closes.iloc[i]) - float(closes.iloc[i-1])) / float(closes.iloc[i-1]) * 100
        vol_ratio = _safe_float(volumes.iloc[i]) / _safe_float(avg_vol.iloc[i], 1)
        if chg >= 1.7 and vol_ratio >= 1.2:
            return {"signal": "confirmed", "index": i, "chg": round(chg, 2), "vol_ratio": round(vol_ratio, 2)}
        elif chg >= 1.0 and vol_ratio >= 1.0:
            return {"signal": "potential", "index": i, "chg": round(chg, 2), "vol_ratio": round(vol_ratio, 2)}
    lows = [float(closes.iloc[i]) for i in range(len(df)-5, len(df))]
    if len(lows) >= 3 and lows[-1] > lows[0]:
        return {"signal": "active", "index": len(df)-1}
    return {"signal": "none"}

def _mcclellan_proxy(df_spy, sector_data=None, breadth_real=None):
    # PRIORIDAD 1: amplitud real de las ~500 acciones del S&P 500 — mismo dato
    # que ya usa el widget "Amplitud de Mercado" (scan nocturno vía
    # scripts/scanner_universe.py), EMA19-EMA39 sobre el avance/declive neto
    # DIARIO REAL, el McClellan de verdad, no un proxy. Solo se pasa en el
    # cálculo EN VIVO — el scan nocturno no guarda 20 años de histórico
    # completo de las 500 acciones (sería un dataset enorme), así que el
    # backtest sigue usando el proxy de más abajo sin cambios.
    if breadth_real and len(breadth_real) >= 40:
        net_series = pd.Series([h["advances"] - h["declines"] for h in breadth_real])
        ema19 = net_series.ewm(span=19, adjust=False).mean()
        ema39 = net_series.ewm(span=39, adjust=False).mean()
        return ema19 - ema39, "Amplitud real S&P 500"
    if sector_data and len(sector_data) >= 3:
        up, down = 0, 0
        for etf, hist in sector_data.items():
            if len(hist) < 2:
                continue
            chg = hist['Close'].pct_change().iloc[-1]
            if chg > 0: up += 1
            else:       down += 1
        total = up + down
        if total > 0:
            osc = (up - down) / total * 100
            return pd.Series([osc]), "Sectores"
    closes = df_spy['Close']
    pct    = closes.pct_change()
    ema19  = pct.ewm(span=19).mean()
    ema39  = pct.ewm(span=39).mean()
    diff   = ema19 - ema39

    # BUG CORREGIDO: la fórmula anterior, (ema19-ema39)*1000 sobre retornos
    # diarios brutos, producía valores de magnitud ~3-5 incluso en el peor
    # crash de los últimos 20 años (COVID: verificado con los retornos reales
    # de feb-mar 2020, rango -3.07 a +4.44). Los umbrales de mc_score
    # (-20/-50/-80) fueron calibrados para un McClellan Oscillator real
    # (rango típico ±100), no para esta escala — así que la puntuación de
    # McClellan ha sido 0 SIEMPRE, en las 49 señales VERDE de 20 años de
    # histórico, incluida la peor crisis de la muestra. 18 puntos de 100
    # completamente inertes.
    #
    # Fix: en vez de una escala absoluta arbitraria, se usa el percentil
    # móvil del diferencial de momentum dentro de su propia ventana de ~2
    # años (500 sesiones) — "¿cuán extremo es esto comparado con los últimos
    # 2 años?", igual que se interpreta un oscilador de amplitud real. Esto
    # se auto-calibra a cualquier régimen de volatilidad (2007 tranquilo vs
    # 2020 violento) y garantiza que la escala completa -100/+100 sea
    # alcanzable por construcción, sin depender de adivinar un multiplicador.
    VENTANA_PCT = 500
    percentil = diff.rolling(VENTANA_PCT, min_periods=60).apply(
        lambda x: (x < x[-1]).sum() / len(x) * 100, raw=True
    )
    mcclellan = (percentil - 50) * 2  # 0 → -100 (mínimo extremo) · 100 → +100 (máximo extremo)
    return mcclellan, "Proxy SPY (percentil móvil 2 años)"

def _descargar_sectores():
    etfs   = ['XLK', 'XLF', 'XLV', 'XLY', 'XLP', 'XLI', 'XLB', 'XLRE', 'XLU']
    result = {}
    def _fetch(etf):
        try:
            return etf, yf.Ticker(etf).history(period="1mo")
        except Exception:
            return etf, pd.DataFrame()
    with ThreadPoolExecutor(max_workers=5) as ex:
        for etf, hist in ex.map(_fetch, etfs):
            result[etf] = hist
    return result

def _resample_semanal(df):
    """Reagrupa un DataFrame diario en velas semanales (cierre los viernes)."""
    if len(df) < 14:
        return None
    try:
        weekly = df.resample('W-FRI').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna()
        return weekly if len(weekly) >= 10 else None
    except Exception:
        return None

def _ema200_semanal(df_spy):
    """
    EMA200 semanal — nivel de soporte/resistencia de muy largo plazo. Distinto de
    la SMA200 diaria que ya existía como contexto: la semanal reacciona mucho más
    lento y suele coincidir con zonas donde los institucionales defienden posiciones.
    Devuelve (valor_ema, pendiente_reciente) o (None, None) si no hay histórico suficiente.
    """
    weekly = _resample_semanal(df_spy)
    if weekly is None or len(weekly) < 200:
        return None, None
    ema200w = weekly['Close'].ewm(span=200, min_periods=200).mean()
    valor   = _safe_float(ema200w.iloc[-1])
    # Pendiente: comparar el valor actual contra el de 4 semanas atrás
    if len(ema200w) >= 5:
        pendiente = _safe_float(ema200w.iloc[-1] - ema200w.iloc[-5])
    else:
        pendiente = 0.0
    return valor, pendiente

def _rsi_semanal(df_spy):
    """RSI(14) calculado sobre velas semanales — sobreventa estructural, no solo diaria."""
    weekly = _resample_semanal(df_spy)
    if weekly is None or len(weekly) < 16:
        return None
    rsi_w = _calcular_rsi(weekly['Close'], 14)
    return _safe_float(rsi_w.iloc[-1], default=50.0)

def _rvol_en_minimo(df_spy, ventana=VENTANA):
    """
    RVOL (volumen relativo) atado específicamente al día del precio mínimo de la
    ventana — no al máximo de volumen de cualquier día de la ventana (que es lo que
    hacía la versión anterior). Esto es más preciso: volumen de clímax importa
    sobre todo si ocurre justo en el día de pánico máximo, no en un día cualquiera.
    """
    sub = df_spy.tail(ventana)
    if len(sub) < 3:
        return 0.0, None
    idx_min   = sub['Low'].idxmin()
    vol_media = float(df_spy['Volume'].rolling(20).mean().iloc[-1])
    vol_dia   = float(sub.loc[idx_min, 'Volume'])
    rvol      = vol_dia / vol_media if vol_media > 0 else 1.0
    return rvol, idx_min

def _mcclellan_con_giro(df_spy, sector_data=None, ventana=5, breadth_real=None):
    """
    Extiende _mcclellan_proxy con detección de "giro al alza" — no basta con que
    el oscilador esté en zona extrema negativa, debe estar recuperándose ya
    (pendiente positiva en los últimos días). Esto ataca directamente el problema
    visto en el backtest original: una señal disparada con McClellan todavía
    cayendo (en plena caída en curso) es mucho menos fiable que una con McClellan
    ya virando hacia arriba (indicio de que la presión vendedora está agotándose).
    """
    mcclellan, metodo = _mcclellan_proxy(df_spy, sector_data, breadth_real)
    if not hasattr(mcclellan, 'iloc') or len(mcclellan) < ventana + 1:
        mc_val = float(mcclellan.iloc[-1]) if hasattr(mcclellan, 'iloc') else float(mcclellan or 0)
        return mc_val, False, metodo
    mc_val    = _safe_float(mcclellan.iloc[-1])
    mc_hace_n = _safe_float(mcclellan.iloc[-(ventana + 1)])
    girando_al_alza = mc_val > mc_hace_n
    return mc_val, girando_al_alza, metodo

def _vix_vix3m_ratio(df_vix, df_vix3m=None):
    """
    Ratio VIX/VIX3M (spot a 30 días / implícita a 3 meses) — mide la forma de la
    curva de volatilidad, no solo el nivel del VIX. Ratio > 1.0 = backwardation =
    pánico de corto plazo más caro que el de medio plazo = señal de capitulación
    extrema, frecuentemente coincidente con suelos de mercado (no una señal para
    EVITAR comprar, como sugeriría una lectura ingenua — ver tooltip para más
    detalle sobre por qué esto es así).
    Recibe df_vix3m ya descargado (no lo descarga internamente) para que el
    backtest pueda recortarlo por fecha sin hacer una llamada de red por día.
    Devuelve None si no hay suficiente histórico para evaluarlo.
    """
    try:
        if df_vix3m is None or df_vix3m.empty or df_vix.empty:
            return None
        vix_spot = float(df_vix['Close'].iloc[-1])
        vix_3m   = float(df_vix3m['Close'].iloc[-1])
        if vix_3m <= 0:
            return None
        return round(vix_spot / vix_3m, 3)
    except Exception:
        return None

def _calcular_score_punto(df_spy, df_vix, sector_data=None, df_vix3m=None, credit_spread=None, mcclellan_precalculado=None, breadth_real=None):
    """
    Núcleo de scoring puro — recibe DataFrames ya recortados hasta un punto temporal
    dado y devuelve el score + desglose. Reutilizado tanto por get_rsu_algoritmo()
    (cálculo en vivo) como por get_rsu_algoritmo_backtest() (recálculo histórico día
    a día), para que ambos usen exactamente la misma lógica de pesos sin duplicarla.

    credit_spread: tupla opcional (valor, nivel) del BAA10Y ya resuelta por el
    llamador (ver _credit_stress_gate) — no se descarga aquí para no repetir la
    llamada a FRED en cada día del backtest.
    """
    score        = 0
    detalles     = []
    advertencias = []
    metricas     = {}
    mm           = _calcular_medias_moviles(df_spy)
    price        = mm['price']

    # FTD — ya NO se suma al score. Pasa a ser confirmación posterior: la capitulación
    # se detecta con los demás factores, y el FTD (si llega en los días siguientes)
    # confirma que hay demanda institucional real detrás del rebote. Tratarlo como
    # input simultáneo del mismo score mezclaba dos momentos temporales distintos
    # del proceso real de formación de un fondo (capitulación, luego confirmación).
    ftd_data = _detectar_ftd(df_spy)
    ftd_confirmado = bool(ftd_data and ftd_data.get('signal') == 'confirmed')
    if ftd_data:
        sig = ftd_data.get('signal', 'none')
        if sig == 'confirmed':
            detalles.append("✓ FTD Confirmado — confirma demanda institucional")
            if price < mm['ema_21']:
                advertencias.append("⚠ FTD bajo EMA21 — Posible trampa alcista")
        elif sig in ['potential', 'early']:
            detalles.append("~ FTD en desarrollo (sin confirmar aún)")
        elif sig == 'active':
            detalles.append("• Rally activo sin FTD todavía")
        else:
            detalles.append("✗ Sin FTD")
    metricas['FTD'] = {"score": 0, "max": 0, "color": "#2962ff", "data": ftd_data,
                       "confirmado": ftd_confirmado, "es_confirmacion": True}

    # 1. RSI Sobrevendido — diario + semanal combinado (+18)
    # El semanal añade sobreventa "estructural": un RSI diario extremo dentro de
    # una tendencia semanal todavía sana es una señal más débil que cuando ambos
    # timeframes coinciden en sobreventa.
    rsi_series  = _calcular_rsi(df_spy['Close'], 14)
    rsi_ventana = rsi_series.tail(VENTANA)
    rsi_min     = float(rsi_ventana.min())
    rsi_actual  = float(rsi_series.iloc[-1])
    rsi_sem     = _rsi_semanal(df_spy)
    rsi_score   = 0
    rsi_sem_oversold = rsi_sem is not None and rsi_sem < 40
    if rsi_min < 30:
        rsi_score = 12; detalles.append(f"✓ RSI diario min {rsi_min:.1f} < 30 (+12)")
    elif rsi_min < 40:
        rsi_score = 9;  detalles.append(f"✓ RSI diario min {rsi_min:.1f} < 40 (+9)")
    elif rsi_min < 50:
        rsi_score = 4;  detalles.append(f"~ RSI diario min {rsi_min:.1f} < 50 (+4)")
    elif rsi_actual > 75:
        rsi_score = -4; detalles.append(f"✗ RSI {rsi_actual:.1f} > 75 sobrecompra (-4)")
    else:
        detalles.append("• RSI diario en rango neutral (0)")
    if rsi_sem_oversold:
        rsi_score += 6
        detalles.append(f"✓ RSI semanal {rsi_sem:.1f} < 40 — sobreventa estructural (+6)")
    elif rsi_sem is not None:
        detalles.append(f"• RSI semanal {rsi_sem:.1f} sin sobreventa estructural (0)")
    score += rsi_score
    metricas['RSI'] = {"score": rsi_score, "max": 18, "color": "#00ffad" if rsi_score >= 0 else "#f23645",
                       "actual": round(rsi_actual, 1), "minimo": round(rsi_min, 1),
                       "semanal": round(rsi_sem, 1) if rsi_sem is not None else None}

    # 2. VIX Spike + curva VIX/VIX3M — zonas de posible capitulación (+22)
    vix_score  = 0
    vix3m_ratio = _vix_vix3m_ratio(df_vix, df_vix3m)
    if len(df_vix) > 20:
        vix_ventana = df_vix['Close'].tail(VENTANA)
        vix_max     = float(vix_ventana.max())
        vix_actual  = float(df_vix['Close'].iloc[-1])
        if vix_max > 35:
            vix_score = 16; detalles.append(f"✓ VIX max {vix_max:.1f} > 35 — capitulación (+16)")
        elif vix_max > 30:
            vix_score = 12; detalles.append(f"✓ VIX max {vix_max:.1f} > 30 (+12)")
        elif vix_max > 25:
            vix_score = 8;  detalles.append(f"~ VIX max {vix_max:.1f} > 25 (+8)")
        else:
            detalles.append("• VIX sin spike significativo (0)")
        # Curva VIX/VIX3M: backwardation (ratio > 1.0) = pánico de corto plazo
        # superando al de medio plazo = señal de capitulación adicional, NO de
        # exclusión (ver tooltip — esto corrige una lectura inicial errónea).
        if vix3m_ratio is not None:
            if vix3m_ratio > 1.0:
                vix_score += 6
                detalles.append(f"✓ Curva VIX/VIX3M en backwardation ({vix3m_ratio}) — pánico extremo (+6)")
            elif vix3m_ratio > 0.95:
                vix_score += 3
                detalles.append(f"~ Curva VIX/VIX3M tensa ({vix3m_ratio}) (+3)")
        if score > 50 and vix_actual < 20:
            advertencias.append(f"⚠ VIX actual bajo ({vix_actual:.1f}) — Posible complacencia")
        metricas['VIX'] = {"score": vix_score, "max": 22, "color": "#ff9800",
                           "actual": round(vix_actual, 1), "maximo": round(vix_max, 1),
                           "vix3m_ratio": vix3m_ratio}
    else:
        atr     = _calcular_atr(df_spy)
        atr_med = atr.rolling(20).mean()
        atr_m   = float(atr_med.tail(VENTANA).mean())
        ratio   = float(atr.tail(VENTANA).max()) / atr_m if atr_m > 0 else 1.0
        if ratio > 2.0:   vix_score = 12
        elif ratio > 1.5: vix_score = 8
        metricas['VIX'] = {"score": vix_score, "max": 22, "color": "#ff9800",
                           "actual": round(ratio, 2), "maximo": round(ratio, 2), "is_proxy": True,
                           "vix3m_ratio": None}
    score += vix_score

    # 3. McClellan con giro al alza (+18)
    # No basta con estar en zona extrema negativa — debe estar virando ya hacia
    # arriba. Ataca directamente el problema visto en el backtest original: una
    # señal con McClellan todavía cayendo (caída en curso) es mucho menos fiable
    # que una con McClellan ya recuperándose (presión vendedora agotándose).
    #
    # mcclellan_precalculado permite pasar (mc_val, girando_al_alza, metodo) ya
    # resuelto en vez de recalcularlo aquí — usado por el backtest, que si no
    # recalcularía el percentil móvil (ventana de 500 días) desde cero en cada
    # uno de los ~5000 días simulados, sobre una porción cada vez mayor del
    # histórico. Se calcula una única vez para todo el rango antes del bucle.
    if mcclellan_precalculado is not None:
        mc_val, girando_al_alza, metodo = mcclellan_precalculado
    else:
        mc_val, girando_al_alza, metodo = _mcclellan_con_giro(df_spy, sector_data, breadth_real=breadth_real)
    mc_score = 0
    if mc_val < -80:
        mc_score = 11; detalles.append(f"✓ McClellan {mc_val:.0f} < -80 (+11)")
    elif mc_val < -50:
        mc_score = 8;  detalles.append(f"~ McClellan {mc_val:.0f} < -50 (+8)")
    elif mc_val < -20:
        mc_score = 3;  detalles.append(f"• McClellan {mc_val:.0f} < -20 (+3)")
    else:
        detalles.append(f"• McClellan {mc_val:.0f} neutral (0)")
    # Bonus por giro al alza: se aplica siempre que haya algún nivel negativo,
    # no solo cuando mc_val < -80 (condición anterior demasiado restrictiva).
    # El giro desde cualquier zona negativa es señal de agotamiento vendedor.
    if girando_al_alza and mc_score > 0:
        mc_score += 7
        detalles.append("✓ McClellan girando al alza — presión vendedora agotándose (+7)")
    elif mc_score > 0 and not girando_al_alza:
        advertencias.append("⚠ McClellan negativo pero aún sin girar al alza — posible caída en curso")
    score += mc_score
    metricas['Breadth'] = {"score": mc_score, "max": 18, "color": "#9c27b0",
                           "actual": round(mc_val, 1), "metodo": metodo, "girando_al_alza": girando_al_alza}

    # 4. RVOL en el día del mínimo de precio (+12)
    # Ventana ampliada a 20 días (antes 10) — si el pánico ocurrió hace 2-3 semanas
    # y ahora hay recuperación en curso, el RVOL de ese día sigue siendo relevante.
    rvol_min, fecha_min = _rvol_en_minimo(df_spy, ventana=20)
    vol_score = 0
    if rvol_min > 2.0:
        vol_score = 12; detalles.append(f"✓ RVOL {rvol_min:.1f}x en día del mínimo (+12)")
    elif rvol_min > 1.5:
        vol_score = 8;  detalles.append(f"~ RVOL {rvol_min:.1f}x en día del mínimo (+8)")
    elif rvol_min > 1.2:
        vol_score = 4;  detalles.append(f"• RVOL {rvol_min:.1f}x en día del mínimo (+4)")
    else:
        detalles.append("• Sin RVOL significativo en el mínimo (0)")
    score += vol_score
    metricas['Volume'] = {"score": vol_score, "max": 12, "color": "#f23645",
                          "rvol_minimo": round(rvol_min, 2),
                          "fecha_minimo": _fmt_fecha(fecha_min)}

    # 5. EMA200 semanal — soporte/resistencia de largo plazo (+20)
    # Rangos ampliados para que el factor sea alcanzable en correcciones reales:
    # ±25% → 20pts (antes ±12%), ±40% → 10pts (antes -25%/-12%).
    # La EMA200W semanal en bull market suele estar 20-35% bajo el precio —
    # la versión anterior requería estar tan cerca que casi nunca se activaba.
    ema200w, pendiente_ema200w = _ema200_semanal(df_spy)
    ema200w_score = 0
    cerca_ema200w = False
    if ema200w is not None and ema200w > 0:
        dist_ema200w = (price - ema200w) / ema200w * 100
        cerca_ema200w = abs(dist_ema200w) <= 25
        if cerca_ema200w:
            ema200w_score = 20
            detalles.append(f"✓ Precio a {dist_ema200w:+.1f}% de EMA200 semanal (+20)")
        elif abs(dist_ema200w) <= 40:
            ema200w_score = 10
            detalles.append(f"~ Precio a {dist_ema200w:+.1f}% de EMA200 semanal (+10)")
        else:
            detalles.append(f"• Precio a {dist_ema200w:+.1f}% de EMA200 semanal (0)")
        if pendiente_ema200w is not None and pendiente_ema200w < 0:
            advertencias.append("⚠ EMA200 semanal con pendiente negativa — soporte débil, no fuerte")
    else:
        detalles.append("• EMA200 semanal sin histórico suficiente")
    score += ema200w_score
    metricas['EMA200W'] = {"score": ema200w_score, "max": 20, "color": "#00d9ff",
                           "valor": round(ema200w, 2) if ema200w is not None else None,
                           "pendiente_negativa": bool(pendiente_ema200w is not None and pendiente_ema200w < 0),
                           "cerca": cerca_ema200w}

    # 6. Régimen de mercado — SMA200 diaria (+10)
    # RÉGIMEN DE MERCADO — decide el UMBRAL de VERDE (60 alcista / 70 bajista),
    # ver más abajo. NO suma puntos al score.
    #
    # BUG CORREGIDO: antes sumaba +10 al score Y ADEMÁS bajaba el umbral de
    # 70 a 60 — el mismo hecho binario (¿está el precio sobre la SMA200?)
    # contaba dos veces a favor de la misma dirección, un balanceo efectivo
    # de 20 puntos por una sola señal, mientras el resto de factores solo
    # cuentan una vez. Se mantiene como determinante del umbral (su propósito
    # original, documentado en el historial de este archivo) pero deja de
    # aportar score aparte — se sigue mostrando y trackeando igual (contexto
    # útil, y el propio panel de Importancia de Variables lo sigue midiendo),
    # solo que ya no puntúa dos veces.
    sobre_sma200 = bool(price > mm['sma_200'])
    dist_sma200  = round((price - mm['sma_200']) / mm['sma_200'] * 100, 2) if mm['sma_200'] != 0 else 0
    regimen_score = 10 if sobre_sma200 else 0  # se muestra/trackea, pero NO se suma a `score` (ver abajo)
    if not sobre_sma200:
        advertencias.append(f"⚠ Precio {dist_sma200:.1f}% bajo SMA200 — Régimen bajista, listón de VERDE sube a 63")
        detalles.append("• Bajo SMA200 — Régimen bajista (umbral 63)")
    else:
        detalles.append(f"✓ Sobre SMA200 ({dist_sma200:+.1f}%) — Régimen alcista (umbral 54)")
    if price < mm['ema_21']:
        advertencias.append("EMA21 actua como resistencia — Cuidado")
    metricas['SMA200'] = {"score": regimen_score, "max": 10,
                          "color": "#00ffad" if sobre_sma200 else "#ff9800",
                          "sobre_sma200": sobre_sma200, "distancia_pct": dist_sma200}

    # Drawdown desde máximo de 52 semanas — solo informativo, NUNCA gatekeeper.
    # Un umbral fijo de drawdown bloquearía señales válidas en crashes severos
    # (ej. el suelo real de COVID en 2020-03-26 tenía drawdown >-30%) y dejaría
    # pasar falsos positivos en correcciones leves — no es un buen filtro binario,
    # pero sí es contexto útil para que el usuario calibre el tamaño de posición.
    max_52w = float(df_spy['Close'].tail(252).max()) if len(df_spy) >= 20 else price
    drawdown_pct = round((price - max_52w) / max_52w * 100, 2) if max_52w > 0 else 0

    # ── GATEKEEPERS ──────────────────────────────────────────────────────────
    # Un score alto NO es suficiente para considerar la señal "accionable" — debe
    # cumplirse al menos UNA condición estructural real, o el VERDE se degrada a
    # VERDE-VOL (igual tratamiento visual que "sin volumen", mismo mensaje de
    # cautela). Esto ataca directamente el caso de 2020-03-02 del backtest: score
    # alto en plena caída en curso, sin ningún soporte estructural real cerca.
    gatekeeper_a = cerca_ema200w  # condición A: precio cerca de EMA200 semanal
    gatekeeper_b = rvol_min > 1.5  # bajado de >2.0 a >1.5
    gatekeeper_ok = gatekeeper_a or gatekeeper_b

    vol_confirmado = bool(vol_score >= 4)

    # Umbral dinámico de VERDE: 54 en régimen alcista, 63 en bajista (60%/70%
    # del máximo real alcanzable, 90 — ya no 100, porque SMA200 dejó de sumar
    # al score, ver comentario junto a `regimen_score` más arriba). Reescalado
    # proporcionalmente para no cambiar sin querer cuánto exige el sistema: si
    # se hubieran dejado 60/70 fijos tras quitar esos 10 puntos del máximo
    # alcanzable, el listón real habría subido de golpe (70/100 → 70/90 es
    # más difícil que antes, no la misma exigencia).
    umbral_verde = 54 if sobre_sma200 else 63

    # ── FILTRO DE ESTRÉS DE CRÉDITO ─────────────────────────────────────────
    # Ver comentario junto a CREDIT_SPREAD_CRITICO más arriba. No es un
    # gatekeeper más (esos son "¿hay condición estructural?", permisivos con
    # que se cumpla uno). Este es un filtro de cautela que actúa después,
    # sobre el resultado: si el crédito está roto, un VERDE que de otro modo
    # sería pleno se degrada a VERDE-VOL — no se bloquea del todo, porque los
    # suelos reales de 2008-09 y COVID ocurrieron con el spread aún cerca de
    # su pico, y bloquear del todo habría descartado también esas señales.
    #
    # "elevado" + empeorando (spread subiendo) se trata como "crítico" —
    # confirmado con el propio backtest: 16/09 y 23/09/2008 (crédito
    # rompiéndose activamente, recién caído Lehman) fueron un desastre pese a
    # no cruzar el umbral crítico, mientras que otras señales igual de
    # "elevado" pero con el crédito ya sanando (jul-2009, sep-2011) fueron
    # excelentes. Bloquear TODO "elevado" sin distinguir tendencia mejoraba el
    # agregado del backtest pero descartaba esas recuperaciones reales —
    # verificado con números antes de implementar esto, no es una corazonada.
    credit_valor, credit_nivel, credit_empeorando = credit_spread if credit_spread else (None, None, None)
    credit_bloquea = credit_nivel == "critico" or (credit_nivel == "elevado" and credit_empeorando)
    if credit_nivel == "elevado" and not credit_empeorando:
        advertencias.append(f"⚠ BAA10Y en {credit_valor}% (elevado, ≥{CREDIT_SPREAD_ELEVADO}%) pero mejorando — estrés de crédito presente aunque no empeorando, vigilar igualmente")
    elif credit_nivel == "elevado" and credit_empeorando:
        advertencias.append(f"⚠ BAA10Y en {credit_valor}% (elevado, ≥{CREDIT_SPREAD_ELEVADO}%) y EMPEORANDO — tratado como crítico, crédito deteriorándose activamente")
    elif credit_nivel == "critico":
        advertencias.append(f"⚠ BAA10Y en {credit_valor}% (CRÍTICO, ≥{CREDIT_SPREAD_CRITICO}%) — crisis de crédito sistémica activa, no solo corrección de acciones")

    if score >= umbral_verde and gatekeeper_ok:
        if credit_bloquea:
            estado, senal, color = "VERDE-VOL", "CRÉDITO EN CRISIS", "#ff9800"
            motivo = "crítico" if credit_nivel == "critico" else "elevado y empeorando"
            rec = f"Setup técnico óptimo (score {score}/100) pero el crédito está {motivo} (BAA10Y {credit_valor}%) — el problema puede ser más profundo que un rebote técnico. Entrada muy reducida (10-15%) y vigilar si el spread empieza a comprimir antes de aumentar posición."
        elif vol_confirmado or gatekeeper_a:
            estado, senal, color = "VERDE", "FONDO PROBABLE", "#00ffad"
            ftd_txt = "FTD ya confirmado — convicción institucional verificada." if ftd_confirmado else "FTD aún no confirmado — vigilar próximos 4-7 días para la confirmación de volumen."
            rec = (f"Setup óptimo. Score {score}/100 (umbral {umbral_verde}). {ftd_txt} "
                   "No es (ni pretende ser) el mínimo exacto — es el punto de EMPEZAR a construir posición de forma gradual. "
                   + ("Revisar advertencias antes de actuar." if advertencias else "Entrada gradual 25% con stop -7%; el resto se añade en tramos posteriores, no de golpe."))
        else:
            estado, senal, color = "VERDE-VOL", "SETUP SIN VOLUMEN", "#00ffad"
            rec = f"Score alto ({score}) y gatekeeper cumplido, pero sin volumen de confirmación. Si se entra, primer tramo reducido (10-15%), no la entrada completa."
    elif score >= umbral_verde and not gatekeeper_ok:
        estado, senal, color = "VERDE-VOL", "SCORE ALTO SIN SOPORTE ESTRUCTURAL", "#ff9800"
        rec = f"Score alto ({score}) pero sin gatekeeper estructural (ni cerca de EMA200 semanal, ni RVOL extremo en el mínimo). Posible falsa señal — tratar como AMBAR, no como VERDE: watchlist, no entrada."
    elif score >= 45:  # 50% del máximo real alcanzable (90) — reescalado, ver comentario junto a umbral_verde
        estado, senal, color = "AMBAR", "DESARROLLANDO", "#ff9800"
        rec = "Condiciones mejorando pero aún sin confirmar. Fase de watchlist: identifica y prioriza los candidatos ahora, para tener la decisión ya tomada cuando (si) llegue el VERDE. Todavía no es momento de construir posición."
    elif score >= 27:  # 30% del máximo real alcanzable (90)
        estado, senal, color = "AMBAR-BAJO", "PRE-SETUP", "#ff9800"
        rec = "Algunos factores presentes pero insuficientes. Demasiado pronto incluso para watchlist activa — mantener liquidez y observar."
    else:
        estado, senal, color = "ROJO", "SIN FONDO", "#f23645"
        rec = "Sin condiciones de fondo detectadas. Preservar capital."

    # SMA200 se excluye aquí porque ya no suma a `score` (solo decide el
    # umbral) — incluir su max=10 sobrestimaría el máximo realmente alcanzable.
    max_score_real = sum(m['max'] for k, m in metricas.items() if m['max'] > 0 and k != 'SMA200')

    # ABI (Absolute Breadth Index) — contextual, NO puntúa. Igual que el
    # McClellan real, solo disponible en el cálculo en vivo (el scan nocturno
    # no guarda 20 años de histórico de las 500 acciones para poder
    # backtestearlo). |avances-declives| / total — no dice dirección, dice
    # cuánta dispersión/actividad hay. Ver tooltip para la interpretación.
    abi_valor, abi_estado = None, None
    if breadth_real and len(breadth_real) > 0:
        ultimo = breadth_real[-1]
        total_issues = (ultimo.get("advances") or 0) + (ultimo.get("declines") or 0)
        if total_issues > 0:
            abi_valor = round(abs(ultimo["advances"] - ultimo["declines"]) / total_issues * 100, 1)
            abi_estado = "ALTA DISPERSIÓN" if abi_valor >= 40 else ("BAJA ACTIVIDAD" if abi_valor <= 15 else "NORMAL")
            if abi_estado == "ALTA DISPERSIÓN":
                detalles.append(f"• ABI {abi_valor}% — alta dispersión de mercado (contexto, no puntúa)")

    return {
        "score":            score,
        "max_score":        max_score_real,
        "umbral_verde":     umbral_verde,
        "estado":           estado,
        "senal":            senal,
        "color":            color,
        "recomendacion":    rec,
        "detalles":         detalles,
        "advertencias":     advertencias,
        "metricas":         metricas,
        "medias":           {k: round(v, 2) for k, v in mm.items()},
        "gatekeeper_a":     gatekeeper_a,
        "gatekeeper_b":     gatekeeper_b,
        "ftd_confirmado":   ftd_confirmado,
        "drawdown_52w_pct": drawdown_pct,
        "credit_spread_valor": credit_valor,
        "credit_spread_nivel": credit_nivel,
        "credit_spread_empeorando": credit_empeorando,
        "abi_valor":  abi_valor,
        "abi_estado": abi_estado,
    }

def _fetch_breadth_real():
    from services.scanner_service import get_breadth_history
    return get_breadth_history()

def get_rsu_algoritmo():
    # Caché de 10 min sobre el resultado completo: antes cada carga del
    # Dashboard/Algoritmo disparaba 6 descargas en paralelo Y ejecutaba
    # procesar_resultado_algoritmo() (escritura en SQLite + posible aviso
    # Telegram) para cada usuario que entraba -- con esto, ambas cosas pasan
    # como mucho 1 vez cada 10 min, lo que además elimina de facto la
    # condición de carrera de notificaciones duplicadas entre usuarios
    # concurrentes (el semáforo no cambia en cuestión de segundos, así que
    # no se pierde nada de inmediatez real). Mismo patrón que ya usa el
    # backtest de esta misma función más abajo.
    from services.cache import cache
    cache_key = "algoritmo:live:v1"
    cached = cache.get(cache_key)
    if cached:
        return cached
    try:
        # SPY ahora se descarga a 5 años (no 6 meses) porque la EMA200 semanal
        # necesita ~200 semanas (~4 años) de histórico para ser fiable. El resto
        # de factores (RSI, VIX, McClellan, RVOL) siguen operando sobre los
        # últimos meses vía .tail() dentro de cada función — el histórico extra
        # solo es relevante para el cálculo semanal.
        with ThreadPoolExecutor(max_workers=6) as ex:
            f_spy     = ex.submit(lambda: yf.Ticker("SPY").history(period="5y"))
            f_vix     = ex.submit(lambda: yf.Ticker("^VIX").history(period="3mo"))
            f_vix3m   = ex.submit(lambda: yf.Ticker("^VIX3M").history(period="5d"))
            f_sect    = ex.submit(_descargar_sectores)
            f_credit  = ex.submit(_fetch_hy_spread_cached)
            f_breadth = ex.submit(_fetch_breadth_real)
            df_spy      = f_spy.result()
            df_vix      = f_vix.result()
            df_vix3m    = f_vix3m.result()
            sector_data = f_sect.result()
            credit_hist = f_credit.result()
            try:
                breadth_real = f_breadth.result()
            except Exception as e:
                print(f"[RSU Algoritmo] Amplitud real no disponible, usando proxy: {type(e).__name__}: {e}")
                breadth_real = None

        if len(df_spy) < 50:
            return {"ok": False, "error": "Datos insuficientes de SPY"}

        df_spy = df_spy.dropna(subset=['Close'])

        # Limpiar datos anómalos usando percentiles (solo sobre el tramo reciente,
        # para no distorsionar el histórico largo usado por la EMA200 semanal)
        recent = df_spy.tail(180)
        q10 = float(recent['Close'].quantile(0.05))
        q90 = float(recent['Close'].quantile(0.95))
        df_spy_clean_tail = recent[recent['Close'].between(q10 * 0.7, q90 * 1.3)].copy()
        # Sustituir solo el tramo reciente limpio, conservando el histórico largo intacto
        df_spy = pd.concat([df_spy.iloc[:-len(recent)], df_spy_clean_tail])

        credit_spread = _credit_stress_gate(credit_hist)  # sin fecha → último dato disponible
        resultado = _calcular_score_punto(df_spy, df_vix, sector_data, df_vix3m, credit_spread=credit_spread, breadth_real=breadth_real)
        resultado['precio'] = round(float(df_spy['Close'].iloc[-1]), 2)

        # Registro de cambios de semáforo + notificación Telegram. Envuelto en
        # su propio try/except: un fallo aquí (Telegram caído, BD bloqueada)
        # no debe tumbar el cálculo del algoritmo en vivo, que es lo que ve
        # el usuario en la página.
        try:
            from services.algoritmo_tracking_service import procesar_resultado_algoritmo
            procesar_resultado_algoritmo(resultado)
        except Exception as e:
            print(f"[AlgoritmoTracking] Error procesando resultado: {type(e).__name__}: {e}")

        # Chart limpio con filtro robusto de percentiles
        closes_raw   = df_spy['Close'].tail(90)
        q10          = float(closes_raw.quantile(0.10))
        q90          = float(closes_raw.quantile(0.90))
        closes_clean = closes_raw[closes_raw.between(q10 * 0.8, q90 * 1.2)].tail(60)

        chart = {
            "dates":  [_fmt_fecha(d) for d in closes_clean.index],
            "closes": [round(float(c), 2) for c in closes_clean.values],
        }

        result = {
            "ok":        True,
            **resultado,
            "chart":     chart,
            "timestamp": get_timestamp(),
        }
        cache.set(cache_key, result, 600)  # 10 min
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}

def _retornos_con_stop(closes_full, lows_full, pos, horizontes, precio_entrada, stop_pct=-7.0):
    """
    Retornos forward simulando un stop-loss de stop_pct% desde la entrada —
    la estrategia que de verdad se recomienda en el texto de la señal VERDE
    ("entrada gradual 25% con stop -7%"), no "mantener sin tocar nada" que es
    lo que mide el retorno normal.

    Usa el MÍNIMO diario (Low), no el cierre — un stop se dispara en cuanto
    el precio TOCA ese nivel intradía, cerrar por encima ese mismo día no lo
    salva. Simplificación asumida: el stop se ejecuta exactamente al nivel
    del stop, sin slippage por gap bajista (en la realidad, un hueco a la
    baja podría ejecutar peor que el nivel exacto).

    Una vez disparado el stop en el día k, TODOS los horizontes >= k devuelven
    ese mismo retorno (stop_pct) — estás fuera, no participas de ninguna
    recuperación posterior salvo que reentres (estrategia distinta, no
    simulada aquí). Los horizontes < k no se ven afectados, el stop aún no
    había saltado en ese punto.
    """
    precio_stop = precio_entrada * (1 + stop_pct / 100)
    max_h = max(horizontes)
    dia_stop = None
    for k in range(1, max_h + 1):
        if pos + k >= len(closes_full):
            break
        low_k = lows_full.iloc[pos + k]
        if pd.notna(low_k) and low_k <= precio_stop:
            dia_stop = k
            break

    resultado = {}
    stopeada = {}
    for h in horizontes:
        if pos + h >= len(closes_full):
            resultado[f'd{h}'] = None
            stopeada[f'd{h}'] = False
        elif dia_stop is not None and dia_stop <= h:
            resultado[f'd{h}'] = round(stop_pct, 2)
            stopeada[f'd{h}'] = True
        else:
            precio_h = closes_full.iloc[pos + h]
            resultado[f'd{h}'] = round((precio_h - precio_entrada) / precio_entrada * 100, 2)
            stopeada[f'd{h}'] = False
    return resultado, stopeada


def get_rsu_algoritmo_backtest(years: int = 10) -> dict:
    """
    Backtest histórico del RSU Algoritmo sobre SPY (sistema reformulado: sin
    Divergencia, FTD como confirmación posterior, RSI diario+semanal, VIX con
    curva VIX/VIX3M, McClellan con giro al alza, RVOL en el día del mínimo,
    EMA200 semanal, régimen de mercado, y gatekeepers obligatorios).

    Metodología:
    - Descarga histórico SPY/VIX/VIX3M con buffer adicional de 5 años (no 1 año
      como en la versión anterior) — la EMA200 semanal necesita ~200 semanas
      (~4 años) de histórico previo para ser fiable desde el primer día medido.
    - Recalcula el score día a día usando _calcular_score_punto() — la MISMA
      función que el cálculo en vivo, así que mide exactamente el algoritmo
      actual, no una aproximación.
    - McClellan usa el proxy SPY de forma consistente en todo el backtest (no
      datos sectoriales reales) — recalcular sectores en miles de días sería
      excesivamente costoso en llamadas HTTP, y mezclar fuentes de distinta
      calidad en distintos días introduciría una variable oculta no controlada.
    - Detecta "señal VERDE" como una transición a estado puro 'VERDE' (no
      'VERDE-VOL', que ahora incluye tanto "score alto sin volumen" como "score
      alto sin gatekeeper estructural" — ambos casos de cautela explícita, no
      señales accionables) — mide el momento en que el semáforo se enciende
      en verde pleno, no cada día que permanece encendido.
    - Para cada señal, mide el retorno forward de SPY en +5/+10/+20/+60 días
      de trading.
    - Compara esos retornos contra el "baseline": el retorno medio de SPY en
      esos mismos horizontes calculado sobre TODOS los días del periodo, no
      solo los días de señal. Esta comparación es la que realmente contesta
      si el algoritmo aporta ventaja sobre simplemente estar invertido siempre.
    """
    from services.cache import cache
    cache_key = f"algoritmo:backtest:{years}y:v16"  # v8 — endpoint FRED /data/{id}.csv en vez de /graph/fredgraph.csv (confirmado en logs de producción que este último trunca a ~3 años pase lo que pase); invalida caché v7
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # Buffer de 5 años antes del periodo real medido, para que la EMA200
        # semanal tenga histórico suficiente desde el primer día evaluado.
        BUFFER_YEARS = 5
        period_str = f"{years + BUFFER_YEARS}y"
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_spy    = ex.submit(lambda: yf.Ticker("SPY").history(period=period_str))
            f_vix    = ex.submit(lambda: yf.Ticker("^VIX").history(period=period_str))
            f_vix3m  = ex.submit(lambda: yf.Ticker("^VIX3M").history(period=period_str))
            f_credit = ex.submit(_fetch_hy_spread_cached)
            df_spy_full   = f_spy.result()
            df_vix_full   = f_vix.result()
            df_vix3m_full = f_vix3m.result()
            hy_spread_full = f_credit.result()  # puede ser None si FRED falla — se maneja más abajo

        df_spy_full = df_spy_full.dropna(subset=['Close'])
        df_vix_full = df_vix_full.dropna(subset=['Close'])
        df_vix3m_full = df_vix3m_full.dropna(subset=['Close']) if not df_vix3m_full.empty else df_vix3m_full

        if len(df_spy_full) < 300:
            return {"ok": False, "error": "Histórico insuficiente para backtest"}

        # Normalizar índices de fecha para alinear SPY/VIX/VIX3M por día
        df_spy_full.index = df_spy_full.index.normalize()
        df_vix_full.index = df_vix_full.index.normalize()
        if not df_vix3m_full.empty:
            df_vix3m_full.index = df_vix3m_full.index.normalize()
        # El BAA10Y viene de FRED sin timezone (naive) mientras que SPY/VIX
        # vienen de yfinance con timezone (America/New_York) — sin esto,
        # comparar índices más abajo lanza TypeError.
        if hy_spread_full is not None and not hy_spread_full.empty and df_spy_full.index.tz is not None:
            hy_spread_full.index = hy_spread_full.index.tz_localize(df_spy_full.index.tz)

        BUFFER = 252 * BUFFER_YEARS  # ~5 años de días de trading
        if len(df_spy_full) <= BUFFER + 60:
            return {"ok": False, "error": "Histórico insuficiente tras aplicar buffer"}

        # McClellan precalculado UNA sola vez sobre todo el histórico — evita
        # recalcular el percentil móvil (ventana de 500 días) desde cero en
        # cada uno de los ~5000 días del backtest, sobre una porción cada vez
        # mayor del histórico (ver comentario en _calcular_score_punto).
        mcclellan_full, mcclellan_metodo = _mcclellan_proxy(df_spy_full, sector_data=None)
        VENTANA_GIRO = 5

        fechas = df_spy_full.index[BUFFER:]
        closes_full = df_spy_full['Close']
        # 'Low' para simular el stop -7% (ver _retornos_con_stop) — si por lo
        # que sea faltara algún día, se rellena con el Close de ese día como
        # aproximación conservadora razonable (no hay huecos reales en SPY,
        # pero por robustez frente a datos incompletos de yfinance).
        lows_full = df_spy_full['Low'].fillna(closes_full) if 'Low' in df_spy_full.columns else closes_full

        senales = []
        fue_verde_ayer = False

        # Recorrer día a día desde el final del buffer hasta el final del histórico
        for pos in range(BUFFER, len(df_spy_full)):
            fecha = df_spy_full.index[pos]
            spy_slice = df_spy_full.iloc[:pos + 1]

            # Alinear VIX/VIX3M hasta la misma fecha (pueden tener calendario ligeramente distinto)
            vix_slice   = df_vix_full[df_vix_full.index <= fecha]
            vix3m_slice = df_vix3m_full[df_vix3m_full.index <= fecha] if not df_vix3m_full.empty else None
            credit_spread = _credit_stress_gate(hy_spread_full, fecha)

            mc_val    = _safe_float(mcclellan_full.iloc[pos])
            mc_hace_n = _safe_float(mcclellan_full.iloc[pos - VENTANA_GIRO]) if pos >= VENTANA_GIRO else mc_val
            mcclellan_precalculado = (mc_val, mc_val > mc_hace_n, mcclellan_metodo)

            try:
                resultado = _calcular_score_punto(spy_slice, vix_slice, sector_data=None, df_vix3m=vix3m_slice, credit_spread=credit_spread, mcclellan_precalculado=mcclellan_precalculado)
            except Exception:
                fue_verde_ayer = False
                continue

            # Solo el estado 'VERDE' puro cuenta como señal accionable real —
            # 'VERDE-VOL' ahora cubre tanto "sin volumen" como "sin gatekeeper
            # estructural", ambos casos de cautela explícita que el propio
            # sistema marca como NO accionables.
            es_verde_hoy = resultado['estado'] == 'VERDE'

            if es_verde_hoy and not fue_verde_ayer:
                senales.append({
                    "fecha":          _fmt_fecha(fecha),
                    "pos":            pos,
                    "score":          resultado['score'],
                    "umbral_verde":   resultado['umbral_verde'],
                    "gatekeeper_a":   resultado['gatekeeper_a'],
                    "gatekeeper_b":   resultado['gatekeeper_b'],
                    "ftd_confirmado": resultado['ftd_confirmado'],
                    "drawdown_pct":   resultado['drawdown_52w_pct'],
                    "credit_spread_valor": resultado['credit_spread_valor'],
                    "credit_spread_nivel": resultado['credit_spread_nivel'],
                    "credit_spread_empeorando": resultado['credit_spread_empeorando'],
                    "precio":         round(float(closes_full.iloc[pos]), 2),
                    # Desglose por factor — necesario para el análisis de importancia
                    # de variables (correlación factor-individual vs retorno real).
                    "factores": {
                        k: m['score'] for k, m in resultado['metricas'].items() if m.get('max', 0) > 0
                    },
                })

            fue_verde_ayer = es_verde_hoy

        # Guardar posiciones antes de que el bucle siguiente las borre — se
        # necesitan para agrupar señales cercanas en "episodios" independientes
        # (ver más abajo, sección de episodios).
        posiciones_senales = [s['pos'] for s in senales]

        # Calcular retornos forward para cada señal, en varios horizontes
        horizontes = [5, 10, 20, 60]
        for s in senales:
            pos = s['pos']
            precio_entrada = closes_full.iloc[pos]
            s['retornos'] = {}
            for h in horizontes:
                if pos + h < len(closes_full):
                    precio_futuro = closes_full.iloc[pos + h]
                    ret = round((precio_futuro - precio_entrada) / precio_entrada * 100, 2)
                    s['retornos'][f'd{h}'] = ret
                else:
                    s['retornos'][f'd{h}'] = None  # fuera de rango (señal muy reciente)
            # Retornos siguiendo la estrategia realmente recomendada (stop -7%),
            # no "mantener sin tocar nada" — ver _retornos_con_stop.
            s['retornos_con_stop'], s['stopeada'] = _retornos_con_stop(closes_full, lows_full, pos, horizontes, precio_entrada, stop_pct=-7.0)
            del s['pos']  # no exponer el índice interno en la respuesta

        # Baseline: retorno medio de SPY en cada horizonte calculado sobre TODOS
        # los días del periodo medido (no solo los días de señal) — la comparación
        # honesta de "¿el algoritmo aporta algo sobre estar simplemente invertido?"
        baseline = {}
        for h in horizontes:
            rets = []
            for pos in range(BUFFER, len(closes_full) - h):
                precio_ini = closes_full.iloc[pos]
                precio_fin = closes_full.iloc[pos + h]
                rets.append((precio_fin - precio_ini) / precio_ini * 100)
            baseline[f'd{h}'] = round(float(np.mean(rets)), 2) if rets else None

        # Estadísticas agregadas por horizonte: retorno medio de las señales,
        # tasa de éxito (% de señales con retorno positivo), y nº de señales válidas
        stats = {}
        for h in horizontes:
            key = f'd{h}'
            valid = [s['retornos'][key] for s in senales if s['retornos'][key] is not None]
            if valid:
                stats[key] = {
                    "retorno_medio_senal": round(float(np.mean(valid)), 2),
                    "retorno_baseline":    baseline[key],
                    "ventaja_pp":          round(float(np.mean(valid)) - (baseline[key] or 0), 2),
                    "tasa_exito_pct":      round(sum(1 for v in valid if v > 0) / len(valid) * 100, 1),
                    "n_senales":           len(valid),
                }
            else:
                stats[key] = None

        # Mismo cálculo pero con el stop -7% simulado — la estrategia que de
        # verdad se recomienda, no "mantener sin tocar nada". El baseline es
        # el mismo (comprar y mantener SPY sin stop es la comparación honesta
        # en ambos casos — el stop es una particularidad de ESTA estrategia,
        # no algo que también haría un inversor pasivo).
        stats_con_stop = {}
        for h in horizontes:
            key = f'd{h}'
            valid = [s['retornos_con_stop'][key] for s in senales if s['retornos_con_stop'][key] is not None]
            if valid:
                stats_con_stop[key] = {
                    "retorno_medio_senal": round(float(np.mean(valid)), 2),
                    "retorno_baseline":    baseline[key],
                    "ventaja_pp":          round(float(np.mean(valid)) - (baseline[key] or 0), 2),
                    "tasa_exito_pct":      round(sum(1 for v in valid if v > 0) / len(valid) * 100, 1),
                    "n_senales":           len(valid),
                    "n_stopeadas":         sum(1 for s in senales if s['stopeada'][key]),
                }
            else:
                stats_con_stop[key] = None

        # ── ANÁLISIS DE IMPORTANCIA DE VARIABLES ────────────────────────────────
        # Para cada factor, mide su relación real con el retorno forward de las
        # señales ya detectadas — antes de tocar ningún peso, esto dice qué
        # factores se han correlacionado más con buenos resultados en la práctica,
        # en vez de asignar pesos por intuición. Usa el horizonte de 20 días por
        # ser donde el sistema anterior mostró más señal real (ver backtest previo).
        importancia = {}
        horizonte_analisis = 20
        key_h = f'd{horizonte_analisis}'
        factor_names = ['RSI', 'VIX', 'Breadth', 'Volume', 'EMA200W', 'SMA200']

        senales_con_retorno = [s for s in senales if s['retornos'].get(key_h) is not None]

        if len(senales_con_retorno) >= 8:
            for factor in factor_names:
                valores_factor = [s['factores'].get(factor, 0) for s in senales_con_retorno]
                retornos_h     = [s['retornos'][key_h] for s in senales_con_retorno]

                # Correlación de Pearson simple (sin librerías externas) entre el
                # score del factor en el momento de la señal y el retorno forward.
                n = len(valores_factor)
                mean_x, mean_y = np.mean(valores_factor), np.mean(retornos_h)
                cov = sum((valores_factor[i] - mean_x) * (retornos_h[i] - mean_y) for i in range(n))
                std_x = (sum((x - mean_x) ** 2 for x in valores_factor)) ** 0.5
                std_y = (sum((y - mean_y) ** 2 for y in retornos_h)) ** 0.5
                correlacion = round(cov / (std_x * std_y), 3) if std_x > 0 and std_y > 0 else None

                # Comparación más interpretable: retorno medio cuando el factor
                # tuvo score alto vs score bajo — más fácil de leer que un
                # coeficiente de correlación aislado.
                #
                # BUG CORREGIDO: la versión anterior comparaba cada valor contra
                # la mediana con ">" estricto. La mayoría de estos factores son
                # discretos (p.ej. 0 o el máximo, o pocos valores posibles), así
                # que en cuanto >50% de las señales compartían el valor mayoritario,
                # la mediana coincidía con ese valor y NINGÚN caso quedaba "> mediana"
                # → grupo "alto" vacío (n=0) sistemáticamente, aunque sí hubiera
                # variación real en la muestra (por eso "corr" podía mostrar un
                # número mientras alto/bajo mostraba n=0). Ahora se hace un split
                # por ranking (mitad superior vs mitad inferior de valores), que
                # no depende de que la mediana caiga justo en el punto de corte.
                if std_x == 0:
                    # Sin variación real: el factor tuvo el mismo valor en todas
                    # las señales de esta muestra — no hay nada que comparar.
                    importancia[factor] = {
                        "correlacion_d20":          None,
                        "retorno_medio_score_alto": None,
                        "retorno_medio_score_bajo": None,
                        "n_alto":   0,
                        "n_bajo":   0,
                        "fiable":   False,
                        "sin_variacion": True,
                    }
                else:
                    valores_unicos = sorted(set(valores_factor))
                    if len(valores_unicos) <= 4:
                        # Factor discreto/binario (p.ej. Régimen SMA200: solo 0 o 10).
                        # BUG CORREGIDO: forzar un split de tamaño fijo (mitad/mitad)
                        # por ranking, cuando las dos clases reales no tienen el mismo
                        # tamaño, "gotea" empates de la clase minoritaria al grupo
                        # contrario y contamina la media — se detectó porque en
                        # Régimen SMA200 la corr salía negativa pero el grupo "alto"
                        # mostraba mejor retorno medio que el "bajo" (contradictorio:
                        # con una variable binaria ambos deben apuntar en el mismo
                        # sentido). Ahora se agrupa por el valor real: "alto" = valor
                        # máximo observado, "bajo" = el resto — sin contaminación.
                        valor_max = valores_unicos[-1]
                        idx_altos = [i for i in range(n) if valores_factor[i] == valor_max]
                        idx_bajos = [i for i in range(n) if valores_factor[i] != valor_max]
                    else:
                        # Factor con suficiente variación continua (RSI, VIX, RVOL,
                        # EMA200W): split por ranking, mitad superior vs inferior.
                        orden = sorted(range(n), key=lambda i: valores_factor[i], reverse=True)
                        corte = (n + 1) // 2  # mitad superior (redondeando hacia arriba)
                        idx_altos = orden[:corte]
                        idx_bajos = orden[corte:]

                    altos = [retornos_h[i] for i in idx_altos]
                    bajos = [retornos_h[i] for i in idx_bajos]

                    importancia[factor] = {
                        "correlacion_d20":          correlacion,
                        "retorno_medio_score_alto": round(float(np.mean(altos)), 2) if altos else None,
                        "retorno_medio_score_bajo": round(float(np.mean(bajos)), 2) if bajos else None,
                        "n_alto":   len(altos),
                        "n_bajo":   len(bajos),
                        # Si cualquiera de los dos grupos tiene <2 muestras, la comparación
                        # alto/bajo no es estadísticamente fiable aunque el número se calcule
                        # igual — se marca explícitamente para que el frontend lo muestre con cautela.
                        "fiable":   bool(len(altos) >= 2 and len(bajos) >= 2),
                        "sin_variacion": False,
                    }
        else:
            importancia = None  # muestra insuficiente para un análisis con sentido

        # ── EPISODIOS INDEPENDIENTES ─────────────────────────────────────────
        # "N señales" puede sobrestimar la fiabilidad estadística: varias
        # señales seguidas del mismo evento de mercado (p.ej. 4 señales en 2
        # semanas durante un mismo crash) no son 4 pruebas independientes, son
        # el mismo episodio disparando varias veces. Se agrupan señales que
        # caen a ≤15 días de trading de la anterior en un mismo "episodio" —
        # da una medida más honesta de cuántos eventos de mercado distintos
        # ha visto realmente el sistema.
        EPISODIO_GAP = 15
        n_episodios = 0
        pos_anterior = None
        for pos in posiciones_senales:
            if pos_anterior is None or (pos - pos_anterior) > EPISODIO_GAP:
                n_episodios += 1
            pos_anterior = pos

        # Quitar el desglose de factores de cada señal individual antes de
        # devolver — ya cumplió su propósito en el cálculo de importancia,
        # no hace falta duplicarlo en cada fila del historial.
        for s in senales:
            s.pop('factores', None)

        credit_ok = hy_spread_full is not None and not hy_spread_full.empty
        credit_cobertura_completa = credit_ok and hy_spread_full.index.min() <= fechas[0]
        result = {
            "ok":              True,
            "years":           years,
            "periodo_inicio":  _fmt_fecha(fechas[0]),
            "periodo_fin":     _fmt_fecha(fechas[-1]),
            "total_dias":      len(fechas),
            "n_senales":       len(senales),
            "n_episodios":     n_episodios,
            "senales":         senales,
            "stats":           stats,
            "stats_con_stop":  stats_con_stop,
            "importancia":     importancia,
            "horizonte_importancia": horizonte_analisis,
            "credit_spread_disponible": credit_ok,
            "credit_spread_cobertura_completa": credit_cobertura_completa,
            "credit_spread_desde": _fmt_fecha(hy_spread_full.index.min()) if credit_ok else None,
            "metodologia":     "Sistema reformulado: sin Divergencia, FTD como confirmación posterior (no input del score), RSI diario+semanal, VIX con curva VIX/VIX3M, McClellan con giro al alza, RVOL en el día del mínimo, EMA200 semanal, régimen de mercado, gatekeepers obligatorios, filtro de estrés de crédito (BAA10Y) · McClellan vía proxy SPY (consistente en todo el periodo) · Señal = transición a estado VERDE puro (no VERDE-VOL, que cubre casos de cautela)",
            "timestamp":       get_timestamp(),
        }
        # Si el fetch de BAA10Y falló ESTE cálculo en concreto, o si tiene
        # datos pero no cubre todo el rango del backtest (ver
        # credit_spread_cobertura_completa), el backtest se completa igualmente
        # (sin filtro de crédito en los tramos sin cobertura) pero no se guarda
        # 12h — un fallo puntual o parcial de FRED no debe bloquear el filtro
        # medio día.
        ttl = 3600 * 12 if credit_cobertura_completa else 300
        cache.set(cache_key, result, ttl)
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}