import copy
from fastapi import APIRouter, Depends
from auth import verify_token
from services import users_service, watchlist_service
from services.insider_service import (
    get_insider_feed, get_insider_ticker, get_insider_clusters, get_confluence_tickers,
)

router = APIRouter(prefix="/api/v1/insider", tags=["insider"])


def _watchlist_tickers(user) -> set:
    """in_watchlist es por usuario -- fuera de cualquier caché compartida,
    mismo criterio que scanner.py/rsrw.py."""
    user_id = users_service.get_user_id(user)
    return {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()


def _tag_rows(rows: list, watchlist_tickers: set, confluence_tickers: set):
    for row in rows:
        t = row.get("ticker")
        row["in_watchlist"]  = t in watchlist_tickers
        row["is_confluence"] = t in confluence_tickers

@router.get("/feed")
async def feed(user=Depends(verify_token)):
    result = get_insider_feed()
    watchlist_tickers = _watchlist_tickers(user)
    confluence_tickers = get_confluence_tickers()
    _tag_rows(result.get("buys", []), watchlist_tickers, confluence_tickers)
    _tag_rows(result.get("sells", []), watchlist_tickers, confluence_tickers)
    return result

@router.get("/ticker/{ticker}")
async def ticker(ticker: str, user=Depends(verify_token)):
    # get_insider_ticker() cachea 1h -- copiar antes de mutar (mismo motivo
    # que get_insider_clusters() más abajo).
    result = dict(get_insider_ticker(ticker.upper()))
    result["in_watchlist"] = ticker.upper() in _watchlist_tickers(user)
    return result

@router.get("/clusters")
async def clusters(user=Depends(verify_token)):
    # get_insider_clusters() cachea 30 min y services/cache.py (L1) guarda
    # la MISMA referencia, no una copia -- mutar "clusters" in-place
    # filtraría el in_watchlist/is_confluence de un usuario a la respuesta
    # cacheada que ve el siguiente. deepcopy porque lo que se muta es una
    # lista anidada de dicts, no solo una clave de primer nivel.
    result = copy.deepcopy(get_insider_clusters())
    _tag_rows(result.get("clusters", []), _watchlist_tickers(user), get_confluence_tickers())
    return result