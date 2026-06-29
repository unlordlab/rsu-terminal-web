from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.rsu_algoritmo_service import get_rsu_algoritmo, get_rsu_algoritmo_backtest

router = APIRouter(prefix="/api/v1/algoritmo", tags=["algoritmo"])

@router.get("/")
async def algoritmo(user=Depends(verify_token)):
    return get_rsu_algoritmo()

@router.get("/backtest")
async def algoritmo_backtest(years: int = Query(10, ge=2, le=15), user=Depends(verify_token)):
    return get_rsu_algoritmo_backtest(years=years)