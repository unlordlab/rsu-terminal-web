from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.options_service import get_options_flow, get_options_ticker

router = APIRouter(prefix="/api/v1/options", tags=["options"])

@router.get("/flow")
async def options_flow(
    min_premium: float = Query(50000, ge=0),
    user=Depends(verify_token)
):
    return get_options_flow(min_premium=min_premium)

@router.get("/ticker/{ticker}")
async def options_ticker(ticker: str, user=Depends(verify_token)):
    return get_options_ticker(ticker)