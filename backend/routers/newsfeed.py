from fastapi import APIRouter, Depends, Query
from typing import Optional
from auth import verify_token
from services.newsfeed_service import get_newsfeed, get_newsfeed_prices, get_trump_feed

router = APIRouter(prefix="/api/v1/newsfeed", tags=["newsfeed"])

@router.get("/")
async def newsfeed(
    impact: Optional[str] = Query(None),
    sector: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    # max_length acotado: `q` solo se usa como subcadena en memoria (no toca
    # SQL ni el sistema de ficheros), pero no hay motivo para aceptar una
    # cadena de un megabyte y recorrer con ella 120 titulares.
    q:      Optional[str] = Query(None, max_length=80),
    limit:  int           = Query(50, ge=1, le=200),
    user=Depends(verify_token)
):
    return get_newsfeed(impact=impact, sector=sector, source=source, q=q, limit=limit)

@router.get("/prices")
async def prices(user=Depends(verify_token)):
    return get_newsfeed_prices()

@router.get("/trump")
async def trump_feed(
    limit: int = Query(15, ge=1, le=30),
    user=Depends(verify_token)
):
    return get_trump_feed(limit=limit)