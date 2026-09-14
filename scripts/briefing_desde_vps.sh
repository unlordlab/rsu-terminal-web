#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# briefing_desde_vps.sh — el briefing se lanza DESDE EL SERVIDOR, a su hora.
#
# EL CASO (Infraestructura #23). El briefing es una nota de premercado, pero lo
# disparaba el planificador de GitHub Actions a las 07:00 UTC, que es la hora
# más saturada de crons del planeta. Medido: desde el 27/08 llegaba con 4 h 50
# min de retraso de media, y el 14/09 con 6 h 26 min — el usuario pensó que
# había fallado. En cambio, un `workflow_dispatch` arranca en segundos: la cola
# solo castiga a `schedule`. Así que el servidor, que ya corre 24/7, pide a
# GitHub que lo ejecute. Todo lo demás sigue igual (secretos y registros en
# GitHub); solo cambia quién aprieta el botón.
#
# DOS ÓRDENES, cada una con su línea de cron (hora UTC del servidor):
#
#   lanzar     A las 07:00. Pide a GitHub que ejecute el workflow del briefing.
#              Si GitHub lo rechaza (token caducado, sin permiso...), avisa por
#              Telegram diciendo qué pasa y cómo arreglarlo.
#   comprobar  A las 07:30. Si el briefing publicado no es de hoy, avisa. Es el
#              aviso que faltaba el 14/09: un briefing que llega tarde no falla,
#              y el aviso de fallo de GitHub no salta.
#
#     0 7 * * 1-5  /home/rsu/rsu-terminal-web/scripts/briefing_desde_vps.sh lanzar    >> /home/rsu/briefing_vps.log 2>&1
#     30 7 * * 1-5 /home/rsu/rsu-terminal-web/scripts/briefing_desde_vps.sh comprobar >> /home/rsu/briefing_vps.log 2>&1
#
# El disparo programado de GitHub se queda como RESPALDO: si este script no
# llegara a lanzarlo, el de GitHub lo haría tarde. Y si ya se publicó, el
# workflow lo detecta y no lo repite (ver daily_briefing.yml).
#
# EL TOKEN (GITHUB_DISPATCH_TOKEN en el .env) es de grano fino, SOLO para este
# repositorio y SOLO con permiso «Actions: Read and write». Va aparte de
# GITHUB_TOKEN, que solo lee Gists: si uno se filtra, no da el poder del otro.
# Nunca va en la línea de comandos de curl: viaja por la entrada estándar
# (`-K -`), así que no aparece en `ps` ni en ningún log.
#
# Las variables RSU_*, GITHUB_API_BASE y TELEGRAM_API_BASE solo existen para
# probar el script de verdad (tests/test_briefing_desde_vps.py).
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GITHUB_API="${GITHUB_API_BASE:-https://api.github.com}"
TELEGRAM_API="${TELEGRAM_API_BASE:-https://api.telegram.org}"
REPO="${RSU_REPO:-unlordlab/rsu-terminal-web}"
WORKFLOW="daily_briefing.yml"
GIST_BRIEFING="${RSU_GIST_BRIEFING:-715ee0c4e571517c11fa65c5c2376c34}"
PYTHON="${RSU_PYTHON:-$(command -v python3 || command -v python || true)}"

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

ahora() { date -u +"%Y-%m-%d %H:%M UTC"; }

avisar() {
    local token chat
    token=$(leer_env TELEGRAM_BOT_TOKEN)
    chat=$(leer_env TELEGRAM_ADMIN_CHAT_ID)
    [ -n "$chat" ] || chat=$(leer_env TELEGRAM_CHAT_ID)
    if [ -z "$token" ] || [ -z "$chat" ]; then
        echo "[briefing_vps] Sin credenciales de Telegram en el .env: no se puede avisar"
        return 1
    fi
    # El texto va DENTRO de la configuración que curl lee por la entrada
    # estándar, no como argumento: así llega byte a byte, con sus acentos,
    # también con el curl de Windows (que pasa los argumentos a la página de
    # códigos del sistema y los rompe) y sin ficheros temporales.
    {
        printf 'url = "%s/bot%s/sendMessage"\n' "$TELEGRAM_API" "$token"
        printf 'data-urlencode = "chat_id=%s"\n' "$(para_config "$chat")"
        printf 'data-urlencode = "text=%s"\n' "$(para_config "$1")"
    } | curl -s -f -o /dev/null -m 15 -K -
}

# Escapa un valor para ir entre comillas en un fichero de configuración de curl.
# Con variables entre comillas y no con barras escritas en el patrón: bash 5.2
# cambió cómo trata las barras del reemplazo, y la versión con barras perdía la
# barra y convertía el salto de línea en una «n» (lo cazó el test).
para_config() {
    local s="$1" bs='\' dq='"' nl=$'\n'
    s=${s//"$bs"/"$bs$bs"}
    s=${s//"$dq"/"$bs$dq"}
    s=${s//"$nl"/"${bs}n"}
    printf '%s' "$s"
}

# Petición a la API de GitHub con el token por la entrada estándar. Escribe el
# cuerpo en $2 y devuelve el código HTTP por stdout.
github() {
    local metodo="$1" salida="$2" ruta="$3" token="$4" datos="${5:-}"
    local extra=()
    if [ -n "$datos" ]; then
        extra=(-H "Content-Type: application/json" --data "$datos")
    fi
    {
        printf 'url = "%s%s"\n' "$GITHUB_API" "$ruta"
        if [ -n "$token" ]; then
            printf 'header = "Authorization: Bearer %s"\n' "$token"
        fi
        printf 'header = "Accept: application/vnd.github+json"\n'
        printf 'header = "X-GitHub-Api-Version: 2022-11-28"\n'
    } | curl -s -o "$salida" -m 20 -w '%{http_code}' -K - -X "$metodo" "${extra[@]}"
}

que_significa() {
    case "$1" in
        401) echo "el token no vale (caducado o mal copiado). Crea uno nuevo y cámbialo en GITHUB_DISPATCH_TOKEN del .env." ;;
        403) echo "el token no tiene permiso para lanzar workflows. Tiene que tener «Actions: Read and write» sobre $REPO." ;;
        404) echo "GitHub no ve el repositorio o el workflow con ese token: revisa que el token incluya $REPO." ;;
        422) echo "GitHub no acepta la petición (¿se ha quitado workflow_dispatch del workflow?)." ;;
        000) echo "no hubo respuesta de GitHub (red caída o GitHub sin servicio)." ;;
        *)   echo "respuesta inesperada de GitHub." ;;
    esac
}

lanzar() {
    local token codigo cuerpo
    token=$(leer_env GITHUB_DISPATCH_TOKEN)
    if [ -z "$token" ]; then
        echo "[briefing_vps] $(ahora) GITHUB_DISPATCH_TOKEN vacío: no se lanza (queda el disparo programado de GitHub)"
        avisar "⚠️ El briefing no se ha podido lanzar desde el servidor: falta GITHUB_DISPATCH_TOKEN en el .env. Saldrá igualmente cuando lo lance GitHub, con retraso."
        return 1
    fi
    cuerpo=$(mktemp)
    codigo=$(github POST "$cuerpo" "/repos/$REPO/actions/workflows/$WORKFLOW/dispatches" "$token" '{"ref":"main"}')
    if [ "$codigo" = "204" ]; then
        echo "[briefing_vps] $(ahora) briefing lanzado (GitHub respondió 204)"
        rm -f "$cuerpo"
        return 0
    fi
    echo "[briefing_vps] $(ahora) GitHub rechazó el lanzamiento: HTTP $codigo $(head -c 300 "$cuerpo" 2>/dev/null)"
    rm -f "$cuerpo"
    avisar "⚠️ El briefing no se ha podido lanzar desde el servidor (HTTP $codigo): $(que_significa "$codigo") Saldrá igualmente cuando lo lance GitHub, con retraso."
    return 1
}

comprobar() {
    local hoy cuerpo codigo fecha token detalle=""
    hoy=$(date -u +%Y-%m-%d)
    cuerpo=$(mktemp)
    codigo=$(github GET "$cuerpo" "/gists/$GIST_BRIEFING" "$(leer_env GITHUB_TOKEN)")
    fecha=""
    if [ "$codigo" = "200" ] && [ -n "$PYTHON" ]; then
        fecha=$(PYTHONIOENCODING=utf-8 "$PYTHON" -c '
import json, sys
g = json.load(open(sys.argv[1], encoding="utf-8"))
print(json.loads(g["files"]["briefing.json"]["content"]).get("date", ""))
' "$cuerpo" 2>/dev/null || true)
    fi
    rm -f "$cuerpo"
    if [ "$fecha" = "$hoy" ]; then
        echo "[briefing_vps] $(ahora) el briefing de hoy está publicado"
        return 0
    fi

    # No está: se añade qué dice GitHub de la última ejecución, para que el
    # aviso diga si está en cola, corriendo o ha fallado.
    token=$(leer_env GITHUB_DISPATCH_TOKEN)
    if [ -n "$token" ] && [ -n "$PYTHON" ]; then
        cuerpo=$(mktemp)
        if [ "$(github GET "$cuerpo" "/repos/$REPO/actions/workflows/$WORKFLOW/runs?per_page=1" "$token")" = "200" ]; then
            detalle=$(PYTHONIOENCODING=utf-8 "$PYTHON" -c '
import json, sys
r = (json.load(open(sys.argv[1], encoding="utf-8")).get("workflow_runs") or [None])[0]
if r:
    estado = {"queued": "en cola", "in_progress": "ejecutándose", "completed": "terminada"}.get(r["status"], r["status"])
    fin = {"success": "bien", "failure": "con fallo", "cancelled": "cancelada"}.get(r.get("conclusion") or "", r.get("conclusion") or "")
    creada = (r.get("created_at") or "").replace("T", " ")[:16]
    print(" Última ejecución: " + estado + (" " + fin if fin else "") + ", creada " + creada + " UTC.")
' "$cuerpo" 2>/dev/null || true)
        fi
        rm -f "$cuerpo"
    fi
    local publicado="${fecha:-desconocida (no se pudo leer el Gist, HTTP $codigo)}"
    echo "[briefing_vps] $(ahora) el briefing de hoy NO está publicado (último: $publicado)"
    avisar "🕘 A las $(date -u +%H:%M) UTC el briefing de hoy todavía no está publicado. El último es del $publicado.$detalle"
    return 1
}

case "${1:-}" in
    lanzar)    lanzar ;;
    comprobar) comprobar ;;
    *) echo "Uso: $0 lanzar|comprobar" >&2; exit 2 ;;
esac
