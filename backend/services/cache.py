import time
import threading
from typing import Any, Optional

class TTLCache:
    """
    Caché en memoria con TTL por clave.
    Thread-safe para uso con ThreadPoolExecutor.
    """
    def __init__(self):
        self._store: dict = {}
        self._lock  = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            value, expires_at = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any, ttl: int = 300):
        with self._lock:
            self._store[key] = (value, time.time() + ttl)

    def delete(self, key: str):
        with self._lock:
            self._store.pop(key, None)

    def clear_prefix(self, prefix: str):
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]

    def stats(self) -> dict:
        with self._lock:
            now   = time.time()
            total = len(self._store)
            valid = sum(1 for _, (_, exp) in self._store.items() if exp > now)
            return {"total": total, "valid": valid, "expired": total - valid}

# Instancia global
cache = TTLCache()

# TTLs por tipo de dato
TTL = {
    "research":    900,   # 15 min — fundamentales no cambian tan rápido
    "market":      60,    # 1 min  — índices, forex, commodities
    "sectors":     120,   # 2 min  — sectores
    "fear_greed":  300,   # 5 min  — fear & greed
    "vix":         120,   # 2 min  — VIX
    "spreads":     3600,  # 1 hora — credit spreads FRED
    "reddit":      300,   # 5 min  — reddit pulse
    "briefing":    3600,  # 1 hora — nightly briefing
    "calendar":    1800,  # 30 min — calendario económico
    "earnings":    1800,  # 30 min — earnings calendar
    "canslim":     600,   # 10 min — CANSLIM screener
    "rsrw":        300,   # 5 min  — RS/RW scanner
    "options":     120,   # 2 min  — options flow
}