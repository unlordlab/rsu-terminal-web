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

    # Enviar vía el contenedor (reutiliza credenciales y servicio existentes).
    # Si el propio envío falla, se anota en el log — no hay mucho más que
    # hacer si Telegram no responde.
    docker exec -i rsu-terminal-web-app-1 python3 - <<PY || echo "[cron_alert] No se pudo enviar el aviso a Telegram"
import sys
sys.path.insert(0, '/app/backend')
from services.telegram_service import enviar_telegram
ok = enviar_telegram("""$MENSAJE""")
print("[cron_alert] Aviso enviado a Telegram" if ok else "[cron_alert] enviar_telegram devolvio False")
PY
fi

exit $CODIGO