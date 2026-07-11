from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from auth import verify_token
from config import settings
from services import users_service, community_service

router = APIRouter(prefix="/api/v1/community", tags=["community"])


class FeedbackCreate(BaseModel):
    tipo: str = Field(..., description="'bug' | 'sugerencia' | 'otro'")
    mensaje: str = Field(..., min_length=1, max_length=3000)
    contacto: str = Field("", max_length=200, description="Email opcional para que Marc pueda responder")


@router.post("/feedback")
async def create_feedback(body: FeedbackCreate, user=Depends(verify_token)):
    email = user.get("sub")
    account = users_service.get_user_by_email(email) if email else None
    user_id = account["id"] if account else None
    return community_service.submit_feedback(user_id, email, body.tipo, body.mensaje, body.contacto)


@router.get("/feedback")
async def list_feedback(x_admin_key: str = Header(None)):
    """Panel de Admin — mismo patrón X-Admin-Key que auth.py/analytics.py."""
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
    return community_service.get_all_feedback()


@router.post("/feedback/{feedback_id}/read")
async def mark_read(feedback_id: int, x_admin_key: str = Header(None)):
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
    return community_service.mark_feedback_read(feedback_id)