from datetime import datetime, timedelta, timezone
import secrets
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

bearer = HTTPBearer()

def create_token(data: dict, expire_minutes: int | None = None) -> str:
    minutos = expire_minutes if expire_minutes is not None else settings.token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutos)
    return jwt.encode(
        {**data, "exp": expire},
        settings.secret_key,
        algorithm=settings.algorithm
    )

def decode_token(token: str) -> dict | None:
    """Decodifica un token JWT en crudo (string). Devuelve None si no es válido.

    Se usa tanto para WebSockets (donde el token llega como query param,
    ya que el navegador no permite fijar cabeceras en el handshake de WS)
    como internamente desde verify_token().
    """
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )
    except JWTError:
        return None

def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
) -> dict:
    payload = decode_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    # Comprobar token_version contra la BD -- permite revocar TODAS las
    # sesiones de un usuario (tokens de hasta 30 días) sin esperar a que
    # caduquen solos. Si el usuario no existe ya (cuenta borrada) o la
    # versión no coincide (se llamó a revoke_sessions después de emitir
    # este token), se rechaza aunque la firma sea válida. Ver auditoría
    # 19/07/2026, hallazgo #7.
    from services import users_service
    email = payload.get("sub")
    user = users_service.get_user_by_email(email) if email else None
    if user is None or user.get("token_version", 0) != payload.get("tv", 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión revocada, inicia sesión de nuevo"
        )
    return payload

# ── Tiers ──────────────────────────────────────────────────────────────────
# Jerarquía de planes: free < tier1 < tiers ("tier S"). El JWT lleva el tier
# del usuario en el momento del login/registro (payload["tier"]); si por lo
# que sea no está presente se trata como "free" (el más restrictivo).
TIER_ORDER = {"free": 0, "tier1": 1, "tiers": 2}

def require_tier(min_tier: str):
    """Dependency factory: exige que el usuario tenga como mínimo `min_tier`.

    Uso: dependencies=[Depends(require_tier("tier1"))] a nivel de router,
    para bloquear secciones enteras (p.ej. Cartera, Tesis) a usuarios free.

    Importante: el tier se relee de la base de datos en cada request (no del
    JWT), para que si el admin sube el tier de alguien vía /admin/set-tier,
    el cambio surta efecto de inmediato y no haga falta esperar a que
    expire el token viejo (hasta 8h) ni pedirle a la persona que reinicie
    sesión.
    """
    min_level = TIER_ORDER.get(min_tier, 0)

    def dependency(payload: dict = Depends(verify_token)) -> dict:
        from services import users_service  # import diferido: evita ciclo de imports
        email     = payload.get("sub")
        user      = users_service.get_user_by_email(email) if email else None
        user_tier = user["tier"] if user else payload.get("tier", "free")
        user_level = TIER_ORDER.get(user_tier, 0)
        if user_level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Esta sección requiere el plan '{min_tier}' o superior. Tu plan actual: '{user_tier}'."
            )
        return {**payload, "tier": user_tier}

    return dependency

# ── Admin (X-Admin-Key) ──────────────────────────────────────────────────
# Dependencia compartida para los endpoints solo-admin (Meeting Room, Tesis
# pendientes, Academy review, Laia, Analytics, Community, admin de auth...).
# Antes esta misma comprobación de 2 líneas estaba copiada por separado en
# 7+ routers -- deduplicada aquí, y de paso con comparación en tiempo
# constante (secrets.compare_digest en vez de !=) para no ser vulnerable a
# un ataque de temporización, aunque el riesgo real por red sea bajo. Ver
# auditoría 19/07/2026, hallazgos #15 y #17 (Fase 2.4 del Plan Maestro).
ADMIN_KEY_FAIL_LIMIT  = 20    # intentos fallidos permitidos
ADMIN_KEY_FAIL_WINDOW = 3600  # por hora, por IP

def verify_admin_key(request: Request, x_admin_key: str = Header(None)) -> None:
    if not settings.admin_key or not x_admin_key or not secrets.compare_digest(x_admin_key, settings.admin_key):
        # Solo los fallos cuentan contra este límite -- el uso legítimo con la
        # clave correcta (todo el panel /admin) no se ve afectado nunca.
        from middleware.rate_limit import _check_limit, _get_ip
        ip = _get_ip(request)
        allowed, retry_in = _check_limit(f"adminkey_fail:{ip}", ADMIN_KEY_FAIL_LIMIT, ADMIN_KEY_FAIL_WINDOW)
        print(f"[SECURITY] Intento fallido de X-Admin-Key desde {ip}")
        if not allowed:
            raise HTTPException(status_code=429, detail=f"Demasiados intentos fallidos. Espera {retry_in}s.")
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")