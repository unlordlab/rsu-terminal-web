"""
Tests del versionado del descargo de responsabilidad (28/07/2026).

Contexto: antes solo se guardaba `disclaimer_accepted_at` (una fecha). Al
cambiar el texto del descargo, los usuarios que ya lo habían aceptado NO
volvían a verlo: quedaba constancia de que aceptaron algo, pero no de qué.
Con condiciones de pago/cancelación/reembolsos a la vuelta de la esquina,
eso no se sostiene. Ver auditoría de páginas de contenido 21/07/2026 (#14).

Lo que protegen estos tests:
  1. Aceptar guarda la versión VIGENTE, no solo la fecha.
  2. Subir DISCLAIMER_VERSION invalida las aceptaciones anteriores (el
     modal vuelve a salir) sin borrar la constancia de la anterior.
  3. Se distingue "aceptó una versión vieja" de "no aceptó nunca" — el
     modal se lo explica al primero, que lleva meses usando la terminal.
  4. La migración etiqueta como v1 a quien aceptó antes de que existiera
     el versionado, para NO forzar una re-aceptación por un cambio
     puramente técnico (el texto no cambió).

Uso:
    cd backend
    python -m pytest tests/test_disclaimer_version.py -v
"""
import os
import sys
import sqlite3
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services import users_service  # noqa: E402


@pytest.fixture
def db_temporal(monkeypatch):
    fd, ruta = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(users_service, "DB_PATH", ruta)
    users_service.init_db()
    yield ruta
    try:
        os.remove(ruta)
    except OSError:
        pass


def _crear(email="u@rsu.local"):
    users_service.create_user(email, "contraseña-de-prueba")
    return users_service.get_user_by_email(email)


def test_aceptar_guarda_la_version_vigente(db_temporal):
    user = _crear()
    assert users_service.disclaimer_al_dia(user) is False

    users_service.accept_disclaimer(user["id"])
    user = users_service.get_user_by_email(user["email"])

    assert user["disclaimer_version"] == users_service.DISCLAIMER_VERSION
    assert user["disclaimer_accepted_at"], "Se sigue guardando también la fecha"
    assert users_service.disclaimer_al_dia(user) is True


def test_subir_la_version_vuelve_a_pedir_la_aceptacion(db_temporal, monkeypatch):
    user = _crear()
    users_service.accept_disclaimer(user["id"])
    user = users_service.get_user_by_email(user["email"])
    assert users_service.disclaimer_al_dia(user) is True

    # El texto del descargo cambia -> sube la versión
    monkeypatch.setattr(users_service, "DISCLAIMER_VERSION", 2)

    assert users_service.disclaimer_al_dia(user) is False, \
        "Con el texto cambiado, la aceptación anterior no vale para la nueva versión"
    assert users_service.disclaimer_desactualizado(user) is True, \
        "Debe distinguirse de quien no aceptó nunca (el modal se lo explica)"
    assert user["disclaimer_version"] == 1, \
        "No se borra la constancia de qué versión firmó antes"


def test_quien_no_acepto_nunca_no_es_desactualizado(db_temporal):
    user = _crear()
    assert users_service.disclaimer_al_dia(user) is False
    assert users_service.disclaimer_desactualizado(user) is False, \
        "'Nunca aceptó' no es 'aceptó una versión vieja': el modal no debe decirle que el texto cambió"


def test_migracion_etiqueta_como_v1_a_quien_acepto_antes_del_versionado(db_temporal):
    user = _crear()
    # Simula el estado ANTERIOR a esta sesión: fecha de aceptación, sin versión.
    conn = sqlite3.connect(db_temporal)
    conn.execute(
        "UPDATE users SET disclaimer_accepted_at = '2026-01-15T10:00:00+00:00', disclaimer_version = NULL WHERE id = ?",
        (user["id"],)
    )
    conn.commit()
    conn.close()

    users_service.init_db()   # idempotente: vuelve a correr la migración

    user = users_service.get_user_by_email(user["email"])
    assert user["disclaimer_version"] == 1
    assert users_service.disclaimer_al_dia(user) is True, \
        "El texto no cambió: no se debe forzar una re-aceptación por un cambio puramente técnico"


def test_la_migracion_no_inventa_aceptaciones(db_temporal):
    """Quien nunca aceptó no debe salir aceptado tras la migración."""
    user = _crear()
    users_service.init_db()
    user = users_service.get_user_by_email(user["email"])
    assert user["disclaimer_accepted_at"] is None
    assert user["disclaimer_version"] is None
    assert users_service.disclaimer_al_dia(user) is False


def test_disclaimer_al_dia_tolera_usuario_inexistente():
    # /me llama a esto con None si el token apunta a un usuario borrado.
    assert users_service.disclaimer_al_dia(None) is False
    assert users_service.disclaimer_desactualizado(None) is False
