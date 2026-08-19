from fastapi import APIRouter, HTTPException, Depends, Response
from pydantic import BaseModel, field_validator
from auth import (
    create_token, verify_token, verify_admin_key, es_titular,
    set_session_cookie, clear_session_cookie,
    set_admin_cookie, clear_admin_cookie,
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


class BorrarCuentaRequest(BaseModel):
    # La contraseña, otra vez. Borrar es irreversible y la cookie de sesión
    # puede estar viva en un ordenador que el dueño dejó abierto -- pedirla
    # aquí es la diferencia entre "quien tenga la pestaña abierta" y "quien
    # sea la persona". Mismo criterio que cualquier acción destructiva.
    password: str


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
        # Para que la interfaz no ofrezca acciones que el backend va a
        # rechazar (hoy: forzar la comprobación de avisos de Cartera). Es una
        # pista de pintado, NO la barrera: quien mande la petición igualmente
        # se lleva un 403 de verify_owner.
        "es_titular": es_titular(payload),
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


@router.get("/mis-datos")
async def mis_datos(payload: dict = Depends(verify_token)):
    """Todo lo que la terminal guarda de quien lo pide, en un JSON.

    Derecho de acceso y de portabilidad (arts. 15 y 20 del RGPD). Hasta el
    18/08/2026 no existía ninguna forma de pedirlo: la única manera de saber
    qué se guardaba era leer el código."""
    from services.datos_personales_service import exportar
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return exportar(user["id"], user["email"])


@router.post("/borrar-cuenta")
async def borrar_cuenta(req: BorrarCuentaRequest, response: Response,
                        payload: dict = Depends(verify_token)):
    """Borra la cuenta y TODO lo asociado, de las cuatro bases donde vive.

    Derecho de supresión (art. 17 del RGPD). Es irreversible y no hay
    papelera, así que:
      - se exige la contraseña otra vez (una sesión abierta no basta),
      - se devuelve el recuento por tabla, para que el borrado se pueda
        comprobar en vez de creer,
      - se limpia la cookie, porque la sesión apunta a un usuario que ya no
        existe y dejarla puesta produce errores raros en la siguiente carga.

    Lo que NO se borra, y es deliberado: los datos de mercado (escaneos,
    snapshots, cadenas de opciones). Son precios públicos, no identifican a
    nadie, y no dejan de ser ciertos porque alguien se dé de baja."""
    from services.datos_personales_service import borrar
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    if not users_service.authenticate(email, req.password):
        raise HTTPException(status_code=401, detail="La contraseña no es correcta")

    resultado = borrar(user["id"], user["email"])
    clear_session_cookie(response)
    return resultado


@router.post("/admin/session")
async def admin_session(response: Response, _admin: None = Depends(verify_admin_key)):
    """Canjea la clave de administración por una cookie httpOnly.

    El panel la llama UNA vez, al introducir la clave, y a partir de ahí no
    vuelve a tocarla: la cookie viaja sola en cada petición y JavaScript no
    puede leerla. Antes la clave se guardaba en sessionStorage y se enviaba
    a mano en cada llamada, así que cualquier XSS en el panel se la llevaba
    -- y eso no era hipotético: el 08/08 se demostró la cadena entera desde
    un POST anónimo a /analytics/track.

    La comprobación de la clave la hace verify_admin_key, con su límite de
    intentos fallidos, así que este endpoint no puede usarse para probar
    claves a ciegas más rápido que cualquier otro."""
    # Si la dependencia ha dejado pasar la petición es porque la clave
    # recibida coincide exactamente con settings.admin_key (comparación en
    # tiempo constante), así que sembrar la cookie con ese valor es lo
    # mismo que sembrarla con la que vino, sin tener que leer la cabecera
    # aquí otra vez.
    set_admin_cookie(response, settings.admin_key)
    return {"ok": True}


@router.post("/admin/logout")
async def admin_logout(response: Response):
    """Cierra la sesión de administración de este navegador. Sin
    verify_admin_key a propósito, mismo criterio que /auth/logout: si la
    cookie ya no vale, poder deshacerse de ella no debe depender de que
    valga."""
    clear_admin_cookie(response)
    return {"ok": True}


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