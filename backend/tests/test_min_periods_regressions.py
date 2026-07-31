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


def test_ema200_semanal_con_260_semanas_sigue_siendo_insuficiente():
    """ACTUALIZADO el 30/07/2026 -- antes este test afirmaba lo contrario, que
    con ~260 semanas la función "SÍ funciona". Codificaba una suposición falsa:
    `min_periods=200` impide publicar un valor prematuro, pero NO garantiza que
    la EMA haya convergido. Con adjust=True (el default de pandas) el valor es
    una media ponderada de todo lo disponible, y con 262 semanas todavía pesa
    el arranque de la serie.

    Medido con SPY real: 262 semanas dan 584,99 cuando el valor convergido es
    563,45 -- un 3,8% de error, casi 5 puntos porcentuales en la distancia al
    precio. Y el gatekeeper compara contra un corte, así que ese error decidía
    si se abría o no. Ver rsu_algoritmo_service.MIN_SEMANAS_EMA200W."""
    df = _df_spy_sintetico(1820)  # ~260 semanas
    valor, pendiente = _ema200_semanal(df)
    assert valor is None and pendiente is None


def test_ema200_semanal_con_historico_convergido_da_valor_valido():
    """El caso bueno: ~570 semanas (11 años), por encima del mínimo de 500."""
    df = _df_spy_sintetico(4000)
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
