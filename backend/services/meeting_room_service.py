"""
meeting_room_service.py — buzón de instrucciones de Marc a los agentes
(Gael, Elia, Laia). No es un chat en vivo: cada agente revisa sus
mensajes pendientes la próxima vez que se ejecuta (vía cron), actúa
según lo que se le pida, y deja una respuesta en el mismo hilo.
"""
import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'meeting_room.db')

DESTINATARIOS_VALIDOS = {"gael", "elia", "laia", "todos"}


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS meeting_room (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            autor         TEXT NOT NULL,       -- 'marc' | 'gael' | 'elia' | 'laia'
            destinatario  TEXT,                 -- solo en mensajes de marc: gael/elia/laia/todos
            mensaje       TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'pending',  -- pending | procesado
            created_at    REAL NOT NULL,
            procesado_en  REAL
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_meeting_room_status ON meeting_room(status)')
    conn.commit()
    conn.close()


_init_db()


def enviar_mensaje(destinatario: str, mensaje: str, autor: str = "marc") -> int:
    destinatario = (destinatario or "").lower().strip()
    if autor == "marc" and destinatario not in DESTINATARIOS_VALIDOS:
        raise ValueError(f"Destinatario no válido: {destinatario!r} (debe ser gael, elia, laia o todos)")
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO meeting_room (autor, destinatario, mensaje, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (autor, destinatario, mensaje.strip(), time.time())
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_historial(limit: int = 100) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM meeting_room ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in reversed(rows)]  # orden cronológico ascendente, como un chat


def get_pendientes_para(agente: str) -> list:
    """Mensajes de Marc dirigidos a este agente (o a 'todos') todavía sin procesar."""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM meeting_room WHERE autor = 'marc' AND status = 'pending' "
        "AND (destinatario = ? OR destinatario = 'todos') ORDER BY created_at ASC",
        (agente,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def marcar_procesado(msg_id: int):
    conn = _conn()
    conn.execute(
        "UPDATE meeting_room SET status = 'procesado', procesado_en = ? WHERE id = ?",
        (time.time(), msg_id)
    )
    conn.commit()
    conn.close()


def responder(agente: str, mensaje: str) -> int:
    """El agente deja una respuesta o confirmación en el mismo hilo."""
    conn = _conn()
    cur = conn.execute(
        "INSERT INTO meeting_room (autor, destinatario, mensaje, status, created_at) VALUES (?, NULL, ?, 'procesado', ?)",
        (agente, mensaje.strip(), time.time())
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id