from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.tesis_service import get_tesis_list, get_tesis_detail

router = APIRouter(prefix="/api/v1/tesis", tags=["tesis"])

@router.get("/")
async def tesis_list(
    search:   str = Query(""),
    rating:   str = Query(""),
    page:     int = Query(1, ge=1),
    per_page: int = Query(9, ge=1, le=30),
    user=Depends(verify_token)
):
    return get_tesis_list(search=search, rating=rating, page=page, per_page=per_page)

@router.get("/{ticker}")
async def tesis_detail(
    ticker: str,
    fecha:  str = Query(""),
    user=Depends(verify_token)
):
    return get_tesis_detail(ticker=ticker, fecha=fecha)