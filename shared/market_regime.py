"""
market_regime.py -- primitiva pura de tendencia de SPY (precio vs
SMA50/SMA200), compartida entre market_service.py::get_market_breadth()
y canslim_service.py::get_market_status() -- ambos calculaban
exactamente la misma fórmula por separado (mismo criterio de ventana y
de min_periods), con el mismo riesgo de divergencia silenciosa ya visto
en el motor RS/McClellan/Weinstein de este proyecto. Ver auditoría
CANSLIM 21/07/2026, hallazgo #10.

DELIBERADAMENTE NO incluye a rsu_algoritmo_service.py: su cálculo de
SMA200 corre en vivo Y dentro del backtest día a día (point-in-time, sin
look-ahead, sobre un DataFrame que cambia de tamaño en cada iteración) --
no puede compartir una caché "de hoy" sin romper la corrección histórica
del backtest. Su propia fórmula (`close.tail(200).mean()`) ya es
matemáticamente equivalente a la de aquí cuando hay ≥200 sesiones (que
siempre las hay, por su buffer de 5 años) -- no hay divergencia real que
arreglar ahí, solo estilo de código distinto; se deja tal cual.

NO depende de nada de backend/ (fastapi, pydantic).
"""
import pandas as pd


def spy_trend_snapshot(close: pd.Series) -> dict:
    """close: cierres de SPY en orden cronológico (cualquier ventana --
    1 año, 2 años, lo que el llamador ya tenga descargado). Devuelve
    {price, sma50, sma200, above_sma50, above_sma200} -- sma200/
    above_sma200 son None si hay menos de 200 sesiones (nunca se
    aproxima con el SMA50 ni con la media de lo que haya)."""
    # Se descartan las sesiones sin cierre ANTES de nada. yfinance devuelve la
    # barra del día en curso con Close=NaN, y ese NaN no se propaga como error
    # sino como una MENTIRA silenciosa: `NaN > sma50` es False, así que un
    # mercado claramente alcista sale "por debajo de su media" sin que nada
    # chirríe. Medido el 17/08/2026: SPY cerró en 776,34 con la SMA50 en 748,54
    # y la SMA200 en 702,75 -- por encima de las dos -- y CAN SLIM anunciaba
    # "MERCADO EN CORRECCIÓN". Se limpia aquí, en la primitiva, para que valga
    # igual para market_service.py que para canslim_service.py.
    close = close.dropna()
    if close.empty:
        raise ValueError("Serie de cierres vacía tras descartar las sesiones sin dato")
    price = float(close.iloc[-1])
    sma50 = float(close.rolling(50).mean().iloc[-1])
    above_sma50 = price > sma50
    if len(close) >= 200:
        sma200 = float(close.rolling(200).mean().iloc[-1])
        above_sma200 = price > sma200
    else:
        sma200, above_sma200 = None, None
    return {
        "price": price, "sma50": sma50, "sma200": sma200,
        "above_sma50": above_sma50, "above_sma200": above_sma200,
    }
