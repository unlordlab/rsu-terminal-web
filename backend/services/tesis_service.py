"""
Servicio de Tesis — reescrito 17/07/2026 para dejar de depender del Google
Sheet externo (CSV publicado) y pasar a una tabla SQLite propia, con estado
de aprobación nativo (pending/approved/rejected). Ver conversación sobre el
agente Bull: necesitábamos una cola de aprobación real, algo que una hoja
de cálculo externa no ofrece de forma natural.

Esquema alineado con TODOS los campos que ya consumía el frontend
(frontend/pages/tesis.js) en la versión CSV: ticker, nombre, fecha, rating,
sector, autor, resumen, imagen, riesgo, precio_objetivo, url_doc — más los
nuevos: contenido (el informe completo, ya no vive en un Google Doc
externo), status, fuente, criterio.

Las tesis históricas del Google Sheet se migran una sola vez con
scripts/migrate_tesis_from_sheet.py (ejecutar antes de desplegar esto en
producción, o las tesis antiguas desaparecerán de la sección pública).
"""
import sqlite3
import os
import re
import time
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'tesis.db')

RATING_CONFIG = {
    "BUY":  {"color": "#00ffad", "label": "BUY"},
    "SELL": {"color": "#f23645", "label": "SELL"},
    "HOLD": {"color": "#ff9800", "label": "HOLD"},
}


def _get_rating_cfg(rating: str) -> dict:
    r = (rating or '').upper()
    if "BUY" in r: return RATING_CONFIG["BUY"]
    if "SELL" in r: return RATING_CONFIG["SELL"]
    return RATING_CONFIG["HOLD"]


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.row_factory = sqlite3.Row
    return conn


def _init_db():
    conn = _conn()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS tesis (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker           TEXT NOT NULL,
            nombre           TEXT,
            fecha            TEXT NOT NULL,
            rating           TEXT NOT NULL DEFAULT 'HOLD',
            sector           TEXT,
            autor            TEXT,
            titulo           TEXT,
            resumen          TEXT,
            imagen           TEXT,
            riesgo           TEXT,
            precio_objetivo  REAL,
            contenido        TEXT NOT NULL,
            status           TEXT NOT NULL DEFAULT 'pending',  -- pending | approved | rejected
            fuente           TEXT NOT NULL DEFAULT 'manual',   -- manual | agente_bull
            criterio         TEXT,
            doc_url          TEXT,
            created_at       REAL NOT NULL,
            approved_at      REAL,
            approved_by      TEXT
        )
    ''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tesis_status ON tesis(status)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_tesis_ticker ON tesis(ticker)')
    conn.commit()
    conn.close()


_init_db()

_DRIVE_FILE_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")
_DRIVE_OPEN_ID_RE = re.compile(r"[?&]id=([a-zA-Z0-9_-]+)")


def _normalize_doc_url(url: str) -> str:
    """Igual que antes: normaliza enlaces de Google Docs/Drive para que
    funcionen embebidos en un iframe. Se mantiene por si alguna tesis
    todavía enlaza a un documento externo en vez de tener el contenido
    guardado directamente en `contenido`."""
    if not url:
        return url
    if "/pub" in url and "docs.google.com" in url:
        return url.split("?")[0].split("&")[0] + "?embedded=true"
    if "drive.google.com" in url:
        m = _DRIVE_FILE_ID_RE.search(url) or _DRIVE_OPEN_ID_RE.search(url)
        if m:
            return f"https://drive.google.com/file/d/{m.group(1)}/preview"
    return url


def _es_nuevo(fecha_str: str) -> bool:
    try:
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        return (datetime.now() - fecha_dt).days <= 7
    except Exception:
        return False


# ── Lectura pública (solo tesis aprobadas) ──────────────────────────────

def get_tesis_list(search: str = "", rating: str = "", page: int = 1, per_page: int = 9) -> dict:
    conn = _conn()
    query = "SELECT * FROM tesis WHERE status = 'approved'"
    params = []
    if search:
        query += " AND (ticker LIKE ? OR nombre LIKE ?)"
        params.extend([f"%{search.upper()}%", f"%{search}%"])
    if rating and rating != "Todos":
        query += " AND rating = ?"
        params.append(rating.upper())
    query += " ORDER BY fecha DESC, id DESC"

    all_rows = conn.execute(query, params).fetchall()

    ratings_rows = conn.execute(
        "SELECT DISTINCT rating FROM tesis WHERE status = 'approved' ORDER BY rating"
    ).fetchall()
    conn.close()

    total = len(all_rows)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    page_rows = all_rows[start:start + per_page]

    items = []
    for r in page_rows:
        cfg = _get_rating_cfg(r["rating"])
        items.append({
            "id": f"{r['ticker']}_{r['fecha']}",
            "ticker": r["ticker"],
            "nombre": r["nombre"] or "",
            "fecha": r["fecha"],
            "rating": r["rating"],
            "rating_color": cfg["color"],
            "sector": r["sector"] or "",
            "autor": r["autor"] or "",
            "resumen": (r["resumen"] or "")[:300],
            "imagen": r["imagen"] or "",
            "upside": None,  # se calcula solo en el detalle (precio en vivo)
            "riesgo": r["riesgo"] or "",
            "es_nuevo": _es_nuevo(r["fecha"]),
            "titulo": r["titulo"] or "",
        })

    return {
        "ok": True,
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "ratings": ["Todos"] + [r["rating"] for r in ratings_rows],
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


def get_tesis_detail(ticker: str, fecha: str = "") -> dict:
    conn = _conn()
    query = "SELECT * FROM tesis WHERE status = 'approved' AND ticker = ?"
    params = [ticker.upper()]
    if fecha:
        query += " AND fecha = ?"
        params.append(fecha)
    query += " ORDER BY fecha DESC, id DESC LIMIT 1"

    row = conn.execute(query, params).fetchone()
    conn.close()

    if not row:
        return {"ok": False, "error": f"Tesis no encontrada: {ticker}"}

    cfg = _get_rating_cfg(row["rating"])
    ticker_up = row["ticker"]

    # Precio actual en vivo (mismo patrón que la versión anterior — yfinance
    # vía cartera_service, no un valor congelado desde el día de creación).
    precio_actual = None
    try:
        from services.cartera_service import fetch_live_prices
        live = fetch_live_prices([ticker_up])
        if ticker_up in live and live[ticker_up].get('price'):
            precio_actual = float(live[ticker_up]['price'])
    except Exception:
        pass

    precio_objetivo = row["precio_objetivo"]
    upside = None
    if precio_objetivo is not None and precio_actual not in (None, 0):
        try:
            upside = round((precio_objetivo - precio_actual) / precio_actual * 100, 1)
        except Exception:
            pass

    return {
        "ok": True,
        "ticker": ticker_up,
        "nombre": row["nombre"] or "",
        "fecha": row["fecha"],
        "rating": row["rating"],
        "rating_color": cfg["color"],
        "sector": row["sector"] or "",
        "autor": row["autor"] or "",
        "titulo": row["titulo"] or "",
        "resumen": row["resumen"] or "",
        "imagen": row["imagen"] or "",
        "riesgo": (row["riesgo"] or "").upper(),
        "precio_objetivo": round(precio_objetivo, 2) if precio_objetivo is not None else None,
        "precio_actual": round(precio_actual, 2) if precio_actual is not None else None,
        "upside": upside,
        "contenido": row["contenido"],
        "url_doc": _normalize_doc_url(row["doc_url"]) if row["doc_url"] else None,
        "es_nuevo": _es_nuevo(row["fecha"]),
        "timestamp": datetime.now().strftime("%H:%M:%S"),
    }


# ── Gestión (admin) ──────────────────────────────────────────────────────

def create_tesis(ticker: str, contenido: str, rating: str = "HOLD", titulo: str = "",
                  nombre: str = "", sector: str = "", autor: str = "", resumen: str = "",
                  imagen: str = "", riesgo: str = "", precio_objetivo: float = None,
                  fuente: str = "manual", criterio: str = None, status: str = "pending") -> int:
    """Crea una tesis nueva. Por defecto queda 'pending' — hace falta
    aprobarla explícitamente para que aparezca en la sección pública."""
    conn = _conn()
    cur = conn.execute(
        """INSERT INTO tesis (ticker, nombre, fecha, rating, sector, autor, titulo, resumen,
                               imagen, riesgo, precio_objetivo, contenido, status, fuente, criterio, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (ticker.upper(), nombre, datetime.now().strftime("%Y-%m-%d"), rating.upper(), sector,
         autor, titulo, resumen, imagen, riesgo, precio_objetivo, contenido, status, fuente,
         criterio, time.time())
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_pending_tesis() -> list:
    """Para el panel de admin — todas las tesis a la espera de revisión,
    más recientes primero."""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM tesis WHERE status = 'pending' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_tesis_by_id(tesis_id: int) -> dict | None:
    conn = _conn()
    row = conn.execute("SELECT * FROM tesis WHERE id = ?", (tesis_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def approve_tesis(tesis_id: int, approved_by: str = "admin") -> bool:
    conn = _conn()
    cur = conn.execute(
        "UPDATE tesis SET status = 'approved', approved_at = ?, approved_by = ? WHERE id = ? AND status = 'pending'",
        (time.time(), approved_by, tesis_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def reject_tesis(tesis_id: int, approved_by: str = "admin") -> bool:
    conn = _conn()
    cur = conn.execute(
        "UPDATE tesis SET status = 'rejected', approved_at = ?, approved_by = ? WHERE id = ? AND status = 'pending'",
        (time.time(), approved_by, tesis_id)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def get_approved_tesis(limit: int = 20) -> list:
    """Últimas tesis aprobadas -- para poder retirarlas desde el panel de
    admin si hace falta (volver a 'pending', desaparece de la sección
    pública al instante)."""
    conn = _conn()
    rows = conn.execute(
        "SELECT * FROM tesis WHERE status = 'approved' ORDER BY approved_at DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def unpublish_tesis(tesis_id: int) -> bool:
    """Retira una tesis ya aprobada -- vuelve a 'pending', deja de verse
    en la sección pública inmediatamente."""
    conn = _conn()
    cur = conn.execute(
        "UPDATE tesis SET status = 'pending', approved_at = NULL, approved_by = NULL WHERE id = ? AND status = 'approved'",
        (tesis_id,)
    )
    conn.commit()
    ok = cur.rowcount > 0
    conn.close()
    return ok


def recent_tickers_with_tesis(days: int = 60) -> set:
    """Tickers que ya tienen una tesis (aprobada o pendiente) reciente —
    para que el agente Bull no proponga el mismo ticker una y otra vez en
    cada escaneo."""
    since = time.time() - days * 86400
    conn = _conn()
    rows = conn.execute(
        "SELECT DISTINCT ticker FROM tesis WHERE created_at >= ? AND status != 'rejected'",
        (since,)
    ).fetchall()
    conn.close()
    return {r["ticker"] for r in rows}