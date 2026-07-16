from datetime import datetime, timedelta, timezone
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends
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