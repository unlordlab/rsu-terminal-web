#!/usr/bin/env bash
# deploy.sh — despliegue estándar de RSU Terminal en el VPS.
# Ver conversación 16-17/07/2026: el "version drift" entre VS Code local,
# GitHub y el VPS causó un problema real en producción (código con el
# arreglo del proxy/crumb nunca llegó a desplegarse). Este script es la
# única forma "oficial" de desplegar — nada de tocar código a mano en el
# VPS nunca más.
#
# Uso: ./deploy.sh
set -e  # cualquier fallo detiene el script en vez de seguir a ciegas

echo "=== 1/7: Comprobando estado de git ==="
# Solo bloqueamos por cambios en archivos que YA están en git (modificados,
# borrados, en stage) — no por archivos sueltos sin trackear (backups, etc.),
# que son normales y no afectan al despliegue.
DIRTY_TRACKED=$(git status --porcelain | grep -v '^??' || true)
if [ -n "$DIRTY_TRACKED" ]; then
    echo "✗ Hay cambios sin commitear en archivos que SÍ están en git. Esto no debería pasar nunca."
    echo "  Revisa 'git status' a mano antes de desplegar — abortando por seguridad."
    echo "$DIRTY_TRACKED"
    exit 1
fi
UNTRACKED=$(git status --porcelain | grep '^??' || true)
if [ -n "$UNTRACKED" ]; then
    echo "  (aviso, no bloquea) hay archivos sueltos sin trackear:"
    echo "$UNTRACKED"
fi

echo "=== 2/7: Trayendo cambios de GitHub ==="
# IMPORTANTE -- riesgo de auto-modificación: git pull puede actualizar este
# mismo fichero (deploy.sh) mientras bash ya lo tiene cargado en memoria de
# esta ejecución. Sin el relanzamiento de abajo, el resto de los pasos (3-7)
# seguirían corriendo con la lógica VIEJA que bash ya había leído, aunque el
# fichero en disco esté al día -- esto causó 2 despliegues seguidos
# ejecutando código de sesiones anteriores sin que nadie se diera cuenta
# hasta comparar el texto exacto de los mensajes de error (22/07/2026).
if [ -z "${DEPLOY_SH_RELANZADO:-}" ]; then
    BEFORE_COMMIT=$(git rev-parse HEAD)
    git pull
    AFTER_COMMIT=$(git rev-parse HEAD)

    if [ "$BEFORE_COMMIT" == "$AFTER_COMMIT" ]; then
        echo "  Este 'git pull' no trajo nada nuevo (puede que ya lo hubieras traído a mano)."
        echo "  Seguimos igualmente: recrear el contenedor es barato y así nos aseguramos"
        echo "  de que lo que está corriendo coincide siempre con lo último en disco."
    else
        echo "  Código actualizado -- relanzando deploy.sh desde la versión recién"
        echo "  descargada (necesario, ver comentario arriba)."
    fi
    DEPLOY_SH_RELANZADO=1 DEPLOY_SH_BEFORE="$BEFORE_COMMIT" DEPLOY_SH_AFTER="$AFTER_COMMIT" exec "$0"
fi
# A partir de aquí, garantizado que este proceso viene de una relectura
# fresca del fichero en disco -- todo lo de abajo es siempre la última
# versión, nunca una mezcla vieja/nueva.
BEFORE_COMMIT="$DEPLOY_SH_BEFORE"
AFTER_COMMIT="$DEPLOY_SH_AFTER"

echo "=== 3/7: Backup de las bases de datos antes de tocar nada ==="
# Antes de reconstruir la imagen o recrear el contenedor -- si algo sale mal
# en los pasos siguientes, queda una copia de las 13 bases de datos
# EXACTAMENTE como estaban justo antes de este despliegue. Reutiliza
# scripts/backup_dbs.sh (el mismo que ya corre a diario por cron) en vez de
# duplicar su lógica -- misma API .backup() de SQLite, segura con WAL activo
# (un cp normal puede copiar un estado inconsistente). Si el backup falla
# (p.ej. el contenedor anterior no está corriendo), se aborta ANTES de tocar
# nada -- no tiene sentido arriesgar el contenedor en marcha sin red de
# seguridad. Ver auditoría de infraestructura 21/07/2026, hallazgo crítico
# #4 ("el más grave de todo el proyecto" según el propio documento).
if ! ./scripts/backup_dbs.sh; then
    echo "✗ El backup pre-despliegue falló -- abortando ANTES de tocar nada."
    echo "  Revisa el error de arriba (¿está corriendo rsu-terminal-web-app-1?)."
    echo "  El contenedor en marcha sigue intacto, no se ha reconstruido ni recreado nada."
    exit 1
fi
echo "✓ Backup completado."

echo "=== 4/7: Comprobando si cambió algo que afecte a la imagen Docker ==="
# Antes solo miraba requirements.txt -- el fix de Reddit Pulse (23/07/2026)
# tocó el Dockerfile (instalación de Chromium) sin tocar requirements.txt,
# así que este chequeo dijo "sin cambios" y el contenedor se recreó con la
# imagen VIEJA, sin el binario arreglado -- el bug seguía en producción
# aunque el despliegue "funcionara". Cualquier cambio en el propio
# Dockerfile (no solo en lo que él instala) tiene que disparar rebuild.
if git diff --name-only "$BEFORE_COMMIT" "$AFTER_COMMIT" | grep -qE "^(requirements\.txt|Dockerfile)$"; then
    echo "  requirements.txt o Dockerfile cambió — reconstruyendo la imagen (esto tarda 1-2 min)..."
    docker compose build --no-cache app
else
    echo "  Sin cambios que afecten a la imagen — no hace falta reconstruir."
fi

echo "=== 5/7: Ejecutando la suite de tests (red de seguridad, ~35 tests) ==="
# El host del VPS no tiene pip NI las dependencias de la app (fastapi,
# pandas, yfinance...) -- solo viven dentro de la imagen Docker, que ya
# las trae instaladas de requirements.txt (Dockerfile). Intentar correr
# pytest con el python3 del host estaba mal planteado desde el principio
# (además de pelearse con pip ausente / PEP 668 "externally-managed", el
# import de cualquier servicio real habría fallado por falta de fastapi).
# Se corre en un contenedor EFÍMERO (--rm, se descarta al terminar) desde
# la MISMA imagen que se acaba de reconstruir arriba si hacía falta. -T
# desactiva la pseudo-TTY, necesario para correr sin terminal interactiva
# adjunta (cron, SSH no interactivo).
#
# NO se corre como root, y esto importa (incidente del 28/07/2026): antes
# llevaba --user root "solo para instalar pytest", con un comentario que
# afirmaba que eso no tocaba nada real. Era falso -- el repo va montado en
# vivo (`.:/app`), así que todo lo que root escribiera ahí quedaba en el
# disco del VPS con propietario root. Y al importar cualquier servicio se
# ejecuta su init_db(), o sea que SQLite abría las bases REALES y dejaba
# sus ficheros -wal/-shm siendo de root. A partir de ahí el contenedor
# normal (USER app) ya no podía escribir: "attempt to write a readonly
# database" -- Gael y Elia llevaban días generando propuestas y
# perdiéndolas al guardarlas, sin que nadie se enterara.
#
# Solución: correr como el usuario normal (app) e instalar pytest en /tmp,
# que sí es escribible sin privilegios. Cualquier fichero que toquen los
# tests queda con el mismo propietario que usa la app.
if ! docker compose run --rm -T app sh -c \
    "pip install --no-cache-dir -q --target /tmp/devdeps -r ../requirements-dev.txt && PYTHONPATH=/tmp/devdeps python -m pytest tests/ -q"; then
    echo "✗ La suite de tests ha fallado con el código ya en disco (commit $AFTER_COMMIT)."
    echo "  Abortando ANTES de recrear el contenedor en marcha -- el contenedor viejo"
    echo "  sigue corriendo intacto, producción no se ha tocado todavía."
    echo "  Revisa el fallo (arriba) y no despliegues hasta que la suite pase en verde."
    exit 1
fi
echo "✓ Suite de tests en verde."

# Red de seguridad del incidente del 28/07/2026: si por lo que sea vuelve a
# aparecer algún fichero propiedad de root dentro del repo (un contenedor
# lanzado a mano con --user root, un script suelto...), la app dejaría de
# poder escribir en sus propias bases de datos y los agentes fallarían en
# silencio. Se avisa aquí, que es cuando alguien está mirando la pantalla.
ROOT_FILES=$(find backend agents -maxdepth 1 -user root 2>/dev/null | head -5)
if [ -n "$ROOT_FILES" ]; then
    echo "⚠ ATENCIÓN: hay ficheros propiedad de root dentro del repo:"
    echo "$ROOT_FILES" | sed 's/^/    /'
    echo "  La app corre como usuario sin privilegios y NO podrá escribirlos."
    echo "  Arreglar con:  sudo chown -R \$(id -u):\$(id -g) backend agents"
fi

echo "=== 6/7: Recreando el contenedor ==="
docker compose up -d --force-recreate

echo "=== 7/7: Comprobación rápida de salud (10s de margen para arrancar) ==="
sleep 10
if docker ps --filter "name=rsu-terminal-web-app-1" --filter "status=running" | grep -q rsu-terminal-web-app-1; then
    echo "✓ Contenedor arriba y corriendo."
    docker logs rsu-terminal-web-app-1 --tail 20
else
    echo "✗ El contenedor no está corriendo — revisa los logs:"
    docker logs rsu-terminal-web-app-1 --tail 50
    exit 1
fi

echo ""
echo "=== Despliegue completado: $BEFORE_COMMIT -> $AFTER_COMMIT ==="