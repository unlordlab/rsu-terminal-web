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

def _calcular_score_punto(df_spy, df_vix, sector_data=None):
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

    # 1. FTD (+30)
    ftd_data  = _detectar_ftd(df_spy)
    ftd_score = 0
    if ftd_data:
        sig = ftd_data.get('signal', 'none')
        if sig == 'confirmed':
            ftd_score = 30
            detalles.append("✓ FTD Confirmado (+30)")
            if price < mm['ema_21']:
                advertencias.append("⚠ FTD bajo EMA21 — Posible trampa alcista")
        elif sig in ['potential', 'early']:
            ftd_score = 13
            detalles.append("~ FTD en desarrollo (+13)")
        elif sig == 'active':
            ftd_score = 4
            detalles.append("• Rally activo sin FTD (+4)")
        else:
            detalles.append("✗ Sin FTD (0)")
    score += ftd_score
    metricas['FTD'] = {"score": ftd_score, "max": 30, "color": "#2962ff", "data": ftd_data}

    # 2. RSI Sobrevendido diario (+19)
    rsi_series  = _calcular_rsi(df_spy['Close'], 14)
    rsi_ventana = rsi_series.tail(VENTANA)
    rsi_min     = float(rsi_ventana.min())
    rsi_actual  = float(rsi_series.iloc[-1])
    rsi_score   = 0
    if rsi_min < 25:
        rsi_score = 19; detalles.append(f"✓ RSI min {rsi_min:.1f} < 25 (+19)")
    elif rsi_min < 35:
        rsi_score = 15; detalles.append(f"✓ RSI min {rsi_min:.1f} < 35 (+15)")
    elif rsi_min < 45:
        rsi_score = 6;  detalles.append(f"~ RSI min {rsi_min:.1f} < 45 (+6)")
    elif rsi_actual > 75:
        rsi_score = -4; detalles.append(f"✗ RSI {rsi_actual:.1f} > 75 sobrecompra (-4)")
    else:
        detalles.append("• RSI en rango neutral (0)")
    score += rsi_score
    metricas['RSI'] = {"score": rsi_score, "max": 19, "color": "#00ffad" if rsi_score >= 0 else "#f23645",
                       "actual": round(rsi_actual, 1), "minimo": round(rsi_min, 1)}

    # 3. VIX Spike — zonas de posible capitulación (+24)
    vix_score = 0
    if len(df_vix) > 20:
        vix_ventana = df_vix['Close'].tail(VENTANA)
        vix_max     = float(vix_ventana.max())
        vix_actual  = float(df_vix['Close'].iloc[-1])
        if vix_max > 35:
            vix_score = 24; detalles.append(f"✓ VIX max {vix_max:.1f} > 35 — capitulación (+24)")
        elif vix_max > 30:
            vix_score = 18; detalles.append(f"✓ VIX max {vix_max:.1f} > 30 (+18)")
        elif vix_max > 25:
            vix_score = 12; detalles.append(f"~ VIX max {vix_max:.1f} > 25 (+12)")
        else:
            detalles.append("• VIX sin spike significativo (0)")
        if score > 50 and vix_actual < 20:
            advertencias.append(f"⚠ VIX actual bajo ({vix_actual:.1f}) — Posible complacencia")
        metricas['VIX'] = {"score": vix_score, "max": 24, "color": "#ff9800",
                           "actual": round(vix_actual, 1), "maximo": round(vix_max, 1)}
    else:
        atr     = _calcular_atr(df_spy)
        atr_med = atr.rolling(20).mean()
        atr_m   = float(atr_med.tail(VENTANA).mean())
        ratio   = float(atr.tail(VENTANA).max()) / atr_m if atr_m > 0 else 1.0
        if ratio > 2.0:   vix_score = 13
        elif ratio > 1.5: vix_score = 9
        metricas['VIX'] = {"score": vix_score, "max": 24, "color": "#ff9800",
                           "actual": round(ratio, 2), "maximo": round(ratio, 2), "is_proxy": True}
    score += vix_score

    # 4. McClellan (+17)
    mcclellan, metodo = _mcclellan_proxy(df_spy, sector_data)
    mc_val   = float(mcclellan.iloc[-1]) if hasattr(mcclellan, 'iloc') else float(mcclellan or 0)
    mc_score = 0
    if mc_val < -80:
        mc_score = 17; detalles.append(f"✓ McClellan {mc_val:.0f} < -80 (+17)")
    elif mc_val < -50:
        mc_score = 13; detalles.append(f"~ McClellan {mc_val:.0f} < -50 (+13)")
    elif mc_val < -20:
        mc_score = 4;  detalles.append(f"• McClellan {mc_val:.0f} < -20 (+4)")
    else:
        detalles.append(f"• McClellan {mc_val:.0f} neutral (0)")
    score += mc_score
    metricas['Breadth'] = {"score": mc_score, "max": 17, "color": "#9c27b0",
                           "actual": round(mc_val, 1), "metodo": metodo}

    # 5. Volumen (+10)
    vol_ventana = df_spy['Volume'].tail(VENTANA)
    vol_media   = float(df_spy['Volume'].rolling(20).mean().iloc[-1])
    vol_max_r   = float(vol_ventana.max())
    vol_actual  = float(df_spy['Volume'].iloc[-1])
    vol_ratio_m = vol_max_r / vol_media if vol_media > 0 else 1.0
    vol_ratio_a = vol_actual / vol_media if vol_media > 0 else 1.0
    vol_score   = 0
    if vol_ratio_m > 2.0:
        vol_score = 10; detalles.append(f"✓ Volumen max {vol_ratio_m:.1f}x media (+10)")
    elif vol_ratio_m > 1.5:
        vol_score = 7;  detalles.append(f"~ Volumen max {vol_ratio_m:.1f}x media (+7)")
    elif vol_ratio_m > 1.2:
        vol_score = 3;  detalles.append(f"• Volumen max {vol_ratio_m:.1f}x media (+3)")
    else:
        detalles.append("• Volumen sin spike (0)")
    score += vol_score
    metricas['Volume'] = {"score": vol_score, "max": 10, "color": "#f23645",
                          "actual_ratio": round(vol_ratio_a, 2), "max_ratio": round(vol_ratio_m, 2)}

    # 6. SMA200 contexto (no aporta score, es contexto informativo)
    sobre_sma200 = bool(price > mm['sma_200'])
    dist_sma200  = round((price - mm['sma_200']) / mm['sma_200'] * 100, 2) if mm['sma_200'] != 0 else 0
    if not sobre_sma200:
        advertencias.append(f"⚠ Precio {dist_sma200:.1f}% bajo SMA200 — Mercado bajista")
        detalles.append("• Bajo SMA200 — Contexto bajista")
    else:
        detalles.append("• Sobre SMA200 — Tendencia alcista")
    if price < mm['ema_21']:
        advertencias.append("EMA21 actua como resistencia — Cuidado")
    metricas['SMA200'] = {"score": 0, "max": 0,
                          "color": "#00ffad" if sobre_sma200 else "#ff9800",
                          "sobre_sma200": sobre_sma200, "distancia_pct": dist_sma200}

    vol_confirmado = bool(vol_score >= 3)
    if score >= 70:
        if vol_confirmado:
            estado, senal, color = "VERDE", "FONDO PROBABLE", "#00ffad"
            rec = f"Setup optimo. Score {score}/100. " + ("Revisar advertencias." if advertencias else "Entrada gradual 25% con stop -7%.")
        else:
            estado, senal, color = "VERDE-VOL", "SETUP SIN VOLUMEN", "#00ffad"
            rec = f"Score alto ({score}) sin volumen. Reducir tamano (10-15%)."
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
        "score":         score,
        "max_score":     max_score_real,
        "estado":        estado,
        "senal":         senal,
        "color":         color,
        "recomendacion": rec,
        "detalles":      detalles,
        "advertencias":  advertencias,
        "metricas":      metricas,
        "medias":        {k: round(v, 2) for k, v in mm.items()},
    }

def get_rsu_algoritmo():
    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_spy  = ex.submit(lambda: yf.Ticker("SPY").history(period="6mo"))
            f_vix  = ex.submit(lambda: yf.Ticker("^VIX").history(period="3mo"))
            f_sect = ex.submit(_descargar_sectores)
            df_spy      = f_spy.result()
            df_vix      = f_vix.result()
            sector_data = f_sect.result()

        if len(df_spy) < 50:
            return {"ok": False, "error": "Datos insuficientes de SPY"}

        # Limpiar datos anómalos usando percentiles
        q10 = float(df_spy['Close'].quantile(0.05))
        q90 = float(df_spy['Close'].quantile(0.95))
        df_spy = df_spy[df_spy['Close'].between(q10 * 0.7, q90 * 1.3)].copy()

        resultado = _calcular_score_punto(df_spy, df_vix, sector_data)

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
    Backtest histórico del RSU Algoritmo sobre SPY.

    Metodología:
    - Descarga histórico SPY/VIX con buffer adicional (SMA200 necesita 200 días
      previos al inicio del periodo de análisis real).
    - Recalcula el score día a día usando _calcular_score_punto() — la MISMA
      función que el cálculo en vivo, así que mide exactamente el algoritmo
      actual, no una aproximación.
    - McClellan usa el proxy SPY de forma consistente en todo el backtest (no
      datos sectoriales reales) — recalcular sectores en miles de días sería
      excesivamente costoso en llamadas HTTP, y mezclar fuentes de distinta
      calidad en distintos días introduciría una variable oculta no controlada.
    - Detecta "señal VERDE" como una transición (score≥70 y volumen confirmado
      hoy, pero NO ayer) — mide el momento en que el semáforo se encendió, no
      cada día que permanece encendido.
    - Para cada señal, mide el retorno forward de SPY en +5/+10/+20/+60 días
      de trading.
    - Compara esos retornos contra el "baseline": el retorno medio de SPY en
      esos mismos horizontes calculado sobre TODOS los días del periodo, no
      solo los días de señal. Esta comparación es la que realmente contesta
      si el algoritmo aporta ventaja sobre simplemente estar invertido siempre.
    """
    from services.cache import cache
    cache_key = f"algoritmo:backtest:{years}y"
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        # Buffer de 250 días de trading (~1 año) antes del periodo real, para que
        # SMA200/RSI/etc. tengan suficiente histórico ya desde el primer día medido.
        period_str = f"{years + 1}y"
        with ThreadPoolExecutor(max_workers=2) as ex:
            f_spy = ex.submit(lambda: yf.Ticker("SPY").history(period=period_str))
            f_vix = ex.submit(lambda: yf.Ticker("^VIX").history(period=period_str))
            df_spy_full = f_spy.result()
            df_vix_full = f_vix.result()

        df_spy_full = df_spy_full.dropna(subset=['Close'])
        df_vix_full = df_vix_full.dropna(subset=['Close'])

        if len(df_spy_full) < 300:
            return {"ok": False, "error": "Histórico insuficiente para backtest"}

        # Normalizar índices de fecha para alinear SPY y VIX por día
        df_spy_full.index = df_spy_full.index.normalize()
        df_vix_full.index = df_vix_full.index.normalize()

        BUFFER = 250  # días de calentamiento antes de empezar a medir señales
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

            # Alinear VIX hasta la misma fecha (puede tener calendario ligeramente distinto)
            vix_slice = df_vix_full[df_vix_full.index <= fecha]

            try:
                resultado = _calcular_score_punto(spy_slice, vix_slice, sector_data=None)
            except Exception:
                fue_verde_ayer = False
                continue

            es_verde_hoy = resultado['estado'] in ('VERDE', 'VERDE-VOL')

            # Señal = transición a VERDE (no estaba ayer, sí está hoy)
            if es_verde_hoy and not fue_verde_ayer:
                senales.append({
                    "fecha": fecha.strftime('%Y-%m-%d'),
                    "pos": pos,
                    "score": resultado['score'],
                    "estado": resultado['estado'],
                    "precio": round(float(closes_full.iloc[pos]), 2),
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

        result = {
            "ok":              True,
            "years":           years,
            "periodo_inicio":  fechas[0].strftime('%Y-%m-%d'),
            "periodo_fin":     fechas[-1].strftime('%Y-%m-%d'),
            "total_dias":      len(fechas),
            "n_senales":       len(senales),
            "senales":         senales,
            "stats":           stats,
            "metodologia":     "McClellan vía proxy SPY (consistente en todo el periodo, no datos sectoriales reales) · Señal = transición a VERDE (score≥70 + volumen confirmado), no días consecutivos en VERDE",
            "timestamp":       datetime.now().strftime('%H:%M:%S'),
        }
        cache.set(cache_key, result, 3600 * 12)  # 12h — recálculo pesado, no cambia intradía
        return result

    except Exception as e:
        return {"ok": False, "error": str(e)}
    try:
        with ThreadPoolExecutor(max_workers=3) as ex:
            f_spy  = ex.submit(lambda: yf.Ticker("SPY").history(period="6mo"))
            f_vix  = ex.submit(lambda: yf.Ticker("^VIX").history(period="3mo"))
            f_sect = ex.submit(_descargar_sectores)
            df_spy      = f_spy.result()
            df_vix      = f_vix.result()
            sector_data = f_sect.result()

        if len(df_spy) < 50:
            return {"ok": False, "error": "Datos insuficientes de SPY"}

        # Limpiar datos anómalos usando percentiles
        q10 = float(df_spy['Close'].quantile(0.05))
        q90 = float(df_spy['Close'].quantile(0.95))
        df_spy = df_spy[df_spy['Close'].between(q10 * 0.7, q90 * 1.3)].copy()

        resultado = _calcular_score_punto(df_spy, df_vix, sector_data)

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