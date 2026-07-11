"""
Servicio de la sección Comunidad — solo gestiona el formulario de feedback
(bugs/sugerencias). El enlace de Discord es estático, no necesita backend.

Guarda en SQLite propio (community.db), mismo patrón que insider_history.db —
sin SMTP configurado en el servidor, no se puede enviar el email directamente
desde el backend, así que el mensaje se persiste aquí y se revisa desde el
panel de Admin. El formulario del frontend también ofrece un enlace mailto
directo como alternativa para quien prefiera escribir desde su propio cliente
de correo.
"""
import sqlite3
import os
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'community.db')

VALID_TYPES = ("bug", "sugerencia", "otro")
MAX_MESSAGE_LEN = 3000


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            user_email  TEXT,
            tipo        TEXT NOT NULL,
            mensaje     TEXT NOT NULL,
            contacto    TEXT,
            created_at  TEXT NOT NULL,
            leido       INTEGER NOT NULL DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def submit_feedback(user_id: int, user_email: str, tipo: str, mensaje: str, contacto: str = "") -> dict:
    tipo = (tipo or "").strip().lower()
    mensaje = (mensaje or "").strip()
    if tipo not in VALID_TYPES:
        return {"ok": False, "error": "Tipo inválido (usa 'bug', 'sugerencia' u 'otro')"}
    if not mensaje:
        return {"ok": False, "error": "El mensaje no puede estar vacío"}
    if len(mensaje) > MAX_MESSAGE_LEN:
        mensaje = mensaje[:MAX_MESSAGE_LEN]

    conn = _conn()
    try:
        cur = conn.execute(
            "INSERT INTO feedback (user_id, user_email, tipo, mensaje, contacto, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, user_email, tipo, mensaje, (contacto or "").strip(), datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        return {"ok": True, "id": cur.lastrowid}
    finally:
        conn.close()


def get_all_feedback() -> dict:
    conn = _conn()
    try:
        rows = conn.execute("SELECT * FROM feedback ORDER BY created_at DESC").fetchall()
        return {"ok": True, "data": [dict(r) for r in rows]}
    finally:
        conn.close()


def mark_feedback_read(feedback_id: int) -> dict:
    conn = _conn()
    try:
        conn.execute("UPDATE feedback SET leido = 1 WHERE id = ?", (feedback_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


init_db()