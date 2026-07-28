"""
Tests del progreso de Academy (services/academy_service.py, 28/07/2026).

Contexto: hasta esta sesión la barra de progreso de cada módulo estaba
escrita a mano como `width:0%` en la plantilla — no había cálculo ni
persistencia detrás. Estos tests cubren las tres decisiones de diseño que
más fácil sería romper en un refactor futuro:

  1. Marcar una lección es IDEMPOTENTE (releerla no duplica ni reescribe la
     fecha: queda la primera vez que se completó).
  2. El quiz guarda el MEJOR resultado — repetirlo para practicar y sacar
     menos no debe empeorar lo ya conseguido.
  3. La clave de lección se valida por FORMATO (el backend no conoce el
     catálogo, que vive en el frontend), igual que el regex de ticker de
     routers/watchlist.py — para que no entre basura arbitraria en la base.

Uso:
    cd backend
    python -m pytest tests/test_academy_progress.py -v
"""
import os
import sys
import sqlite3
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services import academy_service  # noqa: E402


@pytest.fixture
def db_temporal(monkeypatch):
    """Base aparte por test: no se toca users.db real."""
    fd, ruta = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setattr(academy_service, "DB_PATH", ruta)
    academy_service.init_db()
    yield ruta
    try:
        os.remove(ruta)
    except OSError:
        pass


def test_marcar_leccion_es_idempotente(db_temporal):
    academy_service.marcar_leccion(1, "0-1")
    primera = sqlite3.connect(db_temporal).execute(
        "SELECT completed_at FROM academy_progress WHERE user_id=1 AND lesson_key='0-1'"
    ).fetchone()[0]

    academy_service.marcar_leccion(1, "0-1")
    filas = sqlite3.connect(db_temporal).execute(
        "SELECT completed_at FROM academy_progress WHERE user_id=1 AND lesson_key='0-1'"
    ).fetchall()

    assert len(filas) == 1, "Releer una lección no debe crear una segunda fila"
    assert filas[0][0] == primera, "Debe conservarse la PRIMERA vez que se completó"


def test_progreso_aislado_por_usuario(db_temporal):
    academy_service.marcar_leccion(1, "0-1")
    academy_service.marcar_leccion(2, "5-3")

    assert academy_service.obtener_progreso(1)["lessons"] == ["0-1"]
    assert academy_service.obtener_progreso(2)["lessons"] == ["5-3"]


def test_quiz_conserva_el_mejor_resultado(db_temporal):
    academy_service.marcar_quiz(1, 12, score=4, total=5)
    academy_service.marcar_quiz(1, 12, score=2, total=5)   # repetición peor

    quizzes = academy_service.obtener_progreso(1)["quizzes"]
    assert quizzes["12"]["score"] == 4, "Repetir un quiz y sacar menos no debe pisar el mejor resultado"

    academy_service.marcar_quiz(1, 12, score=5, total=5)   # repetición mejor
    assert academy_service.obtener_progreso(1)["quizzes"]["12"]["score"] == 5


def test_claves_de_leccion_validas():
    for clave in ("0-1", "12-3", "25-4", "999-999"):
        assert academy_service.es_lesson_key_valida(clave), clave


def test_claves_de_leccion_invalidas():
    # El vector real: una clave con HTML/comillas acabaría interpolada en el
    # frontend. Mismo criterio que _validar_ticker en routers/watchlist.py.
    for clave in ("<script>alert(1)</script>", "0-1'; DROP TABLE academy_progress;--",
                  "12", "abc-def", "", "0-", "-1", "0 - 1", "0-1 "):
        assert not academy_service.es_lesson_key_valida(clave), clave


def test_reiniciar_borra_lecciones_y_quizzes_solo_del_usuario(db_temporal):
    academy_service.marcar_leccion(1, "0-1")
    academy_service.marcar_quiz(1, 0, 3, 4)
    academy_service.marcar_leccion(2, "0-1")

    academy_service.reiniciar_progreso(1)

    p1 = academy_service.obtener_progreso(1)
    assert p1["lessons"] == [] and p1["quizzes"] == {}
    assert academy_service.obtener_progreso(2)["lessons"] == ["0-1"], "No debe tocar a otros usuarios"
