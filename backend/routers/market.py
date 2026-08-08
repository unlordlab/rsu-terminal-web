from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.market_service import (
    get_indices, get_fear_greed, get_forex,
    get_commodities, get_sectors,
    get_vix_term_structure,
    get_reddit_pulse, get_nightly_briefing,
    get_credit_spreads, get_market_breadth, get_shiller_cape,
    get_fed_macro, get_vix_levels, get_crypto_prices, get_crypto_fear_greed,
    get_liquidity, get_sector_composition, get_crypto_relative_strength
)
from services.earnings_service import get_earnings_calendar, get_earnings_ticker

router = APIRouter(prefix="/api/v1/market", tags=["market"])

@router.get("/vix-levels")
async def vix_levels(user=Depends(verify_token)):
    return get_vix_levels()

@router.get("/crypto")
async def crypto(user=Depends(verify_token)):
    return get_crypto_prices()

@router.get("/crypto-rs")
async def crypto_rs(top_n: int = 5, user=Depends(verify_token)):
    """Top N criptomonedas por fuerza relativa (momentum de precio a 30 días)
    sobre un universo más amplio que las 6 fijas del widget principal."""
    return get_crypto_relative_strength(top_n)

@router.get("/crypto-fear-greed")
async def crypto_fear_greed(user=Depends(verify_token)):
    return get_crypto_fear_greed()

@router.get("/breadth")
async def breadth(user=Depends(verify_token)):
    return get_market_breadth()

@router.get("/indices")
async def indices(user=Depends(verify_token)):
    return get_indices()

@router.get("/earnings")
async def earnings(user=Depends(verify_token)):
    return get_earnings_calendar()

@router.get("/earnings/{ticker}")
async def earnings_ticker(ticker: str, user=Depends(verify_token)):
    return get_earnings_ticker(ticker)

@router.get("/fear-greed")
async def fear_greed(user=Depends(verify_token)):
    return get_fear_greed()

@router.get("/sentimiento-historico")
async def sentimiento_historico(user=Depends(verify_token)):
    from services.snapshots_service import historico_sentimiento
    return historico_sentimiento()


@router.get("/put-call")
async def put_call(user=Depends(verify_token)):
    from services.putcall_service import get_put_call_ratio
    from services.cache import cache
    cacheado = cache.get("market:putcall")
    return cacheado if cacheado else get_put_call_ratio()

@router.get("/forex")
async def forex(user=Depends(verify_token)):
    return get_forex()

@router.get("/commodities")
async def commodities(user=Depends(verify_token)):
    return get_commodities()

@router.get("/sectors")
async def sectors(period: str = Query("1d"), user=Depends(verify_token)):
    return get_sectors(period=period)

@router.get("/vix")
async def vix(user=Depends(verify_token)):
    return get_vix_term_structure()

@router.get("/reddit")
async def reddit(user=Depends(verify_token)):
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, get_reddit_pulse)

@router.get("/briefing")
async def briefing(user=Depends(verify_token)):
    return get_nightly_briefing()

@router.get("/credit-spreads")
async def credit_spreads(user=Depends(verify_token)):
    return get_credit_spreads()

@router.get("/shiller-cape")
async def shiller_cape(user=Depends(verify_token)):
    return get_shiller_cape()

@router.get("/fed-macro")
async def fed_macro(user=Depends(verify_token)):
    return get_fed_macro()

@router.get("/liquidity")
async def liquidity(user=Depends(verify_token)):
    return get_liquidity()

@router.get("/sector-composition")
async def sector_composition(user=Depends(verify_token)):
    return get_sector_composition()