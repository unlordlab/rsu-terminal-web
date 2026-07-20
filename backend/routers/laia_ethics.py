from fastapi import APIRouter, Depends
from auth import verify_admin_key
from services.laia_ethics_service import get_veredictos

# Solo lectura -- Laia no tiene cola de aprobación, sus veredictos ya se
# enviaron a Telegram al generarse. Router aislado sin dependencia `paid`,
# mismo patrón que tesis.admin_router y academy_review.router.
#
# La comprobación de la clave ya no vive aquí -- deduplicada en
# auth.verify_admin_key (Fase 2.4 del Plan Maestro, 20/07/2026).
router = APIRouter(prefix="/api/v1/laia", tags=["laia-ethics"])


@router.get("/verdicts")
async def verdicts(limit: int = 30, _admin: None = Depends(verify_admin_key)):
    return {"items": get_veredictos(limit=limit)}