import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

VENTANA = 10

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

def _mcclellan_proxy(df_spy, sector_data=None):
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
    closes    = df_spy['Close']
    pct       = closes.pct_change()
    ema19     = pct.ewm(span=19).mean()
    ema39     = pct.ewm(span=39).mean()
    mcclellan = (ema19 - ema39) * 1000
    return mcclellan, "Proxy SPY"

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
    if weekly is None or len(weekly) < 20:
        return None, None
    ema200w = weekly['Close'].ewm(span=200, min_periods=20).mean()
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

def _mcclellan_con_giro(df_spy, sector_data=None, ventana=5):
    """
    Extiende _mcclellan_proxy con detección de "giro al alza" — no basta con que
    el oscilador esté en zona extrema negativa, debe estar recuperándose ya
    (pendiente positiva en los últimos días). Esto ataca directamente el problema
    visto en el backtest original: una señal disparada con McClellan todavía
    cayendo (en plena caída en curso) es mucho menos fiable que una con McClellan
    ya virando hacia arriba (indicio de que la presión vendedora está agotándose).
    """
    mcclellan, metodo = _mcclellan_proxy(df_spy, sector_data)
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

def _calcular_score_punto(df_spy, df_vix, sector_data=None, df_vix3m=None):
    """
    Núcleo de scoring puro — recibe DataFrames ya recortados hasta un punto temporal
    dado y devuelve el score + desglose. Reutilizado tanto por get_rsu_algoritmo()
    (cálculo en vivo) como por get_rsu_algoritmo_backtest() (recálculo histórico día
    a día), para que ambos usen exactamente la misma lógica de pesos sin duplicarla.
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
    if rsi_min < 25:
        rsi_score = 12; detalles.append(f"✓ RSI diario min {rsi_min:.1f} < 25 (+12)")
    elif rsi_min < 35:
        rsi_score = 9;  detalles.append(f"✓ RSI diario min {rsi_min:.1f} < 35 (+9)")
    elif rsi_min < 45:
        rsi_score = 4;  detalles.append(f"~ RSI diario min {rsi_min:.1f} < 45 (+4)")
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
    mc_val, girando_al_alza, metodo = _mcclellan_con_giro(df_spy, sector_data)
    mc_score = 0
    if mc_val < -80:
        mc_score = 11; detalles.append(f"✓ McClellan {mc_val:.0f} < -80 (+11)")
    elif mc_val < -50:
        mc_score = 8;  detalles.append(f"~ McClellan {mc_val:.0f} < -50 (+8)")
    elif mc_val < -20:
        mc_score = 3;  detalles.append(f"• McClellan {mc_val:.0f} < -20 (+3)")
    else:
        detalles.append(f"• McClellan {mc_val:.0f} neutral (0)")
    if girando_al_alza and mc_score > 0:
        mc_score += 7
        detalles.append("✓ McClellan girando al alza — presión vendedora agotándose (+7)")
    elif mc_score > 0:
        advertencias.append("⚠ McClellan en zona extrema pero aún sin girar al alza — posible caída en curso")
    score += mc_score
    metricas['Breadth'] = {"score": mc_score, "max": 18, "color": "#9c27b0",
                           "actual": round(mc_val, 1), "metodo": metodo, "girando_al_alza": girando_al_alza}

    # 4. RVOL en el día del mínimo de precio (+12)
    # Atado específicamente al día del precio mínimo de la ventana, no al máximo
    # de volumen de cualquier día — volumen de clímax importa sobre todo si ocurre
    # justo en el día de pánico máximo.
    rvol_min, fecha_min = _rvol_en_minimo(df_spy)
    vol_score = 0
    if rvol_min > 2.5:
        vol_score = 12; detalles.append(f"✓ RVOL {rvol_min:.1f}x en día del mínimo (+12)")
    elif rvol_min > 2.0:
        vol_score = 8;  detalles.append(f"~ RVOL {rvol_min:.1f}x en día del mínimo (+8)")
    elif rvol_min > 1.5:
        vol_score = 4;  detalles.append(f"• RVOL {rvol_min:.1f}x en día del mínimo (+4)")
    else:
        detalles.append("• Sin RVOL significativo en el mínimo (0)")
    score += vol_score
    metricas['Volume'] = {"score": vol_score, "max": 12, "color": "#f23645",
                          "rvol_minimo": round(rvol_min, 2),
                          "fecha_minimo": fecha_min.strftime('%Y-%m-%d') if fecha_min is not None else None}

    # 5. EMA200 semanal — soporte/resistencia de largo plazo (+20)
    ema200w, pendiente_ema200w = _ema200_semanal(df_spy)
    ema200w_score = 0
    cerca_ema200w = False
    if ema200w is not None and ema200w > 0:
        dist_ema200w = (price - ema200w) / ema200w * 100
        cerca_ema200w = abs(dist_ema200w) <= 5
        if cerca_ema200w:
            ema200w_score = 20
            detalles.append(f"✓ Precio a {dist_ema200w:+.1f}% de EMA200 semanal — zona de soporte (+20)")
        elif -15 <= dist_ema200w < -5:
            ema200w_score = 10
            detalles.append(f"~ Precio a {dist_ema200w:+.1f}% bajo EMA200 semanal (+10)")
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
    # Antes era solo contexto informativo sin aportar score. Ahora aporta puntos
    # reales porque el régimen de mercado (alcista/bajista de fondo) es information
    # necesaria para decidir el umbral de VERDE más adelante (ver más abajo).
    sobre_sma200 = bool(price > mm['sma_200'])
    dist_sma200  = round((price - mm['sma_200']) / mm['sma_200'] * 100, 2) if mm['sma_200'] != 0 else 0
    regimen_score = 10 if sobre_sma200 else 0
    if not sobre_sma200:
        advertencias.append(f"⚠ Precio {dist_sma200:.1f}% bajo SMA200 — Régimen bajista, listón de VERDE sube a 90")
        detalles.append("• Bajo SMA200 — Régimen bajista (0)")
    else:
        detalles.append(f"✓ Sobre SMA200 ({dist_sma200:+.1f}%) — Régimen alcista (+10)")
    if price < mm['ema_21']:
        advertencias.append("EMA21 actua como resistencia — Cuidado")
    score += regimen_score
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
    gatekeeper_b = rvol_min > 2.0  # condición B: RVOL extremo en el día del mínimo
    gatekeeper_ok = gatekeeper_a or gatekeeper_b

    vol_confirmado = bool(vol_score >= 4)

    # Umbral dinámico de VERDE: sube a 90 si el régimen de mercado es bajista
    # (precio bajo SMA200 diaria) — exige mucha más evidencia antes de considerar
    # un fondo creíble cuando la tendencia de fondo todavía es adversa.
    umbral_verde = 70 if sobre_sma200 else 90

    if score >= umbral_verde and gatekeeper_ok:
        if vol_confirmado or gatekeeper_a:
            estado, senal, color = "VERDE", "FONDO PROBABLE", "#00ffad"
            ftd_txt = "FTD ya confirmado — convicción institucional verificada." if ftd_confirmado else "FTD aún no confirmado — vigilar próximos 4-7 días para la confirmación de volumen."
            rec = f"Setup óptimo. Score {score}/100 (umbral {umbral_verde}). {ftd_txt} " + ("Revisar advertencias." if advertencias else "Entrada gradual 25% con stop -7%.")
        else:
            estado, senal, color = "VERDE-VOL", "SETUP SIN VOLUMEN", "#00ffad"
            rec = f"Score alto ({score}) y gatekeeper cumplido, pero sin volumen de confirmación. Reducir tamaño (10-15%)."
    elif score >= umbral_verde and not gatekeeper_ok:
        estado, senal, color = "VERDE-VOL", "SCORE ALTO SIN SOPORTE ESTRUCTURAL", "#ff9800"
        rec = f"Score alto ({score}) pero sin gatekeeper estructural (ni cerca de EMA200 semanal, ni RVOL extremo en el mínimo). Posible falsa señal — tratar con máxima cautela."
    elif score >= 50:
        estado, senal, color = "AMBAR", "DESARROLLANDO", "#ff9800"
        rec = "Condiciones mejorando. Preparar watchlist o entrada parcial (10-15%)."
    elif score >= 30:
        estado, senal, color = "AMBAR-BAJO", "PRE-SETUP", "#ff9800"
        rec = "Algunos factores presentes. Mantener liquidez."
    else:
        estado, senal, color = "ROJO", "SIN FONDO", "#f23645"
        rec = "Sin condiciones de fondo detectadas. Preservar capital."

    max_score_real = sum(m['max'] for m in metricas.values() if m['max'] > 0)

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
    }

def get_rsu_algoritmo():
    try:
        # SPY ahora se descarga a 5 años (no 6 meses) porque la EMA200 semanal
        # necesita ~200 semanas (~4 años) de histórico para ser fiable. El resto
        # de factores (RSI, VIX, McClellan, RVOL) siguen operando sobre los
        # últimos meses vía .tail() dentro de cada función — el histórico extra
        # solo es relevante para el cálculo semanal.
        with ThreadPoolExecutor(max_workers=4) as ex:
            f_spy   = ex.submit(lambda: yf.Ticker("SPY").history(period="5y"))
            f_vix   = ex.submit(lambda: yf.Ticker("^VIX").history(period="3mo"))
            f_vix3m = ex.submit(lambda: yf.Ticker("^VIX3M").history(period="5d"))
            f_sect  = ex.submit(_descargar_sectores)
            df_spy      = f_spy.result()
            df_vix      = f_vix.result()
            df_vix3m    = f_vix3m.result()
            sector_data = f_sect.result()

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

        resultado = _calcular_score_punto(df_spy, df_vix, sector_data, df_vix3m)

        # Chart limpio con filtro robusto de percentiles
        closes_raw   = df_spy['Close'].tail(90)
        q10          = float(closes_raw.quantile(0.10))
        q90          = float(closes_raw.quantile(0.90))
        closes_clean = closes_raw[closes_raw.between(q10 * 0.8, q90 * 1.2)].tail(60)

        chart = {
            "dates":  [d.strftime('%Y-%m-%d') for d in closes_clean.index],
            "closes": [round(float(c), 2) for c in closes_clean.values],
        }

        return {
            "ok":        True,
            **resultado,
            "chart":     chart,
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}

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
    cache_key = f"algoritmo:backtest:{years}y:v2"  # v2 — cambia con el nuevo sistema, evita servir caché del sistema viejo
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # Buffer de 5 años antes del periodo real medido, para que la EMA200
        # semanal tenga histórico suficiente desde el primer día evaluado.
        BUFFER_YEARS = 5
        period_str = f"{years + BUFFER_YEARS}y"
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_spy   = ex.submit(lambda: yf.Ticker("SPY").history(period=period_str))
            f_vix   = ex.submit(lambda: yf.Ticker("^VIX").history(period=period_str))
            f_vix3m = ex.submit(lambda: yf.Ticker("^VIX3M").history(period=period_str))
            df_spy_full   = f_spy.result()
            df_vix_full   = f_vix.result()
            df_vix3m_full = f_vix3m.result()

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

        BUFFER = 252 * BUFFER_YEARS  # ~5 años de días de trading
        if len(df_spy_full) <= BUFFER + 60:
            return {"ok": False, "error": "Histórico insuficiente tras aplicar buffer"}

        fechas = df_spy_full.index[BUFFER:]
        closes_full = df_spy_full['Close']

        senales = []
        fue_verde_ayer = False

        # Recorrer día a día desde el final del buffer hasta el final del histórico
        for pos in range(BUFFER, len(df_spy_full)):
            fecha = df_spy_full.index[pos]
            spy_slice = df_spy_full.iloc[:pos + 1]

            # Alinear VIX/VIX3M hasta la misma fecha (pueden tener calendario ligeramente distinto)
            vix_slice   = df_vix_full[df_vix_full.index <= fecha]
            vix3m_slice = df_vix3m_full[df_vix3m_full.index <= fecha] if not df_vix3m_full.empty else None

            try:
                resultado = _calcular_score_punto(spy_slice, vix_slice, sector_data=None, df_vix3m=vix3m_slice)
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
                    "fecha":          fecha.strftime('%Y-%m-%d'),
                    "pos":            pos,
                    "score":          resultado['score'],
                    "umbral_verde":   resultado['umbral_verde'],
                    "gatekeeper_a":   resultado['gatekeeper_a'],
                    "gatekeeper_b":   resultado['gatekeeper_b'],
                    "ftd_confirmado": resultado['ftd_confirmado'],
                    "drawdown_pct":   resultado['drawdown_52w_pct'],
                    "precio":         round(float(closes_full.iloc[pos]), 2),
                    # Desglose por factor — necesario para el análisis de importancia
                    # de variables (correlación factor-individual vs retorno real).
                    "factores": {
                        k: m['score'] for k, m in resultado['metricas'].items() if m.get('max', 0) > 0
                    },
                })

            fue_verde_ayer = es_verde_hoy

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
                # tuvo score alto (por encima de la mediana de esta muestra) vs
                # score bajo — más fácil de leer que un coeficiente de correlación
                # aislado, y no depende de conocer el máximo teórico del factor.
                scores_ordenados = sorted(valores_factor)
                mediana = scores_ordenados[n // 2] if n > 0 else 0
                altos = [retornos_h[i] for i in range(n) if valores_factor[i] > mediana]
                bajos = [retornos_h[i] for i in range(n) if valores_factor[i] <= mediana]

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
                }
        else:
            importancia = None  # muestra insuficiente para un análisis con sentido

        # Quitar el desglose de factores de cada señal individual antes de
        # devolver — ya cumplió su propósito en el cálculo de importancia,
        # no hace falta duplicarlo en cada fila del historial.
        for s in senales:
            s.pop('factores', None)

        result = {
            "ok":              True,
            "years":           years,
            "periodo_inicio":  fechas[0].strftime('%Y-%m-%d'),
            "periodo_fin":     fechas[-1].strftime('%Y-%m-%d'),
            "total_dias":      len(fechas),
            "n_senales":       len(senales),
            "senales":         senales,
            "stats":           stats,
            "importancia":     importancia,
            "horizonte_importancia": horizonte_analisis,
            "metodologia":     "Sistema reformulado: sin Divergencia, FTD como confirmación posterior (no input del score), RSI diario+semanal, VIX con curva VIX/VIX3M, McClellan con giro al alza, RVOL en el día del mínimo, EMA200 semanal, régimen de mercado, gatekeepers obligatorios · McClellan vía proxy SPY (consistente en todo el periodo) · Señal = transición a estado VERDE puro (no VERDE-VOL, que cubre casos de cautela)",
            "timestamp":       datetime.now().strftime('%H:%M:%S'),
        }
        cache.set(cache_key, result, 3600 * 12)  # 12h — recálculo pesado, no cambia intradía
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}