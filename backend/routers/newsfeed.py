from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import verify_token
from services.newsfeed_service import get_newsfeed, get_newsfeed_prices

router = APIRouter(prefix="/api/v1/newsfeed", tags=["newsfeed"])

@router.get("/")
async def newsfeed(
    impact: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    limit:  int           = Query(50, ge=1, le=200),
    user=Depends(verify_token)
):
    return get_newsfeed(impact=impact, sector=sector, limit=limit)

@router.get("/prices")
async def prices(user=Depends(verify_token)):
    return get_newsfeed_prices()