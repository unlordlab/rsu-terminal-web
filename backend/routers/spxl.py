from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.spxl_service import (
    get_spxl_live, get_backtest, get_backtest_validation, get_backtest_con_slippage,
)

router = APIRouter(prefix="/api/v1/spxl", tags=["spxl"])

@router.get("/live")
async def live(user=Depends(verify_token)):
    return get_spxl_live()

@router.get("/backtest")
async def backtest(
    capital: float = Query(100000, ge=1000),
    user=Depends(verify_token)
):
    return get_backtest(capital)


@router.get("/backtest/validation")
async def backtest_validation(
    capital: float = Query(100000, ge=1000),
    user=Depends(verify_token)
):
    """Validación fuera de muestra: corre el backtest por separado en tres
    sub-periodos históricos independientes, para ver si el comportamiento se
    mantiene entre regímenes de mercado distintos. Ver Plan Maestro 3.7."""
    return get_backtest_validation(capital)


@router.get("/backtest/slippage")
async def backtest_slippage(
    capital: float = Query(100000, ge=1000),
    user=Depends(verify_token)
):
    """Rango de resultados según distintos niveles de coste de ejecución --
    el backtest base ejecuta al cierre sin spread ni deslizamiento. Ver
    Plan Maestro 3.8."""
    return get_backtest_con_slippage(capital)