"""
Smoke test de arranque: confirma que la app FastAPI se importa y arranca
sin excepciones (imports rotos, mounts de estáticos fallidos, middleware
mal configurado), y que el middleware de auth sigue enganchado en un
endpoint protegido representativo.

TestClient(app) SIN "with" no dispara el lifespan (Starlette solo lo
ejecuta dentro del context manager) -- evita arrancar las 9 tareas asyncio
de fondo (websockets, polling loops) que main.py arranca en producción,
así que este test no toca red ni DB real.

Uso:
    cd backend
    python -m pytest tests/test_smoke.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402


def test_health_responde_ok_sin_arrancar_tareas_de_fondo():
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_endpoint_protegido_sin_credenciales_devuelve_401():
    """Confirma que el middleware de auth sigue enganchado -- si un
    refactor futuro quita por error el Depends(verify_token) de un
    router, este endpoint pasaría de 401 a 200 y el test fallaría.
    /research/AAPL elegido porque su única dependencia extra es
    rate_limit (en memoria, sin efectos colaterales).

    Antes esto daba 403, y no porque nadie lo decidiera: era el
    comportamiento por defecto de HTTPBearer(auto_error=True), que
    responde 403 cuando falta la cabecera. Con el paso a cookie httpOnly
    la comprobación es nuestra (falta cookie Y falta cabecera) y devuelve
    el 401 que corresponde a "no autenticado". El interceptor de
    core/router.js ya trataba los dos códigos igual, así que el cambio no
    altera lo que ve el usuario."""
    client = TestClient(app)
    r = client.get("/api/v1/research/AAPL")
    assert r.status_code == 401


def test_una_ruta_de_api_inexistente_da_404_y_no_un_200_con_null():
    """El catch-all de main.py sirve index.html para las rutas de la SPA,
    pero para las que empiezan por api/ terminaba sin `return` -- y FastAPI
    serializa ese None implícito como un 200 con cuerpo `null`. El efecto:
    un fetch contra una URL mal escrita, o contra un endpoint retirado, no
    fallaba nunca de forma visible; el módulo se quedaba vacío en silencio.
    Ver auditoría de Options Flow #27 (encontrado ahí, afecta a toda la
    API)."""
    client = TestClient(app)
    for ruta in ["/api/v1/no/existe", "/api/v1/options/flow", "/api/v1/options/save"]:
        r = client.get(ruta)
        assert r.status_code == 404, f"{ruta} devolvió {r.status_code}"
        assert r.json() != None  # noqa: E711 -- el cuerpo `null` es justo el bug


def test_las_rutas_de_la_spa_siguen_sirviendo_el_html():
    """La otra mitad del cambio anterior: cerrar las rutas de API no puede
    romper la navegación de la SPA, que depende de que cualquier ruta que
    NO sea api/ devuelva index.html para que el router del frontend la
    resuelva."""
    client = TestClient(app)
    for ruta in ["/", "/options", "/research", "/cartera"]:
        r = client.get(ruta)
        assert r.status_code == 200, f"{ruta} devolvió {r.status_code}"
        assert "text/html" in r.headers.get("content-type", "")
