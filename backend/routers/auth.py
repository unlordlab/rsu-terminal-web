from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, field_validator
from auth import (
    create_token, verify_token, verify_admin_key,
    set_session_cookie, clear_session_cookie,
)
from middleware.rate_limit import login_rate_limit
from services import users_service
from config import settings

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _validate_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5:
        raise ValueError("Email no válido")
    return v


class RegisterRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return _validate_email(v)

    @field_validator("password")
    @classmethod
    def _password(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str
    remember: bool = False

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return _validate_email(v)


class SetTierRequest(BaseModel):
    email: str
    tier: str


class RevokeSessionsRequest(BaseModel):
    email: str


class MintTokenRequest(BaseModel):
    email: str
    expire_days: int = 1825  # ~5 años -- pensado para credenciales de
    # servicio (scripts), no para una sesión de usuario normal.


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


# El token ya NO se devuelve en el cuerpo de la respuesta: va en una cookie
# httpOnly que el navegador guarda y reenvía solo, y que JavaScript no puede
# leer (ver auth.py). Devolverlo además en el JSON dejaría al frontend la
# tentación de guardarlo en localStorage otra vez, que es justo el problema
# que esto cierra. /admin/mint-token sí lo sigue devolviendo, porque los
# tokens de servicio no tienen navegador donde guardar una cookie.
@router.post("/register", dependencies=[Depends(login_rate_limit)])
async def register(req: RegisterRequest, response: Response):
    user = users_service.create_user(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con este email")
    token = create_token({"sub": user["email"], "tier": user["tier"], "tv": user["token_version"]})
    set_session_cookie(response, token, max_age=settings.token_expire_minutes * 60)
    return {"ok": True, "tier": user["tier"], "email": user["email"]}


@router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login(req: LoginRequest, response: Response):
    user = users_service.authenticate(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    # "Mantener sesión" antes solo decidía DÓNDE se guardaba el token
    # (localStorage vs sessionStorage) pero el token en sí caducaba igual a
    # las 8h siempre — así que alguien cerraba el portátil por la noche y al
    # día siguiente el token ya llevaba horas caducado, aunque siguiera
    # "guardado". Ahora si se marca, el token dura 30 días de verdad.
    #
    # Y desde el paso a cookie, "mantener sesión" decide también cuánto vive
    # la cookie: sin marcar es de sesión (max_age=None, el navegador la tira
    # al cerrarse), marcada dura los mismos 30 días que el token que lleva
    # dentro. Antes esa correspondencia no existía y era la causa del fallo:
    # marcar la casilla guardaba el token en un sitio que media terminal no
    # miraba, así que la sesión moría al abrir cualquier módulo.
    minutos = 60 * 24 * 30 if req.remember else None  # None = usa el default (8h)
    token = create_token({"sub": user["email"], "tier": user["tier"], "tv": user["token_version"]}, expire_minutes=minutos)
    set_session_cookie(response, token, max_age=(minutos * 60) if minutos else None)
    return {"ok": True, "tier": user["tier"], "email": user["email"]}


@router.post("/logout")
async def logout(response: Response):
    """Cierra la sesión de ESTE navegador borrando la cookie. Sin
    verify_token a propósito: si el token ya caducó o se revocó, cerrar
    sesión tiene que seguir funcionando -- si no, la cookie se quedaría
    pegada hasta que expirase sola. Para cerrar sesión en todos los
    dispositivos a la vez está /logout-all-sessions, que sí invalida los
    tokens de verdad en la base de datos."""
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(payload: dict = Depends(verify_token)):
    # Igual que require_tier: se relee de la BD para reflejar un cambio de
    # tier reciente sin esperar a que expire el token viejo.
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    tier  = user["tier"] if user else payload.get("tier", "free")
    # Aceptado = aceptó la versión VIGENTE. Si el texto del descargo cambia
    # (users_service.DISCLAIMER_VERSION sube), esto pasa a False y el modal
    # vuelve a salir — ver users_service.disclaimer_al_dia().
    disclaimer_accepted = users_service.disclaimer_al_dia(user)
    pricing_message_seen = bool(user and user.get("pricing_message_seen_at"))
    telegram_linked = bool(user and user.get("telegram_chat_id"))
    return {
        "email": email, "tier": tier,
        "disclaimer_accepted": disclaimer_accepted,
        # True solo si aceptó una versión ANTERIOR (distinto de no haberlo
        # aceptado nunca): el modal lo usa para explicar por qué se lo vuelve
        # a pedir a alguien que lleva meses usando la terminal.
        "disclaimer_actualizado": users_service.disclaimer_desactualizado(user),
        "disclaimer_version": users_service.DISCLAIMER_VERSION,
        "pricing_message_seen": pricing_message_seen,
        "telegram_linked": telegram_linked,
    }


@router.post("/logout-all-sessions")
async def logout_all_sessions(response: Response, payload: dict = Depends(verify_token)):
    """Invalida todos los tokens emitidos hasta ahora para este usuario
    (todos los dispositivos, todas las pestañas) -- útil tras sospechar
    que un token se filtró, o simplemente para forzar un cierre de sesión
    real en todas partes. El propio token usado en esta petición también
    queda invalidado -- el usuario tendrá que volver a iniciar sesión."""
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Token sin email asociado")
    users_service.revoke_sessions(email)
    # La cookie de este navegador se borra además de revocar los tokens: sin
    # esto seguiría enviándose en cada petición hasta caducar, provocando un
    # 401 tras otro en vez de un cierre de sesión limpio.
    clear_session_cookie(response)
    return {"ok": True, "detail": "Todas las sesiones han sido cerradas. Vuelve a iniciar sesión."}


@router.post("/accept-disclaimer")
async def accept_disclaimer(payload: dict = Depends(verify_token)):
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return users_service.accept_disclaimer(user["id"])


@router.post("/acknowledge-pricing")
async def acknowledge_pricing(payload: dict = Depends(verify_token)):
    """Marca como visto el mensaje de transparencia de costes -- se
    muestra una sola vez, justo después del disclaimer, en el mismo flujo
    de bienvenida para usuarios nuevos."""
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return users_service.acknowledge_pricing_message(user["id"])


@router.post("/telegram-link")
async def telegram_link(payload: dict = Depends(verify_token)):
    """Genera un código de un solo uso (caduca en 15 min) para vincular la
    cuenta a Telegram vía deep-link -- el usuario lo abre, Telegram le manda
    automáticamente '/start <código>' al bot, y el bucle de long-polling
    (ver services/telegram_service.py) lo consume y guarda su chat_id. Si
    el bot no está configurado en este entorno, error explícito en vez de
    un código que nunca podrá usarse."""
    from config import settings
    if not getattr(settings, "telegram_bot_token", "") or not getattr(settings, "telegram_bot_username", ""):
        raise HTTPException(status_code=503, detail="Notificaciones de Telegram no configuradas en este servidor")
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    code, expires_at = users_service.create_telegram_link_code(user["id"])
    deep_link = f"https://t.me/{settings.telegram_bot_username}?start={code}"
    return {"ok": True, "code": code, "deep_link": deep_link, "expires_at": expires_at}


@router.post("/telegram-unlink")
async def telegram_unlink(payload: dict = Depends(verify_token)):
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return users_service.unlink_telegram(user["id"])


@router.post("/admin/set-tier")
async def admin_set_tier(req: SetTierRequest, _admin: None = Depends(verify_admin_key)):
    """Sube (o baja) manualmente el tier de un usuario.

    De momento no hay pasarela de pago integrada: esto es lo que usa Marc
    a mano (curl/Postman) para pasar a alguien de 'free' a 'tier1'/'tiers'
    tras un pago manual (Stripe/Bizum/lo que sea), hasta que se automatice.
    Protegido con una clave de administrador (ADMIN_KEY en .env), no con el
    login de usuario normal.
    """
    if req.tier not in users_service.VALID_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"Tier inválido. Válidos: {sorted(users_service.VALID_TIERS)}"
        )
    ok = users_service.set_tier(req.email, req.tier)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True, "email": req.email.strip().lower(), "tier": req.tier}


@router.get("/admin/users")
async def admin_list_users(_admin: None = Depends(verify_admin_key)):
    return {"users": users_service.list_users()}


@router.post("/admin/reset-password")
async def admin_reset_password(req: ResetPasswordRequest, _admin: None = Depends(verify_admin_key)):
    """Stopgap manual mientras no haya email de recuperación: Marc fija una
    contraseña nueva (p.ej. una temporal) y se la pasa a la persona por otro
    canal (WhatsApp, etc.). No requiere conocer la contraseña anterior.
    """
    ok = users_service.reset_password(req.email, req.new_password)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True, "email": req.email.strip().lower()}


@router.post("/admin/revoke-sessions")
async def admin_revoke_sessions(req: RevokeSessionsRequest, _admin: None = Depends(verify_admin_key)):
    """Cierra todas las sesiones activas de un usuario sin tocar su
    contraseña -- p.ej. si sospechas que compartió su token sin querer, o
    quieres forzar un re-login tras cambiar algo de su cuenta a mano."""
    ok = users_service.revoke_sessions(req.email)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True, "email": req.email.strip().lower()}


@router.post("/admin/mint-token")
async def admin_mint_token(req: MintTokenRequest, _admin: None = Depends(verify_admin_key)):
    """Emite un token de larga duración para una cuenta ya existente --
    pensado para credenciales de SERVICIO (p.ej. daily_briefing.py
    llamando a un endpoint protegido), no para el login de una persona.
    Se recomienda usar una cuenta dedicada (no la personal del admin):
    /admin/revoke-sessions sube el token_version de la cuenta indicada, lo
    que invalidaría en silencio CUALQUIER token de esa cuenta, incluido
    este, si algún día se revocan las sesiones de la cuenta personal por
    otro motivo."""
    user = users_service.get_user_by_email(req.email.strip().lower())
    if user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    token = create_token(
        {"sub": user["email"], "tier": user["tier"], "tv": user["token_version"]},
        expire_minutes=req.expire_days * 24 * 60,
    )
    return {"access_token": token, "email": user["email"], "expire_days": req.expire_days}