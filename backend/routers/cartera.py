from fastapi import APIRouter, Depends
from auth import verify_token, verify_owner
from services.cartera_service import get_cartera, fetch_live_prices, fetch_sparklines

router = APIRouter(prefix="/api/v1/cartera", tags=["cartera"])

@router.get("/")
async def cartera(user=Depends(verify_token)):
    return get_cartera()

@router.post("/notificaciones/check")
async def cartera_notificaciones_check(user=Depends(verify_owner)):
    """Fuerza la comprobación de aperturas/cierres nuevos ahora mismo, sin
    esperar a los 15 min del bucle periódico — lo llama el botón «Actualizar»
    de la página de Cartera.

    SOLO EL TITULAR (auditoría de Cartera, #B9). El resto del módulo es
    visible para cualquier usuario de pago, pero esto no: la cartera es una
    sola —la del titular— y los avisos van a SU Telegram, así que forzarlos
    no le sirve a nadie más. Lo que se cerró de verdad al restringirlo es que
    un usuario cualquiera decidiera CUÁNDO se manda un aviso al chat del
    dueño, y que consumiera él la reserva de dedupe de un aviso que no es
    suyo. Sin OWNER_EMAIL configurado no puede forzarlo nadie: el bucle de
    15 minutos sigue igual, solo se pierde la inmediatez."""
    from services.cartera_tracking_service import procesar_cartera_notificaciones
    return procesar_cartera_notificaciones()

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