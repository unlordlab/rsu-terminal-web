"""Configuración común de la suite: la red queda cerrada durante los tests.

POR QUÉ EXISTE ESTE FICHERO

Los tests corrían sin ningún `conftest.py` a propósito (sesión 18/07/2026):
no hacía falta, cada fichero se apaña con su `sys.path.insert`. Lo que ha
cambiado es que se descubrió que la suite SÍ salía a internet, y eso rompía
el CI.

El síntoma: los workflows de GitHub fallaban repetidamente con una duración
clavada de ~15m51s -- la firma de un tiempo agotado, no de un test que falla,
porque un test que falla lo hace en segundos. En local la suite tardaba 8
segundos y pasaba, así que era invisible desde aquí.

La causa, medida bloqueando los sockets y anotando quién intentaba conectar:
`test_research_llamadas_red.py::test_un_ticker_invalido_no_repite_el_pipeline_entero_en_cada_peticion`
hacía **8 conexiones salientes reales**. Ese test parchea `_get_yfinance`,
pero `get_research()` alcanza otras fuentes de red que no estaban parcheadas.
En un portátil eso pasa desapercibido —fallan rápido o responden— pero en un
runner de GitHub, con una IP compartida que los proveedores limitan
agresivamente, esas llamadas se quedan esperando hasta agotar el tiempo del
job.

QUÉ HACE

Bloquea cualquier conexión que no sea a localhost. No es solo un parche para
ese test: es una garantía de que la suite mide el CÓDIGO y no el estado de
internet. Un test que dependa de la red da falsos rojos cuando el proveedor
tiene un mal día, y falsos verdes cuando devuelve basura -- las dos cosas
peores que no tener test.

Comprobado antes de activarlo: los 157 tests pasan con la red cerrada, así que
ninguno dependía de verdad de ella para dar su resultado.

SI ALGÚN DÍA HACE FALTA UN TEST CON RED DE VERDAD

Se marca con `@pytest.mark.red` y este fichero lo deja pasar. Pero piénsalo
dos veces: casi siempre lo que se quiere es un mock, y lo que se gana con una
llamada real es un test que falla por motivos ajenos al código.
"""
import socket

import pytest

_PERMITIDOS = {"127.0.0.1", "localhost", "::1", ""}
_connect_real = socket.socket.connect
_connect_ex_real = socket.socket.connect_ex


def _es_local(direccion) -> bool:
    host = direccion[0] if isinstance(direccion, tuple) else str(direccion)
    return host in _PERMITIDOS


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "red: el test necesita salir a internet de verdad (evítalo salvo que no haya alternativa)",
    )


@pytest.fixture(autouse=True)
def _sin_red(request):
    """Cierra la red durante cada test, salvo que lleve la marca `red`."""
    if request.node.get_closest_marker("red"):
        yield
        return

    def _bloquear(self, direccion, *args, **kwargs):
        if _es_local(direccion):
            return _connect_real(self, direccion, *args, **kwargs)
        host = direccion[0] if isinstance(direccion, tuple) else direccion
        raise OSError(
            f"Este test ha intentado conectar a {host}. La suite corre sin red "
            f"a propósito (ver backend/tests/conftest.py): usa un mock, o marca "
            f"el test con @pytest.mark.red si de verdad no hay otra forma."
        )

    def _bloquear_ex(self, direccion, *args, **kwargs):
        if _es_local(direccion):
            return _connect_ex_real(self, direccion, *args, **kwargs)
        return 1   # "falló", que es lo que un socket bloqueado debe aparentar

    socket.socket.connect = _bloquear
    socket.socket.connect_ex = _bloquear_ex
    try:
        yield
    finally:
        socket.socket.connect = _connect_real
        socket.socket.connect_ex = _connect_ex_real
