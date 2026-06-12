from fastapi import APIRouter, Depends
from auth import verify_token
from services.research_service import get_research

router = APIRouter(prefix="/api/v1/research", tags=["research"])

@router.get("/{ticker}")
async def research(ticker: str, user=Depends(verify_token)):
    return get_research(ticker)