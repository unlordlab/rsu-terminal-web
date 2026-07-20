from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import verify_admin_key
from services.meeting_room_service import enviar_mensaje, get_historial

# Router aislado, solo X-Admin-Key -- mismo patrón que tesis.admin_router,
# academy_review.router y laia_ethics.router (ver conversación 17-18/07/2026:
# nunca meter esto en el mismo router que exige sesión de usuario de pago).
#
# La comprobación de la clave ya no vive aquí -- deduplicada en
# auth.verify_admin_key (Fase 2.4 del Plan Maestro, 20/07/2026).
router = APIRouter(prefix="/api/v1/meeting-room", tags=["meeting-room"])


class NuevoMensaje(BaseModel):
    destinatario: str
    mensaje: str


@router.get("/historial")
async def historial(limit: int = 100, _admin: None = Depends(verify_admin_key)):
    return {"items": get_historial(limit=limit)}


@router.post("/enviar")
async def enviar(req: NuevoMensaje, _admin: None = Depends(verify_admin_key)):
    try:
        msg_id = enviar_mensaje(req.destinatario, req.mensaje)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "id": msg_id}