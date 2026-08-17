"""
El «HOY %» de Cartera volvía a salir mal cada día, y no era por el cálculo.

Se arregló tres veces (11/08, 12/08 y 13/08) dentro de `_fetch_price_single()`,
que es donde estaba el síntoma. Cada arreglo se verificó con datos reales y
quedaba correcto... y al día siguiente volvía. El motivo, encontrado el
13/08/2026: la corrupción NO ocurre en el cálculo, ocurre DESPUÉS, desde otro
módulo que escribe en la misma caché.

`_fetch_price_single()` hace lo correcto cuando a yfinance le falta la barra de
ayer: devuelve `chg=None` y `sin_datos_hoy=True` para que la tabla pinte «—».
Pero sigue devolviendo `prev` -- que en ese caso NO es el cierre de ayer, sino
el último que se pudo conseguir. `_aplicar_trade()` (stream de Finnhub) solo
comprobaba que ese número existiera y fuera positivo, así que al llegar el
primer tick recalculaba el porcentaje contra él y sobrescribía el None.

Reproducido con los números reales de la cartera del 13/08: LITE aparecía
+13,45% cuando su movimiento del día era +0,28%; SPCX y COHR se pintaban
subiendo cuando los dos bajaban. Y el mismo write borraba `sin_datos_hoy`,
`chg_fecha` y `ultimo_cierre`, así que el aviso de "estos datos no son de hoy"
-- construido el 11/08 justo para esto -- quedaba desactivado a la vez.

POR QUÉ NO SALTÓ EN NINGUNA VERIFICACIÓN LOCAL: `FINNHUB_REALTIME` viene
apagado por defecto (es una decisión de licencia, ver finnhub_stream_service),
y está encendido en producción. Sin el flag, `_aplicar_trade()` no llega a
ejecutarse. Estos tests lo llaman DIRECTAMENTE, sin flag y sin red, que es lo
único que los habría hecho fallar a tiempo.

Uso:
    cd backend
    python -m pytest tests/test_cartera_tick_no_resucita.py -v
"""
import sys, os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.cartera_service import _price_cache  # noqa: E402
from services.finnhub_stream_service import _aplicar_trade
from services.cartera_service import _ultima_sesion_esperada  # noqa: E402


@pytest.fixture(autouse=True)
def cache_limpia():
    _price_cache.clear()
    yield
    _price_cache.clear()


def _entrada_sin_referencia(prev):
    """Lo que devuelve _fetch_price_single() cuando falta la barra de ayer:
    admite que no sabe el % de hoy, pero entrega el último cierre que
    consiguió como `prev`."""
    return {"ticker": "SPCX", "price": prev, "prev": prev, "chg": None,
            "sin_datos_hoy": True, "chg_fecha": None,
            "ultimo_cierre": "2026-08-11", "updated": 0}


# ── El fallo en sí ──────────────────────────────────────────────────────────

def test_un_tick_no_convierte_un_no_lo_se_en_un_porcentaje():
    """Caso real del 13/08: prev = cierre del 11/08 (133,29) porque faltaba la
    barra del 12. Con el precio en vivo de hoy, el porcentaje resucitado era
    +6,53% -- el movimiento de DOS sesiones. El del día era -2,41%."""
    _price_cache["SPCX"] = _entrada_sin_referencia(133.29)
    _aplicar_trade("SPCX", 142.00)
    assert _price_cache["SPCX"]["chg"] is None


def test_el_aviso_de_sesion_desfasada_sobrevive_al_tick():
    """El write no solo inventaba el porcentaje: borraba los campos con los que
    la pantalla avisa de que los datos no son de hoy, así que el número salía
    además sin ninguna advertencia."""
    _price_cache["SPCX"] = _entrada_sin_referencia(133.29)
    _aplicar_trade("SPCX", 142.00)
    d = _price_cache["SPCX"]
    assert d["sin_datos_hoy"] is True
    assert d["ultimo_cierre"] == "2026-08-11"


def test_el_precio_en_vivo_si_se_publica_aunque_no_haya_porcentaje():
    """No se tira el tick: el P&L de cada posición se calcula contra el precio
    de COMPRA, no contra `prev`, así que el precio nuevo es correcto y útil
    aunque el % del día siga siendo desconocido."""
    _price_cache["SPCX"] = _entrada_sin_referencia(133.29)
    assert _aplicar_trade("SPCX", 142.00) is True
    assert _price_cache["SPCX"]["price"] == 142.00


# ── Las DOS mitades de la guarda, por separado ──────────────────────────────
#
# El caso de arriba trae `chg=None` Y `sin_datos_hoy=True` a la vez -- que es
# como lo devuelve hoy _fetch_price_single() -- así que cualquiera de las dos
# comprobaciones lo caza sola y no distingue si la otra sirve. Estos dos tests
# aíslan cada mitad. Se detectó saboteando la guarda: quitar cualquiera de las
# dos condiciones dejaba todos los tests en verde.

def test_un_chg_a_none_basta_para_no_fiarse_del_prev():
    """Sin la marca `sin_datos_hoy`. Un `chg` a None ya significa que quien
    escribió la entrada no sabía el movimiento del día, así que su `prev`
    tampoco es una referencia de hoy."""
    _price_cache["AAA"] = {"ticker": "AAA", "price": 100.0, "prev": 100.0,
                           "chg": None, "updated": 0}
    _aplicar_trade("AAA", 110.0)
    assert _price_cache["AAA"]["chg"] is None


def test_sin_datos_hoy_basta_aunque_venga_un_numero_en_chg():
    """Al revés: la marca puesta pero con un número en `chg`. Hoy ninguna rama
    produce esta combinación -- es una red para que, si algún día alguien
    marca una entrada como desfasada sin poner el porcentaje a None, el tick
    no la dé por buena igualmente."""
    _price_cache["BBB"] = {"ticker": "BBB", "price": 100.0, "prev": 100.0,
                           "chg": 1.23, "sin_datos_hoy": True, "updated": 0}
    _aplicar_trade("BBB", 110.0)
    assert _price_cache["BBB"]["chg"] is None


# ── Y el camino bueno sigue funcionando ─────────────────────────────────────

def test_con_referencia_buena_el_tick_si_calcula_el_porcentaje():
    """El arreglo no puede apagar el stream: cuando `prev` SÍ es el cierre de
    ayer (la entrada traía un chg real), el tick actualiza el porcentaje."""
    _price_cache["MSTR"] = {"ticker": "MSTR", "price": 95.00, "prev": 94.83,
                            "chg": 0.18, "sin_datos_hoy": False,
                            "chg_fecha": "2026-08-13",
                            # Desde el 17/08/2026 la referencia declara de qué
                            # sesión es; sin fecha ya no se considera válida.
                            "prev_fecha": str(_ultima_sesion_esperada()),
                            "updated": 0}
    _aplicar_trade("MSTR", 98.55)
    d = _price_cache["MSTR"]
    assert d["chg"] == pytest.approx(3.92, abs=0.01)
    assert d["price"] == 98.55
    assert d["fuente"] == "finnhub"


def test_la_fecha_de_la_sesion_no_se_pierde_en_el_camino_bueno():
    """`chg_fecha` es lo que permite decir de qué sesión es el dato. El write
    antiguo lo borraba SIEMPRE, también con datos buenos."""
    _price_cache["MSTR"] = {"ticker": "MSTR", "price": 95.00, "prev": 94.83,
                            "chg": 0.18, "sin_datos_hoy": False,
                            "chg_fecha": "2026-08-13",
                            # Desde el 17/08/2026 la referencia declara de qué
                            # sesión es; sin fecha ya no se considera válida.
                            "prev_fecha": str(_ultima_sesion_esperada()),
                            "updated": 0}
    _aplicar_trade("MSTR", 98.55)
    assert _price_cache["MSTR"]["chg_fecha"] == "2026-08-13"


def test_sin_prev_no_se_toca_nada():
    """Comportamiento de siempre, que sigue siendo el correcto: sin cierre de
    referencia no hay nada que publicar."""
    _price_cache["NADA"] = {"ticker": "NADA", "prev": None, "chg": None}
    assert _aplicar_trade("NADA", 10.0) is False
    assert "price" not in _price_cache["NADA"]


def test_ticker_desconocido_no_se_inventa_una_entrada():
    assert _aplicar_trade("XYZ", 10.0) is False
    assert "XYZ" not in _price_cache
