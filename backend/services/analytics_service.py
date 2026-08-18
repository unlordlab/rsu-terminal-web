"""
Servicio de analítica interna: qué secciones se visitan más, qué tickers se
consultan más y qué tesis despiertan más interés.

Dos fuentes de datos, cada una con su propósito:

  - page_view: lo dispara el frontend (router.js) en cada navegación de
    sección. Es la señal fiable de "quién entra dónde", porque no depende
    de si la página termina llamando o no a la API (Academy, Roadmap, etc.
    no hacen fetch al navegar, pero sí cuentan como visita).

  - ticker_view: lo detecta automáticamente el middleware
    (middleware/analytics.py) inspeccionando las rutas de la API que llevan
    un ticker (research/{ticker}, rsrw/ticker/{ticker}, tesis/{ticker}...).
    No hace falta tocar cada router a mano: si mañana se añade un endpoint
    nuevo con un ticker en la URL, basta con añadir su patrón ahí.

Guardado en SQLite (analytics.db), mismo patrón que users.db / options_flow.db
para no introducir un ORM/dependencia nueva.
"""
import sqlite3
import os
import hmac
import hashlib
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'analytics.db')

# Cuánto se conserva. Estos números son los que promete la política de
# privacidad, así que cambiarlos aquí obliga a cambiarlos allí -- y al revés.
#
# 90 días para la analítica: sirve para ver qué secciones se usan y qué tickers
# se miran, y esa pregunta se responde igual de bien con un trimestre que con
# dos años. Guardar más no aporta y sí aumenta lo que hay que proteger.
RETENCION_DIAS = 90


def seudonimo(email: str | None) -> str | None:
    """El email convertido en una huella irreversible y estable.

    POR QUÉ. Hasta el 18/08/2026 esta tabla guardaba el email en cada evento:
    1.379 eventos, 478 de ellos identificables. Eso no es medir el uso, es
    perfilar a personas -- deja de ser «qué se mira» para ser «qué mira
    Fulano», que es un dato mucho más delicado y que no hace falta para
    ninguna de las preguntas que esta tabla responde.

    ESTABLE, para que `COUNT(DISTINCT ...)` siga contando personas distintas y
    no se pierda nada de lo que la analítica servía.

    IRREVERSIBLE DE VERDAD, y aquí está el detalle que importa: un SHA-256 del
    email a secas NO sería irreversible en la práctica. El espacio de emails de
    los usuarios es pequeño y conocido, así que cualquiera con la base delante
    podría probar los emails uno a uno hasta que cuadre el hash. Con la clave
    secreta del servidor mezclada (HMAC), eso deja de poder hacerse sin robar
    además esa clave.

    CONSECUENCIA QUE HAY QUE SABER: si algún día se cambia `SECRET_KEY`, los
    seudónimos nuevos dejan de casar con los viejos y el recuento de usuarios
    únicos se parte en dos por esa fecha. No se pierde ningún dato ni se rompe
    nada, pero conviene tenerlo escrito antes de rotar la clave.
    """
    if not email:
        return None
    from config import settings
    return hmac.new(settings.secret_key.encode(),
                    email.strip().lower().encode(), hashlib.sha256).hexdigest()[:32]


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            ts         TEXT NOT NULL,
            event_type TEXT NOT NULL,   -- 'page_view' | 'ticker_view'
            section    TEXT NOT NULL,   -- '/research', '/tesis', '/cartera', ...
            ticker     TEXT,            -- solo en ticker_view
            email      TEXT             -- NULL si no se pudo identificar (token ausente/expirado)
        )
    ''')
    # Seudónimo en vez del email (18/08/2026). Patrón idempotente de siempre.
    try:
        conn.execute('ALTER TABLE events ADD COLUMN usuario_hash TEXT')
    except sqlite3.OperationalError:
        pass
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(event_type, ts)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_section  ON events(section)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_ticker   ON events(ticker)')
    conn.commit()
    conn.close()
    _migrar_emails_a_seudonimo()


def _migrar_emails_a_seudonimo() -> int:
    """Convierte los emails que ya estaban guardados y los borra.

    Se hace en la migración y no dejando los viejos como estaban a propósito:
    si los antiguos siguieran con el email, la tabla seguiría siendo
    identificable y el cambio no serviría de nada. Se conserva el seudónimo,
    así que la analítica histórica no se pierde -- solo deja de saberse de
    quién es cada fila."""
    conn = _conn()
    try:
        filas = conn.execute(
            "SELECT id, email FROM events WHERE email IS NOT NULL AND email != ''"
        ).fetchall()
        if not filas:
            return 0
        conn.executemany(
            "UPDATE events SET usuario_hash = ?, email = NULL WHERE id = ?",
            [(seudonimo(f["email"]), f["id"]) for f in filas]
        )
        conn.commit()
        print(f"[Analytics] {len(filas)} eventos seudonimizados: el email se ha "
              f"sustituido por una huella irreversible")
        return len(filas)
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()


def log_page_view(section: str, email: str | None) -> None:
    section = (section or '/').strip()[:64]
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO events (ts, event_type, section, ticker, usuario_hash) "
            "VALUES (?, 'page_view', ?, NULL, ?)",
            (datetime.now(timezone.utc).isoformat(), section, seudonimo(email))
        )
        conn.commit()
    finally:
        conn.close()


def log_ticker_view(section: str, ticker: str, email: str | None) -> None:
    ticker = (ticker or '').strip().upper()[:16]
    if not ticker:
        return
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO events (ts, event_type, section, ticker, usuario_hash) "
            "VALUES (?, 'ticker_view', ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), section, ticker, seudonimo(email))
        )
        conn.commit()
    finally:
        conn.close()


def get_summary(days: int = 30) -> dict:
    """Agregados para el panel de admin. `days` limita la ventana (por
    defecto 30). Las tesis son ticker_view con section == '/tesis'; el resto
    de ticker_view (research, rsrw, canslim, options, insider, market) se
    agregan juntos como "tickers más consultados".
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    conn = _conn()
    try:
        sections = conn.execute('''
            SELECT section, COUNT(*) AS visits, COUNT(DISTINCT usuario_hash) AS unique_users
            FROM events
            WHERE event_type = 'page_view' AND ts >= ?
            GROUP BY section
            ORDER BY visits DESC
        ''', (since,)).fetchall()

        tickers = conn.execute('''
            SELECT ticker, COUNT(*) AS views, COUNT(DISTINCT usuario_hash) AS unique_users
            FROM events
            WHERE event_type = 'ticker_view' AND ts >= ? AND section != '/tesis'
            GROUP BY ticker
            ORDER BY views DESC
            LIMIT 25
        ''', (since,)).fetchall()

        tesis = conn.execute('''
            SELECT ticker, COUNT(*) AS views, COUNT(DISTINCT usuario_hash) AS unique_users
            FROM events
            WHERE event_type = 'ticker_view' AND ts >= ? AND section = '/tesis'
            GROUP BY ticker
            ORDER BY views DESC
            LIMIT 25
        ''', (since,)).fetchall()

        daily = conn.execute('''
            SELECT substr(ts, 1, 10) AS day, COUNT(*) AS visits
            FROM events
            WHERE event_type = 'page_view' AND ts >= ?
            GROUP BY day
            ORDER BY day ASC
        ''', (since,)).fetchall()

        total_page_views = conn.execute(
            "SELECT COUNT(*) c FROM events WHERE event_type = 'page_view' AND ts >= ?", (since,)
        ).fetchone()['c']
        total_ticker_views = conn.execute(
            "SELECT COUNT(*) c FROM events WHERE event_type = 'ticker_view' AND ts >= ?", (since,)
        ).fetchone()['c']
        unique_users = conn.execute(
            "SELECT COUNT(DISTINCT usuario_hash) c FROM events WHERE ts >= ? AND usuario_hash IS NOT NULL", (since,)
        ).fetchone()['c']

        return {
            "days": days,
            "since": since,
            "total_page_views": total_page_views,
            "total_ticker_views": total_ticker_views,
            "unique_users": unique_users,
            "sections": [dict(r) for r in sections],
            "tickers": [dict(r) for r in tickers],
            "tesis": [dict(r) for r in tesis],
            "daily": [dict(r) for r in daily],
        }
    finally:
        conn.close()


init_db()


def purgar_antiguos() -> int:
    """Borra los eventos de más de RETENCION_DIAS días.

    Hasta el 18/08/2026 esta tabla no se purgaba NUNCA: crecía sin límite desde
    el primer día. Una política de privacidad que prometa un plazo de
    conservación tiene que estar respaldada por código que lo cumpla, o es una
    promesa vacía -- que es exactamente lo que este proyecto lleva meses
    quitando de otros sitios."""
    from datetime import timedelta
    corte = (datetime.now(timezone.utc) - timedelta(days=RETENCION_DIAS)).isoformat()
    conn = _conn()
    try:
        cur = conn.execute("DELETE FROM events WHERE ts < ?", (corte,))
        n = cur.rowcount or 0
        conn.commit()
        if n:
            print(f"[Analytics] Purgados {n} eventos con más de {RETENCION_DIAS} días")
        return n
    except sqlite3.OperationalError:
        return 0
    finally:
        conn.close()
