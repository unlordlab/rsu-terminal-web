"""
Cartera: por qué el «HOY %» volvía a salir mal cada pocos días (17/08/2026).

Hubo tres arreglos anteriores, y los tres vivían dentro de las ramas de
`_fetch_price_single()`. Ninguno aguantó, y la razón es que esa función DEJA DE
EJECUTARSE en cuanto llegan ticks del stream:

  · `_price_cache` tiene un TTL de 60 segundos.
  · `_aplicar_trade()` escribía `updated: time.time()` en CADA trade.
  · Con el stream vivo, la entrada nunca cumple 60 s -> nunca se vuelve a pedir
    -> su `prev` se queda congelado en el que hubiera al arrancar el stream,
    cruzando noches y fines de semana enteros.

Medido con la cartera real el lunes 17/08/2026: de 24 posiciones, 12 calculaban
contra el cierre del viernes 14 (correcto), 11 contra el del jueves 13 y una
contra el del miércoles 12. SNDK enseñaba +14,02% cuando su movimiento del día
era +6,72% -- viernes y lunes sumados bajo la etiqueta «HOY».

Lo que se protege aquí es el arreglo de raíz, que tiene dos mitades:
  1. `prev` viaja con la fecha de su sesión (`prev_fecha`). Una referencia sin
     fecha no se puede validar: solo se podía comprobar que existiera y fuera
     positiva, que es exactamente lo que fallaba.
  2. Si esa fecha no es la de la última sesión cerrada, no se publica
     porcentaje Y NO se renueva `updated`, para que la entrada caduque y se
     vuelva a pedir. Renovarla era lo que hacía inmortal al dato viejo.

Uso:
    cd backend
    python -m pytest tests/test_cartera_hoy_pct.py -v
"""
import os
import sys
import time
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_service as C  # noqa: E402
from services.finnhub_stream_service import _aplicar_trade  # noqa: E402

TICKER = "TEST-HOY"


def _sembrar(prev_fecha, prev=100.0, chg=1.0, updated=None):
    """Entrada de caché como la que deja `_fetch_price_single()`."""
    C._price_cache[TICKER] = {
        "ticker": TICKER, "price": prev, "prev": prev, "chg": chg,
        "chg_fecha": "2026-08-17", "prev_fecha": prev_fecha,
        "sin_datos_hoy": False, "updated": updated if updated is not None else time.time(),
    }


def _limpiar():
    C._price_cache.pop(TICKER, None)


# ── El defecto de fondo: la caché se volvía inmortal ─────────────────────────

def test_un_tick_no_resucita_una_referencia_de_otra_sesion():
    """EL test. Con `prev` del jueves y el mercado abierto el lunes, un tick NO
    debe convertir ese cierre viejo en el «HOY %» del día."""
    try:
        with patch.object(C, "_is_market_open", return_value=True), \
             patch.object(C, "_ultima_sesion_esperada", return_value=_fecha("2026-08-14")):
            _sembrar(prev_fecha="2026-08-13", prev=1528.07, chg=1.0)
            assert _aplicar_trade(TICKER, 1742.31) is True
            e = C._price_cache[TICKER]
        assert e["chg"] is None, \
            f"ha recalculado el porcentaje contra el cierre del 13: {e['chg']}"
        assert e["sin_datos_hoy"] is True
        assert e["price"] == 1742.31, "el precio en vivo sí debe publicarse"
    finally:
        _limpiar()


def test_con_la_referencia_caducada_no_se_renueva_el_reloj_de_la_cache():
    """La otra mitad del arreglo. Si el tick renovara `updated`, la entrada no
    caducaría nunca y `_fetch_price_single()` no volvería a pedirla -- que es
    justo lo que hacía que el dato viejo sobreviviera días enteros."""
    try:
        viejo = time.time() - 3600
        with patch.object(C, "_is_market_open", return_value=True), \
             patch.object(C, "_ultima_sesion_esperada", return_value=_fecha("2026-08-14")):
            _sembrar(prev_fecha="2026-08-13", updated=viejo)
            _aplicar_trade(TICKER, 123.45)
            e = C._price_cache[TICKER]
        assert e["updated"] == viejo, \
            "el reloj se ha renovado: la entrada nunca caducaria y el prev viejo seria inmortal"
        assert (time.time() - e["updated"]) > C._CACHE_TTL, \
            "la entrada deberia quedar caducada para que se vuelva a pedir"
    finally:
        _limpiar()


def test_con_la_referencia_correcta_el_tick_si_actualiza_el_porcentaje():
    """El camino normal no se toca: si `prev` es del cierre que toca, el tick
    recalcula y renueva la caché como siempre."""
    try:
        with patch.object(C, "_is_market_open", return_value=True), \
             patch.object(C, "_ultima_sesion_esperada", return_value=_fecha("2026-08-14")):
            _sembrar(prev_fecha="2026-08-14", prev=100.0, chg=0.0, updated=time.time() - 3600)
            _aplicar_trade(TICKER, 110.0)
            e = C._price_cache[TICKER]
        assert e["chg"] == 10.0, e["chg"]
        assert e["fuente"] == "finnhub"
        assert (time.time() - e["updated"]) < 5, "aqui si debe renovarse el reloj"
    finally:
        _limpiar()


def test_se_respeta_un_no_lo_se_previo_aunque_la_fecha_cuadre():
    """Si quien puso `prev` ya dijo que no servía de referencia, el tick no lo
    convierte en un porcentaje (protección que ya existía, se mantiene)."""
    try:
        with patch.object(C, "_is_market_open", return_value=True), \
             patch.object(C, "_ultima_sesion_esperada", return_value=_fecha("2026-08-14")):
            C._price_cache[TICKER] = {
                "ticker": TICKER, "price": 100.0, "prev": 100.0, "chg": None,
                "prev_fecha": "2026-08-14", "sin_datos_hoy": True,
                "updated": time.time(),
            }
            _aplicar_trade(TICKER, 110.0)
            e = C._price_cache[TICKER]
        assert e["chg"] is None
    finally:
        _limpiar()


def test_sin_prev_el_tick_se_descarta_entero():
    try:
        C._price_cache[TICKER] = {"ticker": TICKER, "price": 0, "prev": None,
                                  "updated": time.time()}
        assert _aplicar_trade(TICKER, 110.0) is False
    finally:
        _limpiar()


# ── La referencia tiene que traer su fecha ───────────────────────────────────

def test_toda_entrada_del_cache_declara_de_que_sesion_es_su_referencia():
    """Sin esto no hay nada que validar: era imposible distinguir el cierre de
    ayer del de hace tres sesiones."""
    import inspect
    fuente = inspect.getsource(C._fetch_price_single)
    entradas = fuente.count('"ticker": ticker')
    con_fecha = fuente.count('"prev_fecha"')
    assert con_fecha >= entradas, \
        f"{entradas} entradas de cache y solo {con_fecha} declaran prev_fecha"


def _fecha(iso):
    from datetime import datetime
    return datetime.strptime(iso, "%Y-%m-%d").date()
