#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# vigilar_salud.sh — avisa por Telegram si la terminal deja de responder.
#
# EL CASO (Infraestructura #31). El 12/09/2026 a las 20:05 UTC un despliegue se
# interrumpió y la terminal estuvo 12 HORAS caída sin que nadie se enterara: se
# descubrió a la mañana siguiente porque otro despliegue no pudo hacer la copia
# de seguridad. `cron_alert.sh` avisa cuando falla un CRON, pero nada vigilaba
# que la web respondiera.
#
# QUÉ HACE, cada vez que lo lanza el cron (cada 5 minutos):
#
#   - Pide /health A TRAVÉS DE NGINX, que es el camino de los usuarios.
#   - Si falla DOS veces seguidas, avisa. Una sola no: recrear el contenedor en
#     un despliegue deja la web sin responder unos 15 segundos, y un aviso por
#     cada despliegue enseña a ignorar los avisos.
#   - Al avisar, prueba también la app directamente en el puerto 8000, para que
#     el mensaje diga DÓNDE está el fallo: en Nginx o en el contenedor.
#   - Avisa UNA vez por caída, no cada 5 minutos, y manda otro mensaje cuando la
#     web vuelve a responder, con la hora a la que se detectó la caída.
#
# LAS CREDENCIALES se leen del .env en el propio servidor, sin pasar por el
# contenedor: si lo que ha caído ES el contenedor, un `docker exec` fallaría
# justo cuando más falta hace el aviso (lección de cron_alert.sh, 28/07/2026).
# El token NUNCA va en la línea de comandos de curl — se le pasa por la entrada
# estándar (`-K -`) —, así que no aparece en `ps` ni en ningún log.
#
# INSTALACIÓN (una vez, en el VPS): ver la línea de crontab en el mensaje del
# commit, o simplemente:
#     */5 * * * * /home/rsu/rsu-terminal-web/scripts/vigilar_salud.sh >> /home/rsu/vigilar_salud.log 2>&1
#
# Las variables RSU_* y TELEGRAM_API_BASE solo existen para poder probar el
# script de verdad (tests/test_vigilar_salud.py); en el cron no hacen falta.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
URL_WEB="${RSU_HEALTH_URL:-http://localhost/health}"
URL_APP="${RSU_HEALTH_URL_APP:-http://127.0.0.1:8000/health}"
API="${TELEGRAM_API_BASE:-https://api.telegram.org}"
ESTADO="${RSU_VIGILANCIA_DIR:-$HOME/.rsu-vigilancia}"
UMBRAL="${RSU_FALLOS_PARA_AVISAR:-2}"

mkdir -p "$ESTADO"
FALLOS="$ESTADO/fallos_seguidos"
AVISADO="$ESTADO/caida_avisada"

# El .env que carga docker-compose está en la raíz; se mira también en backend/
# por el mismo motivo que en cron_alert.sh.
ENV_FILE="${RSU_ENV_FILE:-}"
if [ -z "$ENV_FILE" ]; then
    for candidato in "$RAIZ/.env" "$RAIZ/backend/.env"; do
        if [ -f "$candidato" ]; then ENV_FILE="$candidato"; break; fi
    done
fi

leer_env() {
    [ -n "$ENV_FILE" ] || return 0
    grep -m1 -E "^$1=" "$ENV_FILE" 2>/dev/null | cut -d= -f2- | tr -d '"'"'"' \r'
}

responde() {
    local codigo
    codigo=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$1" 2>/dev/null)
    [ "$codigo" = "200" ]
}

avisar() {
    local token chat
    token=$(leer_env TELEGRAM_BOT_TOKEN)
    chat=$(leer_env TELEGRAM_ADMIN_CHAT_ID)
    if [ -z "$chat" ]; then
        echo "[vigilar_salud] TELEGRAM_ADMIN_CHAT_ID sin configurar: el aviso va al canal de siempre"
        chat=$(leer_env TELEGRAM_CHAT_ID)
    fi
    if [ -z "$token" ] || [ -z "$chat" ]; then
        echo "[vigilar_salud] Sin credenciales de Telegram en el .env: no se puede avisar"
        return 1
    fi
    # La URL, con el token dentro, viaja por la entrada estándar y no por los
    # argumentos: así no se ve en `ps`, y `-s` sin `-S` no imprime la URL si
    # la conexión falla.
    printf 'url = "%s/bot%s/sendMessage"\n' "$API" "$token" \
        | curl -s -f -o /dev/null -m 15 -K - \
               --data-urlencode "chat_id=$chat" --data-urlencode "text=$1"
}

ahora() { date -u +"%Y-%m-%d %H:%M UTC"; }

# ── Responde: todo bien, y si venía de una caída, se dice ────────────────────
if responde "$URL_WEB"; then
    if [ -f "$AVISADO" ]; then
        desde=$(cat "$AVISADO")
        if avisar "✅ RSU Terminal vuelve a responder. La caída se detectó el $desde; recuperada el $(ahora)."; then
            rm -f "$AVISADO"
            echo "[vigilar_salud] $(ahora) recuperada, aviso enviado"
        fi
    fi
    rm -f "$FALLOS"
    exit 0
fi

# ── No responde ──────────────────────────────────────────────────────────────
n=$(( $(cat "$FALLOS" 2>/dev/null || echo 0) + 1 ))
echo "$n" > "$FALLOS"
echo "[vigilar_salud] $(ahora) /health no responde ($n seguidas)"

[ "$n" -lt "$UMBRAL" ] && exit 0          # puede ser un despliegue: se espera a la siguiente
[ -f "$AVISADO" ] && exit 0               # esta caída ya está avisada

if responde "$URL_APP"; then
    donde="La app SÍ responde en el puerto 8000: el fallo está en Nginx (sudo systemctl status nginx)."
else
    donde="La app tampoco responde en el puerto 8000: el contenedor está caído o colgado (docker ps -a)."
fi

if avisar "🔴 RSU Terminal NO responde: $n comprobaciones seguidas sin respuesta de /health. $donde"; then
    ahora > "$AVISADO"
    echo "[vigilar_salud] aviso de caída enviado"
else
    echo "[vigilar_salud] NO se pudo enviar el aviso; se reintenta en la próxima pasada"
fi
exit 0
