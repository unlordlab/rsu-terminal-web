"""
Test de regresión para shared/weinstein_phases.py::classify_phase() -- el
rediseño A+B+D de la sesión 9 (commit 37c3940), tras validar empíricamente
en la sesión 8 que la versión anterior (apilamiento de 5 EMAs) NO separaba
el rendimiento de Fase 2 vs Fase 4. La SMA150 pasó a ser el discriminador
principal de tendencia; sin tendencia clara, Fase 1 vs Fase 3 se decide por
la procedencia (retorno de los últimos ~6 meses) en vez de por la posición
frente a una EMA200 sin memoria; y sin histórico suficiente para la SMA150
se devuelve phase=None en vez de asumir condiciones favorables por defecto
(el sesgo optimista que tenía la versión vieja).

Uso:
    cd backend
    python -m pytest tests/test_weinstein_phases.py -v
"""
import sys
import os

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from weinstein_phases import classify_phase  # noqa: E402


def test_classify_phase_sin_historico_suficiente_devuelve_none():
    """Fix D (sesión 9): sin las 150 sesiones que exige la SMA150, se
    devuelve phase=None -- antes de la reforma se asumían condiciones
    favorables por defecto (sesgo optimista)."""
    close = pd.Series(np.full(149, 100.0))
    r = classify_phase(close)
    assert r["phase"] is None
    assert r["trend"] is None
    assert "SMA150" in r["phase_label"]


def test_classify_phase_fase2_alcista_con_tendencia_clara():
    close = pd.Series(np.linspace(100, 250, 220), index=pd.date_range("2020-01-01", periods=220))
    r = classify_phase(close)
    assert r["phase"] == 2
    assert r["trend"] == "ALCISTA"


def test_classify_phase_fase4_bajista_con_tendencia_clara():
    close = pd.Series(np.linspace(250, 100, 220), index=pd.date_range("2020-01-01", periods=220))
    r = classify_phase(close)
    assert r["phase"] == 4
    assert r["trend"] == "BAJISTA"


def test_classify_phase_rango_decide_fase1_vs_fase3_por_retorno_6m():
    """Sin tendencia clara (SMA150 plana), la Fase 1 vs Fase 3 se decide
    por el retorno de los últimos ~126 sesiones -- viene de una caída
    (<=0) o de una subida (>0). Este es el fix B de la sesión 9, reemplaza
    a "price >= ema200 ahora mismo", que no miraba el pasado en absoluto."""
    # Fase 1: completamente plano, retorno 6m = 0 -> Fase 1.
    close_plano = pd.Series(np.full(300, 100.0))
    r1 = classify_phase(close_plano)
    assert r1["trend"] == "RANGO"
    assert r1["phase"] == 1

    # Fase 3: 150 días planos + subida suave y ANTIGUA (100->103 en 100
    # días) + 50 días planos al nuevo nivel -- la subida ya terminó hace
    # tiempo, así que la SMA150 no muestra pendiente reciente clara
    # (RANGO), pero el retorno de los últimos 126 días sigue siendo
    # positivo porque hace 126 sesiones el precio aún estaba a mitad de
    # la subida. Parámetros verificados ejecutando la función (ver
    # sesión 18) -- el margen entre RANGO/ALCISTA es sensible al timing
    # exacto de la subida, no solo a su magnitud.
    close_rango_alcista = pd.Series(
        np.concatenate([np.full(150, 100.0), np.linspace(100, 103, 100), np.full(50, 103.0)]),
        index=pd.date_range("2020-01-01", periods=300),
    )
    r3 = classify_phase(close_rango_alcista)
    assert r3["trend"] == "RANGO", f"Se esperaba RANGO, salió {r3['trend']}"
    assert r3["phase"] == 3, f"Se esperaba Fase 3, salió Fase {r3['phase']}"
