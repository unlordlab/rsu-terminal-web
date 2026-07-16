from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
from config import settings
from auth import verify_token, require_tier
from middleware.rate_limit import rate_limit
from middleware.analytics import AnalyticsMiddleware
from routers import auth, market, cartera, canslim, rsu_algoritmo, research, newsfeed, tesis, spxl, rsrw, ws, options, btc_stratum, insider, scanner, analytics, watchlist, community, chat

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

# "Precalentar" el crumb de sesión de yfinance con UNA sola llamada síncrona
# antes de que arranque nada concurrente (ThreadPoolExecutor en market_service,
# cartera_service, etc.). yfinance cachea el crumb una vez por proceso, y si dos
# hilos lo piden a la vez en el primer arranque, uno puede pisar la caché
# compartida con un crumb inválido (el propio texto de un 429), contaminando
# TODAS las peticiones del proceso a partir de ahí — ver conversación 16/07/2026
# sobre el bloqueo de Yahoo/proxy residencial. Esto evita la carrera por completo.
# Precalentado del crumb CON reintentos y reseteo del singleton interno
# de yfinance (YfData) — ver conversación 16/07/2026. Si el primer intento
# recibe un 429 de Yahoo, yfinance cachea ese error como si fuera un crumb
# válido en YfData()._crumb, y lo reutiliza para SIEMPRE dentro de este
# proceso — reintentar sin más no sirve de nada, hay que resetear ese
# atributo a mano antes de cada reintento para que yfinance pida uno nuevo.
try:
    import yfinance as _yf_warmup
    import yfinance.data as _yfdata_warmup
    import time as _time_warmup

    _YF_WARMUP_MAX_INTENTOS = 5
    _YF_WARMUP_ESPERA_SEGUNDOS = 5

    for _intento in range(1, _YF_WARMUP_MAX_INTENTOS + 1):
        try:
            _h = _yf_warmup.Ticker("SPY").history(period="1d")
            if _h is not None and len(_h) > 0:
                print(f"[Startup] Crumb de yfinance precalentado correctamente (intento {_intento}/{_YF_WARMUP_MAX_INTENTOS})")
                break
            raise ValueError("history() devolvió vacío")
        except Exception as _e:
            print(f"[Startup] Intento {_intento}/{_YF_WARMUP_MAX_INTENTOS} de precalentar crumb falló ({type(_e).__name__}: {_e})")
            try:
                _d = _yfdata_warmup.YfData()
                _d._crumb = None
                _d._cookie = None
            except Exception:
                pass
            if _intento < _YF_WARMUP_MAX_INTENTOS:
                _time_warmup.sleep(_YF_WARMUP_ESPERA_SEGUNDOS)
    else:
        print(f"[Startup] No se pudo precalentar el crumb tras {_YF_WARMUP_MAX_INTENTOS} intentos — se reintentará en la primera petición real")
except Exception as _e:
    print(f"[Startup] Fallo inesperado en el precalentado de yfinance: {type(_e).__name__}: {_e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    task1 = asyncio.create_task(ws.broadcast_loop())
    task2 = asyncio.create_task(ws.broadcast_cartera_loop())
    task3 = asyncio.create_task(ws.alerts_check_loop())
    task4 = asyncio.create_task(ws.insider_ingest_loop())
    task5 = asyncio.create_task(ws.market_cache_warm_loop())
    task6 = asyncio.create_task(ws.algoritmo_check_loop())
    task7 = asyncio.create_task(ws.algoritmo_resultados_loop())
    task8 = asyncio.create_task(ws.cartera_check_loop())
    task9 = asyncio.create_task(ws.options_flow_scan_loop())
    yield
    task1.cancel()
    task2.cancel()
    task3.cancel()
    task4.cancel()
    task5.cancel()
    task6.cancel()
    task7.cancel()
    task8.cancel()
    task9.cancel()

app = FastAPI(
    title=settings.app_name,
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
app.include_router(market.router,       dependencies=rl)
app.include_router(cartera.router,      dependencies=paid)
app.include_router(canslim.router,      dependencies=rl)
app.include_router(rsu_algoritmo.router,dependencies=rl)
app.include_router(research.router,     dependencies=rl)
app.include_router(newsfeed.router,     dependencies=rl)
app.include_router(tesis.router,        dependencies=paid)
app.include_router(spxl.router,         dependencies=rl)
app.include_router(rsrw.router,         dependencies=rl)
app.include_router(ws.router)
app.include_router(options.router,      dependencies=rl)
app.include_router(btc_stratum.router,  dependencies=rl)
app.include_router(insider.router,      dependencies=rl)
app.include_router(scanner.router,      dependencies=rl)
# Watchlist + Alertas: abierto a cualquier usuario registrado (tier free
# incluido) por ahora. El día que se quiera pasar a tiers de pago, cambiar
# `dependencies=rl` por `dependencies=paid` aquí es el único cambio necesario.
app.include_router(watchlist.router,    dependencies=rl)
# Comunidad: abierta para todos los usuarios registrados, sin gate de tier —
# es soporte/feedback/Discord, no una herramienta de análisis.
app.include_router(community.router,    dependencies=rl)
app.include_router(chat.router,         dependencies=rl)
# /track es "fire and forget" desde el frontend (rate limit general para
# evitar abuso); /summary va protegido con X-Admin-Key dentro del propio
# router, igual que los endpoints /admin/* de auth.py.
app.include_router(analytics.router,    dependencies=rl)

app.mount("/static",     StaticFiles(directory="../static"),          name="static")
app.mount("/assets",     StaticFiles(directory="../frontend/assets"), name="assets")
app.mount("/themes",     StaticFiles(directory="../frontend/themes"), name="themes")
app.mount("/core",       StaticFiles(directory="../frontend/core"),   name="core")
app.mount("/components", StaticFiles(directory="../frontend/components"), name="components")
app.mount("/pages",      StaticFiles(directory="../frontend/pages"),  name="pages")

@app.get("/health")
async def health():
    # Endpoint público a propósito (lo usan Docker/uptime checks sin token).
    # No exponemos aquí el detalle de la caché para no dar información
    # interna gratis; para eso está /api/v1/cache/stats, que si pide token.
    return {"status": "ok", "app": settings.app_name}

@app.get("/api/v1/rate-limit/stats")
async def rate_limit_stats(user=Depends(verify_token)):
    from middleware.rate_limit import _store
    return {"message": "Rate limiting activo", "active_keys": len(_store), "general_limit": "60/min", "heavy_limit": "10/min"}

@app.get("/api/v1/cache/stats")
async def cache_stats(user=Depends(verify_token)):
    from services.cache import cache
    return {"ok": True, "cache": cache.stats()}

@app.delete("/api/v1/cache/{prefix}")
async def clear_cache(prefix: str, user=Depends(verify_token)):
    from services.cache import cache
    cache.clear_prefix(prefix)
    return {"ok": True, "cleared": prefix}

@app.get("/sw.js")
async def service_worker():
    # Necesita ruta explícita — si no, cae en el comodín del SPA de más abajo
    # y se sirve index.html (HTML) en vez del JS real, que el navegador
    # rechaza al intentar registrarlo como service worker.
    return FileResponse("../frontend/sw.js", media_type="application/javascript")

@app.get("/manifest.json")
async def pwa_manifest():
    return FileResponse("../frontend/manifest.json", media_type="application/manifest+json")

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if not full_path.startswith("api/"):
        return FileResponse("../frontend/index.html")