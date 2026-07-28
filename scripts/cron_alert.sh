#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# cron_alert.sh — envoltorio para tareas de cron: ejecuta el comando que se le
# pase y, SI FALLA (exit code ≠ 0), avisa por Telegram con el nombre de la
# tarea y las últimas líneas del error.
#
# Ver PLAN_MAESTRO 1.3 / auditoría 19/07/2026 #12: hasta ahora, si un cron
# fallaba (Gael, Elia, el monitor SPXL, los backups...), nadie se enteraba
# salvo que Marc mirara los logs por casualidad — el rate limit de Gael se
# descubrió revisando una tesis a mano.
#
# Uso en crontab (envolver el comando existente, sin cambiar nada más):
#   ANTES:  0 19 * * 1-5 cd /home/rsu/rsu-terminal-web && docker exec ... bull_agent.py >> /home/rsu/bull_agent.log 2>&1
#   AHORA:  0 19 * * 1-5 /home/rsu/rsu-terminal-web/scripts/cron_alert.sh "Gael (tesis diaria)" "cd /home/rsu/rsu-terminal-web && docker exec rsu-terminal-web-app-1 python3 ../agents/bull_agent.py --max 1" >> /home/rsu/bull_agent.log 2>&1
#
# El aviso llega al mismo bot/chat de Telegram que ya usan los agentes
# (mismas credenciales del .env — se leen vía el contenedor, sin duplicarlas).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail   # sin -e: queremos capturar el fallo, no morir con él

NOMBRE="${1:?Uso: cron_alert.sh \"nombre de la tarea\" \"comando\"}"
COMANDO="${2:?Falta el comando a ejecutar}"

SALIDA=$(bash -c "$COMANDO" 2>&1)
CODIGO=$?

# La salida siempre se reenvía al log (el >> del crontab la recoge)
echo "$SALIDA"

if [ $CODIGO -ne 0 ]; then
    # Últimas 12 líneas del error, truncadas por si son enormes, y sin
    # caracteres que rompan el Markdown de Telegram (_ * [ `)
    ULTIMO=$(echo "$SALIDA" | tail -12 | cut -c1-300 | tr '_*[`' ' ')

    MENSAJE="🚨 CRON FALLIDO: ${NOMBRE}
Código de salida: ${CODIGO}
Hora: $(date '+%Y-%m-%d %H:%M')

Últimas líneas:
${ULTIMO}"

    # Vía 1: a través del contenedor (reutiliza credenciales y servicio).
    ENVIADO=0
    if docker exec -i rsu-terminal-web-app-1 python3 - <<PY
import sys
sys.path.insert(0, '/app/backend')
from services.telegram_service import enviar_telegram
sys.exit(0 if enviar_telegram("""$MENSAJE""") else 1)
PY
    then
        ENVIADO=1
        echo "[cron_alert] Aviso enviado a Telegram"
    fi

    # Vía 2: curl directo desde el host, leyendo las credenciales del .env.
    #
    # Hace falta porque la vía 1 depende del propio contenedor: si lo que ha
    # fallado ES el contenedor (caído, reiniciándose, a medio desplegar), el
    # `docker exec` falla también y te quedas SIN aviso justo en el caso en
    # que más falta hace. Visto en producción el 28/07/2026:
    #   "Error response from daemon: container ... is not running"
    #   "[cron_alert] No se pudo enviar el aviso a Telegram"
    if [ "$ENVIADO" -eq 0 ]; then
        ENV_FILE="$(dirname "${BASH_SOURCE[0]}")/../backend/.env"
        if [ -f "$ENV_FILE" ]; then
            TOKEN=$(grep -m1 -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' \r')
            CHAT=$(grep -m1 -E '^TELEGRAM_CHAT_ID='  "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' \r')
            if [ -n "${TOKEN:-}" ] && [ -n "${CHAT:-}" ]; then
                if curl -s -f -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" \
                        -d chat_id="$CHAT" \
                        --data-urlencode "text=${MENSAJE}
(aviso enviado desde el host: el contenedor no respondia)" > /dev/null; then
                    ENVIADO=1
                    echo "[cron_alert] Aviso enviado a Telegram (via host, contenedor no disponible)"
                fi
            fi
        fi
    fi

    [ "$ENVIADO" -eq 0 ] && echo "[cron_alert] No se pudo enviar el aviso a Telegram por ninguna via"
fi

exit $CODIGO