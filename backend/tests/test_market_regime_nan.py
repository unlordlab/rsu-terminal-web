"""
La barra del día en curso viene con Close=NaN, y eso no fallaba: MENTÍA.

Reportado por el usuario el 17/08/2026: CAN SLIM anunciaba «MERCADO EN
CORRECCIÓN» con un 20/100, SPY a «$0» y −100% en la variación del día, en el
1M, en el 3M y en la distancia al máximo. La realidad de ese mismo momento: SPY
cerró en 776,34, con la SMA50 en 748,54 y la SMA200 en 702,75 -- por encima de
las dos, que es la definición de tendencia alcista. Tras el arreglo: «TENDENCIA
ALCISTA CONFIRMADA», 85/100.

Dos mecanismos, y los dos hacen falta cubrir:

  1. `_safe(NaN)` devuelve su valor por defecto, 0.0. Para un PRECIO eso no es
     un respaldo prudente: es un número imposible que envenena todo lo que se
     derive de él, y encima con aspecto de dato.
  2. `NaN > sma50` es False en Python, sin aviso. Así que un mercado claramente
     por encima de sus medias sale «por debajo» sin que nada chirríe.

Lo peligroso de esta familia es que no rompe nada: no hay excepción, ni 500, ni
hueco en la pantalla. Solo un veredicto tranquilo y equivocado, del tipo que
lleva a no comprar en un mercado alcista.

Uso:
    cd backend
    python -m pytest tests/test_market_regime_nan.py -v
"""
import os
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from market_regime import spy_trend_snapshot  # noqa: E402


def _serie_alcista(n=260, nan_al_final=False):
    """Precio subiendo de 100 a 200: por encima de sus dos medias sin discusión."""
    valores = list(np.linspace(100.0, 200.0, n))
    if nan_al_final:
        valores.append(float("nan"))
    idx = pd.date_range("2025-01-01", periods=len(valores), freq="D")
    return pd.Series(valores, index=idx)


def test_una_sesion_sin_cierre_no_convierte_un_alcista_en_bajista():
    """EL test. Misma serie, con y sin la barra en curso vacía: el veredicto no
    puede cambiar por un dato que todavía no existe."""
    limpio = spy_trend_snapshot(_serie_alcista())
    con_nan = spy_trend_snapshot(_serie_alcista(nan_al_final=True))

    assert limpio["above_sma50"] is True and limpio["above_sma200"] is True
    assert con_nan["above_sma50"] is True, \
        "la barra sin cierre ha dado la vuelta al veredicto de la SMA50"
    assert con_nan["above_sma200"] is True, \
        "la barra sin cierre ha dado la vuelta al veredicto de la SMA200"
    assert con_nan["price"] == limpio["price"]
    assert con_nan["sma50"] == pytest.approx(limpio["sma50"])


def test_el_precio_nunca_sale_como_nan():
    s = spy_trend_snapshot(_serie_alcista(nan_al_final=True))
    for clave in ("price", "sma50", "sma200"):
        assert s[clave] == s[clave], f"{clave} ha salido NaN"


def test_sin_ninguna_sesion_valida_se_dice_en_vez_de_inventar():
    """Cero datos no puede acabar en un precio de 0 y un -100%: se levanta."""
    vacia = pd.Series([float("nan")] * 5,
                      index=pd.date_range("2026-01-01", periods=5, freq="D"))
    with pytest.raises(ValueError):
        spy_trend_snapshot(vacia)


def test_con_menos_de_200_sesiones_la_sma200_sigue_siendo_none():
    """Protección anterior que no se puede perder: sin histórico suficiente NO
    se aproxima la SMA200 con la SMA50 (eso era un sesgo optimista)."""
    s = spy_trend_snapshot(_serie_alcista(n=120, nan_al_final=True))
    assert s["sma200"] is None and s["above_sma200"] is None
    assert s["sma50"] is not None


def test_el_descarte_cuenta_las_sesiones_reales_no_las_filas():
    """Si el dropna no fuera lo primero, la SMA50 se calcularía sobre 49
    cierres y un hueco, y saldría un número distinto."""
    con_huecos = _serie_alcista(n=260)
    con_huecos.iloc[-3] = float("nan")
    a = spy_trend_snapshot(con_huecos)
    b = spy_trend_snapshot(con_huecos.dropna())
    assert a["sma50"] == pytest.approx(b["sma50"])
