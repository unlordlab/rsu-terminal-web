"""
Servicio de revisiones/propuestas de Academy generadas por Elia — cola de
aprobación igual que Tesis/Bull, pero el "publicar" final lo hace Marc a
mano (copiar el bloque ya listo dentro de academy_lessons.js y subirlo por
git), porque el contenido de Academy vive en código fuente, no en base de
datos. Ver conversación 17/07/2026.
"""
import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'academy_review.db')


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS academy_review (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo         TEXT NOT NULL,   -- 'revision' | 'nueva_leccion'
            modulo_id    INTEGER,
            leccion_ref  TEXT,            -- ej. '0-1', solo para revisiones
            titulo       TEXT NOT NULL,
            resumen      TEXT,            -- explicación en prosa de qué propone y por qué
            bloque_js    TEXT NOT NULL,   -- el objeto listo para pegar en academy_lessons.js
            contenido_json TEXT,           -- JSON valido del mismo contenido, para la vista previa
            status       TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
            fuente       TEXT NOT NULL DEFAULT 'agente_elia',
            created_at   REAL NOT NULL,
            approved_at  REAL,
            approved_by  TEXT
        )
    ''')
    # Migración para tablas creadas antes de añadir esta columna (17/07/2026)
    try:
        conn.execute('ALTER TABLE academy_review ADD COLUMN contenido_json TEXT')
    except sqlite3.OperationalError:
        pass  # ya existe
    conn.execute('CREATE INDEX IF NOT EXISTS idx_academy_review_status ON academy_review(status)')
    conn.commit()
    conn.close()


_init_db()


def create_review(tipo: str, titulo: str, bloque_js: str, resumen: str = "",
                   modulo_id: int = None, leccion_ref: str = None,
                   fuente: str = "agente_elia", status: str = "pending",
                   contenido_json: str = None) -> int:
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO academy_review (tipo, modulo_id, leccion_ref, titulo, resumen, bloque_js, contenido_json, status, fuente, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (tipo, modulo_id, leccion_ref, titulo, resumen, bloque_js, contenido_json, status, fuente, time.time())
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_approved_reviews(limit: int = 20) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM academy_review WHERE status = 'approved' ORDER BY approved_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def unapprove_review(review_id: int) -> bool:
    """Revierte una propuesta ya aprobada de vuelta a 'pending' -- solo
    afecta al registro de seguimiento en el panel de admin, no a
    academy_lessons.js (eso lo pegas tú a mano, así que si ya lo habías
    copiado al código, retirarlo aquí no lo borra de ahí)."""
    conn = _conn()
    cur = conn.execute(
        "UPDATE academy_review SET status = 'pending', approved_at = NULL, approved_by = NULL WHERE id = ? AND status = 'approved'",
        (review_id,)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def get_pending_reviews() -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM academy_review WHERE status = 'pending' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def approve_review(review_id: int, approved_by: str = "admin") -> bool:
    conn = _conn()
    cur = conn.execute(
        "UPDATE academy_review SET status = 'approved', approved_at = ?, approved_by = ? WHERE id = ? AND status = 'pending'",
        (time.time(), approved_by, review_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def reject_review(review_id: int, approved_by: str = "admin") -> bool:
    conn = _conn()
    cur = conn.execute(
        "UPDATE academy_review SET status = 'rejected', approved_at = ?, approved_by = ? WHERE id = ? AND status = 'pending'",
        (time.time(), approved_by, review_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok