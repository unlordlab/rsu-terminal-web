import re
from fastapi import APIRouter, Depends
from auth import verify_token
from services import users_service, watchlist_service
from services.research_service import get_research

router = APIRouter(prefix="/api/v1/research", tags=["research"])

# Cierra en origen el XSS reflejado vía ?ticker= (ver auditoría de Research
# #4): un ticker que no encaja en este patrón ni siquiera llega a
# get_research(), así que tampoco puede acabar reflejado en ningún sitio.
_TICKER_RE = re.compile(r"^[A-Z0-9.\-^=]{1,12}$")

# Registrada ANTES de /{ticker} -- si no, "score-tracking" se interpretaría
# como un ticker y esta ruta nunca se alcanzaría (mismo motivo por el que
# watchlist.py registra /alerts antes que /{ticker}).
@router.get("/score-tracking/resumen")
async def score_tracking_resumen(user=Depends(verify_token)):
    from services.rsu_score_tracking_service import obtener_resumen_por_bucket, obtener_historial
    return {"ok": True, "resumen": obtener_resumen_por_bucket(), "historial": obtener_historial(100)}

@router.get("/{ticker}")
async def research(ticker: str, user=Depends(verify_token)):
    if not _TICKER_RE.match(ticker.upper()):
        return {"ok": False, "error": "Ticker inválido"}
    result = get_research(ticker)
    # get_research() cachea el dict devuelto (services/cache.py L1 guarda
    # la MISMA referencia, no una copia) -- copiar antes de mutar, o
    # in_watchlist de un usuario se filtraría a la respuesta cacheada que
    # ve el siguiente usuario que pida el mismo ticker.
    if result.get("ok"):
        result = {**result}
    user_id = users_service.get_user_id(user)
    watchlist_tickers = (
        {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()
    )
    result["in_watchlist"] = ticker.upper() in watchlist_tickers
    return result