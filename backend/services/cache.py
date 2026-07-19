import time
import json
import sqlite3
import os
import threading
from typing import Any, Optional

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'cache.db')


class TTLCache:
    """
    Caché con TTL por clave, en dos capas:

    - L1 (memoria de este proceso): lectura instantánea, igual de rápida
      que la versión anterior — no se pierde nada de velocidad en el caso
      normal (mismo worker que ya tenía el dato).
    - L2 (SQLite compartida): cuando L1 no tiene el dato (proceso recién
      arrancado, o TTL caducado en ESTE worker en concreto), se comprueba
      la caché compartida antes de rendirse y disparar una llamada externa
      en vivo — por si OTRO worker ya lo había refrescado hace un momento.

    Por qué hacía falta esto: con solo caché en memoria, cada worker de
    uvicorn tiene la suya propia y por separado. El día que se despliegue
    con varios workers (como está previsto en producción), el mismo dato
    se pediría en vivo una vez por worker en vez de una sola vez para
    todos — este cambio soluciona eso sin tocar ninguna otra parte del
    código, porque la interfaz pública (get/set/delete/clear_prefix/stats)
    es exactamente la misma que antes.
    """
    def __init__(self):
        self._store: dict = {}
        self._lock  = threading.Lock()
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_db(self):
        try:
            conn = self._conn()
            conn.execute('''
                CREATE TABLE IF NOT EXISTS cache_kv (
                    key        TEXT PRIMARY KEY,
                    value      TEXT NOT NULL,
                    expires_at REAL NOT NULL
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[Cache] No se pudo inicializar la caché compartida (SQLite): {e}")

    def get(self, key: str) -> Optional[Any]:
        # L1 primero — instantáneo, sin tocar disco
        with self._lock:
            entry = self._store.get(key)
            if entry is not None:
                value, expires_at = entry
                if time.time() <= expires_at:
                    return value
                del self._store[key]

        # L1 sin dato (o caducado en este worker) — probar L2 compartida
        try:
            conn = self._conn()
            row = conn.execute(
                "SELECT value, expires_at FROM cache_kv WHERE key = ?", (key,)
            ).fetchone()
            conn.close()
        except Exception:
            return None

        if row is None:
            return None
        value_json, expires_at = row
        if time.time() > expires_at:
            return None
        try:
            value = json.loads(value_json)
        except Exception:
            return None

        # Promocionar a L1 para que la próxima lectura en este worker sea instantánea
        with self._lock:
            self._store[key] = (value, expires_at)
        return value

    def set(self, key: str, value: Any, ttl: int = 300):
        expires_at = time.time() + ttl
        with self._lock:
            self._store[key] = (value, expires_at)
        try:
            value_json = json.dumps(value, default=str)
            conn = self._conn()
            conn.execute(
                "INSERT OR REPLACE INTO cache_kv (key, value, expires_at) VALUES (?, ?, ?)",
                (key, value_json, expires_at)
            )
            conn.commit()
            conn.close()
        except Exception as e:
            # Si falla la escritura compartida, seguimos teniendo L1 — no es
            # crítico, solo se pierde el compartir con otros workers.
            print(f"[Cache] No se pudo escribir '{key}' en la caché compartida: {e}")

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)
        try:
            conn = self._conn()
            conn.execute("DELETE FROM cache_kv WHERE key = ?", (key,))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def clear_prefix(self, prefix: str):
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
        try:
            conn = self._conn()
            conn.execute("DELETE FROM cache_kv WHERE key LIKE ?", (prefix + '%',))
            conn.commit()
            conn.close()
        except Exception:
            pass

    def stats(self) -> dict:
        with self._lock:
            now   = time.time()
            total = len(self._store)
            valid = sum(1 for _, (_, exp) in self._store.items() if exp > now)
        db_total = None
        try:
            conn = self._conn()
            db_total = conn.execute("SELECT COUNT(*) FROM cache_kv").fetchone()[0]
            conn.close()
        except Exception:
            pass
        return {"l1_total": total, "l1_valid": valid, "l1_expired": total - valid, "l2_total": db_total}

# Instancia global
cache = TTLCache()

# TTLs por tipo de dato
TTL = {
    "research":    900,   # 15 min — fundamentales no cambian tan rápido
    "market":      300,   # 5 min  — índices, forex, commodities (antes 60s: caducaba
                           # cada minuto y disparaba llamadas en vivo constantemente)
    "sectors":     300,   # 5 min (antes 120s) — no hay margen de sobra para
                           # trading intradía en la filosofía de la terminal,
                           # así que no hace falta refrescar cada 2 min
    "fear_greed":  300,   # 5 min — fear & greed
    "vix":         300,   # 5 min (antes 120s) — mismo razonamiento
    "spreads":     3600,  # 1 hora — credit spreads FRED
    "reddit":      300,   # 5 min  — reddit pulse
    "briefing":    3600,  # 1 hora — nightly briefing
    "calendar":    1800,  # 30 min — calendario económico
    "earnings":    1800,  # 30 min — earnings calendar
    "canslim":     600,   # 10 min — CANSLIM screener
    "bull_info":   3600,  # 1 hora — .info crudo cacheado para Gael, ver conversación 18/07/2026
    "rsrw":        300,   # 5 min  — RS/RW scanner
    "options":     300,   # 5 min (antes 120s) — options flow
}