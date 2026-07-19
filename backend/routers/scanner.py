from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import verify_token
from services.scanner_service import get_scanner_data, run_filter

router = APIRouter(prefix="/api/v1/scanner", tags=["scanner"])

@router.get("/universe")
async def scanner_universe(user=Depends(verify_token)):
    return get_scanner_data()

@router.get("/filter")
async def scanner_filter(
    rvol_min: Optional[float] = Query(None, ge=0),
    rs_min: Optional[float] = Query(None, ge=0, le=100),
    score_min: Optional[float] = Query(None, ge=0, le=100),
    phase: Optional[int] = Query(None, ge=1, le=4),
    sector: Optional[str] = Query(None),
    new_high_only: Optional[bool] = Query(None),
    absorcion_min: Optional[int] = Query(None, ge=0, le=10),
    limit: int = Query(100, ge=1, le=500),
    user=Depends(verify_token),
):
    return run_filter(
        rvol_min=rvol_min, rs_min=rs_min, score_min=score_min,
        phase=phase, sector=sector, new_high_only=new_high_only,
        absorcion_min=absorcion_min, limit=limit,
    )