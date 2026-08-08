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
