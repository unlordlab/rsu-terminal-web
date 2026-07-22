from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services import users_service, watchlist_service
from services.rsrw_service import get_rsrw_from_gist, get_rsrw_scan, get_rsrw_ticker

router = APIRouter(prefix="/api/v1/rsrw", tags=["rsrw"])


def _tag_watchlist(result: dict, user) -> dict:
    """in_watchlist en leaders/laggards -- por usuario, fuera de cualquier
    caché compartida (Fase 3 del roadmap, mismo criterio que scanner.py)."""
    user_id = users_service.get_user_id(user)
    watchlist_tickers = (
        {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()
    )
    for key in ("leaders", "laggards"):
        for row in result.get(key, []):
            row["in_watchlist"] = row.get("ticker") in watchlist_tickers
    return result

@router.get("/gist")
async def rsrw_gist(user=Depends(verify_token)):
    return _tag_watchlist(get_rsrw_from_gist(), user)

@router.get("/scan")
async def rsrw_scan(
    max_tickers: int = Query(500, ge=10, le=510),
    user=Depends(verify_token)
):
    return _tag_watchlist(get_rsrw_scan(max_tickers), user)

@router.get("/ticker/{ticker}")
async def rsrw_ticker(ticker: str, user=Depends(verify_token)):
    return get_rsrw_ticker(ticker)