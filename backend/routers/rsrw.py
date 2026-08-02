from fastapi import APIRouter, Depends
from auth import verify_token
from services import users_service, watchlist_service
from services.rsrw_service import get_rsrw_from_gist, get_rsrw_ticker, get_rs_movimientos

router = APIRouter(prefix="/api/v1/rsrw", tags=["rsrw"])


def _watchlist_tickers(user) -> set:
    """La watchlist es POR USUARIO, así que se resuelve aquí y nunca dentro de
    una función cacheada (Fase 3 del roadmap, mismo criterio que scanner.py)."""
    user_id = users_service.get_user_id(user)
    return {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()


def _tag_watchlist(result: dict, user) -> dict:
    """in_watchlist en leaders/laggards."""
    watchlist_tickers = _watchlist_tickers(user)
    for key in ("leaders", "laggards"):
        for row in result.get(key, []):
            row["in_watchlist"] = row.get("ticker") in watchlist_tickers
    return result

@router.get("/gist")
async def rsrw_gist(user=Depends(verify_token)):
    return _tag_watchlist(get_rsrw_from_gist(), user)

# GET /scan retirado el 30/07/2026: descargaba ~500 tickers dentro de la
# petición, bloqueando el event loop. Nadie lo llamaba (cero referencias en
# frontend/) y la propia UI ya anunciaba "scan nocturno automático, sin scan
# on-demand". El cálculo vive en scripts/rsrw_scan.py. Ver auditoría RS/RW #3.

@router.get("/movimientos")
async def rsrw_movimientos(ventana: int = 10, user=Depends(verify_token)):
    """Cómo ha cambiado el percentil RS en las últimas sesiones: quién entra
    y quién sale del grupo de líderes, y quién más se mueve. Lee de
    snapshots.db, que ya guardaba el dato cada noche sin que nadie lo
    consultara. `ventana` se acota para que nadie pida un histórico que no
    existe ni fuerce una lectura desmedida."""
    ventana = max(2, min(int(ventana), 60))
    result = get_rs_movimientos(ventana)
    if result.get("ok"):
        watchlist = _watchlist_tickers(user)
        for key in ("nuevos_lideres", "lideres_perdidos", "mas_suben", "mas_bajan"):
            for row in result.get(key, []):
                row["in_watchlist"] = row.get("ticker") in watchlist
    return result


@router.get("/ticker/{ticker}")
async def rsrw_ticker(ticker: str, user=Depends(verify_token)):
    return get_rsrw_ticker(ticker)