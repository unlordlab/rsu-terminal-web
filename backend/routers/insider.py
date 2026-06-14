from fastapi import APIRouter, Depends
from auth import verify_token
from services.insider_service import get_insider_feed, get_insider_ticker, get_insider_clusters

router = APIRouter(prefix="/api/v1/insider", tags=["insider"])

@router.get("/feed")
async def feed(user=Depends(verify_token)):
    return get_insider_feed()

@router.get("/ticker/{ticker}")
async def ticker(ticker: str, user=Depends(verify_token)):
    return get_insider_ticker(ticker.upper())

@router.get("/clusters")
async def clusters(user=Depends(verify_token)):
    return get_insider_clusters()