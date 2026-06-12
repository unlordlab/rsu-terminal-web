from fastapi import APIRouter, Depends
from auth import verify_token
from services.rsu_algoritmo_service import get_rsu_algoritmo

router = APIRouter(prefix="/api/v1/algoritmo", tags=["algoritmo"])

@router.get("/")
async def algoritmo(user=Depends(verify_token)):
    return get_rsu_algoritmo()