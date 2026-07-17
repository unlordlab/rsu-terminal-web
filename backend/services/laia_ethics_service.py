"""
Histórico de veredictos del Comité de Ética (Laia) — solo lectura, sin
cola de aprobación (a diferencia de Tesis/Academy). Laia no pide permiso
para señalar algo; esto es solo el registro de lo que ya dijo, para poder
consultarlo con el tiempo en vez de que se pierda en el scroll de
Telegram. Ver conversación 17/07/2026.
"""
import sqlite3
import os
import time
import json

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'laia_ethics.db')


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS laia_verdicts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            texto           TEXT NOT NULL,
            hype_hallazgos  TEXT,
            sesgo_detectado INTEGER,
            sesgo_detalle   TEXT,
            tesis_auditadas INTEGER,
            enviado_ok      INTEGER,
            created_at      REAL NOT NULL
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_laia_verdicts_created ON laia_verdicts(created_at)')
    conn.commit()
    conn.close()


_init_db()


def guardar_veredicto(texto: str, hype_result: dict, sesgo_result: dict,
                       tesis_auditadas: int, enviado_ok: bool) -> int:
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO laia_verdicts (texto, hype_hallazgos, sesgo_detectado, sesgo_detalle,
                                       tesis_auditadas, enviado_ok, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (texto, json.dumps(hype_result.get("hallazgos", []), ensure_ascii=False),
         1 if sesgo_result.get("sesgo_detectado") else 0,
         json.dumps(sesgo_result, ensure_ascii=False),
         tesis_auditadas, 1 if enviado_ok else 0, time.time())
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_veredictos(limit: int = 30) -> list:
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM laia_verdicts ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]