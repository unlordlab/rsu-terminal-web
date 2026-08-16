from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import verify_token
from services import users_service, watchlist_service
from services.scanner_service import get_scanner_data, run_filter

router = APIRouter(prefix="/api/v1/scanner", tags=["scanner"])

@router.get("/universe")
async def scanner_universe(user=Depends(verify_token)):
    return get_scanner_data()

@router.get("/divergencia")
async def scanner_divergencia(user=Depends(verify_token)):
    """Amplitud del S&P 500 frente a la del Russell 2000, por separado."""
    from services.scanner_service import get_divergencia_universos
    return get_divergencia_universos()


@router.get("/transiciones")
async def scanner_transiciones(
    sesiones: int = Query(5, ge=1, le=60),
    user=Depends(verify_token),
):
    """Quién ha entrado y salido de la fase de avance. Sale del histórico que
    snapshots.db ya venía guardando; no cuesta ninguna descarga."""
    from services.snapshots_service import transiciones_de_fase
    return transiciones_de_fase(sesiones=sesiones)


@router.get("/filter")
async def scanner_filter(
    rvol_min: Optional[float] = Query(None, ge=0),
    rs_min: Optional[float] = Query(None, ge=0, le=100),
    score_min: Optional[float] = Query(None, ge=0, le=100),
    phase: Optional[int] = Query(None, ge=1, le=4),
    sector: Optional[str] = Query(None),
    new_high_only: Optional[bool] = Query(None),
    absorcion_min: Optional[int] = Query(None, ge=0, le=10),
    l3_zona_baja: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user=Depends(verify_token),
):
    result = run_filter(
        rvol_min=rvol_min, rs_min=rs_min, score_min=score_min,
        phase=phase, sector=sector, new_high_only=new_high_only,
        absorcion_min=absorcion_min, l3_zona_baja=l3_zona_baja, limit=limit,
    )
    # in_watchlist se añade aquí, fuera de cualquier caché compartida --
    # es por usuario, a diferencia de en_cartera (Cartera es única/global,
    # ver cartera_service.get_cartera_tickers()).
    user_id = users_service.get_user_id(user)
    watchlist_tickers = (
        {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()
    )
    for row in result.get("results", []):
        row["in_watchlist"] = row.get("ticker") in watchlist_tickers
    return result