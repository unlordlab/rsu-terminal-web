from fastapi import APIRouter, Depends
from pydantic import BaseModel
from auth import verify_token

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class MensajeIn(BaseModel):
    mensaje: str


def _usuario_id(user) -> str:
    """El objeto user viene de verify_token — es el payload del JWT (dict),
    con el email en la clave 'sub' (mismo patrón que backend/routers/community.py)."""
    return user.get("sub", "desconocido")


@router.post("/mensaje")
async def enviar_mensaje(body: MensajeIn, user=Depends(verify_token)):
    from services.chat_service import enviar_mensaje as _enviar
    return _enviar(_usuario_id(user), body.mensaje)


@router.get("/historial")
async def historial(user=Depends(verify_token)):
    from services.chat_service import obtener_historial
    return {"ok": True, "mensajes": obtener_historial(_usuario_id(user))}


@router.delete("/historial")
async def borrar_historial(user=Depends(verify_token)):
    from services.chat_service import borrar_historial as _borrar
    return _borrar(_usuario_id(user))