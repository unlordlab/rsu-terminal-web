"""
weinstein_phases.py -- clasificación de fase de mercado (metodología
Weinstein, 4 fases), compartida entre scripts/scanner_universe.py (GitHub
Actions, standalone) y backend/services/research_service.py (FastAPI).
Fase 2.2 del Plan Maestro, 20/07/2026.

Antes esta misma lógica (5 funciones: _ema_slope, el clasificador diario, la
versión con debounce de confirmación, el resample semanal, y el clasificador
semanal) estaba duplicada en los dos archivos. Verificado el 20/07/2026 con
diff real (no solo conteo de líneas) que la LÓGICA era idéntica carácter por
carácter -- las diferencias que aparecían a simple vista eran solo
comentarios, docstrings y anotaciones de tipo. Unificado aquí para que un
futuro ajuste de umbral no pueda volver a divergir en silencio entre Scanner
y Research sin que nadie se dé cuenta.

IMPORTANTE: este archivo puede depender de pandas (ya lo usa
scanner_universe.py libremente para todo lo demás), pero NO debe depender de
nada de backend/ (fastapi, pydantic, servicios) -- scripts/ corre en el
runner de GitHub Actions sin ese entorno instalado.

Rediseño 22/07/2026 (sesión 9, tras validar empíricamente en la sesión 8 que
la Fase 2 NO rendía mejor que la Fase 4 con la versión anterior basada solo
en apilamiento de EMAs): la SMA150 (≈30 semanas, la media móvil original del
método) es ahora el discriminador principal de tendencia; cuando no hay
tendencia clara, la Fase 1 vs Fase 3 se decide por la procedencia (retorno de
los últimos ~6 meses) en vez de por la posición actual frente a una EMA200
sin memoria del pasado; y sin histórico suficiente para la SMA150/30-semanas
se devuelve phase=None en vez de asumir condiciones favorables por defecto.

Pendiente: falta usar volumen como confirmación de las transiciones a Fase 2
(mejora C, no implementada aún -- ver memoria del proyecto).
"""
import pandas as pd


def _ema_slope(series: pd.Series, lookback: int, threshold: float):
    """Pendiente de una EMA comparando valor actual vs hace `lookback`
    sesiones."""
    if len(series) <= lookback:
        return None, None
    now  = float(series.iloc[-1])
    prev = float(series.iloc[-1 - lookback])
    if prev == 0:
        return None, None
    pct = round((now - prev) / prev * 100, 2)
    if pct > threshold:  return "alcista", pct
    if pct < -threshold: return "bajista", pct
    return "plana", pct


def classify_phase(close: pd.Series) -> dict:
    """Fase Weinstein (1-4) diaria, a partir de una serie de cierres.

    La SMA150 (≈30 semanas, la media móvil original del método) es el
    discriminador principal: Fase 2 si sube y el precio está por encima,
    Fase 4 si baja y el precio está por debajo. Sin tendencia clara (RANGO),
    la Fase 1 vs Fase 3 se decide por la procedencia -- el retorno de los
    últimos ~6 meses -- en vez de por la posición actual frente a una media
    sin memoria del pasado. Las EMA10/20 solo aportan un matiz táctico
    ("posible giro") dentro de Fase 1/3, no cambian el número de fase."""
    if len(close) < 150:
        return {"phase": None, "phase_label": "Sin datos suficientes (hace falta SMA150)", "trend": None}

    price    = float(close.iloc[-1])
    sma150_s = close.rolling(150, min_periods=150).mean()
    ema10_s  = close.ewm(span=10, adjust=False).mean()
    ema20_s  = close.ewm(span=20, adjust=False).mean()

    sma150 = float(sma150_s.iloc[-1])
    ema20  = float(ema20_s.iloc[-1])

    slope150_dir, _ = _ema_slope(sma150_s, 15, 0.4)
    slope10_dir,  _ = _ema_slope(ema10_s,  3,  0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  5,  0.4)

    if slope150_dir == "alcista" and price > sma150:
        trend = "ALCISTA"
    elif slope150_dir == "bajista" and price < sma150:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    else:
        lookback = 126  # ~6 meses de sesiones
        if len(close) > lookback:
            ref = float(close.iloc[-lookback - 1])
            retorno_6m = (price - ref) / ref if ref else 0.0
        else:
            retorno_6m = 0.0

        early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
        early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

        if retorno_6m <= 0:
            phase, label = 1, "Fase 1 · Acumulación" + (" (posible giro)" if early_reversal else "")
        else:
            phase, label = 3, "Fase 3 · Distribución" + (" (posible giro bajista)" if early_breakdown else "")

    return {"phase": phase, "phase_label": label, "trend": trend}


def classify_phase_debounced(close: pd.Series, confirm_sessions: int = 3) -> dict:
    """Exige que la fase se mantenga `confirm_sessions` sesiones seguidas
    antes de darla por "confirmada" — si la fase de hoy no coincide con la de
    hace 1 y 2 sesiones, se marca phase_confirmed=False y se añade
    "(sin confirmar)" a la etiqueta, en vez de reportar el cambio el primer
    día que aparece. No toca la fórmula de clasificación en sí — cada fase
    individual se calcula exactamente igual, solo se exige que se repita
    varias veces antes de confiar en un cambio. Reduce el parpadeo entre
    fases por ruido de un solo día."""
    today_result = classify_phase(close)
    if today_result["phase"] is None:
        today_result["phase_confirmed"] = None
        return today_result

    recent_phases = [today_result["phase"]]
    for i in range(1, confirm_sessions):
        cutoff = len(close) - i
        if cutoff < 50:
            break
        sub = classify_phase(close.iloc[:cutoff])
        if sub["phase"] is None:
            break
        recent_phases.append(sub["phase"])

    if len(recent_phases) < confirm_sessions:
        # Histórico insuficiente para confirmar del todo (ticker con poco
        # recorrido) — se sirve el resultado de hoy, sin marcar ni confirmar
        # ni desconfirmar.
        today_result["phase_confirmed"] = None
        return today_result

    confirmed = len(set(recent_phases)) == 1
    result = dict(today_result)
    result["phase_confirmed"] = confirmed
    if not confirmed:
        result["phase_label"] = result["phase_label"] + " (sin confirmar)"
    return result


def resample_weekly_close(close: pd.Series):
    """Reagrupa una serie de cierres diarios en cierres semanales (viernes)."""
    if len(close) < 14:
        return None
    try:
        weekly = close.resample('W-FRI').last().dropna()
        return weekly if len(weekly) >= 10 else None
    except Exception:
        return None


def classify_phase_weekly(close_daily: pd.Series) -> dict:
    """Fase Weinstein sobre velas SEMANALES — la temporalidad original del
    método (el libro de Weinstein usa gráficos semanales, no diarios). Mucho
    más lenta a reaccionar que classify_phase (diaria), pero con muchísimo
    menos ruido — pensada como CONFIRMACIÓN estructural junto a la fase
    diaria (más rápida y táctica), no como sustituta.

    Usa la SMA30 semanal (la media móvil original del método -- 30 semanas)
    como discriminador principal, igual que la versión diaria con SMA150;
    antes de este rediseño se usaba una EMA200 semanal como sustituto forzado
    (documentado como inadecuado: con ~104 semanas de histórico disponible se
    quedaba corta para una media de 200), lo cual ya no aplica."""
    weekly = resample_weekly_close(close_daily)
    if weekly is None or len(weekly) < 30:
        return {"phase": None, "phase_label": "Sin histórico semanal suficiente (hace falta SMA30)", "trend": None}

    price   = float(weekly.iloc[-1])
    sma30_s = weekly.rolling(30, min_periods=30).mean()
    ema10_s = weekly.ewm(span=10, adjust=False, min_periods=5).mean()
    ema20_s = weekly.ewm(span=20, adjust=False, min_periods=10).mean()

    sma30 = float(sma30_s.iloc[-1])
    ema20 = float(ema20_s.iloc[-1])

    slope30_dir, _ = _ema_slope(sma30_s, 3, 0.5)
    slope10_dir, _ = _ema_slope(ema10_s, 1, 0.4)
    slope20_dir, _ = _ema_slope(ema20_s, 2, 0.4)

    if slope30_dir == "alcista" and price > sma30:
        trend = "ALCISTA"
    elif slope30_dir == "bajista" and price < sma30:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    else:
        lookback = 26  # ~6 meses en semanas
        if len(weekly) > lookback:
            ref = float(weekly.iloc[-lookback - 1])
            retorno_6m = (price - ref) / ref if ref else 0.0
        else:
            retorno_6m = 0.0

        early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
        early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

        if retorno_6m <= 0:
            phase, label = 1, "Fase 1 · Acumulación" + (" (posible giro)" if early_reversal else "")
        else:
            phase, label = 3, "Fase 3 · Distribución" + (" (posible giro bajista)" if early_breakdown else "")

    return {"phase": phase, "phase_label": label, "trend": trend}