from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, field_validator
from auth import create_token, verify_token
from config import settings
from middleware.rate_limit import login_rate_limit
from services import users_service

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


class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def _password(cls, v):
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        return v


@router.post("/register", dependencies=[Depends(login_rate_limit)])
async def register(req: RegisterRequest):
    user = users_service.create_user(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con este email")
    token = create_token({"sub": user["email"], "tier": user["tier"], "tv": user["token_version"]})
    return {"access_token": token, "token_type": "bearer", "tier": user["tier"], "email": user["email"]}


@router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login(req: LoginRequest):
    user = users_service.authenticate(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    # "Mantener sesión" antes solo decidía DÓNDE se guardaba el token
    # (localStorage vs sessionStorage) pero el token en sí caducaba igual a
    # las 8h siempre — así que alguien cerraba el portátil por la noche y al
    # día siguiente el token ya llevaba horas caducado, aunque siguiera
    # "guardado". Ahora si se marca, el token dura 30 días de verdad.
    minutos = 60 * 24 * 30 if req.remember else None  # None = usa el default (8h)
    token = create_token({"sub": user["email"], "tier": user["tier"], "tv": user["token_version"]}, expire_minutes=minutos)
    return {"access_token": token, "token_type": "bearer", "tier": user["tier"], "email": user["email"]}


@router.get("/me")
async def me(payload: dict = Depends(verify_token)):
    # Igual que require_tier: se relee de la BD para reflejar un cambio de
    # tier reciente sin esperar a que expire el token viejo.
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    tier  = user["tier"] if user else payload.get("tier", "free")
    disclaimer_accepted = bool(user and user.get("disclaimer_accepted_at"))
    return {"email": email, "tier": tier, "disclaimer_accepted": disclaimer_accepted}


@router.post("/logout-all-sessions")
async def logout_all_sessions(payload: dict = Depends(verify_token)):
    """Invalida todos los tokens emitidos hasta ahora para este usuario
    (todos los dispositivos, todas las pestañas) -- útil tras sospechar
    que un token se filtró, o simplemente para forzar un cierre de sesión
    real en todas partes. El propio token usado en esta petición también
    queda invalidado -- el usuario tendrá que volver a iniciar sesión."""
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=400, detail="Token sin email asociado")
    users_service.revoke_sessions(email)
    return {"ok": True, "detail": "Todas las sesiones han sido cerradas. Vuelve a iniciar sesión."}


@router.post("/accept-disclaimer")
async def accept_disclaimer(payload: dict = Depends(verify_token)):
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return users_service.accept_disclaimer(user["id"])


@router.post("/admin/set-tier")
async def admin_set_tier(req: SetTierRequest, x_admin_key: str = Header(None)):
    """Sube (o baja) manualmente el tier de un usuario.

    De momento no hay pasarela de pago integrada: esto es lo que usa Marc
    a mano (curl/Postman) para pasar a alguien de 'free' a 'tier1'/'tiers'
    tras un pago manual (Stripe/Bizum/lo que sea), hasta que se automatice.
    Protegido con una clave de administrador (ADMIN_KEY en .env), no con el
    login de usuario normal.
    """
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
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
async def admin_list_users(x_admin_key: str = Header(None)):
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
    return {"users": users_service.list_users()}


@router.post("/admin/reset-password")
async def admin_reset_password(req: ResetPasswordRequest, x_admin_key: str = Header(None)):
    """Stopgap manual mientras no haya email de recuperación: Marc fija una
    contraseña nueva (p.ej. una temporal) y se la pasa a la persona por otro
    canal (WhatsApp, etc.). No requiere conocer la contraseña anterior.
    """
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
    ok = users_service.reset_password(req.email, req.new_password)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True, "email": req.email.strip().lower()}


@router.post("/admin/revoke-sessions")
async def admin_revoke_sessions(req: RevokeSessionsRequest, x_admin_key: str = Header(None)):
    """Cierra todas las sesiones activas de un usuario sin tocar su
    contraseña -- p.ej. si sospechas que compartió su token sin querer, o
    quieres forzar un re-login tras cambiar algo de su cuenta a mano."""
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
    ok = users_service.revoke_sessions(req.email)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"ok": True, "email": req.email.strip().lower()}