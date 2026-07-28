"""
Servicio de progreso de Academy (lecciones leídas + quizzes superados).

Guarda en users.db, mismo patrón que watchlist_service.py: tablas propias
dentro de la base de usuarios, sin ORM nuevo. Academy es GRATUITA para
cualquier usuario registrado — el router se registra con `rl`, no con `paid`.

Por qué existe: hasta ahora la barra de progreso de cada módulo estaba
escrita a mano como `width:0%` en la plantilla (frontend/pages/academy.js).
No es que el cálculo saliera mal: es que no había ningún cálculo ni ninguna
persistencia detrás. Una barra permanentemente vacía en las 26 tarjetas
comunica abandono, no progreso — y el progreso es la mecánica de retención
más básica de una plataforma educativa.

Criterio de "lección leída": el frontend la marca cuando el usuario llega al
FINAL del contenido (un centinela al pie de la lección entra en el viewport),
no al abrirla. Marcar al abrir habría inflado la barra con lecciones que
nadie llegó a leer — el mismo pecado que los fallbacks que fabricaban datos
plausibles, ya eliminados del resto de la terminal.
"""
import os
import re
import sqlite3
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.db')

# Clave de lección: "<modulo>-<indice>", p.ej. "12-3". El backend no conoce el
# catálogo de lecciones (vive entero en el frontend), así que valida el
# FORMATO, no la existencia — mismo criterio que el regex de ticker en
# routers/watchlist.py: cerrar la puerta a basura arbitraria en la base.
LESSON_KEY_RE = re.compile(r"^\d{1,3}-\d{1,3}$")

MAX_MODULE_ID = 999


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS academy_progress (
            user_id      INTEGER NOT NULL,
            lesson_key   TEXT NOT NULL,       -- "<modulo>-<indice>", p.ej. "12-3"
            completed_at TEXT NOT NULL,
            PRIMARY KEY (user_id, lesson_key)
        )
    ''')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS academy_quiz (
            user_id      INTEGER NOT NULL,
            module_id    INTEGER NOT NULL,
            score        INTEGER NOT NULL,    -- aciertos a la primera
            total        INTEGER NOT NULL,
            completed_at TEXT NOT NULL,
            PRIMARY KEY (user_id, module_id)
        )
    ''')
    conn.commit()
    conn.close()


def es_lesson_key_valida(lesson_key: str) -> bool:
    return bool(LESSON_KEY_RE.match(lesson_key or ""))


def marcar_leccion(user_id: int, lesson_key: str) -> dict:
    """Idempotente: releer una lección ya marcada no duplica ni actualiza la
    fecha (queda la primera vez que se completó, que es el dato honesto)."""
    conn = _conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO academy_progress (user_id, lesson_key, completed_at) VALUES (?, ?, ?)",
            (user_id, lesson_key, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        return {"ok": True, "lesson_key": lesson_key}
    finally:
        conn.close()


def marcar_quiz(user_id: int, module_id: int, score: int, total: int) -> dict:
    """Guarda el mejor resultado: si el usuario repite el quiz y saca menos,
    no se pisa el anterior (repetir para practicar no debe penalizar)."""
    ahora = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    try:
        fila = conn.execute(
            "SELECT score FROM academy_quiz WHERE user_id = ? AND module_id = ?",
            (user_id, module_id)
        ).fetchone()
        if fila is None:
            conn.execute(
                "INSERT INTO academy_quiz (user_id, module_id, score, total, completed_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, module_id, score, total, ahora)
            )
        elif score > fila["score"]:
            conn.execute(
                "UPDATE academy_quiz SET score = ?, total = ?, completed_at = ? WHERE user_id = ? AND module_id = ?",
                (score, total, ahora, user_id, module_id)
            )
        conn.commit()
        return {"ok": True, "module_id": module_id}
    finally:
        conn.close()


def obtener_progreso(user_id: int) -> dict:
    """{lessons: ["0-1", ...], quizzes: {"12": {score, total}}} — el frontend
    calcula el porcentaje por módulo contra las lecciones que EXISTEN de
    verdad (academy_manifest.js), no contra un total declarado a mano."""
    conn = _conn()
    try:
        lecciones = [
            r["lesson_key"] for r in conn.execute(
                "SELECT lesson_key FROM academy_progress WHERE user_id = ?", (user_id,)
            ).fetchall()
        ]
        quizzes = {
            str(r["module_id"]): {"score": r["score"], "total": r["total"]}
            for r in conn.execute(
                "SELECT module_id, score, total FROM academy_quiz WHERE user_id = ?", (user_id,)
            ).fetchall()
        }
        return {"ok": True, "lessons": lecciones, "quizzes": quizzes}
    finally:
        conn.close()


def reiniciar_progreso(user_id: int) -> dict:
    """Borra el progreso del usuario (lecciones y quizzes). Existe para que
    el progreso sea reversible desde la propia interfaz — sin esto, una
    lección marcada por error se queda marcada para siempre."""
    conn = _conn()
    try:
        conn.execute("DELETE FROM academy_progress WHERE user_id = ?", (user_id,))
        conn.execute("DELETE FROM academy_quiz WHERE user_id = ?", (user_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


init_db()
