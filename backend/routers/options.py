from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services.options_service import (
    get_options_flow, get_options_ticker,
    save_current_scan, get_history_from_db,
    get_db_stats, get_repeat_signals,
    get_ticker_history_summary, init_db,
    get_options_flow_simple, get_ticker_flow_simple, get_oi_changes,
)

router = APIRouter(prefix="/api/v1/options", tags=["options"])
init_db()

# ── VERSIÓN SIMPLE — la que usa el frontend rediseñado (sin ruido) ─────────────

@router.get("/flow-simple")
async def flow_simple(user=Depends(verify_token)):
    return get_options_flow_simple()

@router.get("/ticker-flow/{ticker}")
async def ticker_flow(ticker: str, period: str = Query("1w"), user=Depends(verify_token)):
    return get_ticker_flow_simple(ticker, period)

@router.get("/oi-changes")
async def oi_changes(user=Depends(verify_token)):
    return get_oi_changes()

@router.post("/scan-now")
async def scan_now(user=Depends(verify_token)):
    """Dispara el escaneo+guardado ahora mismo, en vez de esperar al loop
    programado (corre 1h tras arrancar, luego cada 24h) — útil justo después
    de desplegar, cuando la base de datos todavía está vacía. Es un escaneo
    pesado (~150 tickers x 5 vencimientos vía yfinance), puede tardar un rato."""
    from services.options_service import run_and_save_scan
    return run_and_save_scan()

# ── VERSIÓN ANTERIOR — se deja por compatibilidad, ya no la usa el frontend ────

@router.get("/flow")
async def options_flow(
    min_premium: float = Query(100000, ge=0),
    min_score:   int   = Query(4, ge=0, le=10),
    user=Depends(verify_token)
):
    return get_options_flow(min_premium=min_premium, min_score=min_score)

@router.post("/save")
async def save_scan(body: dict, user=Depends(verify_token)):
    return save_current_scan(body)

@router.get("/history")
async def history(
    ticker: str = Query(None),
    period: str = Query("1w"),
    user=Depends(verify_token)
):
    rows = get_history_from_db(ticker=ticker, period=period)
    return {"ok": True, "records": rows, "total": len(rows), "period": period}

@router.get("/repeats")
async def repeats(
    days:        int = Query(7, ge=1, le=90),
    min_repeats: int = Query(2, ge=2),
    user=Depends(verify_token)
):
    return {"ok": True, "signals": get_repeat_signals(days, min_repeats)}

@router.get("/ticker-summary/{ticker}")
async def ticker_summary(ticker: str, user=Depends(verify_token)):
    return get_ticker_history_summary(ticker)

@router.get("/stats")
async def stats(user=Depends(verify_token)):
    return get_db_stats()

@router.get("/ticker/{ticker}")
async def options_ticker(ticker: str, user=Depends(verify_token)):
    return get_options_ticker(ticker)