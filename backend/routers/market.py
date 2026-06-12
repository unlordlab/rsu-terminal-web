from fastapi import APIRouter, Depends
from auth import verify_token
from services.market_service import (
    get_indices, get_fear_greed, get_forex,
    get_commodities, get_sectors,
    get_economic_calendar, get_vix_term_structure
)

router = APIRouter(prefix="/api/v1/market", tags=["market"])

@router.get("/indices")
async def indices(user=Depends(verify_token)):
    return get_indices()

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
async def sectors(user=Depends(verify_token)):
    return get_sectors()

@router.get("/calendar")
async def calendar(user=Depends(verify_token)):
    return get_economic_calendar()

@router.get("/vix")
async def vix(user=Depends(verify_token)):
    return get_vix_term_structure()