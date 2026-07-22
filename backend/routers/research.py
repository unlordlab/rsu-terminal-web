import re
from fastapi import APIRouter, Depends
from auth import verify_token
from services.research_service import get_research

router = APIRouter(prefix="/api/v1/research", tags=["research"])

# Cierra en origen el XSS reflejado vía ?ticker= (ver auditoría de Research
# #4): un ticker que no encaja en este patrón ni siquiera llega a
# get_research(), así que tampoco puede acabar reflejado en ningún sitio.
_TICKER_RE = re.compile(r"^[A-Z0-9.\-^=]{1,12}$")

@router.get("/{ticker}")
async def research(ticker: str, user=Depends(verify_token)):
    if not _TICKER_RE.match(ticker.upper()):
        return {"ok": False, "error": "Ticker inválido"}
    return get_research(ticker)