from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.spxl_service import get_spxl_live, get_backtest

router = APIRouter(prefix="/api/v1/spxl", tags=["spxl"])

@router.get("/live")
async def live(user=Depends(verify_token)):
    return get_spxl_live()

@router.get("/backtest")
async def backtest(
    capital: float = Query(100000, ge=1000),
    user=Depends(verify_token)
):
    return get_backtest(capital)