"""
Test de regresión para los 4 fallbacks fabricados eliminados en la sesión
12 (commit b8b70af, 22/07/2026): ante ausencia de dato real, estas
funciones ahora devuelven None/ok:False, nunca un número aproximado con
la misma forma que uno real (Reddit Pulse con 8 tickers inventados, DXY
fijo en 103.0, Yield 2Y sintetizado como Y3M+0.47, RS Rating de CANSLIM
aproximado con 50+perf/2).

Uso:
    cd backend
    python -m pytest tests/test_fallbacks_removidos.py -v
"""
import sys, os
from unittest.mock import patch, MagicMock

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.market_service import _reddit_fallback, get_fed_macro  # noqa: E402
from services.btc_stratum_service import _get_macro_data  # noqa: E402
from services.canslim_service import _rs_rating_real  # noqa: E402


def test_reddit_fallback_sin_datos_devuelve_ok_false():
    r = _reddit_fallback()
    assert r["ok"] is False
    assert r["data"] == [] and r["sources"] == []


def test_dxy_fallback_sin_datos_devuelve_none_no_103():
    with patch("services.btc_stratum_service.yf.download", side_effect=Exception("red caída")):
        r = _get_macro_data()
    assert r == {"dxy": None, "dxy_score": None, "liquidity_score": None, "status": None}


def test_rs_rating_sin_universo_devuelve_none():
    assert _rs_rating_real(50.0, []) is None


def test_rs_rating_con_universo_da_percentil_real_no_formula_aproximada():
    universo = [10.0, 20.0, 30.0, 40.0, 60.0, 70.0, 80.0, 90.0, 5.0]
    resultado = _rs_rating_real(perf_12m=50.0, universe_perfs=universo)
    # 5 de 9 valores del universo están por debajo de 50 -> percentil real,
    # no 50 + 50/2 = 75 (la fórmula vieja que se eliminó)
    assert resultado != 75
    assert 1 <= resultado <= 99


def test_fetch_yields_sin_fuentes_reales_no_sintetiza_2y():
    fake_ticker = MagicMock()
    fake_ticker.history.return_value = pd.DataFrame()  # vacío para los 6 símbolos
    fake_response = MagicMock(status_code=500)  # FRED también falla

    with patch("services.cache.cache.get", return_value=None), \
         patch("services.cache.cache.set"), \
         patch("services.market_service.yf.Ticker", return_value=fake_ticker), \
         patch("requests.get", return_value=fake_response):
        result = get_fed_macro()

    assert result["ok"] is True
    yields = result["yields"]
    assert yields["Y2Y"] is None, "Sin fuentes reales, Y2Y no debe sintetizarse con Y3M+0.47"
    assert yields["Y3M"] is None and yields["Y10Y"] is None
