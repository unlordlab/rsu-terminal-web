"""
Test de la cadena XSS que iba de atacante anónimo al robo de la ADMIN_KEY,
más la validación de estado de tesis. Hallazgos #5, #3, #2 y #4 de la
auditoría de Tesis+Admin.

LA CADENA, demostrada en el navegador el 08/08 antes de arreglarla:
  1. POST /api/v1/analytics/track con section="<img src=x onerror=...>".
     Sin cuenta, sin token, sin nada -- el endpoint es anónimo a propósito.
  2. El texto se guardaba tal cual y salía por /analytics/summary.
  3. El panel de admin lo pintaba sin escapar en la pestaña de Métricas,
     porque barRow() recibía el nombre de sección crudo cuando no estaba en
     el diccionario de etiquetas.
  4. Ejecución de código con la sesión del admin.
  5. Ese código leía sessionStorage.getItem('rsu_admin_key') -- la clave
     maestra, que sirve para cambiar tiers, resetear la contraseña de
     cualquier usuario y emitir tokens de cinco años.

Se cerraron los tres eslabones, y este fichero fija los dos que se pueden
probar desde el backend (el escapado de admin.js es frontend, verificado en
navegador inyectando directamente en la base de datos para saltarse el
primer eslabón).

Uso:
    cd backend
    python -m pytest tests/test_admin_seguridad.py -v
"""
import sys, os, sqlite3, uuid

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from auth import ADMIN_COOKIE_NAME  # noqa: E402
from config import settings  # noqa: E402
from services import tesis_service  # noqa: E402


@pytest.fixture
def client():
    from middleware.rate_limit import _store
    _store.clear()   # el límite de fallos de clave es por IP, ver auth.py
    return TestClient(app)


@pytest.fixture
def admin_key(monkeypatch):
    """Clave conocida para el test, sin depender del .env de quien lo corra
    -- en CI no hay .env y settings.admin_key trae el valor por defecto."""
    clave = "clave-de-test-" + uuid.uuid4().hex[:8]
    monkeypatch.setattr(settings, "admin_key", clave)
    return clave


# ── Eslabón 1: /track no acepta texto libre ──────────────────────────────

@pytest.mark.parametrize("payload", [
    '<img src=x onerror="alert(1)">',
    '<script>fetch("//malo")</script>',
    'javascript:alert(1)',
    '/market"><svg onload=x>',
    'sin barra inicial',
    '/' + 'a' * 60,          # más largo de lo que puede ser una ruta real
])
def test_track_rechaza_secciones_que_no_son_rutas(client, payload):
    r = client.post("/api/v1/analytics/track", json={"section": payload})
    assert r.status_code == 422, f"aceptó {payload!r}"


@pytest.mark.parametrize("seccion", [
    "/", "/market", "/btc-stratum", "/track-record", "/research", "/options",
])
def test_track_sigue_aceptando_las_rutas_reales(client, seccion):
    """La otra mitad: cerrar el hueco no puede cargarse las métricas."""
    r = client.post("/api/v1/analytics/track", json={"section": seccion})
    assert r.status_code == 200, f"rechazó la ruta legítima {seccion!r}"


# ── Eslabón 3: la clave sale de sessionStorage a una cookie httpOnly ─────

def test_la_cookie_de_admin_es_httponly(client, admin_key):
    r = client.post("/api/v1/auth/admin/session", headers={"X-Admin-Key": admin_key})
    assert r.status_code == 200
    cabecera = r.headers["set-cookie"].lower()
    assert ADMIN_COOKIE_NAME in cabecera
    assert "httponly" in cabecera, "sin httpOnly, un XSS vuelve a poder leerla"
    assert "samesite=lax" in cabecera


def test_la_cookie_de_admin_no_sobrevive_al_navegador(client, admin_key):
    """Sin max-age: es cookie de sesión, igual de efímera que el
    sessionStorage al que sustituye. Una clave maestra persistente en disco
    sería un cambio a peor, no a mejor."""
    r = client.post("/api/v1/auth/admin/session", headers={"X-Admin-Key": admin_key})
    assert "max-age" not in r.headers["set-cookie"].lower()


def test_con_la_cookie_ya_no_hace_falta_la_cabecera(client, admin_key):
    client.post("/api/v1/auth/admin/session", headers={"X-Admin-Key": admin_key})
    r = client.get("/api/v1/auth/admin/users")   # sin X-Admin-Key
    assert r.status_code == 200


def test_la_cabecera_sigue_valiendo_para_los_scripts(client, admin_key):
    """El workflow que dispara el escaneo de Options Flow manda
    X-Admin-Key y no tiene navegador donde guardar una cookie."""
    r = client.get("/api/v1/auth/admin/users", headers={"X-Admin-Key": admin_key})
    assert r.status_code == 200


def test_una_clave_incorrecta_no_reparte_cookies(client, admin_key):
    r = client.post("/api/v1/auth/admin/session", headers={"X-Admin-Key": "no-es"})
    assert r.status_code == 401
    assert ADMIN_COOKIE_NAME not in r.headers.get("set-cookie", "")


def test_sin_credenciales_no_se_entra(client, admin_key):
    assert client.get("/api/v1/auth/admin/users").status_code == 401


def test_el_logout_de_admin_invalida_la_cookie(client, admin_key):
    client.post("/api/v1/auth/admin/session", headers={"X-Admin-Key": admin_key})
    assert client.get("/api/v1/auth/admin/users").status_code == 200
    assert client.post("/api/v1/auth/admin/logout").status_code == 200
    assert client.get("/api/v1/auth/admin/users").status_code == 401


# ── #4: una tesis con estado inválido desaparecía sin decir nada ─────────

@pytest.fixture
def tesis_db(monkeypatch, tmp_path):
    """Base propia: sembrar en la real dejaría tesis de prueba sueltas."""
    ruta = str(tmp_path / "tesis.db")
    monkeypatch.setattr(tesis_service, "DB_PATH", ruta)
    tesis_service._init_db()
    return ruta


@pytest.mark.parametrize("estado", ["Approved", "APPROVED", "aprobada", "banana"])
def test_un_estado_desconocido_se_rechaza_en_vez_de_tragarse_la_tesis(tesis_db, estado):
    """Antes se creaba la fila igual, y como todas las consultas filtran por
    igualdad exacta la tesis no salía en la sección pública, ni en la
    bandeja de pendientes, ni se podía aprobar: invisible e inalcanzable,
    sin un solo aviso."""
    with pytest.raises(ValueError):
        tesis_service.create_tesis(ticker="TEST", contenido="x", status=estado)


def test_los_estados_conocidos_siguen_funcionando(tesis_db):
    for estado in ("pending", "approved", "rejected"):
        assert tesis_service.create_tesis(ticker="TEST", contenido="x", status=estado) > 0


def test_un_estado_vacio_cae_a_pendiente_en_vez_de_fallar(tesis_db):
    """Ausencia y error no son lo mismo. Un estado VACÍO es "no me lo han
    dicho", y ahí lo correcto es la cola de pendientes: visible y
    recuperable. Lo que no puede pasar es que un estado EQUIVOCADO se
    acepte, porque ese sí esconde la tesis para siempre."""
    tid = tesis_service.create_tesis(ticker="TEST", contenido="x", status="")
    assert tid > 0
    assert any(t["id"] == tid for t in tesis_service.get_pending_tesis())


def test_un_rating_inventado_no_ensucia_el_filtro_publico(tesis_db):
    """El desplegable de la sección pública se construye con un
    SELECT DISTINCT rating, así que una errata crearía una opción fantasma."""
    with pytest.raises(ValueError):
        tesis_service.create_tesis(ticker="TEST", contenido="x", rating="COMPRAR")
    assert tesis_service.create_tesis(ticker="TEST", contenido="x", rating="buy") > 0
