FROM python:3.12-slim

# Dependencias del sistema mínimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Instalar dependencias primero (capa cacheada)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Aquí se instalaba Chromium headless (Playwright) para Reddit Pulse, entre
# el 23/07/2026 y el 28/07/2026. Retirado: el bloqueo de Reddit dejó de ser
# un *challenge* JavaScript (que un navegador real resolvía) y pasó a ser un
# bloqueo de RED por IP de datacenter -- verificado en el propio VPS el
# 28/07/2026: HTTP 403, título "Blocked", "Your request has been blocked due
# to a network policy", devuelto ANTES de servir página alguna. Con un
# bloqueo previo a cualquier JS, el navegador no aportaba nada y costaba
# ~180MB de imagen, dependencias de sistema y varios segundos por petición.
# Reddit Pulse usa ahora el RSS público, que sí responde 200 desde esa misma
# IP (ver market_service._fetch_reddit_titles_via_rss).
#
# Si algún día hace falta volver a un navegador headless, el historial de
# git tiene la receta completa, incluida la lección que costó dos despliegues
# fallidos: instalarlo DENTRO de /app no funciona, porque el bind mount
# ".:/app" del docker-compose lo tapa en tiempo de ejecución -- tiene que ir
# fuera, como estaba aquí en /opt/pw-browsers.

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