from fastapi import APIRouter, Depends
from auth import verify_token
from services.market_service import get_indices, get_fear_greed

router = APIRouter(prefix="/api/v1/market", tags=["market"])

@router.get("/indices")
async def indices(user=Depends(verify_token)):
    return get_indices()

@router.get("/fear-greed")
async def fear_greed(user=Depends(verify_token)):
    return get_fear_greed()
