"""
Rastreador ligero de éxito/fallo de las llamadas a yfinance por módulo —
alimenta la pestaña "PETICIONES" del panel de admin (/admin). Ver
conversación 16/07/2026 sobre el bloqueo de Yahoo y el blindaje posterior.

Guarda cada resultado (éxito o fallo total) en SQLite, con marca de tiempo
y, si falló, un fragmento del error. Con esto se puede ver desde el admin
qué módulos están fallando más y con qué frecuencia — la señal real de
cuándo haría falta escalar (revisar versión de yfinance, retomar un proxy,
o migrar a una API de pago tipo EODHD/FMP), en vez de tener que adivinarlo
mirando logs de Docker a mano.
"""
import sqlite3
import os
import time
import threading

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'cache.db')
_lock = threading.Lock()


def _conn():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _init_db():
    try:
        conn = _conn()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS yf_health_log (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                module     TEXT NOT NULL,
                ok         INTEGER NOT NULL,
                detail     TEXT,
                created_at REAL NOT NULL
            )
        ''')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_yf_health_module_time ON yf_health_log(module, created_at)')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[YfHealth] No se pudo inicializar la tabla de salud: {e}")


_init_db()


def log(module: str, ok: bool, detail: str = None):
    """Registra un resultado. Nunca lanza excepción hacia arriba — si falla
    el propio registro, no debe tumbar la petición real que lo llamó."""
    try:
        with _lock:
            conn = _conn()
            conn.execute(
                "INSERT INTO yf_health_log (module, ok, detail, created_at) VALUES (?, ?, ?, ?)",
                (module, 1 if ok else 0, (detail or "")[:300], time.time())
            )
            # Housekeeping: nos quedamos solo con los últimos 7 días, de
            # sobra para el panel de admin, para que la tabla no crezca sin
            # límite con el tiempo.
            conn.execute("DELETE FROM yf_health_log WHERE created_at < ?", (time.time() - 7 * 86400,))
            conn.commit()
            conn.close()
    except Exception as e:
        print(f"[YfHealth] No se pudo registrar el resultado de '{module}': {e}")


def summary(hours: int = 24) -> dict:
    """Resumen por módulo: nº de éxitos/fallos y % de éxito en la ventana
    indicada, más los últimos fallos con detalle del error."""
    since = time.time() - hours * 3600
    try:
        conn = _conn()
        rows = conn.execute(
            "SELECT module, ok, COUNT(*) FROM yf_health_log WHERE created_at >= ? GROUP BY module, ok",
            (since,)
        ).fetchall()
        last_fail = conn.execute(
            "SELECT module, detail, created_at FROM yf_health_log "
            "WHERE ok = 0 AND created_at >= ? ORDER BY created_at DESC LIMIT 20",
            (since,)
        ).fetchall()
        conn.close()
    except Exception as e:
        print(f"[YfHealth] No se pudo leer el resumen: {e}")
        return {"modules": [], "recent_failures": [], "window_hours": hours}

    by_module = {}
    for module, ok, count in rows:
        entry = by_module.setdefault(module, {"module": module, "ok": 0, "fail": 0})
        if ok:
            entry["ok"] += count
        else:
            entry["fail"] += count

    modules = []
    for entry in by_module.values():
        total = entry["ok"] + entry["fail"]
        entry["total"] = total
        entry["success_rate"] = round((entry["ok"] / total) * 100, 1) if total else None
        modules.append(entry)
    modules.sort(key=lambda m: (m["success_rate"] if m["success_rate"] is not None else 999))

    recent_failures = [
        {"module": m, "detail": d, "timestamp": t}
        for m, d, t in last_fail
    ]

    return {"modules": modules, "recent_failures": recent_failures, "window_hours": hours}