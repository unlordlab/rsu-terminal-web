"""
`/health` dice qué commit está corriendo.

POR QUÉ EXISTE ESTO. Hasta el 14/08/2026 no había forma de saber qué código
había desplegado en el servidor. El «HOY %» de Cartera se reportó roto cuatro
veces y en DOS de ellas el cálculo en `main` ya era correcto: lo que corría era
una versión anterior. Cada una de esas dos veces costó una sesión entera de
depuración —medir contra datos reales, releer las ramas, reproducir el fallo—
para acabar descubriendo que el código bueno nunca había llegado allí.

El `git pull` del despliegue ya avisa cuando no trae nada nuevo, pero eso no
dice nada sobre lo que hay DENTRO del contenedor: la imagen puede ser vieja
aunque el disco esté al día.

Con esto, «¿está desplegado el arreglo?» pasa de costar una sesión a costar una
petición.

LO QUE FIJA ESTE FICHERO: que sin fichero de versión se diga «desconocida» en
vez de inventarse un número o reventar el endpoint. Un /health caído es peor
que un /health sin versión: lo usan los chequeos de Docker.

Uso:
    cd backend
    python -m pytest tests/test_version_desplegada.py -v
"""
import sys, os, importlib

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import main  # noqa: E402

RUTA_VERSION = os.path.join(os.path.dirname(main.__file__), "VERSION")


@pytest.fixture(autouse=True)
def sin_fichero():
    previo = None
    if os.path.exists(RUTA_VERSION):
        with open(RUTA_VERSION, encoding='utf-8') as f:
            previo = f.read()
        os.remove(RUTA_VERSION)
    yield
    if previo is not None:
        with open(RUTA_VERSION, 'w', encoding='utf-8') as f:
            f.write(previo)
    elif os.path.exists(RUTA_VERSION):
        os.remove(RUTA_VERSION)


def _escribir(contenido):
    with open(RUTA_VERSION, 'w', encoding='utf-8') as f:
        f.write(contenido)


def test_lee_el_commit_y_la_fecha_que_sella_el_despliegue():
    """Formato exacto que escribe deploy.sh: commit corto y fecha UTC."""
    _escribir("a1b2c3d\n2026-08-14T14:05:00Z\n")
    v = main._version_desplegada()
    assert v["commit"] == "a1b2c3d"
    assert v["desplegado"] == "2026-08-14T14:05:00Z"


def test_sin_fichero_dice_desconocida_y_no_se_inventa_nada():
    """Pasa al ejecutar en local, fuera de un despliegue. Decir «desconocida»
    es correcto; devolver un commit falso sería peor que no tener versión."""
    v = main._version_desplegada()
    assert v["commit"] == "desconocida"
    assert v["desplegado"] is None


def test_un_fichero_vacio_o_corrupto_no_tumba_el_endpoint():
    """/health lo usan los chequeos de Docker: si revienta, el contenedor se
    marca como caído por no poder leer un fichero informativo."""
    _escribir("")
    assert main._version_desplegada()["commit"] == "desconocida"
    _escribir("basura sin formato")
    assert main._version_desplegada()["commit"] == "basura sin formato"


def test_health_devuelve_la_version_ademas_del_estado():
    """El contrato que consumen los chequeos externos no puede romperse: los
    campos de siempre siguen ahí, la versión se AÑADE."""
    from fastapi.testclient import TestClient
    _escribir("deadbee\n2026-08-14T14:05:00Z\n")
    importlib.reload(main)
    try:
        r = TestClient(main.app).get("/health")
        assert r.status_code == 200
        cuerpo = r.json()
        assert cuerpo["status"] == "ok"
        assert "app" in cuerpo
        assert cuerpo["commit"] == "deadbee"
    finally:
        importlib.reload(main)
