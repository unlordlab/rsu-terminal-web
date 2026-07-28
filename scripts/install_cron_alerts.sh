#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# install_cron_alerts.sh — envuelve los crons existentes del VPS con
# cron_alert.sh, para que dejen de fallar en silencio.
#
# EL PROBLEMA: los crons de Gael, Elia, Laia, el monitor de SPXL y los backups
# corren cada día y, si fallan, no se entera nadie. El rate limit de Gael se
# descubrió revisando una tesis a mano; el Daily Briefing estuvo TRES DÍAS
# fallando por un 413 de Groq antes de que alguien lo notara. cron_alert.sh
# existe desde el 20/07/2026 y hace exactamente esto, pero nunca se llegó a
# aplicar al crontab — hasta este script, que lo hace de una vez.
#
# CÓMO SE USA (en el VPS):
#     cd ~/rsu-terminal-web
#     ./scripts/install_cron_alerts.sh            # muestra qué haría, no toca nada
#     ./scripts/install_cron_alerts.sh --aplicar  # pide confirmación e instala
#
# QUÉ HACE, exactamente:
#   1. Lee el crontab actual (`crontab -l`) y guarda una copia de seguridad.
#   2. Por cada línea con un comando, la reescribe envuelta en cron_alert.sh,
#      conservando el horario, la redirección al log y el nombre de la tarea.
#   3. Enseña el ANTES y el DESPUÉS y pide confirmación explícita.
#   4. Solo entonces instala el crontab nuevo.
#
# Es idempotente: una línea ya envuelta se detecta y se deja igual.
# ─────────────────────────────────────────────────────────────────────────────
set -uo pipefail

DIR_SCRIPTS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVOLTORIO="$DIR_SCRIPTS/cron_alert.sh"
APLICAR="${1:-}"
RESPALDO="$HOME/crontab.backup.$(date +%Y%m%d_%H%M%S)"

if [ ! -x "$ENVOLTORIO" ]; then
    echo "✗ No encuentro $ENVOLTORIO (o no es ejecutable)."
    echo "  Solución: chmod +x scripts/cron_alert.sh"
    exit 1
fi

ACTUAL=$(crontab -l 2>/dev/null)
if [ -z "$ACTUAL" ]; then
    echo "✗ No hay crontab para este usuario (o no se puede leer)."
    exit 1
fi

# Nombre legible de la tarea a partir del comando, para que el aviso de
# Telegram diga "Gael (tesis diaria)" y no un comando de 200 caracteres.
nombre_tarea() {
    local cmd="$1"
    case "$cmd" in
        *bull_agent*)          echo "Gael (tesis)" ;;
        *academy_agent*|*elia*) echo "Elia (Academy)" ;;
        *laia*)                echo "Laia (comité de ética)" ;;
        *spxl_phase_monitor*)  echo "Monitor de fases SPXL" ;;
        *backup_dbs*)          echo "Backup de bases de datos" ;;
        *weekly*|*resumen*)    echo "Resumen semanal" ;;
        *)                     echo "$(echo "$cmd" | grep -oE '[a-zA-Z0-9_]+\.(py|sh)' | head -1)" ;;
    esac
}

NUEVO=""
declare -i ENVUELTAS=0 YA_OK=0 SALTADAS=0

while IFS= read -r linea; do
    # Comentarios, líneas en blanco y variables (MAILTO=, PATH=) se copian tal cual
    if [[ -z "${linea// }" || "$linea" =~ ^[[:space:]]*# || "$linea" =~ ^[A-Z_]+= ]]; then
        NUEVO+="$linea"$'\n'
        continue
    fi
    if [[ "$linea" == *"cron_alert.sh"* ]]; then
        NUEVO+="$linea"$'\n'
        YA_OK+=1
        continue
    fi

    # Separar: 5 campos de horario + resto (comando)
    if [[ "$linea" =~ ^([^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+[^[:space:]]+[[:space:]]+[^[:space:]]+)[[:space:]]+(.*)$ ]]; then
        HORARIO="${BASH_REMATCH[1]}"
        RESTO="${BASH_REMATCH[2]}"
    else
        NUEVO+="$linea"$'\n'
        SALTADAS+=1
        continue
    fi

    # Separar la redirección final (>> log 2>&1) para dejarla FUERA del
    # envoltorio: así el log sigue recogiendo la salida igual que ahora.
    REDIR=""
    COMANDO="$RESTO"
    if [[ "$RESTO" =~ ^(.*[^[:space:]])[[:space:]]+(\>\>?[[:space:]]*[^[:space:]]+([[:space:]]+2\>\&1)?)$ ]]; then
        COMANDO="${BASH_REMATCH[1]}"
        REDIR=" ${BASH_REMATCH[2]}"
    fi

    NOMBRE=$(nombre_tarea "$COMANDO")
    [ -z "$NOMBRE" ] && NOMBRE="tarea de cron"
    # Se escapan las comillas dobles del comando original
    COMANDO_ESC="${COMANDO//\"/\\\"}"
    NUEVO+="$HORARIO $ENVOLTORIO \"$NOMBRE\" \"$COMANDO_ESC\"$REDIR"$'\n'
    ENVUELTAS+=1
done <<< "$ACTUAL"

echo "═══════════════════════════════════════════════════════════════"
echo " CRONTAB ACTUAL"
echo "═══════════════════════════════════════════════════════════════"
echo "$ACTUAL"
echo
echo "═══════════════════════════════════════════════════════════════"
echo " CÓMO QUEDARÍA"
echo "═══════════════════════════════════════════════════════════════"
echo "$NUEVO"
echo "───────────────────────────────────────────────────────────────"
echo " $ENVUELTAS línea(s) a envolver · $YA_OK ya tenían aviso · $SALTADAS sin tocar (formato no reconocido)"
echo

if [ "$ENVUELTAS" -eq 0 ]; then
    echo "✓ No hay nada que hacer: todos los crons ya avisan si fallan."
    exit 0
fi

if [ "$APLICAR" != "--aplicar" ]; then
    echo "Esto ha sido solo una vista previa — no se ha tocado nada."
    echo "Para aplicarlo de verdad:  ./scripts/install_cron_alerts.sh --aplicar"
    exit 0
fi

read -r -p "¿Instalar el crontab nuevo? Se guardará una copia en $RESPALDO [s/N] " RESPUESTA
if [[ ! "$RESPUESTA" =~ ^[sSyY]$ ]]; then
    echo "Cancelado. No se ha tocado nada."
    exit 0
fi

echo "$ACTUAL" > "$RESPALDO"
echo "✓ Copia de seguridad en $RESPALDO"

if echo "$NUEVO" | crontab -; then
    echo "✓ Crontab instalado. Comprueba con: crontab -l"
    echo
    echo "Para revertir:  crontab $RESPALDO"
else
    echo "✗ Falló la instalación. El crontab anterior sigue intacto."
    echo "  La copia está en $RESPALDO por si acaso."
    exit 1
fi
