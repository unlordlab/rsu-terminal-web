"""
Test de la sesión por cookie httpOnly (hallazgo #2 de Paginas Contenido).

Fija dos cosas distintas, y conviene no confundirlas:

1) LO QUE SE ARREGLÓ DE SEGURIDAD. El token de sesión ya no viaja en el
   cuerpo de /login ni acaba en localStorage: va en una cookie httpOnly,
   que JavaScript no puede leer. Si alguien vuelve a devolver el token en
   el JSON "por comodidad", el primer test falla -- y esa comodidad es
   exactamente por donde volvería a colarse en localStorage.

2) LO QUE SE ARREGLÓ DE FUNCIONAMIENTO, que era peor y no estaba en la
   auditoría: "mantener sesión" estaba ROTO. setSession(remember=true)
   guardaba el token solo en localStorage, pero 41 lecturas repartidas por
   18 ficheros del frontend leían solo sessionStorage -> recibían null ->
   petición sin cabecera -> 403 -> el interceptor lo tomaba por sesión
   caducada, borraba el token y mandaba a /login?expired=1. Marcar la
   casilla te expulsaba al abrir cualquier módulo. Verificado en navegador
   contra el backend real antes de tocar nada (08/08/2026).

La cabecera Bearer sigue valiendo a propósito, y por dos motivos reales:
los tokens de servicio (daily_briefing.py, el disparador del scan de
Options Flow) no tienen navegador donde guardar una cookie, y las sesiones
ya abiertas el día del despliegue no deben cortarse.

Uso:
    cd backend
    python -m pytest tests/test_cookie_sesion.py -v
"""
import sys, os, uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from auth import COOKIE_NAME, create_token  # noqa: E402
from services import users_service  # noqa: E402

PROTEGIDO = "/api/v1/research/AAPL"


@pytest.fixture
def usuario():
    """Cuenta desechable, con su propio email cada vez -- no se reutiliza
    ninguna cuenta real de users.db ni se deja basura con un nombre fijo
    que colisione entre ejecuciones.

    Se vacía además el contador anti fuerza-bruta de /login (5 intentos por
    IP cada 15 min, middleware/rate_limit.py): estos tests hacen más de 5
    logins seguidos desde la misma IP, así que sin esto los últimos
    recibirían un 429 y fallarían por el límite, no por lo que miden.
    Detectado al pasar el fichero entero -- aislados pasaban todos."""
    from middleware.rate_limit import _store
    _store.clear()
    email = f"test-cookie-{uuid.uuid4().hex[:10]}@local.test"
    password = "probando1234"
    users_service.create_user(email, password)
    try:
        yield {"email": email, "password": password}
    finally:
        # Se borra al terminar, pase lo que pase. Sin esto cada ejecución
        # de este fichero dejaría 9 cuentas muertas en users.db, y la tabla
        # de usuarios acabaría siendo mayormente basura de tests -- que es
        # exactamente lo que ya pasó antes de añadir esta limpieza.
        import sqlite3
        conn = sqlite3.connect(users_service.DB_PATH)
        try:
            conn.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
        finally:
            conn.close()


def _login(client, usuario, remember=False):
    return client.post("/api/v1/auth/login", json={
        "email": usuario["email"], "password": usuario["password"], "remember": remember,
    })


def test_el_login_no_devuelve_el_token_en_el_cuerpo(usuario):
    """Si vuelve a salir en el JSON, vuelve a acabar en localStorage."""
    client = TestClient(app)
    r = _login(client, usuario)
    assert r.status_code == 200
    assert "access_token" not in r.json(), "El token debe ir solo en la cookie httpOnly"


def test_la_cookie_es_httponly_y_samesite_lax(usuario):
    """httpOnly es lo que impide que un XSS lea la sesión. SameSite=lax es
    lo que cubre el CSRF ahora que la credencial se envía sola."""
    client = TestClient(app)
    cabecera = _login(client, usuario).headers["set-cookie"].lower()
    assert COOKIE_NAME in cabecera
    assert "httponly" in cabecera
    assert "samesite=lax" in cabecera


def test_mantener_sesion_marcado_no_expulsa_al_abrir_un_modulo(usuario):
    """El bug real: con remember=True la sesión se perdía en cuanto se
    tocaba cualquier módulo. Aquí tiene que responder 200."""
    client = TestClient(app)
    _login(client, usuario, remember=True)
    assert client.get(PROTEGIDO).status_code == 200


def test_mantener_sesion_marcado_da_una_cookie_persistente(usuario):
    """Marcada dura lo mismo que el token que lleva dentro (30 días); sin
    marcar es cookie de sesión y el navegador la tira al cerrarse. Antes no
    había tal correspondencia y era la raíz del fallo."""
    client = TestClient(app)
    con    = _login(client, usuario, remember=True).headers["set-cookie"].lower()
    client.cookies.clear()
    sin    = _login(client, usuario, remember=False).headers["set-cookie"].lower()
    assert "max-age" in con, "Con 'mantener sesión' la cookie debe sobrevivir al cierre del navegador"
    assert "max-age" not in sin, "Sin marcar debe ser cookie de sesión"


def test_sin_credenciales_no_se_entra(usuario):
    client = TestClient(app)
    assert client.get(PROTEGIDO).status_code == 401


def test_la_cabecera_bearer_sigue_valiendo_sin_cookie(usuario):
    """Los tokens de servicio (daily_briefing, scan de Options Flow) no
    tienen navegador, y las sesiones abiertas antes del despliegue tampoco
    tienen cookie todavía: ninguna de las dos puede quedarse fuera."""
    client = TestClient(app)
    u = users_service.get_user_by_email(usuario["email"])
    token = create_token({"sub": u["email"], "tier": u["tier"], "tv": u["token_version"]})
    r = client.get(PROTEGIDO, headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_la_cookie_manda_sobre_una_cabecera_bearer_invalida(usuario):
    """Tras el cambio puede quedar un token viejo en el navegador de quien
    ya usaba la terminal. Un login nuevo tiene que ganarle siempre, no
    quedar bloqueado por ese resto."""
    client = TestClient(app)
    _login(client, usuario, remember=True)
    r = client.get(PROTEGIDO, headers={"Authorization": "Bearer token.completamente.invalido"})
    assert r.status_code == 200


def test_logout_deja_la_sesion_inservible(usuario):
    client = TestClient(app)
    _login(client, usuario, remember=True)
    assert client.get(PROTEGIDO).status_code == 200
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.get(PROTEGIDO).status_code == 401


def test_se_puede_cerrar_sesion_con_el_token_ya_caducado(usuario):
    """/logout no pasa por verify_token a propósito: si exigiera un token
    válido, una sesión ya caducada no podría limpiar su propia cookie y se
    quedaría pegada hasta expirar sola."""
    client = TestClient(app)
    client.cookies.set(COOKIE_NAME, "token.basura.caducado")
    assert client.post("/api/v1/auth/logout").status_code == 200
