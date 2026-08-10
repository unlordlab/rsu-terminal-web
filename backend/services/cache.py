import time
import json
import sqlite3
import os
import functools
import threading
from contextlib import contextmanager
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
        # Un candado por clave, para que solo uno recalcule cada dato a la vez
        # (ver recomputing()). _key_waiters lleva la cuenta de interesados para
        # poder retirar el candado cuando no queda ninguno.
        self._key_locks: dict = {}
        self._key_waiters: dict = {}
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

    @contextmanager
    def recomputing(self, key: str, timeout: float = 25.0):
        """Solo un hilo recalcula esta clave a la vez; los demás esperan a que
        termine y se sirven del resultado que acaba de guardar.

        El problema que resuelve: `_lock` protege el diccionario, no el
        recálculo. Como el cálculo caro vive en el llamador y no aquí, cuando
        caduca una clave popular cada petición que llega mientras se recalcula
        dispara su propia descarga. Medido con 5 peticiones simultáneas a los
        sectores con la caché vacía: 5 descargas reales en vez de 1. Con ~100
        usuarios y el rate-limit de Yahoo como riesgo principal, eso multiplica
        peticiones justo en el peor momento. Ver hallazgo #21 de Market.

        Se ofrece como envoltorio y no como un `get_or_set(clave, funcion)`
        a propósito: en este proyecto casi todos los llamadores deciden por su
        cuenta QUÉ y CUÁNDO cachear -- varios no cachean los fallos, y otros
        solo guardan si el resultado trae datos. Un `get_or_set` obligaría a
        reescribir esa lógica en cada sitio; así cada uno conserva la suya y
        solo se le añade el turno.

        El `timeout` no es adorno: si quien está recalculando se atasca, es
        preferible que los demás dupliquen el trabajo a que se queden colgados.
        Al agotarse, se sigue adelante sin el turno.

        Uso:
            cached = cache.get(clave)
            if cached: return cached
            with cache.recomputing(clave):
                cached = cache.get(clave)      # puede haberlo dejado otro
                if cached: return cached
                ...calcular...
                cache.set(clave, resultado, ttl)
        """
        with self._lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            self._key_waiters[key] = self._key_waiters.get(key, 0) + 1

        adquirido = lock.acquire(timeout=timeout)
        if not adquirido:
            print(f"[Cache] '{key}' lleva más de {timeout:g}s recalculándose; "
                  f"se sigue sin esperar turno")
        try:
            yield adquirido
        finally:
            if adquirido:
                lock.release()
            with self._lock:
                n = self._key_waiters.get(key, 1) - 1
                # El diccionario de candados se limpia cuando no queda nadie
                # interesado en la clave; si no, crecería sin límite (una
                # entrada por ticker consultado, para siempre).
                if n <= 0:
                    self._key_waiters.pop(key, None)
                    self._key_locks.pop(key, None)
                else:
                    self._key_waiters[key] = n

    def single_flight(self, clave):
        """Decorador: evita que varias peticiones recalculen lo mismo a la vez.

        Se prefiere a envolver el cuerpo de cada función con `recomputing()`
        porque eso obligaría a reindentar bloques largos, que es donde se rompen
        las cosas sin que se note. Así el cambio es una línea encima de la
        función y su cuerpo no se toca: la función conserva su propio
        `cache.get`/`cache.set` y, con él, su criterio sobre qué merece
        guardarse (varias no cachean los fallos a propósito).

        `clave` puede ser un texto fijo o una función de los mismos argumentos,
        para las que cachean por parámetro (`market:sectors:1d`, `1w`...).
        """
        def decorador(fn):
            @functools.wraps(fn)
            def envoltorio(*args, **kwargs):
                key = clave(*args, **kwargs) if callable(clave) else clave
                cached = self.get(key)
                if cached is not None:
                    return cached
                with self.recomputing(key):
                    # Segunda mirada: mientras se esperaba turno, puede que
                    # otro ya lo haya dejado hecho. Sin esto, el que espera
                    # recalcularía igualmente y no se habría ganado nada.
                    cached = self.get(key)
                    if cached is not None:
                        return cached
                    return fn(*args, **kwargs)
            return envoltorio
        return decorador

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
    "reddit_fail": 120,   # 2 min  — negative cache: evita relanzar la cadena
                           # completa (OAuth Reddit + StockTwits + fallback de
                           # navegador headless, ~4-5s) en cada petición mientras
                           # la fuente está caída. Más corto que "reddit" para
                           # reintentar razonablemente pronto en cuanto se
                           # recupere. Ver sesión 22/07/2026.
    "briefing":    3600,  # 1 hora — nightly briefing
    "calendar":    1800,  # 30 min — calendario económico
    "earnings":    1800,  # 30 min — earnings calendar
    "canslim":     600,   # 10 min — CANSLIM screener
    "bull_info":   3600,  # 1 hora — .info crudo cacheado para Gael, ver conversación 18/07/2026
    "rsrw":        300,   # 5 min  — RS/RW scanner
    "options":     300,   # 5 min (antes 120s) — options flow
    "spxl_live":   300,   # 5 min  — precio y fase actual de SPXL
    "spxl_bt":     3600,  # 1 hora — los tres backtests. Corren sobre 17 años
                           # de cierres diarios: entre una visita y la
                           # siguiente del mismo día el resultado es el mismo
                           # salvo por la vela de hoy, así que refrescar más a
                           # menudo solo repetiría el trabajo.
}