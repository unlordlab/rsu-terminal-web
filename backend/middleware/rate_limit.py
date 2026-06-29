import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException

_store: dict = defaultdict(list)
_lock        = threading.Lock()

GENERAL_LIMIT = 60
HEAVY_LIMIT   = 10
WINDOW        = 60

HEAVY_ENDPOINTS = {
    "/api/v1/research/",
    "/api/v1/btc-stratum/backtest",
    "/api/v1/canslim/scan",
    "/api/v1/rsrw/scan",
    "/api/v1/algoritmo/backtest",
}

def _get_key(request: Request) -> str:
    token = request.headers.get("Authorization", "")[:20]
    ip    = request.client.host if request.client else "unknown"
    return f"{ip}:{token}"

def _is_heavy(path: str) -> bool:
    return any(path.startswith(ep) for ep in HEAVY_ENDPOINTS)

def _check_limit(key: str, limit: int) -> tuple[bool, int]:
    now = time.time()
    with _lock:
        _store[key] = [t for t in _store[key] if now - t < WINDOW]
        count = len(_store[key])
        if count >= limit:
            oldest   = _store[key][0]
            retry_in = int(WINDOW - (now - oldest)) + 1
            return False, retry_in
        _store[key].append(now)
        return True, 0

async def rate_limit(request: Request):
    """Dependency de FastAPI para rate limiting — solo HTTP, no WebSockets"""
    path = request.url.path

    # Excluir rutas que no son API
    if not path.startswith("/api/"):
        return

    # Excluir auth (login no tiene límite)
    if path.startswith("/api/v1/auth/"):
        return

    key   = _get_key(request)
    limit = HEAVY_LIMIT if _is_heavy(path) else GENERAL_LIMIT

    allowed, retry_in = _check_limit(key, limit)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error":    "Rate limit excedido",
                "retry_in": retry_in,
                "limit":    limit,
                "window":   WINDOW,
                "message":  f"Máximo {limit} requests por {WINDOW}s. Intenta en {retry_in}s."
            }
        )