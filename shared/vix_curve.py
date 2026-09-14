"""
vix_curve.py -- forma de la curva de volatilidad (VIX frente a VIX3M),
compartida entre rsu_algoritmo_service.py (que la puntúa) y market_service.py
(que la enseña en el widget del VIX).

El VIX mide el miedo a 30 días y el VIX3M el miedo a 3 meses. Lo normal es que
el de 3 meses sea el más alto: la incertidumbre crece con el plazo. Cuando se
da la vuelta y el de HOY supera al de dentro de 3 meses (ratio > 1), el pánico
es agudo y de corto plazo -- históricamente eso acompaña a suelos de mercado,
no a techos, que es justo lo contrario de lo que sugiere una lectura ingenua
del VIX alto.

Los umbrales viven aquí y no en cada módulo a propósito: el Algoritmo puntúa
con ellos y Market los enseña, y si un día se recalibran tienen que moverse
los dos a la vez. Ver hallazgo #32 de la auditoría de Market.

NO depende de nada de backend/ (fastapi, pydantic).
"""

# Por encima de 1, el miedo de hoy supera al de dentro de 3 meses.
UMBRAL_BACKWARDATION = 1.0
# Entre 0,95 y 1 la curva todavía es normal, pero está tensa: se ha comprimido
# casi hasta darse la vuelta.
UMBRAL_TENSION = 0.95


def vix_ratio(spot, vix3m):
    """Ratio VIX/VIX3M. None si falta cualquiera de las dos patas o el
    denominador no es positivo -- sin las dos no hay curva que describir."""
    if spot is None or vix3m is None:
        return None
    try:
        spot, vix3m = float(spot), float(vix3m)
    except (TypeError, ValueError):
        return None
    if vix3m <= 0:
        return None
    return round(spot / vix3m, 3)


# ── LAS DOS PATAS TIENEN QUE SER DEL MISMO DÍA ───────────────────────────────
#
# EL CASO, medido el 14/09/2026 (Newsfeed #66). `^VIX3M` (y `^VIX6M`, `^VIX9D`)
# NO TIENE BARRAS DIARIAS en yfinance desde el 17/07/2026: pidiendo 3 meses o
# un año, la serie salta del 17/07 a una única fila suelta con la cotización de
# hoy. Esa fila es buena (en sesión es el precio en vivo), así que el que pide
# 5 días y coge el último valor está bien. Pero quien recorta el histórico por
# fecha —el backtest del Algoritmo— comparaba el VIX de cada día entre el 18/07
# y el 11/09 con el VIX3M del 17/07: 39 sesiones, 1,7 puntos de error medio
# (3,1 máximo), y el 29/07 puntuó «pánico agudo» (+7) cuando era «curva tensa»
# (+3). Un cociente entre dos números de fechas distintas no describe ninguna
# curva: mejor sin dato que con uno de otro día.
#
# 4 días naturales de margen: un fin de semana largo con festivo separa dos
# sesiones seguidas por 4 días sin que haya nada roto.
TOLERANCIA_DIAS = 4


def misma_sesion(fecha_spot, fecha_3m, tolerancia_dias=TOLERANCIA_DIAS):
    """True si las dos fechas (date, datetime o Timestamp) están a menos de
    `tolerancia_dias` naturales. Sin alguna de las dos, False."""
    if fecha_spot is None or fecha_3m is None:
        return False
    try:
        a = fecha_spot.date() if hasattr(fecha_spot, "date") else fecha_spot
        b = fecha_3m.date() if hasattr(fecha_3m, "date") else fecha_3m
        return abs((a - b).days) <= tolerancia_dias
    except Exception:
        return False


# ── EL HISTÓRICO QUE FALTA, DE LA FUENTE ORIGINAL ────────────────────────────
#
# CBOE publica gratis el histórico diario completo de sus índices. Comparado el
# 14/09/2026 con yfinance en los días en que los dos tienen dato: 86 días de
# VIX3M y 127 de VIX, diferencia máxima 0,00. Sirve para rellenar el hueco sin
# mover ni un decimal de lo que ya había.
URL_CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/{indice}_History.csv"


def historico_cboe(indice, timeout=20):
    """Serie de cierres diarios de CBOE (índice de fechas sin zona horaria), o
    una serie vacía si no se puede descargar. Nunca levanta."""
    import io
    import pandas as pd
    import requests
    try:
        r = requests.get(URL_CBOE.format(indice=indice), timeout=timeout,
                         headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        fechas = pd.to_datetime(df["DATE"], format="%m/%d/%Y")
        return pd.Series(df["CLOSE"].astype(float).values, index=fechas).sort_index()
    except Exception as e:
        print(f"[vix_curve] Histórico de CBOE para {indice} no disponible: {type(e).__name__}: {e}")
        return pd.Series(dtype=float)


def completar_con_cboe(df, cboe):
    """Añade a `df` (DataFrame de yfinance con columna Close e índice de fechas
    normalizado) los días que tiene `cboe` y a `df` le faltan, dentro del rango
    hasta el último dato de CBOE. No toca ningún valor existente. Devuelve
    (df_completo, dias_añadidos)."""
    import pandas as pd
    if df is None or cboe is None or len(cboe) == 0:
        return df, 0
    zona = getattr(df.index, "tz", None)
    extra = cboe.copy()
    extra.index = extra.index.tz_localize(zona) if zona is not None else extra.index
    if len(df):
        extra = extra[extra.index >= df.index.min()]
        faltan = extra[~extra.index.isin(df.index)]
    else:
        faltan = extra
    if len(faltan) == 0:
        return df, 0
    nuevas = pd.DataFrame({"Close": faltan.values}, index=faltan.index)
    completo = pd.concat([df, nuevas]).sort_index()
    return completo, len(faltan)


def zona_curva(ratio):
    """'backwardation' | 'tensa' | 'normal', o None si no hay ratio."""
    if ratio is None:
        return None
    if ratio > UMBRAL_BACKWARDATION:
        return "backwardation"
    if ratio > UMBRAL_TENSION:
        return "tensa"
    return "normal"
