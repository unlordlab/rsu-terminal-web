from datetime import datetime, timedelta, timezone
import secrets
from jose import JWTError, jwt
from fastapi import HTTPException, status, Depends, Header, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config import settings

# ── Cookie de sesión ───────────────────────────────────────────────────────
# El token de usuario vive en una cookie httpOnly, no en localStorage. La
# diferencia que importa: httpOnly significa que JavaScript no puede leerla,
# así que un XSS en cualquier página de la terminal ya no puede robar la
# sesión de nadie. Guardarla en localStorage (o en sessionStorage, da igual
# cuál) la deja expuesta a cualquier script que se cuele.
#
# Lo que esto NO arregla, dicho claro: sin HTTPS el token sigue viajando en
# claro por la red, así que quien pueda leer el tráfico lo ve igual. La
# cookie cierra la puerta del XSS; la del sniffing la cierra el certificado.
# Ver settings.cookie_secure.
#
# SameSite=lax basta como defensa CSRF aquí: el frontend y la API son el
# mismo origen, así que ninguna petición legítima de la terminal es
# cross-site, y lax bloquea justamente las que vendrían de fuera.
COOKIE_NAME = "rsu_session"

# La clave de administración sigue el mismo criterio, y por un motivo que no
# es teórico: el 08/08 se demostró de extremo a extremo que un POST anónimo a
# /analytics/track bastaba para ejecutar código en el panel de admin, y desde
# ahí la clave era un sessionStorage.getItem() -- o sea, la credencial más
# potente del proyecto (cambiar tiers, resetear cualquier contraseña, emitir
# tokens de años) al alcance de cualquiera que colase un XSS. Con la cookie
# httpOnly, un XSS futuro que se escape ya no puede leerla.
ADMIN_COOKIE_NAME = "rsu_admin"

bearer = HTTPBearer(auto_error=False)


def set_session_cookie(response: Response, token: str, max_age: int | None) -> None:
    """max_age=None deja una cookie de sesión: el navegador la borra al
    cerrarse. Es lo que corresponde a un login sin "mantener sesión"."""
    response.set_cookie(
        key=COOKIE_NAME, value=token, max_age=max_age,
        httponly=True, samesite="lax", secure=settings.cookie_secure, path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=COOKIE_NAME, httponly=True, samesite="lax",
        secure=settings.cookie_secure, path="/",
    )

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
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer),
) -> dict:
    # La cookie manda sobre la cabecera: tras el cambio a cookie httpOnly
    # puede quedar un token viejo en el almacenamiento del navegador de
    # alguien que ya usaba la terminal, y un login nuevo tiene que ganarle
    # siempre a ese resto. La cabecera Bearer se mantiene como respaldo por
    # dos motivos reales, no por simetría: los tokens de servicio
    # (daily_briefing.py, el disparador del scan de Options Flow) no tienen
    # navegador ni cookies, y las sesiones abiertas antes de este cambio
    # siguen funcionando sin echar a nadie el día del despliegue.
    token = request.cookies.get(COOKIE_NAME)
    if not token and credentials:
        token = credentials.credentials
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado"
        )
    payload = decode_token(token)
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

def set_admin_cookie(response: Response, key: str) -> None:
    """Cookie de sesión (sin max-age): la clave de admin no debe sobrevivir
    al cierre del navegador. Antes vivía en sessionStorage, que tiene esa
    misma duración pero es legible desde JavaScript."""
    response.set_cookie(
        key=ADMIN_COOKIE_NAME, value=key,
        httponly=True, samesite="lax", secure=settings.cookie_secure, path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME, httponly=True, samesite="lax",
        secure=settings.cookie_secure, path="/",
    )


def verify_admin_key(request: Request, x_admin_key: str = Header(None)) -> None:
    # Cookie primero, cabecera después. La cabecera se mantiene porque la
    # usan procesos sin navegador: el workflow que dispara el escaneo de
    # Options Flow manda X-Admin-Key y no tiene dónde guardar una cookie.
    clave = request.cookies.get(ADMIN_COOKIE_NAME) or x_admin_key
    if not settings.admin_key or not clave or not secrets.compare_digest(clave, settings.admin_key):
        # Solo los fallos cuentan contra este límite -- el uso legítimo con la
        # clave correcta (todo el panel /admin) no se ve afectado nunca.
        from middleware.rate_limit import _check_limit, _get_ip
        ip = _get_ip(request)
        allowed, retry_in = _check_limit(f"adminkey_fail:{ip}", ADMIN_KEY_FAIL_LIMIT, ADMIN_KEY_FAIL_WINDOW)
        print(f"[SECURITY] Intento fallido de X-Admin-Key desde {ip}")
        if not allowed:
            raise HTTPException(status_code=429, detail=f"Demasiados intentos fallidos. Espera {retry_in}s.")
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")

# ── Titular ────────────────────────────────────────────────────────────────

def es_titular(payload: dict) -> bool:
    """¿Esta sesión es la del dueño de la cartera? (settings.owner_email).

    Cartera no es por usuario: es una sola, la del titular, y sus avisos van a
    SU Telegram -- así que hay acciones ahí que no tienen sentido para nadie
    más, por mucho que el resto del módulo sí sea visible para los usuarios de
    pago. Sin OWNER_EMAIL configurado devuelve False para todos: se prefiere
    que la acción quede cerrada a que quede abierta por defecto.

    Comparación en minúsculas y sin espacios, igual que hace el login al
    guardar el correo -- si no, el mismo dueño escrito con una mayúscula
    distinta en el .env dejaría de reconocerse.
    """
    correo = (payload or {}).get("sub") or ""
    dueno  = getattr(settings, "owner_email", "") or ""
    if not dueno:
        return False
    return correo.strip().lower() == dueno.strip().lower()


def verify_owner(payload: dict = Depends(verify_token)) -> dict:
    """Dependency: exige que quien llama sea el titular. 403, no 404 -- el
    endpoint existe y se sabe que existe; lo que falta es el derecho."""
    if not es_titular(payload):
        raise HTTPException(
            status_code=403,
            detail="Solo el titular de la cartera puede forzar esta comprobación",
        )
    return payload
