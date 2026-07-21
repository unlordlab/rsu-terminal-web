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

Pendiente (ver TODO, sección "Detector de Fases"): esta metodología tiene
limitaciones conocidas de diseño (Fases 1/3 sin memoria de procedencia, sin
uso de volumen, sin la SMA150/30-semanas del método original) -- las mejoras
propuestas se implementarán AQUÍ, una sola vez, cuando se aborden.
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
    """Fase Weinstein (1-4) diaria, a partir de una serie de cierres."""
    if len(close) < 50:
        return {"phase": None, "phase_label": "Sin datos suficientes", "trend": None}

    price    = float(close.iloc[-1])
    ema10_s  = close.ewm(span=10,  adjust=False).mean()
    ema20_s  = close.ewm(span=20,  adjust=False).mean()
    ema50_s  = close.ewm(span=50,  adjust=False).mean()
    ema200_s = close.ewm(span=200, adjust=False).mean() if len(close) >= 200 else None

    ema20  = float(ema20_s.iloc[-1])
    ema50  = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1]) if ema200_s is not None else None

    slope10_dir,  _ = _ema_slope(ema10_s,  3,  0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  5,  0.4)
    slope50_dir,  _ = _ema_slope(ema50_s,  10, 0.6)
    slope200_dir, _ = _ema_slope(ema200_s, 20, 0.8) if ema200_s is not None else (None, None)

    bull_conditions = [
        price > ema20,
        ema20 > ema50,
        (ema50 > ema200) if ema200 else True,
        slope50_dir == "alcista",
        (slope200_dir in ("alcista", "plana")) if slope200_dir else True,
    ]
    bull_score = sum(1 for c in bull_conditions if c)

    early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
    early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

    if bull_score >= 4:
        trend = "ALCISTA"
    elif bull_score <= 1 and not early_reversal:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    elif early_reversal and bull_score <= 1:
        phase, label = 1, "Fase 1 · Posible Giro Temprano"
    elif early_breakdown:
        phase, label = 3, "Fase 3 · Posible Giro Bajista Temprano"
    elif ema200 and price >= ema200:
        phase, label = 3, "Fase 3 · Distribución"
    else:
        phase, label = 1, "Fase 1 · Acumulación"

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

    Los lookbacks de pendiente se reescalan de sesiones diarias a semanas
    (÷5 aprox.) manteniendo los mismos umbrales porcentuales. La EMA200
    semanal necesita 200 semanas (~4 años) para estar "completa" — con 2
    años de histórico diario disponibles (~104 semanas) se queda corta, así
    que se usa min_periods=20 para que dé un valor utilizable antes,
    aceptando que está menos "asentada" que con histórico completo."""
    weekly = resample_weekly_close(close_daily)
    if weekly is None or len(weekly) < 30:
        return {"phase": None, "phase_label": "Sin histórico semanal suficiente", "trend": None}

    price    = float(weekly.iloc[-1])
    ema10_s  = weekly.ewm(span=10,  adjust=False, min_periods=5).mean()
    ema20_s  = weekly.ewm(span=20,  adjust=False, min_periods=10).mean()
    ema50_s  = weekly.ewm(span=50,  adjust=False, min_periods=20).mean()
    ema200_s = weekly.ewm(span=200, adjust=False, min_periods=20).mean() if len(weekly) >= 20 else None

    ema20  = float(ema20_s.iloc[-1])
    ema50  = float(ema50_s.iloc[-1])
    ema200 = float(ema200_s.iloc[-1]) if ema200_s is not None else None

    slope10_dir,  _ = _ema_slope(ema10_s,  1, 0.4)
    slope20_dir,  _ = _ema_slope(ema20_s,  2, 0.4)
    slope50_dir,  _ = _ema_slope(ema50_s,  3, 0.6)
    slope200_dir, _ = _ema_slope(ema200_s, 4, 0.8) if ema200_s is not None else (None, None)

    bull_conditions = [
        price > ema20,
        ema20 > ema50,
        (ema50 > ema200) if ema200 else True,
        slope50_dir == "alcista",
        (slope200_dir in ("alcista", "plana")) if slope200_dir else True,
    ]
    bull_score = sum(1 for c in bull_conditions if c)

    early_reversal  = (slope10_dir == "alcista" and slope20_dir == "alcista" and price > ema20)
    early_breakdown = (slope10_dir == "bajista" and slope20_dir == "bajista" and price < ema20)

    if bull_score >= 4:
        trend = "ALCISTA"
    elif bull_score <= 1 and not early_reversal:
        trend = "BAJISTA"
    else:
        trend = "RANGO"

    if trend == "ALCISTA":
        phase, label = 2, "Fase 2 · Avance (Markup)"
    elif trend == "BAJISTA":
        phase, label = 4, "Fase 4 · Declive / Corrección"
    elif early_reversal and bull_score <= 1:
        phase, label = 1, "Fase 1 · Posible Giro Temprano"
    elif early_breakdown:
        phase, label = 3, "Fase 3 · Posible Giro Bajista Temprano"
    elif ema200 and price >= ema200:
        phase, label = 3, "Fase 3 · Distribución"
    else:
        phase, label = 1, "Fase 1 · Acumulación"

    return {"phase": phase, "phase_label": label, "trend": trend}