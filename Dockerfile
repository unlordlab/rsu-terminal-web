FROM python:3.12-slim

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Chromium headless para Reddit Pulse -- reddit.com/*.json y
# api.stocktwits.com bloquean con 403 (challenge JS anti-bot) desde la IP
# del VPS; un navegador real lo resuelve, ver sesión 23/07/2026.
# PLAYWRIGHT_BROWSERS_PATH dentro de /app para que el chown de más abajo
# le dé permisos al usuario "app" sin privilegios -- si no, el binario
# quedaría en /root/.cache, inaccesible tras el USER app.
#
# IMPORTANTE: chromium.launch(headless=True) usa por defecto el binario
# "chromium-headless-shell" (más ligero, y el único que en la práctica pasa
# el bloqueo anti-bot -- forzar channel="chromium" con el navegador
# completo SÍ se detecta y bloquea, probado 23/07/2026). Se instalan los
# dos targets explícitos + una comprobación de arranque real ahora mismo:
# si el binario no queda instalado del todo (pasó una vez en el VPS real,
# build "exitoso" pero con el shell incompleto/ausente en tiempo de
# ejecución, sin que el build fallara), esto para el build aquí mismo con
# un error claro, en vez de desplegar en silencio un widget roto.
ENV PLAYWRIGHT_BROWSERS_PATH=/app/pw-browsers
RUN playwright install --with-deps chromium chromium-headless-shell && \
    python -c "from playwright.sync_api import sync_playwright as sp; p = sp().start(); b = p.chromium.launch(headless=True); b.close(); p.stop(); print('[Build] Playwright/Chromium headless verificado OK')"

# Copiar todo el proyecto
COPY . .

EXPOSE 8000

# Usuario sin privilegios -- antes todo corría como root dentro del
# contenedor (auditoría 19/07/2026, hallazgo #11). El UID/GID 1000 es
# A PROPÓSITO el mismo que el usuario "rsu" del VPS (confirmado con
# `id -u rsu` = 1000, 20/07/2026): como el volumen es un bind mount
# (".:/app" en docker-compose, no un volumen con nombre), el proceso
# necesita ese UID exacto para poder seguir escribiendo los .db, los
# backups y los logs de los agentes en el propio disco del host. Si
# alguna vez cambias de servidor y el usuario ahí tiene otro UID, ajusta
# estos dos ARG en el build.
ARG APP_UID=1000
ARG APP_GID=1000
RUN groupadd -g ${APP_GID} app && \
    useradd -u ${APP_UID} -g app -m -s /bin/bash app && \
    chown -R app:app /app
USER app

# Arrancar desde /app/backend para que los imports relativos funcionen:
# "from config import settings" busca config.py en el CWD (/app/backend)
WORKDIR /app/backend
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]