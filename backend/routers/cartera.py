from fastapi import APIRouter, Depends
from auth import verify_token
from services.cartera_service import get_cartera, fetch_live_prices, fetch_sparklines

router = APIRouter(prefix="/api/v1/cartera", tags=["cartera"])

@router.get("/")
async def cartera(user=Depends(verify_token)):
    return get_cartera()

@router.get("/prices")
async def cartera_prices(user=Depends(verify_token)):
    """Precios live de las posiciones abiertas — con caché 60s."""
    import asyncio
    data = get_cartera()
    if not data.get("ok"):
        return {"ok": False, "prices": []}
    tickers = [p["ticker"] for p in data.get("abiertas", [])]
    if not tickers:
        return {"ok": True, "prices": []}
    loop   = asyncio.get_event_loop()
    prices = await loop.run_in_executor(None, fetch_live_prices, tickers)
    return {"ok": True, "prices": list(prices.values())}

@router.get("/sparklines")
async def cartera_sparklines(days: int = 30, user=Depends(verify_token)):
    """Series de cierre (últimos N días) por ticker abierto — para los sparklines de fila."""
    import asyncio
    data = get_cartera()
    if not data.get("ok"):
        return {"ok": False, "sparklines": {}}
    tickers = [p["ticker"] for p in data.get("abiertas", [])]
    if not tickers:
        return {"ok": True, "sparklines": {}}
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, fetch_sparklines, tickers, days)
    return {"ok": True, "sparklines": {t: r["closes"] for t, r in result.items()}}