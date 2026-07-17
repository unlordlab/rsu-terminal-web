from fastapi import APIRouter, Header, HTTPException
from config import settings
from services.laia_ethics_service import get_veredictos

# Solo lectura -- Laia no tiene cola de aprobación, sus veredictos ya se
# enviaron a Telegram al generarse. Router aislado sin dependencia `paid`,
# mismo patrón que tesis.admin_router y academy_review.router.
router = APIRouter(prefix="/api/v1/laia", tags=["laia-ethics"])


@router.get("/verdicts")
async def verdicts(limit: int = 30, x_admin_key: str = Header(None)):
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=401, detail="Clave de administrador inválida")
    return {"items": get_veredictos(limit=limit)}