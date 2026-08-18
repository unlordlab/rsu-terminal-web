from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
import os
from config import settings
from json_seguro import JSONSeguro
from auth import verify_token, require_tier, verify_admin_key
from middleware.rate_limit import rate_limit
from middleware.analytics import AnalyticsMiddleware
from routers import auth, market, cartera, canslim, rsu_algoritmo, research, newsfeed, tesis, spxl, rsrw, ws, options, btc_stratum, insider, scanner, analytics, watchlist, community, chat, academy, academy_review, laia_ethics, meeting_room, congress, track_record, legal

# Proxy global para yfinance — se aplica UNA vez aquí y afecta a TODAS las
# llamadas a yfinance en cualquier archivo del backend (Algoritmo, Cartera,
# Scanner, Options Flow, Research, Market), sin tocar esos archivos.
#
# IMPORTANTE: la versión fijada en requirements.txt (0.2.54) NO tiene el
# sistema yf.config de versiones más recientes (lo comprobé antes de usarlo,
# yf.config no existe ahí — habría reventado con AttributeError en el primer
# arranque). Lo que SÍ acepta esta versión es un parámetro `proxy=` directo
# en yf.Ticker(...) — así que en vez de tocar cada uno de los muchos sitios
# del backend que llaman a yf.Ticker(), se parchea el propio constructor
# una sola vez aquí, para que use el proxy como valor por defecto cuando no
# se pase uno explícito. Si yfinance_proxy_url está vacío (por defecto),
# esto no cambia nada — comportamiento actual, sin proxy, igual que siempre.
if settings.yfinance_proxy_url:
    import yfinance as yf
    _yf_ticker_init_original = yf.Ticker.__init__
    def _yf_ticker_init_con_proxy(self, ticker, session=None, proxy=None):
        if proxy is None:
            proxy = settings.yfinance_proxy_url
        _yf_ticker_init_original(self, ticker, session=session, proxy=proxy)
    yf.Ticker.__init__ = _yf_ticker_init_con_proxy
    print(f"[Startup] Proxy de yfinance activado para toda la terminal (parcheado en yf.Ticker)")
else:
    print(f"[Startup] Sin proxy configurado para yfinance (yfinance_proxy_url vacío)")
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Cada bucle va envuelto en ws.supervisar() -- si la Task muere por una
    # excepción no capturada por su propio try/except interno (hoy se queda
    # muerta para siempre, en silencio), se relanza sola tras 60s con un log
    # explícito. Ver ws.py::supervisar().
    task1 = asyncio.create_task(ws.supervisar("broadcast_loop", ws.broadcast_loop))
    task2 = asyncio.create_task(ws.supervisar("broadcast_cartera_loop", ws.broadcast_cartera_loop))
    task3 = asyncio.create_task(ws.supervisar("alerts_check_loop", ws.alerts_check_loop))
    task4 = asyncio.create_task(ws.supervisar("insider_ingest_loop", ws.insider_ingest_loop))
    task5 = asyncio.create_task(ws.supervisar("market_cache_warm_loop", ws.market_cache_warm_loop))
    task6 = asyncio.create_task(ws.supervisar("algoritmo_check_loop", ws.algoritmo_check_loop))
    task7 = asyncio.create_task(ws.supervisar("algoritmo_resultados_loop", ws.algoritmo_resultados_loop))
    task8 = asyncio.create_task(ws.supervisar("cartera_check_loop", ws.cartera_check_loop))
    task9 = asyncio.create_task(ws.supervisar("telegram_link_poll_loop", ws.telegram_link_poll_loop))
    task10 = asyncio.create_task(ws.supervisar("rsu_score_resultados_loop", ws.rsu_score_resultados_loop))
    # Stream de precios en vivo de Cartera (Finnhub). Se crea siempre, pero la
    # propia corrutina sale de inmediato si FINNHUB_REALTIME no está activo, así
    # que apagarlo no deja ninguna tarea colgando ni conexión abierta.
    task11 = asyncio.create_task(ws.supervisar("finnhub_stream_loop", ws.finnhub_stream_loop))
    # Track record de CANSLIM: rellena el retorno real de los candidatos que
    # propuso cada scan nocturno (ver services/canslim_tracking_service.py).
    task12 = asyncio.create_task(ws.supervisar("canslim_resultados_loop", ws.canslim_resultados_loop))
    # Cumple los plazos de conservación de la política de privacidad. Ver
    # ws.retencion_datos_loop().
    task13 = asyncio.create_task(ws.supervisar("retencion_datos_loop", ws.retencion_datos_loop))
    yield
    task13.cancel()
    task1.cancel()
    task2.cancel()
    task3.cancel()
    task4.cancel()
    task5.cancel()
    task6.cancel()
    task7.cancel()
    task8.cancel()
    task9.cancel()
    task10.cancel()
    task11.cancel()
    task12.cancel()

app = FastAPI(
    title=settings.app_name,
    # Un NaN suelto en cualquier respuesta dejaba de ser un dato que falta y
    # pasaba a ser un 500 en texto plano que borraba el modulo entero de la
    # pantalla. Ver backend/json_seguro.py.
    default_response_class=JSONSeguro,
    # En producción no exponemos el esquema completo de la API (rutas,
    # parámetros, modelos) a cualquiera que visite /api/docs sin login.
    docs_url="/api/docs" if settings.environment != "production" else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Detecta automáticamente peticiones API con ticker en la URL (research,
# rsrw, canslim, options, insider, tesis, earnings) y las registra para el
# panel de métricas de /admin. Ver middleware/analytics.py.
app.add_middleware(AnalyticsMiddleware)

rl = [Depends(rate_limit)]
# Cartera y Tesis son las secciones "core": requieren tier1 o superior
# (bloqueadas para usuarios 'free'). El resto de secciones siguen abiertas
# a cualquier usuario registrado, solo con el rate limit general.
paid = [Depends(rate_limit), Depends(require_tier("tier1"))]
app.include_router(auth.router)
# Sin `dependencies=rl` ni auth: una política de privacidad tiene que poder
# leerse antes de tener cuenta (ver routers/legal.py).
app.include_router(legal.router)
app.include_router(market.router,       dependencies=rl)
app.include_router(cartera.router,      dependencies=paid)
app.include_router(canslim.router,      dependencies=rl)
app.include_router(rsu_algoritmo.router,dependencies=rl)
app.include_router(research.router,     dependencies=rl)
app.include_router(newsfeed.router,     dependencies=rl)
app.include_router(tesis.router,        dependencies=paid)
app.include_router(tesis.admin_router,     dependencies=rl)  # + X-Admin-Key, ver tesis.py
app.include_router(academy_review.router,  dependencies=rl)  # + X-Admin-Key, agente Elia
app.include_router(laia_ethics.router,     dependencies=rl)  # + X-Admin-Key, historico Laia
app.include_router(meeting_room.router,    dependencies=rl)  # + X-Admin-Key, buzon a los agentes
app.include_router(spxl.router,         dependencies=rl)
app.include_router(rsrw.router,         dependencies=rl)
app.include_router(ws.router)
app.include_router(options.router,      dependencies=rl)
app.include_router(btc_stratum.router,  dependencies=rl)
app.include_router(insider.router,      dependencies=rl)
app.include_router(congress.router,     dependencies=rl)
app.include_router(scanner.router,      dependencies=rl)
# Watchlist + Alertas: abierto a cualquier usuario registrado (tier free
# incluido) por ahora. El día que se quiera pasar a tiers de pago, cambiar
# `dependencies=rl` por `dependencies=paid` aquí es el único cambio necesario.
app.include_router(watchlist.router,    dependencies=rl)
# Comunidad: abierta para todos los usuarios registrados, sin gate de tier —
# es soporte/feedback/Discord, no una herramienta de análisis.
app.include_router(community.router,    dependencies=rl)
app.include_router(chat.router,         dependencies=rl)
# Progreso de Academy (lecciones leídas + quizzes). Academy es GRATUITA para
# cualquier usuario registrado, por eso `rl` y no `paid`.
app.include_router(academy.router,      dependencies=rl)
# Track record: el registro de lo que hicieron las señales de verdad. Abierto
# a cualquier usuario registrado a propósito -- es exactamente lo que hay que
# poder enseñar antes de pedirle dinero a nadie. El día que exista landing
# pública, este es el primer candidato a salir del muro de autenticación.
app.include_router(track_record.router, dependencies=rl)
# /track es "fire and forget" desde el frontend (rate limit general para
# evitar abuso); /summary va protegido con X-Admin-Key dentro del propio
# router, igual que los endpoints /admin/* de auth.py.
app.include_router(analytics.router,    dependencies=rl)

class CodigoDeLaApp(StaticFiles):
    """StaticFiles que obliga a revalidar en cada carga.

    StaticFiles ya manda ETag y Last-Modified, pero NO manda Cache-Control.
    Sin esa cabecera el navegador aplica "frescura heurística" (RFC 9111):
    puede reutilizar el fichero sin preguntar al servidor, y cada fichero
    decide por su cuenta cuándo revalidar. Con módulos ES que se importan
    entre sí, eso permite que la app cargue con una MEZCLA de versiones --
    exactamente el fallo que dejó el módulo 27 de Academy sin lecciones el
    01/08/2026 (ver frontend/sw.js).

    `no-cache` no significa "no guardes", significa "guarda pero pregunta
    siempre": con el ETag que ya se manda, la respuesta habitual es un 304
    vacío, así que no cuesta ancho de banda. Solo se aplica al CÓDIGO
    (JS/CSS); las imágenes, iconos y fuentes de /static y /assets se dejan
    con el comportamiento de siempre, que ahí sí es el adecuado.
    """
    async def get_response(self, path, scope):
        response = await super().get_response(path, scope)
        response.headers["Cache-Control"] = "no-cache"
        return response


app.mount("/static",     StaticFiles(directory="../static"),          name="static")
app.mount("/assets",     StaticFiles(directory="../frontend/assets"), name="assets")
app.mount("/themes",     CodigoDeLaApp(directory="../frontend/themes"), name="themes")
app.mount("/core",       CodigoDeLaApp(directory="../frontend/core"),   name="core")
app.mount("/components", CodigoDeLaApp(directory="../frontend/components"), name="components")
app.mount("/pages",      CodigoDeLaApp(directory="../frontend/pages"),  name="pages")

# Commit desplegado, sellado por deploy.sh en backend/VERSION justo antes de
# construir la imagen. Se lee UNA vez al arrancar: dentro del contenedor el
# fichero no cambia mientras el proceso vive.
#
# Por qué existe: hasta el 14/08/2026 no había forma de saber qué código estaba
# corriendo en el servidor. El "HOY %" de Cartera se reportó roto cuatro veces
# y en dos de ellas el cálculo en `main` ya era correcto -- lo que corría era
# una versión anterior, y cada vez costó una sesión entera de depuración
# descubrirlo. El `git pull` del despliegue avisa cuando no trae nada nuevo,
# pero eso no dice nada sobre lo que hay DENTRO del contenedor.
def _version_desplegada() -> dict:
    try:
        with open(os.path.join(os.path.dirname(__file__), "VERSION"), encoding="utf-8") as f:
            lineas = [l.strip() for l in f if l.strip()]
        return {"commit": lineas[0], "desplegado": lineas[1] if len(lineas) > 1 else None}
    except Exception:
        # Sin fichero: se está ejecutando fuera de un despliegue (desarrollo
        # local) o la imagen se construyó sin pasar por deploy.sh. Se dice, en
        # vez de inventar un número de versión.
        return {"commit": "desconocida", "desplegado": None}


_VERSION = _version_desplegada()


@app.get("/health")
async def health():
    # Endpoint público a propósito (lo usan Docker/uptime checks sin token).
    # No exponemos aquí el detalle de la caché para no dar información
    # interna gratis; para eso está /api/v1/cache/stats, que si pide token.
    #
    # El commit SÍ se expone: es un identificador de 7 caracteres de un
    # repositorio privado, no da acceso a nada, y a cambio convierte "¿está
    # desplegado el arreglo?" en una pregunta de cinco segundos.
    return {"status": "ok", "app": settings.app_name, **_VERSION}

@app.get("/api/v1/rate-limit/stats")
async def rate_limit_stats(_=Depends(verify_admin_key)):
    from middleware.rate_limit import _store
    return {"message": "Rate limiting activo", "active_keys": len(_store), "general_limit": "60/min", "heavy_limit": "10/min"}

@app.get("/api/v1/cache/stats")
async def cache_stats(_=Depends(verify_admin_key)):
    from services.cache import cache
    return {"ok": True, "cache": cache.stats()}

@app.delete("/api/v1/cache/{prefix}")
async def clear_cache(prefix: str, _=Depends(verify_admin_key)):
    from services.cache import cache
    cache.clear_prefix(prefix)
    return {"ok": True, "cleared": prefix}

@app.get("/sw.js")
async def service_worker():
    # Necesita ruta explícita — si no, cae en el comodín del SPA de más abajo
    # y se sirve index.html (HTML) en vez del JS real, que el navegador
    # rechaza al intentar registrarlo como service worker.
    #
    # no-cache aquí es lo más importante de todo: si el navegador se queda
    # con un sw.js viejo, la estrategia nueva no llega a activarse nunca y
    # da igual lo que hagan las demás cabeceras.
    return FileResponse("../frontend/sw.js", media_type="application/javascript",
                        headers={"Cache-Control": "no-cache"})

@app.get("/manifest.json")
async def pwa_manifest():
    return FileResponse("../frontend/manifest.json", media_type="application/manifest+json")

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    # Una ruta de API que no existe tiene que decirlo. Antes esta función
    # simplemente terminaba sin `return` para esas rutas, y FastAPI
    # serializa el None implícito como un 200 con cuerpo `null` -- así que
    # un fetch contra una URL mal escrita, o contra un endpoint retirado,
    # no fallaba nunca de forma visible: el módulo se quedaba vacío en
    # silencio y no había nada en la consola que lo delatase. Es el mismo
    # patrón de fallo mudo que ya costó caro en _get_yf_earnings. Ver
    # auditoría de Options Flow, hallazgo #27 (encontrado ahí, pero afecta
    # a toda la API).
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail=f"Endpoint no encontrado: /{full_path}")
    # index.html es el punto de entrada del grafo de módulos: si se
    # sirve cacheado, arrastra consigo la versión vieja de todo lo demás.
    return FileResponse("../frontend/index.html",
                        headers={"Cache-Control": "no-cache"})