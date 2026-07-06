import time
import threading
from collections import defaultdict
from fastapi import Request, HTTPException

_store: dict = defaultdict(list)
_lock        = threading.Lock()

GENERAL_LIMIT = 60
HEAVY_LIMIT   = 10
WINDOW        = 60

# Límite específico para /api/v1/auth/login: es la única puerta de entrada
# de toda la app (una sola contraseña de comunidad), así que necesita un
# límite mucho más estricto que el general para dificultar la fuerza bruta.
# Se cuenta solo por IP (todavía no hay token en el momento de hacer login).
LOGIN_LIMIT  = 5
LOGIN_WINDOW = 900  # 15 minutos

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

def _get_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"

def _is_heavy(path: str) -> bool:
    return any(path.startswith(ep) for ep in HEAVY_ENDPOINTS)

def _check_limit(key: str, limit: int, window: int = WINDOW) -> tuple[bool, int]:
    now = time.time()
    with _lock:
        _store[key] = [t for t in _store[key] if now - t < window]
        count = len(_store[key])
        if count >= limit:
            oldest   = _store[key][0]
            retry_in = int(window - (now - oldest)) + 1
            return False, retry_in
        _store[key].append(now)
        return True, 0

async def rate_limit(request: Request):
    """Dependency de FastAPI para rate limiting — solo HTTP, no WebSockets"""
    path = request.url.path

    # Excluir rutas que no son API
    if not path.startswith("/api/"):
        return

    # El login tiene su propio límite, mucho más estricto (ver login_rate_limit).
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

async def login_rate_limit(request: Request):
    """Límite anti fuerza-bruta para /api/v1/auth/login: máximo LOGIN_LIMIT
    intentos por IP cada LOGIN_WINDOW segundos, independientemente de si la
    contraseña enviada es correcta o no (se cuenta el intento, no el fallo,
    para que tampoco sirva de nada probar rápido esperando acertar)."""
    key = "login:" + _get_ip(request)
    allowed, retry_in = _check_limit(key, LOGIN_LIMIT, LOGIN_WINDOW)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail={
                "error":    "Demasiados intentos de acceso",
                "retry_in": retry_in,
                "limit":    LOGIN_LIMIT,
                "window":   LOGIN_WINDOW,
                "message":  f"Demasiados intentos. Espera {retry_in}s antes de volver a intentarlo."
            }
        )