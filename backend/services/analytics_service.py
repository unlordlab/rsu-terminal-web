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
from datetime import datetime, timedelta, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'analytics.db')


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
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_type_ts ON events(event_type, ts)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_section  ON events(section)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_events_ticker   ON events(ticker)')
    conn.commit()
    conn.close()


def log_page_view(section: str, email: str | None) -> None:
    section = (section or '/').strip()[:64]
    conn = _conn()
    try:
        conn.execute(
            "INSERT INTO events (ts, event_type, section, ticker, email) VALUES (?, 'page_view', ?, NULL, ?)",
            (datetime.now(timezone.utc).isoformat(), section, email)
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
            "INSERT INTO events (ts, event_type, section, ticker, email) VALUES (?, 'ticker_view', ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), section, ticker, email)
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
            SELECT section, COUNT(*) AS visits, COUNT(DISTINCT email) AS unique_users
            FROM events
            WHERE event_type = 'page_view' AND ts >= ?
            GROUP BY section
            ORDER BY visits DESC
        ''', (since,)).fetchall()

        tickers = conn.execute('''
            SELECT ticker, COUNT(*) AS views, COUNT(DISTINCT email) AS unique_users
            FROM events
            WHERE event_type = 'ticker_view' AND ts >= ? AND section != '/tesis'
            GROUP BY ticker
            ORDER BY views DESC
            LIMIT 25
        ''', (since,)).fetchall()

        tesis = conn.execute('''
            SELECT ticker, COUNT(*) AS views, COUNT(DISTINCT email) AS unique_users
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
            "SELECT COUNT(DISTINCT email) c FROM events WHERE ts >= ? AND email IS NOT NULL", (since,)
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