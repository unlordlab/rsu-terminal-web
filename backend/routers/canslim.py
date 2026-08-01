import copy

from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services import users_service, watchlist_service
from services.canslim_service import analyze_ticker, scan_canslim, get_market_status, get_canslim_from_gist

router = APIRouter(prefix="/api/v1/canslim", tags=["canslim"])


def _watchlist_tickers(user) -> set:
    """in_watchlist es POR USUARIO, así que se calcula aquí y nunca dentro de
    una función cacheada -- mismo criterio que scanner.py, rsrw.py e
    insider.py (sesión 16). `en_cartera`, en cambio, sí vive en el servicio:
    la Cartera es única y global en esta aplicación."""
    user_id = users_service.get_user_id(user)
    return {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()


def _marcar_watchlist(filas: list, tickers: set) -> None:
    for fila in filas:
        fila["in_watchlist"] = fila.get("ticker") in tickers


@router.get("/market")
async def market(user=Depends(verify_token)):
    return get_market_status()


@router.get("/gist")
async def gist(user=Depends(verify_token)):
    # get_canslim_from_gist() cachea 10 min y services/cache.py (L1) devuelve
    # la MISMA referencia, no una copia: marcar in_watchlist in-place
    # filtraría la watchlist de un usuario a la respuesta que ve el
    # siguiente. deepcopy porque lo que se muta es una lista de dicts
    # anidada, no una clave de primer nivel.
    result = copy.deepcopy(get_canslim_from_gist())
    _marcar_watchlist(result.get("candidates", []), _watchlist_tickers(user))
    return result


@router.get("/analyze/{ticker}")
async def analyze(ticker: str, user=Depends(verify_token)):
    result = analyze_ticker(ticker)
    if result.get("ok"):
        result["in_watchlist"] = result.get("ticker") in _watchlist_tickers(user)
    return result


@router.get("/scan")
async def scan(
    min_score: int = Query(40, ge=0, le=100),
    max_results: int = Query(50, ge=1, le=200),
    user=Depends(verify_token)
):
    # scan_canslim() no cachea su resultado -- solo deja el universo de
    # percentiles en caché como efecto secundario-, así que aquí no hace
    # falta copiar antes de marcar.
    result = scan_canslim(min_score, max_results)
    _marcar_watchlist(result.get("candidates", []), _watchlist_tickers(user))
    return result
