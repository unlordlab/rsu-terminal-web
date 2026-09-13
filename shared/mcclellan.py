"""
mcclellan.py -- Oscilador McClellan clásico (EMA19-EMA39 sobre el
avance/declive neto diario), compartido entre market_service.py,
rsu_algoritmo_service.py (solo la rama en vivo con amplitud real) y
scripts/daily_briefing.py. La fórmula ya era idéntica carácter por
carácter en los 3 sitios (verificado 22/07/2026) -- solo estaba copiada
3 veces, una de ellas (daily_briefing.py) incluso reimplementando el
bucle EMA a mano en vez de pandas.

IMPORTANTE -- lo que este módulo NO resuelve: el backtest del RSU
Algoritmo (rsu_algoritmo_service.py::_mcclellan_proxy, rama del proxy de
SPY) usa un indicador distinto por diseño, no avance/declive real --
porque no existe histórico reconstruido de amplitud real para los ~10
años que cubre el backtest. Ver comentario en ese fichero y memoria del
proyecto -- sigue pendiente como su propio hallazgo, no una simple
divergencia de fórmula.

NO depende de nada de backend/ (fastapi, pydantic).
"""
import pandas as pd


def mcclellan_series(net_advances: pd.Series) -> pd.Series:
    """net_advances: serie de (avances - declives) por sesión, en orden
    cronológico. Devuelve la serie completa EMA19-EMA39 -- cada sitio lee
    el valor más reciente (.iloc[-1]) o uno histórico (p.ej. "hace una
    semana") según necesite."""
    ema19 = net_advances.ewm(span=19, adjust=False).mean()
    ema39 = net_advances.ewm(span=39, adjust=False).mean()
    return ema19 - ema39


# ── McClellan AJUSTADO POR TAMAÑO, para comparar grandes con pequeñas ────────
#
# El clásico usa avances MENOS descensos, así que su escala depende de cuántos
# valores haya: el mismo mercado da un número cuatro veces mayor sobre las
# ~1.960 del Russell 2000 que sobre las 500 del S&P 500. Para ponerlos uno al
# lado del otro se usa la versión estándar ajustada ("ratio-adjusted"):
# (avances - descensos) / (avances + descensos) × 1000 — la fracción neta del
# universo, en tantos por mil, que ya no depende del tamaño.
#
# CUÁNTA HISTORIA HACE FALTA, medido el 13/09/2026 con el histórico real del
# escaneo (149 sesiones): la EMA39 arranca en el primer dato y tarda en
# olvidarlo. Calculado solo con las últimas N sesiones frente a la serie
# completa, el error medio de las 20 más recientes fue de 34 puntos con 59
# sesiones (lo que publicaba el escaneo por universo), 7 con 90 y 1,2 con 110 —
# con un recorrido típico de unos ±45, 34 puntos es ruido puro. Por debajo de
# este mínimo no se da el número.
MIN_SESIONES_AJUSTADO = 110
SESIONES_SEMANA = 5


def mcclellan_ajustado(historia: list) -> dict | None:
    """historia: filas del escaneo ({date, advances, declines}) en orden
    cronológico. Devuelve {valor, semana, sesiones, fecha} o None si no hay
    historia suficiente para que el número signifique algo."""
    filas = [h for h in (historia or [])
             if (h.get("advances") or 0) + (h.get("declines") or 0) > 0]
    if len(filas) < MIN_SESIONES_AJUSTADO:
        return None
    neto = pd.Series([(h["advances"] - h["declines"]) / (h["advances"] + h["declines"]) * 1000
                      for h in filas])
    serie = mcclellan_series(neto)
    valor = float(serie.iloc[-1])
    return {
        "valor": round(valor, 1),
        "semana": round(valor - float(serie.iloc[-1 - SESIONES_SEMANA]), 1),
        "sesiones": len(filas),
        "fecha": filas[-1].get("date"),
    }
