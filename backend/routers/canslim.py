from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.canslim_service import analyze_ticker, scan_canslim, get_market_status, get_canslim_from_gist

router = APIRouter(prefix="/api/v1/canslim", tags=["canslim"])

@router.get("/market")
async def market(user=Depends(verify_token)):
    return get_market_status()

@router.get("/gist")
async def gist(user=Depends(verify_token)):
    return get_canslim_from_gist()

@router.get("/analyze/{ticker}")
async def analyze(ticker: str, user=Depends(verify_token)):
    return analyze_ticker(ticker)

@router.get("/scan")
async def scan(
    min_score: int = Query(40, ge=0, le=100),
    max_results: int = Query(50, ge=1, le=200),
    user=Depends(verify_token)
):
    return scan_canslim(min_score, max_results)