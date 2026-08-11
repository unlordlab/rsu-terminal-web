"""
Test del "P&L Total Acum." de Cartera y de las cerradas que la simulación de
niveles no pudo dimensionar (11/08/2026, a raíz de que al usuario no le
cuadrara el +55,75% con sus 43 operaciones cerradas).

El número es la MEDIA PONDERADA POR CAPITAL de las cerradas — o sea, el
retorno agregado del dinero desplegado — no la media simple de los
porcentajes (que daría 44,57%) ni su suma (1.916,65%, lo que hacía antes de
corregirse).

De ahí salen seis cerradas con `inv = 0` que no pesan nada en el número. NO
son datos que falten: `simulate_tier_capital()` recorre las operaciones en
orden cronológico y esas seis se abrieron con el capital íntegramente
comprometido, así que devuelve `None` — "no se pudo dimensionar". Este
fichero existe para que ese cero no se "arregle" rellenándolo con el peso del
nivel, que fue justo el primer intento y es un error en tres frentes:
inventaría capital que el modelo dice que no había, lo haría FUERA de la
simulación (así que `equity` y `open_committed` nunca lo verían), y
reescribiría el P&L realizado de una operación ya cerrada — lo que el
comentario de la segunda pasada de esa función prohíbe explícitamente.

Uso:
    cd backend
    python -m pytest tests/test_cartera_pnl_cerradas.py -v
"""
import os
import sys
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_service as C  # noqa: E402


def _cartera(filas, capital_total=100_000.0):
    """Mismo arnés que test_cartera_tickers.py: `url_cartera` se fija a un
    valor de mentira ANTES de parchear read_csv, porque get_cartera()
    comprueba la URL antes de leer nada — sin eso el test pasa en local (que
    tiene .env) y falla en el runner de CI, que arranca sin él."""
    from services.cache import cache
    C._cartera_cache.clear()
    with patch.object(C.settings, "url_cartera", "https://example.invalid/hoja.csv"), \
         patch.object(C.settings, "capital_total", capital_total), \
         patch.object(C.pd, "read_csv", return_value=pd.DataFrame(filas)), \
         patch.object(C, "fetch_live_prices", return_value={}), \
         patch.object(cache, "set"), \
         patch.object(cache, "get", return_value=None):
        return C.get_cartera()


def _cerrada(ticker, fecha, compra, venta, nivel="CORE", cantidad=None):
    return {"Fecha": fecha, "Ticker": ticker, "Estado": "CERRADA", "Nivel": nivel,
            "Precio Compra": compra, "Precio Venta": venta, "Cantidad": cantidad}


def _abierta(ticker, fecha, compra, nivel="CORE", cantidad=None):
    return {"Fecha": fecha, "Ticker": ticker, "Estado": "ABIERTA", "Nivel": nivel,
            "Precio Compra": compra, "Precio Venta": None, "Cantidad": cantidad}


def test_el_pnl_acumulado_pondera_por_capital_no_es_la_media_simple():
    """CORE (5% = $5.000) al +100% y LOTTERY (1% = $1.000) al +10%:
    (100*5000 + 10*1000) / 6000 = 85,0. La media simple daría 55,0 y la suma
    110,0 — dos números con la misma pinta y ningún sentido económico."""
    d = _cartera([
        _cerrada("AAA", "01/02/2026", 100.0, 200.0, "CORE"),
        _cerrada("BBB", "01/03/2026", 100.0, 110.0, "LOTTERY"),
    ])
    assert d["closed_stats"]["avg_pnl"] == 85.0
    assert d["closed_stats"]["total"] == 2


def test_la_ponderada_nunca_cae_fuera_del_rango_de_los_porcentajes():
    """Chequeo de sanidad barato: una media ponderada de +100% y +10% tiene
    que estar entre los dos. Si algún día sale fuera, el peso está roto."""
    d = _cartera([
        _cerrada("AAA", "01/02/2026", 100.0, 200.0, "CORE"),
        _cerrada("BBB", "01/03/2026", 100.0, 110.0, "LOTTERY"),
    ])
    pnls = [r["pnl"] for r in d["cerradas"]]
    assert min(pnls) <= d["closed_stats"]["avg_pnl"] <= max(pnls)


# 21 posiciones CORE al 5%: las 20 primeras comprometen el 100% del capital,
# así que la 21ª se encuentra la caja a cero el día que se abre.
_VEINTIUNA = (
    [_abierta(f"T{i:02d}", f"{(i % 28) + 1:02d}/01/2026", 100.0) for i in range(20)]
    + [_cerrada("ZZZ", "01/06/2026", 100.0, 150.0, "CORE")]
)


def test_una_cerrada_que_no_cabia_en_el_capital_se_queda_a_cero():
    """`simulate_tier_capital()` devuelve None cuando no hay caja el día de la
    apertura, y sin Cantidad ni Inversión en la hoja no hay a qué caer. El 0
    es el resultado del modelo, no un dato que falte."""
    cerradas = {r["ticker"]: r for r in _cartera(_VEINTIUNA)["cerradas"]}
    assert cerradas["ZZZ"]["inv"] == 0.0
    assert cerradas["ZZZ"]["tier"] == "CORE"


def test_esa_cerrada_no_se_rellena_con_el_peso_de_su_nivel():
    """Test canario del error que casi se comete: dimensionarla por su nivel
    (CORE = $5.000) inventaría capital que la simulación dice que no había,
    fuera de la propia simulación, y reescribiría el P&L realizado de una
    operación ya cerrada. Si este test empieza a fallar, alguien ha vuelto a
    intentarlo — no es un bug nuevo, es este."""
    cerradas = {r["ticker"]: r for r in _cartera(_VEINTIUNA)["cerradas"]}
    assert cerradas["ZZZ"]["inv"] != 5000.0


def test_si_la_hoja_dice_cuanto_se_invirtio_ese_dato_manda_sobre_el_cero():
    """Cuando la simulación no puede dimensionar, el llamador cae al cálculo
    antiguo Cantidad*compra — que es precisamente para lo que la función
    devuelve None en vez de 0.0."""
    filas = list(_VEINTIUNA[:-1]) + [
        _cerrada("ZZZ", "01/06/2026", 100.0, 150.0, "CORE", cantidad=7)
    ]
    cerradas = {r["ticker"]: r for r in _cartera(filas)["cerradas"]}
    assert cerradas["ZZZ"]["inv"] == 700.0


def test_una_abierta_sin_capital_sigue_marcandose_sin_dimensionar():
    """El mismo caso en una posición ABIERTA sí lleva aviso: la tabla la pinta
    como «sin dimensionar» en vez de como una posición de $0. Lo que faltaba
    era el equivalente para las cerradas."""
    filas = list(_VEINTIUNA[:-1]) + [_abierta("ZZZ", "01/06/2026", 100.0, "CORE")]
    abiertas = {r["ticker"]: r for r in _cartera(filas)["abiertas"]}
    assert abiertas["ZZZ"]["inv"] == 0.0
    assert abiertas["ZZZ"]["sin_dimensionar"] is True
