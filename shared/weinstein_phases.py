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

Rediseño 11/09/2026, tras auditar OSS en Research: la regla de 22/07 tenía dos
fallos que se sumaban.

  1. Solo había Fase 4 cuando la SMA150 ya BAJABA, y esa media llega tarde:
     tras una subida fuerte sigue plana (o subiendo) semanas después de que
     el precio se haya desplomado. OSS, un 57% por debajo de su máximo y un
     27% por debajo de la SMA150, salía «RANGO».
  2. En RANGO, Fase 1 o 3 se decidía por el retorno punto a punto de hace 6
     meses, que no mira el camino: OSS era Fase 3 hasta el 03/09 y pasó a
     «Fase 1 · Acumulación» el 10/09 solo porque cayó por debajo del precio de
     marzo. Cuanto más caía, más «acumulación» parecía. Medido ese día en el
     S&P 500: de 87 valores en Fase 1, 36 estaban cayendo igual que OSS.

Ahora, con la media plana (o el precio al otro lado de su pendiente):
  · el precio CLARAMENTE por debajo (más de BANDA_RUPTURA) con la media de 50
    sesiones bajando es la ruptura de Weinstein: Fase 4 (y al revés, Fase 2);
  · pegado a la media, la procedencia es dónde está la propia SMA150 dentro
    de su recorrido del último año (arriba: venía de subir → Fase 3; abajo:
    de bajar → Fase 1). No cuánto se movió en los últimos meses: una media
    que lleva meses plana en lo alto dice «0%», y un techo largo salía Fase 1.
    El retorno de 6 meses queda solo como desempate si la media no se movió.

LO QUE LA FASE NO ES: medido en el S&P 500 (2023-2026, 41.205 muestras),
ni esta regla ni la anterior predicen la rentabilidad a 20 o 60 sesiones;
los valores que la regla nueva pasa a Fase 4 incluso rebotaron más que la
media. La fase DESCRIBE dónde está el valor en su ciclo; no es una señal.

Pendiente: falta usar volumen como confirmación de las transiciones a Fase 2
(mejora C, no implementada aún -- ver memoria del proyecto).
"""
import pandas as pd

# Cuánto tiene que separarse el precio de una media de 30 semanas plana para
# contar como ruptura (y no como oscilación dentro de una base o un techo).
BANDA_RUPTURA = 0.05
# Cuánto tiene que haber recorrido la media de 30 semanas en el último año para
# decir de dónde viene el lateral. Por debajo, se desempata con el retorno.
UMBRAL_PROCEDENCIA = 0.02
# Qué regla calculó una fase. Viaja con cada fila del escaneo y se guarda en
# los snapshots, para no comparar fases de reglas distintas: la noche en que
# cambia la regla, el Scanner anunciaría «entradas en Fase 2» que no son
# movimientos del mercado sino de la fórmula. Se cambia al cambiar la regla.
REGLA_FASES = "2026-09-11"


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


def _retorno(serie: pd.Series, atras: int) -> float:
    if len(serie) <= atras:
        return 0.0
    ref = float(serie.iloc[-atras - 1])
    return (float(serie.iloc[-1]) - ref) / ref if ref else 0.0


def _clasificar(close, media_s, pendiente_media, medio_s, pendiente_medio,
                ema10_s, ema20_s, pendientes_cortas, atras_procedencia, atras_retorno) -> dict:
    """El núcleo común de la versión diaria y la semanal; solo cambian las
    series y los plazos. `media_s` es la de 30 semanas (SMA150 diaria o SMA30
    semanal) y `medio_s` la de medio plazo que confirma una ruptura (EMA50
    diaria o EMA10 semanal, ~10 semanas)."""
    price  = float(close.iloc[-1])
    media  = float(media_s.iloc[-1])
    medio  = float(medio_s.iloc[-1])
    ema20  = float(ema20_s.iloc[-1])
    dir_media, _ = _ema_slope(media_s, *pendiente_media)
    dir_medio, _ = _ema_slope(medio_s, *pendiente_medio)
    dir10, _ = _ema_slope(ema10_s, *pendientes_cortas[0])
    dir20, _ = _ema_slope(ema20_s, *pendientes_cortas[1])
    distancia = (price - media) / media if media else 0.0

    # Por encima de una media de 30 semanas que sube sigue siendo Fase 2 aunque
    # el precio corrija fuerte (Weinstein: la fase no cambia hasta romper la
    # media), pero la etiqueta lo dice: OSS el 16/07, un 40% por debajo de su
    # máximo, salía «Avance» a secas. Solo cambia el texto, no el número.
    if dir_media == "alcista" and price > media:
        corrige = dir_medio == "bajista" and price < medio
        phase, label = 2, "Fase 2 · Avance" + (" (en corrección)" if corrige else " (Markup)")
    elif dir_media == "bajista" and price < media:
        rebota = dir_medio == "alcista" and price > medio
        phase, label = 4, "Fase 4 · Declive" + (" (en rebote)" if rebota else " / Corrección")
    elif distancia < -BANDA_RUPTURA and dir_medio == "bajista" and price < medio:
        # La media de 30 semanas aún no ha girado, pero el precio ya ha roto
        # por debajo con la de medio plazo bajando: en Weinstein, eso ES la
        # entrada en Fase 4. Esperar a que la media baje llega semanas tarde.
        phase, label = 4, "Fase 4 · Declive (ruptura reciente)"
    elif distancia > BANDA_RUPTURA and dir_medio == "alcista" and price > medio:
        phase, label = 2, "Fase 2 · Avance (ruptura reciente)"
    else:
        # Lateral, pegado a la media: ¿base o techo? Lo dice en qué parte de
        # su recorrido del último año está la propia media: arriba es que
        # venía de subir (techo), abajo que venía de bajar (base). Cuánto se
        # movió en los últimos meses NO sirve: una media que lleva meses
        # plana en lo alto dice «0%», y un techo largo salía «Acumulación».
        recorrido = media_s.dropna().iloc[-atras_procedencia:]
        alto, bajo = float(recorrido.max()), float(recorrido.min())
        if bajo > 0 and (alto - bajo) / bajo > UMBRAL_PROCEDENCIA:
            procedencia = (media - bajo) / (alto - bajo) - 0.5
        else:
            # La media no se ha movido en un año: desempata el retorno.
            procedencia = _retorno(close, atras_retorno)
        if procedencia <= 0:
            giro = dir10 == "alcista" and dir20 == "alcista" and price > ema20
            phase, label = 1, "Fase 1 · Acumulación" + (" (posible giro)" if giro else "")
        else:
            giro = dir10 == "bajista" and dir20 == "bajista" and price < ema20
            phase, label = 3, "Fase 3 · Distribución" + (" (posible giro bajista)" if giro else "")

    trend = {2: "ALCISTA", 4: "BAJISTA"}.get(phase, "RANGO")
    return {"phase": phase, "phase_label": label, "trend": trend}


def classify_phase(close: pd.Series) -> dict:
    """Fase Weinstein (1-4) diaria, a partir de una serie de cierres.

    La SMA150 (≈30 semanas, la media móvil original del método) es el
    discriminador principal: Fase 2 si sube y el precio está por encima,
    Fase 4 si baja y el precio está por debajo. Con la media plana, una
    ruptura clara confirmada por la EMA50 también es Fase 2 o 4; si el precio
    sigue pegado a la media, Fase 1 o 3 según de dónde venga la media (ver la
    cabecera). Las EMA10/20 solo aportan un matiz táctico ("posible giro")
    dentro de Fase 1/3, no cambian el número de fase."""
    if len(close) < 150:
        return {"phase": None, "phase_label": "Sin datos suficientes (hace falta SMA150)", "trend": None}
    return _clasificar(
        close,
        media_s=close.rolling(150, min_periods=150).mean(), pendiente_media=(15, 0.4),
        medio_s=close.ewm(span=50, adjust=False).mean(), pendiente_medio=(10, 0.6),
        ema10_s=close.ewm(span=10, adjust=False).mean(),
        ema20_s=close.ewm(span=20, adjust=False).mean(),
        pendientes_cortas=((3, 0.4), (5, 0.4)),
        atras_procedencia=250, atras_retorno=126,
    )


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
    # La EMA10 semanal hace dos papeles: la corta del «posible giro» (como
    # antes) y la de medio plazo que confirma una ruptura (≈ la EMA50 diaria).
    ema10_s = weekly.ewm(span=10, adjust=False, min_periods=5).mean()
    return _clasificar(
        weekly,
        media_s=weekly.rolling(30, min_periods=30).mean(), pendiente_media=(3, 0.5),
        medio_s=ema10_s, pendiente_medio=(2, 0.6),
        ema10_s=ema10_s,
        ema20_s=weekly.ewm(span=20, adjust=False, min_periods=10).mean(),
        pendientes_cortas=((1, 0.4), (2, 0.4)),
        atras_procedencia=52, atras_retorno=26,
    )