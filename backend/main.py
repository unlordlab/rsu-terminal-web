from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from config import settings
from routers import auth                    # ← importamos el router

app = FastAPI(title=settings.app_name, docs_url="/api/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registramos el router de autenticación
app.include_router(auth.router)             # ← lo registramos en la app

# Archivos estáticos del frontend
app.mount("/static", StaticFiles(directory="../static"), name="static")
app.mount("/themes", StaticFiles(directory="../frontend/themes"), name="themes")
app.mount("/core", StaticFiles(directory="../frontend/core"), name="core")
app.mount("/components", StaticFiles(directory="../frontend/components"), name="components")
app.mount("/pages", StaticFiles(directory="../frontend/pages"), name="pages")

@app.get("/health")
async def health():
    return {"status": "ok", "app": settings.app_name}

# SPA catch-all
@app.get("/{full_path:path}")
async def spa_fallback(full_path: str):
    if not full_path.startswith("api/"):
        return FileResponse("../frontend/index.html")
