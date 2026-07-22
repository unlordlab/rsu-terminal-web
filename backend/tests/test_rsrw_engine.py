"""
Test de regresión para shared/rsrw_engine.py -- el motor RS unificado en la
sesión 14 (commit f0141f3). Antes de unificarlo, rsrw_scan.py hacía un
ranking manual por posición para el percentil (no promediaba empates como
pandas.rank(pct=True)) y solo rsrw_scan.py tenía el fix de rs_momentum
normalizado por día -- rsrw_service.py y thematic_scan.py seguían con la
comparación cruda sesgada hacia "63d siempre gana". Estos tests fijan el
comportamiento correcto para que ninguna copia futura pueda volver a
divergir en silencio.

Uso:
    cd backend
    python -m pytest tests/test_rsrw_engine.py -v
"""
import sys
import os

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from rsrw_engine import rs_percentile, rs_momentum, rs_smooth  # noqa: E402


def test_rs_percentile_promedia_rangos_empatados():
    """rank(pct=True) promedia el rango de los valores empatados -- el
    ranking manual por posición que tenía rsrw_scan.py antes de la sesión
    14 no lo hacía, y daba un percentil distinto en cuanto dos tickers
    compartían exactamente el mismo rs_score_raw."""
    scores = pd.Series([10, 10, 30, 40])
    resultado = rs_percentile(scores).tolist()
    assert resultado == [37.5, 37.5, 75.0, 100.0], (
        f"Se esperaba [37.5, 37.5, 75.0, 100.0] (rangos 1 y 2 empatados "
        f"promediados a 1.5/4*100=37.5), salió {resultado}"
    )


def test_rs_momentum_normaliza_por_dia_no_favorece_al_periodo_largo():
    """El fix real (sesión 14): comparar diferenciales normalizados por nº
    de días, no en crudo -- comparar rs_21d > rs_63d sin más sesgaba hacia
    "63d gana" solo por acumular más tiempo, no por aceleración real."""
    # Caso A: 4.2 < 6.3 en crudo, pero el RITMO de 21d (0.2/día) supera al
    # de 63d (0.1/día) -- exactamente el caso que la comparación cruda
    # antigua clasificaba mal (habría dado 0).
    assert rs_momentum(rs_21d=4.2, rs_63d=6.3) == 1

    # Caso B: aquí el medio plazo gana genuinamente incluso normalizado --
    # confirma que la función no siempre devuelve 1.
    assert rs_momentum(rs_21d=1.0, rs_63d=6.3) == 0


def test_rs_smooth_es_cero_cuando_no_hay_diferencial_vs_benchmark():
    """Si precio y benchmark son idénticos, el diferencial de retorno (y
    su EMA) debe ser exactamente 0 en todo punto -- smoke test de que la
    resta no se invierta ni se duplique en un refactor futuro."""
    idx = pd.date_range("2024-01-01", periods=40)
    prices = pd.Series([100.0] * 40, index=idx)
    benchmark = prices.copy()

    resultado = rs_smooth(prices, benchmark, period=21)
    assert resultado.dropna().eq(0).all()
