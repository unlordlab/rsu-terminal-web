from fastapi import APIRouter, Depends
from auth import verify_token
from services.btc_stratum_service import get_btc_dashboard, get_btc_backtest

router = APIRouter(prefix="/api/v1/btc-stratum", tags=["btc-stratum"])

@router.get("/dashboard")
async def dashboard(user=Depends(verify_token)):
    return get_btc_dashboard()

@router.get("/backtest")
async def backtest(user=Depends(verify_token)):
    return get_btc_backtest()