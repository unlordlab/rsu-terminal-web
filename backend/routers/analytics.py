from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from auth import decode_token, verify_admin_key
from services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


class TrackRequest(BaseModel):
    section: str


def _email_from_request(request: Request) -> str | None:
    authz = request.headers.get("authorization")
    if not authz or not authz.lower().startswith("bearer "):
        return None
    payload = decode_token(authz.split(" ", 1)[1])
    return payload.get("sub") if payload else None


@router.post("/track")
async def track(req: TrackRequest, request: Request):
    """Registra que un usuario ha entrado en una sección. Lo llama router.js
    en cada navegación.

    Deliberadamente NO exige token válido: si ha expirado o no hay, se
    guarda el evento como anónimo (email=None) en vez de fallar. Este
    endpoint es "fire and forget" desde el frontend — nunca debe poder
    romper ni ralentizar la navegación real del usuario.
    """
    email = _email_from_request(request)
    analytics_service.log_page_view(section=req.section, email=email)
    return {"ok": True}


@router.get("/summary")
async def summary(days: int = 30, _admin: None = Depends(verify_admin_key)):
    """Resumen agregado para el panel de administración: secciones más
    visitadas, tickers y tesis más consultados, actividad diaria.

    Protegido con la misma X-Admin-Key que el resto de endpoints /admin/*
    (comprobación deduplicada en auth.verify_admin_key, Fase 2.4).
    """
    return analytics_service.get_summary(days=days)


@router.get("/yfinance-health")
async def yfinance_health(hours: int = 24, _admin: None = Depends(verify_admin_key)):
    """Salud de las llamadas a yfinance por módulo (Índices, Sectores,
    Forex, Commodities...) en las últimas N horas — panel de admin,
    pestaña PETICIONES. Ver conversación 16/07/2026.
    """
    from services import yf_health
    return yf_health.summary(hours=hours)