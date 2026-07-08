"""
Middleware ligero que detecta cuándo una petición a la API consulta un
ticker concreto (Research, RS/RW, CANSLIM, Options, Insider, Tesis, earnings
de Market) y lo registra en analytics.db a través de services/analytics_service.

Es un único punto de instrumentación: para trackear tickers en un endpoint
nuevo basta con añadir su patrón a TICKER_PATTERNS, sin tocar el router en
sí. Para el resto del tráfico (que es la mayoría de peticiones) el coste es
un simple match de regex sobre el path — no se toca el body ni la respuesta,
y solo se escribe en la base de datos cuando hay match y la petición ha ido
bien (status < 400), para no contar intentos fallidos o bloqueados por tier.
"""
import re
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from auth import decode_token
from services import analytics_service

# (regex, sección) — el grupo capturado es el ticker. La sección reutiliza
# el mismo path que usa el frontend para esa sección (para poder cruzar
# page_view y ticker_view de la misma sección si hiciera falta).
TICKER_PATTERNS = [
    (re.compile(r'^/api/v1/research/([A-Za-z0-9\.\-]{1,10})$'), '/research'),
    (re.compile(r'^/api/v1/rsrw/ticker/([A-Za-z0-9\.\-]{1,10})$'), '/rsrw'),
    (re.compile(r'^/api/v1/canslim/analyze/([A-Za-z0-9\.\-]{1,10})$'), '/canslim'),
    (re.compile(r'^/api/v1/options/ticker-summary/([A-Za-z0-9\.\-]{1,10})$'), '/options'),
    (re.compile(r'^/api/v1/options/ticker/([A-Za-z0-9\.\-]{1,10})$'), '/options'),
    (re.compile(r'^/api/v1/insider/ticker/([A-Za-z0-9\.\-]{1,10})$'), '/insider'),
    (re.compile(r'^/api/v1/market/earnings/([A-Za-z0-9\.\-]{1,10})$'), '/market'),
    (re.compile(r'^/api/v1/tesis/([A-Za-z0-9\.\-]{1,10})$'), '/tesis'),
]


def _match_ticker(path: str):
    for pattern, section in TICKER_PATTERNS:
        m = pattern.match(path)
        if m:
            return section, m.group(1)
    return None, None


class AnalyticsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        section, ticker = _match_ticker(request.url.path)
        response = await call_next(request)

        if section and ticker and response.status_code < 400:
            email = None
            authz = request.headers.get("authorization")
            if authz and authz.lower().startswith("bearer "):
                payload = decode_token(authz.split(" ", 1)[1])
                email = payload.get("sub") if payload else None
            # Insert en un hilo aparte para no bloquear el event loop con
            # I/O de disco (SQLite) en el camino caliente de la respuesta.
            asyncio.create_task(
                asyncio.to_thread(analytics_service.log_ticker_view, section, ticker, email)
            )

        return response