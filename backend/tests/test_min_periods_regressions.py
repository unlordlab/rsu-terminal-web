"""
Test de regresión para los dos casos de "min_periods mal etiquetado"
corregidos en la sesión 13 (commit 2807b34): funciones que decían calcular
una media de N puntos pero exigían muchos menos antes de emitir un valor
"maduro". Verificados AISLADOS del caller (que hoy oculta el bug con un
buffer de datos de sobra) -- si el buffer del caller cambia en el futuro,
estos tests siguen detectando la regresión igual.

1. rsu_algoritmo_service.py::_ema200_semanal() -- EMA200 semanal (~200
   semanas), antes exigía solo 20 semanas (min_periods=20).
2. btc_stratum_service.py::_calc_ma200w() -- MA200W (1400 días = 200
   semanas), antes exigía solo 200 días (14% de la ventana, min_periods=200).

Uso:
    cd backend
    python -m pytest tests/test_min_periods_regressions.py -v
"""
import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.rsu_algoritmo_service import _ema200_semanal  # noqa: E402
from services.btc_stratum_service import _calc_ma200w  # noqa: E402


def _df_spy_sintetico(periods: int) -> pd.DataFrame:
    idx = pd.date_range("2018-01-01", periods=periods, freq="D")
    close = pd.Series(np.linspace(100, 150, periods), index=idx)
    return pd.DataFrame({
        "Open": close, "High": close * 1.01, "Low": close * 0.99,
        "Close": close, "Volume": 1_000_000,
    }, index=idx)


def test_ema200_semanal_con_100_semanas_sigue_devolviendo_none():
    """700 días diarios ~= 100 semanas tras el resample W-FRI --
    deliberadamente muy por encima del umbral viejo (20 semanas) y muy por
    debajo del nuevo (200), para no depender de cuadrar un boundary exacto
    de calendario. Con el bug viejo (min_periods=20), esto ya habría dado
    un valor "maduro" con solo el 10% de la ventana real."""
    df = _df_spy_sintetico(700)
    valor, pendiente = _ema200_semanal(df)
    assert valor is None and pendiente is None


def test_ema200_semanal_con_260_semanas_da_valor_valido():
    """Confirma que la función SÍ funciona una vez hay histórico
    suficiente -- no solo que rechaza correctamente el caso insuficiente."""
    df = _df_spy_sintetico(1820)  # ~260 semanas
    valor, pendiente = _ema200_semanal(df)
    assert valor is not None and isinstance(valor, float)
    assert pendiente is not None


def test_calc_ma200w_con_200_puntos_sigue_siendo_nan():
    """200 puntos = 14% de la ventana de 1400 -- con el bug viejo
    (min_periods=200) esto ya habría dado un valor "maduro"."""
    close = pd.Series(np.linspace(100, 200, 200))
    resultado = _calc_ma200w(close)
    assert resultado.isna().all()


def test_calc_ma200w_madura_exactamente_en_el_punto_1400():
    """Boundary exacto (índice entero, sin ambigüedad de calendario): con
    1450 puntos, la media debe seguir siendo NaN hasta la posición 1399
    (0-indexed) y madurar a partir de ahí -- verifica literalmente el
    umbral de 1400 puntos reales, no solo "en algún momento madura"."""
    close = pd.Series(np.linspace(100, 300, 1450))
    resultado = _calc_ma200w(close)
    assert resultado.iloc[:1399].isna().all()
    assert resultado.iloc[1399:].notna().all()
