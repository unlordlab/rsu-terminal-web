"""
Servicio de usuarios: registro, autenticación y gestión de tiers.

Tiers soportados (de menor a mayor acceso): free, tier1, tiers ("tier S").
Se guarda en SQLite (users.db), en el mismo estilo que options_flow.db
(services/options_service.py) para no introducir un ORM/ dependencia nueva.
"""
import sqlite3
import os
import secrets
import string
import bcrypt
from datetime import datetime, timezone, timedelta

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
    # Aceptación del disclaimer — se añadió después del lanzamiento inicial,
    # así que va como ALTER TABLE idempotente (igual que el patrón ya usado
    # en watchlist_service.py) en vez de tocar el CREATE TABLE original.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN disclaimer_accepted_at TEXT")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    # token_version -- permite revocar TODAS las sesiones activas de un
    # usuario (JWT de hasta 30 días, sin esto no había forma de invalidar
    # uno filtrado antes de que caducara solo). Se incluye en el payload
    # del JWT al hacer login; en cada petición se compara contra este
    # valor en BD -- si no coincide, el token se rechaza aunque su firma
    # sea válida y no haya caducado. Incrementar este número invalida de
    # golpe todas las sesiones anteriores. Ver auditoría 19/07/2026 #7.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN token_version INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    # Mensaje de transparencia de costes, mostrado una sola vez tras el
    # registro (mismo patrón que disclaimer_accepted_at) -- explica que la
    # terminal gestiona/representa datos de mercado reales (no los crea),
    # que esos datos cuestan dinero, y por qué existen los tiers de pago.
    # Ver conversación 20/07/2026.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN pricing_message_seen_at TEXT")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    # Vinculación de Telegram por usuario (Watchlist -> alertas), ver
    # 25/07/2026. telegram_link_code/_expires_at son de un solo uso, corta
    # vida (15 min) -- viven en la propia fila del usuario en vez de una
    # tabla nueva, mismo criterio que pricing_message_seen_at.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN telegram_chat_id TEXT")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    try:
        conn.execute("ALTER TABLE users ADD COLUMN telegram_link_code TEXT")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
    try:
        conn.execute("ALTER TABLE users ADD COLUMN telegram_link_code_expires_at TEXT")
    except sqlite3.OperationalError:
        pass  # la columna ya existe
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
        row = conn.execute("SELECT id, email, tier, token_version FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row)
    finally:
        conn.close()


def authenticate(email: str, password: str) -> dict | None:
    """Verifica email/password. Devuelve {id, email, tier} o None si no coincide."""
    email = email.strip().lower()
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id, email, password_hash, tier, token_version FROM users WHERE email = ?", (email,)
        ).fetchone()
        if not row or not _verify_password(password, row["password_hash"]):
            return None
        return {"id": row["id"], "email": row["email"], "tier": row["tier"], "token_version": row["token_version"]}
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    email = email.strip().lower()
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT id, email, tier, disclaimer_accepted_at, pricing_message_seen_at, token_version, telegram_chat_id FROM users WHERE email = ?", (email,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_id(payload: dict) -> int | None:
    """Resuelve el id numérico del usuario a partir del payload del JWT
    (email en 'sub'). None si no se encuentra -- cada router decide si eso
    es un error (Watchlist, que siempre necesita usuario) o simplemente
    "sin badge de watchlist" (scanner/rsrw/insider/research/options, donde
    el usuario ya está autenticado por tier pero el cruce con Watchlist es
    opcional). Centraliza la resolución que antes solo hacía
    routers/watchlist.py::_user_id() a mano."""
    email = payload.get("sub")
    user  = get_user_by_email(email) if email else None
    return user["id"] if user else None


def revoke_sessions(email: str) -> bool:
    """Invalida TODAS las sesiones activas de un usuario (incrementa
    token_version) -- cualquier JWT emitido antes de este momento deja de
    ser válido en el siguiente request, aunque no haya caducado. Útil tras
    un cambio de contraseña o si se sospecha que un token se filtró.
    Devuelve False si el email no existe."""
    email = email.strip().lower()
    conn = _conn()
    try:
        cur = conn.execute("UPDATE users SET token_version = token_version + 1 WHERE email = ?", (email,))
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def accept_disclaimer(user_id: int) -> dict:
    conn = _conn()
    try:
        conn.execute(
            "UPDATE users SET disclaimer_accepted_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user_id)
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def acknowledge_pricing_message(user_id: int) -> dict:
    """Marca como visto el mensaje de transparencia de costes -- se
    muestra una sola vez, justo después del disclaimer, en el mismo flujo
    de bienvenida. Mismo patrón que accept_disclaimer."""
    conn = _conn()
    try:
        conn.execute(
            "UPDATE users SET pricing_message_seen_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user_id)
        )
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def create_telegram_link_code(user_id: int) -> tuple[str, str]:
    """Código corto de un solo uso para vincular Telegram (deep-link
    t.me/<bot>?start=<code>) -- caduca a los 15 min. Vive en la propia
    fila del usuario (1:1, corta vida) -- mismo criterio que
    pricing_message_seen_at, sin tabla nueva."""
    code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    conn = _conn()
    try:
        conn.execute(
            "UPDATE users SET telegram_link_code = ?, telegram_link_code_expires_at = ? WHERE id = ?",
            (code, expires_at, user_id)
        )
        conn.commit()
        return code, expires_at
    finally:
        conn.close()


def consume_telegram_link_code(code: str, chat_id: str) -> int | None:
    """Busca qué usuario generó este código (sin caducar) y le asigna el
    chat_id que acaba de escribirle al bot. None si no existe/caducó -- el
    llamador (telegram_service, al procesar /start) responde con un aviso
    de código inválido en vez de fallar en silencio."""
    conn = _conn()
    try:
        now_iso = datetime.now(timezone.utc).isoformat()
        row = conn.execute(
            "SELECT id FROM users WHERE telegram_link_code = ? AND telegram_link_code_expires_at > ?",
            (code, now_iso)
        ).fetchone()
        if not row:
            return None
        user_id = row["id"]
        conn.execute(
            "UPDATE users SET telegram_chat_id = ?, telegram_link_code = NULL, "
            "telegram_link_code_expires_at = NULL WHERE id = ?",
            (str(chat_id), user_id)
        )
        conn.commit()
        return user_id
    finally:
        conn.close()


def unlink_telegram(user_id: int) -> dict:
    conn = _conn()
    try:
        conn.execute("UPDATE users SET telegram_chat_id = NULL WHERE id = ?", (user_id,))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()


def get_telegram_chat_ids(user_ids: list[int]) -> dict[int, str]:
    """{user_id: chat_id} solo de quienes tienen Telegram vinculado --
    usado por watchlist_service.notify_triggered_alerts() para resolver a
    quién avisar en una sola consulta por lote (mismo criterio de "un
    fetch por lote, no por usuario" que ya usa check_all_active_alerts())."""
    if not user_ids:
        return {}
    conn = _conn()
    try:
        placeholders = ",".join("?" * len(user_ids))
        rows = conn.execute(
            f"SELECT id, telegram_chat_id FROM users WHERE id IN ({placeholders}) AND telegram_chat_id IS NOT NULL",
            user_ids
        ).fetchall()
        return {r["id"]: r["telegram_chat_id"] for r in rows}
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
        # Cambiar la contraseña también revoca todas las sesiones activas
        # -- si el motivo del reset era una cuenta comprometida, un token
        # ya filtrado seguiría siendo válido tras el cambio si no se hace
        # esto. Ver conversación 20/07/2026 (mismo mecanismo que
        # revoke_sessions()).
        cur = conn.execute(
            "UPDATE users SET password_hash = ?, token_version = token_version + 1 WHERE email = ?",
            (password_hash, email)
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