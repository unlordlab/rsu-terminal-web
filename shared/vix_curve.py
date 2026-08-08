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


def zona_curva(ratio):
    """'backwardation' | 'tensa' | 'normal', o None si no hay ratio."""
    if ratio is None:
        return None
    if ratio > UMBRAL_BACKWARDATION:
        return "backwardation"
    if ratio > UMBRAL_TENSION:
        return "tensa"
    return "normal"
