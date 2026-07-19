from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from config import settings
from services.meeting_room_service import enviar_mensaje, get_historial

# Router aislado, solo X-Admin-Key -- mismo patrón que tesis.admin_router,
# academy_review.router y laia_ethics.router (ver conversación 17-18/07/2026:
# nunca meter esto en el mismo router que exige sesión de usuario de pago).
router = APIRouter(prefix="/api/v1/meeting-room", tags=["meeting-room"])


def _check_admin(x_admin_key: str):
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")


class NuevoMensaje(BaseModel):
    destinatario: str
    mensaje: str


@router.get("/historial")
async def historial(limit: int = 100, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    return {"items": get_historial(limit=limit)}


@router.post("/enviar")
async def enviar(req: NuevoMensaje, x_admin_key: str = Header(None)):
    _check_admin(x_admin_key)
    try:
        msg_id = enviar_mensaje(req.destinatario, req.mensaje)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "id": msg_id}