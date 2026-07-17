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

echo "=== 1/5: Comprobando estado de git ==="
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

echo "=== 2/5: Trayendo cambios de GitHub ==="
BEFORE_COMMIT=$(git rev-parse HEAD)
git pull
AFTER_COMMIT=$(git rev-parse HEAD)

if [ "$BEFORE_COMMIT" == "$AFTER_COMMIT" ]; then
    echo "  Ya estabas al día — nada nuevo que desplegar."
    echo "=== Terminado (sin cambios) ==="
    exit 0
fi

echo "=== 3/5: Comprobando si cambiaron las dependencias de Python ==="
if git diff --name-only "$BEFORE_COMMIT" "$AFTER_COMMIT" | grep -q "requirements.txt"; then
    echo "  requirements.txt cambió — reconstruyendo la imagen (esto tarda 1-2 min)..."
    docker compose build --no-cache app
else
    echo "  Sin cambios en dependencias — no hace falta reconstruir la imagen."
fi

echo "=== 4/5: Recreando el contenedor ==="
docker compose up -d --force-recreate

echo "=== 5/5: Comprobación rápida de salud (10s de margen para arrancar) ==="
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