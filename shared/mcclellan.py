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
