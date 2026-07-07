"""
Servicio de usuarios: registro, autenticación y gestión de tiers.

Tiers soportados (de menor a mayor acceso): free, tier1, tiers ("tier S").
Se guarda en SQLite (users.db), en el mismo estilo que options_flow.db
(services/options_service.py) para no introducir un ORM/ dependencia nueva.
"""
import sqlite3
import os
import bcrypt
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'users.db')

TIER_ORDER  = {"free": 0, "tier1": 1, "tiers": 2}
VALID_TIERS = set(TIER_ORDER.keys())


def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            email         TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            tier          TEXT NOT NULL DEFAULT 'free',
            created_at    TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError):
        return False


def create_user(email: str, password: str) -> dict | None:
    """Crea un usuario nuevo con tier 'free'. Devuelve None si el email ya existe."""
    email = email.strip().lower()
    conn = _conn()
    try:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            return None
        password_hash = _hash_password(password)
        conn.execute(
            "INSERT INTO users (email, password_hash, tier, created_at) VALUES (?, ?, 'free', ?)",
            (email, password_hash, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        row = conn.execute("SELECT id, email, tier FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict | None:
    """Verifica email/password. Devuelve {id, email, tier} o None si no coincide."""
    email = email.strip().lower()
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, tier FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "email": row["email"], "tier": row["tier"]}
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    email = email.strip().lower()
    conn = _conn()
    try:
        row = conn.execute("SELECT id, email, tier FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def reset_password(email: str, new_password: str) -> bool:
    """Fija una contraseña nueva sin necesitar la antigua.

    Pensado para uso de Marc vía /admin/reset-password (protegido con
    ADMIN_KEY) cuando alguien se queda fuera de su cuenta: no hay flujo de
    email de recuperación todavía, así que esto es el stopgap manual.
    """
    if len(new_password) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres")
    email = email.strip().lower()
    conn = _conn()
    try:
        password_hash = _hash_password(new_password)
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, email)
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def set_tier(email: str, tier: str) -> bool:
    if tier not in VALID_TIERS:
        raise ValueError(f"Tier inválido: {tier}. Válidos: {sorted(VALID_TIERS)}")
    email = email.strip().lower()
    conn = _conn()
    try:
        cur = conn.execute("UPDATE users SET tier = ? WHERE email = ?", (tier, email))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def list_users() -> list[dict]:
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT id, email, tier, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


init_db()

