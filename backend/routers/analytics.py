import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, field_validator
from auth import decode_token, verify_admin_key, COOKIE_NAME
from services import analytics_service

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])

# Rutas de la SPA: barra inicial, minúsculas, dígitos y guiones. Nada más.
# Todas las secciones reales encajan aquí ("/", "/market", "/btc-stratum"...).
_SECTION_RE = re.compile(r"^/[a-z0-9\-/]{0,40}$")


class TrackRequest(BaseModel):
    section: str

    @field_validator("section")
    @classmethod
    def _validar_section(cls, v: str) -> str:
        # /track es un endpoint de ESCRITURA ANÓNIMO: no exige token a
        # propósito (ver el docstring de track()). Aceptar texto libre en un
        # sitio así fue una cadena de ataque real, demostrada de extremo a
        # extremo el 08/08: bastaba un POST sin cuenta con
        # section="<img src=x onerror=...>" para que el texto se guardara,
        # saliera por /summary y el panel de admin lo pintara sin escapar en
        # la pestaña de Métricas -- ejecución de código con la sesión del
        # admin, y de ahí la ADMIN_KEY, que entonces vivía en sessionStorage.
        # Se arreglaron los tres eslabones; este es el primero, y el que
        # impide que la basura llegue siquiera a guardarse.
        v = (v or "").strip()
        if not _SECTION_RE.match(v):
            raise ValueError("Sección no válida")
        return v


def _email_from_request(request: Request) -> str | None:
    """Quién ha visitado, si se puede saber. Mira primero la cookie de
    sesión y luego la cabecera Bearer -- mismo orden que verify_token().

    La cookie NO es opcional aquí: desde que la sesión pasó a cookie
    httpOnly, el frontend ya no manda cabecera Authorization, así que
    mirar solo la cabecera dejaba TODAS las visitas como anónimas y las
    métricas por usuario del panel se habrían ido apagando en silencio."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        authz = request.headers.get("authorization")
        if not authz or not authz.lower().startswith("bearer "):
            return None
        token = authz.split(" ", 1)[1]
    payload = decode_token(token)
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