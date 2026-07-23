import copy
from fastapi import APIRouter, Depends
from auth import verify_token
from services import users_service, watchlist_service
from services.congress_service import get_congress_feed, get_congress_clusters, get_congress_ticker

router = APIRouter(prefix="/api/v1/congress", tags=["congress"])


def _watchlist_tickers(user) -> set:
    user_id = users_service.get_user_id(user)
    return {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()


@router.get("/feed")
async def feed(user=Depends(verify_token)):
    result = copy.deepcopy(get_congress_feed())
    wl = _watchlist_tickers(user)
    for row in result.get("buys", []) + result.get("sells", []):
        row["in_watchlist"] = row.get("ticker") in wl
    return result


@router.get("/clusters")
async def clusters(user=Depends(verify_token)):
    result = copy.deepcopy(get_congress_clusters())
    wl = _watchlist_tickers(user)
    for c in result.get("clusters", []):
        c["in_watchlist"] = c.get("ticker") in wl
    return result


@router.get("/ticker/{ticker}")
async def ticker(ticker: str, user=Depends(verify_token)):
    result = get_congress_ticker(ticker)
    if result.get("ok"):
        result["in_watchlist"] = ticker.upper() in _watchlist_tickers(user)
    return result
