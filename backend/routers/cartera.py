from fastapi import APIRouter, Depends
from auth import verify_token
from services.cartera_service import get_cartera

router = APIRouter(prefix="/api/v1/cartera", tags=["cartera"])

@router.get("/")
async def cartera(user=Depends(verify_token)):
    return get_cartera()