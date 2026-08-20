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
# DÓNDE LLEGA EL AVISO. Al chat PERSONAL del admin (TELEGRAM_ADMIN_CHAT_ID),
# no al canal comunitario. Hasta el 20/08/2026 iba al canal de operaciones —el
# de las señales del Algoritmo, las entradas y salidas de Cartera y las tesis—
# y ahí no pinta nada: ese canal lo lee cualquier usuario suscrito, y un
# "CRON FALLIDO: Elia (Academy), código de salida 1" no es información de
# mercado, es un problema de mantenimiento de la casa. Lo reportó el usuario al
# recibir por ese canal un fallo de Elia por límite de tokens de Groq.
#
# Si TELEGRAM_ADMIN_CHAT_ID no está configurado, se cae al canal de siempre y
# se dice en el log: un aviso de fallo que no llega es peor que uno que llega
# al sitio equivocado.
#
# Mismas credenciales del .env — se leen vía el contenedor, sin duplicarlas.
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
from config import settings
from services.telegram_service import enviar_telegram
# Al chat del admin. Si no está configurado, chat_id=None hace que
# enviar_telegram use el canal de siempre -- antes que perder el aviso.
destino = getattr(settings, "telegram_admin_chat_id", "") or None
if destino is None:
    print("[cron_alert] TELEGRAM_ADMIN_CHAT_ID sin configurar: el aviso va al canal comunitario")
sys.exit(0 if enviar_telegram("""$MENSAJE""", chat_id=destino) else 1)
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
        # docker-compose.yml carga `env_file: .env` desde la RAÍZ del repositorio,
        # pero este script solo miraba en backend/. Si en un despliegue solo existe
        # el de la raíz, esta vía de respaldo no encontraba credenciales y se
        # quedaba callada -- justo cuando actúa, que es con el contenedor caído.
        ENV_FILE=""
        for CANDIDATO in "$(dirname "${BASH_SOURCE[0]}")/../backend/.env" \
                         "$(dirname "${BASH_SOURCE[0]}")/../.env"; do
            if [ -f "$CANDIDATO" ]; then ENV_FILE="$CANDIDATO"; break; fi
        done
        if [ -n "$ENV_FILE" ]; then
            TOKEN=$(grep -m1 -E '^TELEGRAM_BOT_TOKEN=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' \r')
            # Mismo criterio que la vía 1: primero el chat del admin.
            CHAT=$(grep -m1 -E '^TELEGRAM_ADMIN_CHAT_ID=' "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' \r')
            if [ -z "${CHAT:-}" ]; then
                echo "[cron_alert] TELEGRAM_ADMIN_CHAT_ID sin configurar: el aviso va al canal comunitario"
                CHAT=$(grep -m1 -E '^TELEGRAM_CHAT_ID='  "$ENV_FILE" | cut -d= -f2- | tr -d '"'"'"' \r')
            fi
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