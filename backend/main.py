from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import asyncio
from config import settings
from routers import auth, market, cartera, canslim, rsu_algoritmo, research, newsfeed, tesis, spxl, rsrw, ws, options, btc_stratum

@asynccontextmanager
async def lifespan(app: FastAPI):
    task1 = asyncio.create_task(ws.broadcast_loop())
    task2 = asyncio.create_task(ws.broadcast_cartera_loop())
    yield
    task1.cancel()
    task2.cancel()

app = FastAPI(title=settings.app_name, docs_url="/api/docs", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(market.router)
app.include_router(cartera.router)
app.include_router(canslim.router)
app.include_router(rsu_algoritmo.router)
app.include_router(research.router)
app.include_router(newsfeed.router)
app.include_router(tesis.router)
app.include_router(spxl.router)
app.include_router(rsrw.router)
app.include_router(ws.router)
app.include_router(options.router)
app.include_router(btc_stratum.router)

app.mount("/static",     StaticFiles(directory="../static"),              name="static")
app.mount("/assets",     StaticFiles(directory="../frontend/assets"),     name="assets")
app.mount("/themes",     StaticFiles(directory="../frontend/themes"),     name="themes")
app.mount("/core",       StaticFiles(directory="../frontend/core"),       name="core")
app.mount("/components", StaticFiles(directory="../frontend/components"), name="components")
app.mount("/pages",      StaticFiles(directory="../frontend/pages"),      name="pages")

@app.get("/health")
async def health():
    from services.cache import cache
    return {"status": "ok", "app": settings.app_name, "cache": cache.stats()}

@app.delete("/api/v1/cache/{prefix}")
async def clear_cache(prefix: str):
    from services.cache import cache
    cache.clear_prefix(prefix)
    return {"ok": True, "cleared": prefix}

@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if not full_path.startswith("api/"):
        return FileResponse("../frontend/index.html")