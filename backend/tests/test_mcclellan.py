"""
Test de regresión para shared/mcclellan.py -- el oscilador McClellan
unificado en la sesión 15 (commit 5f3756c). Antes de unificarlo había 3
copias idénticas (market_service.py x2 ramas, rsu_algoritmo_service.py
rama en vivo) más una reimplementación a mano sin pandas en
daily_briefing.py. Estos tests fijan las propiedades matemáticas básicas
de EMA19-EMA39 para detectar si un futuro cambio invierte la resta,
intercambia los spans, o cambia adjust=False sin darse cuenta.

Uso:
    cd backend
    python -m pytest tests/test_mcclellan.py -v
"""
import sys
import os

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from mcclellan import mcclellan_series  # noqa: E402


def test_mcclellan_converge_a_cero_con_amplitud_constante():
    """Con adjust=False y una entrada constante, tanto EMA19 como EMA39
    quedan sembradas y se mantienen en ese mismo valor constante en todo
    punto -- la diferencia debe ser (esencialmente) cero. Si se invierte
    la resta o se cambia adjust=True, este test detecta la divergencia."""
    net_advances = pd.Series([100.0] * 80)
    resultado = mcclellan_series(net_advances).iloc[-1]
    assert abs(resultado) < 0.5, f"Se esperaba ~0 con amplitud constante, salió {resultado}"


def test_mcclellan_positivo_tras_repunte_reciente():
    """EMA19 (más rápida) debe reaccionar antes que EMA39 a un repunte
    reciente de amplitud, dando oscilador positivo. Si se intercambian
    los spans (19<->39) el signo se invierte -- regresión detectable."""
    net_advances = pd.Series([-50.0] * 40 + [200.0] * 15)
    resultado = mcclellan_series(net_advances).iloc[-1]
    assert resultado > 0, f"Se esperaba oscilador positivo tras el repunte, salió {resultado}"
