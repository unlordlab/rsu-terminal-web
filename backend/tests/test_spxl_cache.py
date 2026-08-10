"""
Test de la caché de SPXL (hallazgo #4 de su auditoría).

QUÉ ESTABA MAL. Ninguna de las cuatro funciones públicas tenía caché: cada
visita a la página descargaba SPXL desde 2008 y volvía a correr el motor.
Medido el 08/08 interceptando las llamadas de yfinance, una sola carga
hacía **8 peticiones a Yahoo, 5 de ellas de la MISMA serie de 17 años** —
una por función. El tiempo (~3,7s en frío) no era lo grave: la cuota de
Yahoo la comparte toda la terminal, así que quemarla cinco veces por
visita en datos idénticos se lo quita a Research, Market y Cartera.

QUÉ FIJA ESTE FICHERO, que son los dos riesgos de una caché con clave y no
el "va más rápido" (eso ya lo dice la medición):

1. QUE NO SE CRUCEN LAS CLAVES. Los tres backtests reciben el capital
   inicial como parámetro. Si la clave no lo incluyera, quien pidiera
   250.000 recibiría el resultado calculado para 100.000 -- números
   plausibles y equivocados, que es la peor clase de error.

2. QUE UN FALLO NO SE QUEDE PEGADO. Si Yahoo falla y la respuesta de error
   se cachea, la página se queda rota durante toda la vida de la entrada
   aunque el proveedor se recupere al segundo siguiente.

Uso:
    cd backend
    python -m pytest tests/test_spxl_cache.py -v
"""
import sys, os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.cache import cache  # noqa: E402
import services.spxl_service as S  # noqa: E402


CLAVES = ["spxl:live", "spxl:bt:100000", "spxl:bt:250000",
          "spxl:btval:100000", "spxl:btslip:100000"]


@pytest.fixture(autouse=True)
def cache_limpia():
    """La caché es la real y vive en cache.db, compartida con la app: si no
    se limpia antes, un test puede pasar leyendo lo que dejó otro (o lo que
    dejó la propia terminal corriendo en local) en vez de lo que cree estar
    probando."""
    for k in CLAVES:
        cache.delete(k)
    yield
    for k in CLAVES:
        cache.delete(k)


def _backtest_falso(initial_capital=100_000):
    """Sustituye al motor real: estos tests miran el comportamiento de la
    caché, no el del backtest, y correrlo de verdad los ataría a la red."""
    return {"ok": True, "stats": {"final_equity": initial_capital * 2},
            "trades": [], "equity_chart": [], "bnh_chart": [], "timestamp": "x"}


def test_cada_capital_tiene_su_propia_entrada():
    """El riesgo nº1: servir a un capital el resultado calculado para otro."""
    llamadas = []

    def espia(df, initial_capital=100_000, debug=False):
        llamadas.append(initial_capital)
        return {"trades": [], "equity_curve": [{"equity": initial_capital}],
                "bnh_curve": [{"equity": initial_capital}]}

    with patch.object(S, "run_backtest", side_effect=espia), \
         patch.object(S, "compute_stats", side_effect=lambda t, e, b, c: {"final_equity": c * 2}):
        a  = S.get_backtest(100_000)
        b  = S.get_backtest(250_000)
        a2 = S.get_backtest(100_000)   # esta ya sale de la caché

    assert a["stats"]["final_equity"] != b["stats"]["final_equity"], \
        "dos capitales distintos han devuelto el mismo resultado"
    assert a2["stats"]["final_equity"] == a["stats"]["final_equity"]
    assert llamadas == [100_000, 250_000], \
        f"el motor debería correr una vez por capital, corrió {llamadas}"


def test_la_segunda_llamada_no_vuelve_a_calcular():
    llamadas = []
    with patch.object(S, "run_backtest",
                      side_effect=lambda df, initial_capital=100_000, debug=False: (
                          llamadas.append(1),
                          {"trades": [], "equity_curve": [{"equity": 1}], "bnh_curve": [{"equity": 1}]})[1]), \
         patch.object(S, "compute_stats", side_effect=lambda t, e, b, c: {}):
        S.get_backtest(100_000)
        S.get_backtest(100_000)
        S.get_backtest(100_000)
    assert len(llamadas) == 1, f"el motor corrió {len(llamadas)} veces, debería ser 1"


def test_un_fallo_de_yahoo_no_se_queda_cacheado():
    """El riesgo nº2. Si se cachea el error, la página sigue rota aunque el
    proveedor se recupere."""
    with patch.object(S.yf, "Ticker", side_effect=Exception("Yahoo caído")):
        r = S.get_spxl_live()
    assert r["ok"] is False
    assert cache.get("spxl:live") is None, "un error no puede quedarse en la caché"


def test_tras_un_fallo_la_siguiente_llamada_lo_reintenta():
    llamadas = []

    def ticker_inestable(*a, **kw):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise Exception("Yahoo caído")
        raise Exception("sigue caído")   # basta con comprobar que se reintenta

    with patch.object(S.yf, "Ticker", side_effect=ticker_inestable):
        S.get_spxl_live()
        S.get_spxl_live()
    assert len(llamadas) == 2, "la segunda llamada debería reintentar, no servir el error cacheado"
