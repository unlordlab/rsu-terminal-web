"""
Test de la curva de patrimonio de Cartera (12/08/2026, reportado por el
usuario con una captura: el gráfico caía a CERO en el último punto y el pie
decía «Patrimonio $0.00» con una cartera de $335.302).

El mecanismo, de punta a punta:

  1. yfinance devuelve fila para la sesión en curso con el cierre a NaN
     mientras no está consolidada. Ese día 11 de los tickers del usuario
     estaban así a la vez.
  2. `mercado += float(px) * shares` con un NaN convierte el total del día en
     NaN en cuanto UNA posición lo tenga.
  3. El guardia `if equity <= 0: continue` existe justo para saltarse los días
     malos... pero **con un NaN toda comparación es falsa**, así que
     `NaN <= 0` da False y el punto se colaba.
  4. `_sanitize()` convierte el NaN en `null` al serializar, y el gráfico
     pinta un null como 0.

Dos arreglos, porque cada uno tapa un agujero distinto: quitar los NaN de la
serie de precios (así ese día se usa el último cierre bueno del ticker, que es
lo que se quiere en una curva de patrimonio) y hacer el guardia a prueba de
NaN.

Uso:
    cd backend
    python -m pytest tests/test_cartera_curva.py -v
"""
import math
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_service as C  # noqa: E402


FECHAS = pd.to_datetime(["2026-08-07", "2026-08-10", "2026-08-11"])


def _serie(valores):
    return pd.Series(valores, index=FECHAS.tz_localize("UTC"), name="Close")


def _posicion(ticker, shares=10.0, inv=1000.0):
    return {"ticker": ticker, "shares": shares, "inv": inv,
            "fecha": "01/01/2026", "actual": 100.0}


def _curva(series_por_ticker, posiciones):
    """Ejecuta get_portfolio_history con precios controlados."""
    C._history_cache.update({"updated": 0, "data": None, "key": None})

    class _Tk:
        def __init__(self, t): self._t = t
        def history(self, **kw):
            return pd.DataFrame({"Close": series_por_ticker[self._t]})

    with patch.object(C.yf_executor, "map",
                      lambda fn, it: [fn(x) for x in it]), \
         patch("yfinance.Ticker", lambda t: _Tk(t)):
        return C.get_portfolio_history(posiciones)


def test_un_nan_en_el_ultimo_dia_ya_no_manda_la_curva_a_cero():
    """El caso reportado: la sesión en curso llega sin consolidar."""
    series = {"AAA": _serie([100.0, 110.0, float("nan")])}
    h = _curva(series, [_posicion("AAA")])
    assert h, "la curva no puede quedarse vacía"
    assert h[-1]["valor"] is not None
    assert not math.isnan(h[-1]["valor"])


def test_ese_dia_se_usa_el_ultimo_cierre_bueno_del_ticker():
    """No se descarta la posición (haría caer el patrimonio de golpe), se
    arrastra su último precio válido."""
    series = {"AAA": _serie([100.0, 110.0, float("nan")])}
    h = _curva(series, [_posicion("AAA", shares=10.0)])
    assert h[-1]["valor"] == 1100.0, "10 acciones al último cierre bueno (110)"


def test_un_solo_ticker_con_nan_no_envenena_a_los_demas():
    """Era lo peor del fallo: bastaba UNA posición sin consolidar para que el
    patrimonio entero del día saliera NaN."""
    series = {
        "AAA": _serie([100.0, 100.0, 100.0]),
        "BBB": _serie([50.0, 50.0, float("nan")]),
    }
    h = _curva(series, [_posicion("AAA", 10.0), _posicion("BBB", 10.0)])
    assert h[-1]["valor"] == 1500.0, "10x100 del bueno + 10x50 del último válido"


def test_el_guardia_de_dias_malos_esta_escrito_a_prueba_de_nan():
    """Este se comprueba sobre el CÓDIGO, no a través de la función, y hay que
    decir por qué: con el `dropna()` de arriba ya no llega ningún NaN hasta el
    guardia, así que quitarlo no rompe ninguna prueba de comportamiento. Es
    defensa en profundidad para un fallo que ya mordió una vez, y sin este
    test volvería al `equity <= 0` sin que nadie se enterase.

    La diferencia importa: `NaN <= 0` es False —toda comparación con NaN lo
    es— así que la forma antigua dejaba pasar justo el día que quería saltarse.
    """
    import inspect
    src = inspect.getsource(C.get_portfolio_history)
    assert "if not (equity > 0):" in src, \
        "el guardia volvió a una forma que un NaN atraviesa"
    # Y la propiedad que lo justifica
    for valor in (float("nan"), 0.0, -5.0):
        assert not (valor > 0)
    assert 1234.5 > 0


def test_una_serie_entera_de_nan_no_aporta_esa_posicion():
    """Si un ticker no tiene NINGÚN precio válido no hay nada que arrastrar.
    La curva sale con el resto en vez de romperse."""
    series = {
        "AAA": _serie([100.0, 100.0, 100.0]),
        "BBB": _serie([float("nan")] * 3),
    }
    h = _curva(series, [_posicion("AAA", 10.0), _posicion("BBB", 10.0)])
    assert h, "la curva sigue existiendo"
    assert all(p["valor"] == 1000.0 for p in h), "solo aporta AAA"


def test_la_curva_normal_no_cambia():
    """Sin NaN de por medio, mismos números que siempre."""
    series = {"AAA": _serie([100.0, 110.0, 120.0])}
    h = _curva(series, [_posicion("AAA", 10.0)])
    assert [p["valor"] for p in h] == [1000.0, 1100.0, 1200.0]
