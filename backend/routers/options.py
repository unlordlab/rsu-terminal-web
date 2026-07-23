from fastapi import APIRouter, Depends, Query
from auth import verify_token
from services import users_service, watchlist_service
from services.insider_service import get_confluence_tickers
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


def _watchlist_tickers(user) -> set:
    """in_watchlist es por usuario -- mismo criterio que scanner.py/rsrw.py/
    insider.py. Ninguna función de options_service.py cachea su resultado
    (leen SQLite directo en cada llamada), así que aquí no hace falta
    copiar antes de mutar como sí hizo falta en insider.py/research.py."""
    user_id = users_service.get_user_id(user)
    return {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()

@router.get("/flow-simple")
async def flow_simple(user=Depends(verify_token)):
    result = get_options_flow_simple()
    watchlist_tickers  = _watchlist_tickers(user)
    confluence_tickers = get_confluence_tickers()
    for key in ("calls_bought", "puts_sold", "puts_bought", "calls_sold",
                "top_premium", "top_bullish", "top_bearish"):
        for row in result.get(key, []):
            row["in_watchlist"]  = row.get("ticker") in watchlist_tickers
            row["is_confluence"] = row.get("ticker") in confluence_tickers
    return result

@router.get("/ticker-flow/{ticker}")
async def ticker_flow(ticker: str, period: str = Query("1w"), user=Depends(verify_token)):
    result = get_ticker_flow_simple(ticker, period)
    if result.get("ok"):
        result["in_watchlist"]  = ticker.upper() in _watchlist_tickers(user)
        result["is_confluence"] = ticker.upper() in get_confluence_tickers()
    return result

@router.get("/oi-changes")
async def oi_changes(user=Depends(verify_token)):
    return get_oi_changes()

@router.post("/scan-now")
async def scan_now(user=Depends(verify_token)):
    """Dispara el escaneo+guardado ahora mismo. Desde la sesión 35, este
    es el endpoint que llama el cron de GitHub Actions
    (.github/workflows/options_scan.yml) a hora fija cada tarde tras el
    cierre de mercado -- antes había un loop en el propio proceso del
    backend que se auto-programaba 1h tras arrancar y luego cada 24h, así
    que la hora real dependía de cuándo se había reiniciado el
    contenedor. También sigue disponible para disparo manual (p.ej. justo
    después de un deploy, si la base de datos está vacía). Escaneo pesado
    (~570 tickers vía yfinance), puede tardar varios minutos."""
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