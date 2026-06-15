from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.market_service import (
    get_indices, get_fear_greed, get_forex,
    get_commodities, get_sectors,
    get_economic_calendar, get_vix_term_structure,
    get_reddit_pulse, get_nightly_briefing,
    get_credit_spreads
)
from services.earnings_service import get_earnings_calendar, get_earnings_ticker

router = APIRouter(prefix="/api/v1/market", tags=["market"])

@router.get("/indices")
async def indices(user=Depends(verify_token)):
    return get_indices()

@router.get("/earnings")
async def earnings(user=Depends(verify_token)):
    return get_earnings_calendar()

@router.get("/earnings/{ticker}")
async def earnings_ticker(ticker: str, user=Depends(verify_token)):
    return get_earnings_ticker(ticker)

@router.get("/fear-greed")
async def fear_greed(user=Depends(verify_token)):
    return get_fear_greed()

@router.get("/forex")
async def forex(user=Depends(verify_token)):
    return get_forex()

@router.get("/commodities")
async def commodities(user=Depends(verify_token)):
    return get_commodities()

@router.get("/sectors")
async def sectors(period: str = Query("1d"), user=Depends(verify_token)):
    return get_sectors(period=period)

@router.get("/calendar")
async def calendar(user=Depends(verify_token)):
    return get_economic_calendar()

@router.get("/vix")
async def vix(user=Depends(verify_token)):
    return get_vix_term_structure()

@router.get("/reddit")
async def reddit(user=Depends(verify_token)):
    return get_reddit_pulse()

@router.get("/briefing")
async def briefing(user=Depends(verify_token)):
    return get_nightly_briefing()

@router.get("/credit-spreads")
async def credit_spreads(user=Depends(verify_token)):
    return get_credit_spreads()

@router.get("/fed-macro")
async def fed_macro():
    from services.market_service import get_fed_macro
    return get_fed_macro()