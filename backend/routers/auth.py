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

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return _validate_email(v)


class SetTierRequest(BaseModel):
    email: str
    tier: str


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
    token = create_token({"sub": user["email"], "tier": user["tier"]})
    return {"access_token": token, "token_type": "bearer", "tier": user["tier"], "email": user["email"]}


@router.post("/login", dependencies=[Depends(login_rate_limit)])
async def login(req: LoginRequest):
    user = users_service.authenticate(req.email, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Email o contraseña incorrectos")
    token = create_token({"sub": user["email"], "tier": user["tier"]})
    return {"access_token": token, "token_type": "bearer", "tier": user["tier"], "email": user["email"]}


@router.get("/me")
async def me(payload: dict = Depends(verify_token)):
    # Igual que require_tier: se relee de la BD para reflejar un cambio de
    # tier reciente sin esperar a que expire el token viejo.
    email = payload.get("sub")
    user  = users_service.get_user_by_email(email) if email else None
    tier  = user["tier"] if user else payload.get("tier", "free")
    return {"email": email, "tier": tier}


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

