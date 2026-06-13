from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.rsrw_service import get_rsrw_from_gist, get_rsrw_scan, get_rsrw_ticker

router = APIRouter(prefix="/api/v1/rsrw", tags=["rsrw"])

@router.get("/gist")
async def rsrw_gist(user=Depends(verify_token)):
    return get_rsrw_from_gist()

@router.get("/scan")
async def rsrw_scan(
    max_tickers: int = Query(150, ge=10, le=500),
    user=Depends(verify_token)
):
    return get_rsrw_scan(max_tickers)

@router.get("/ticker/{ticker}")
async def rsrw_ticker(ticker: str, user=Depends(verify_token)):
    return get_rsrw_ticker(ticker)