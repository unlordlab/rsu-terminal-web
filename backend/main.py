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
from routers import auth, market, cartera, canslim, rsu_algoritmo, research, newsfeed, tesis, spxl, rsrw, ws, options, btc_stratum, insider, scanner, analytics, watchlist
@asynccontextmanager
async def lifespan(app: FastAPI):
    task1 = asyncio.create_task(ws.broadcast_loop())
    task2 = asyncio.create_task(ws.broadcast_cartera_loop())
    task3 = asyncio.create_task(ws.alerts_check_loop())
    task4 = asyncio.create_task(ws.insider_ingest_loop())
    yield
    task1.cancel()
    task2.cancel()
    task3.cancel()
    task4.cancel()

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

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if not full_path.startswith("api/"):
        return FileResponse("../frontend/index.html")