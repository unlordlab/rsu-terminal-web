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

echo "=== 1/6: Comprobando estado de git ==="
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

echo "=== 2/6: Trayendo cambios de GitHub ==="
BEFORE_COMMIT=$(git rev-parse HEAD)
git pull
AFTER_COMMIT=$(git rev-parse HEAD)

if [ "$BEFORE_COMMIT" == "$AFTER_COMMIT" ]; then
    echo "  Este 'git pull' no trajo nada nuevo (puede que ya lo hubieras traído a mano)."
    echo "  Seguimos igualmente: recrear el contenedor es barato y así nos aseguramos"
    echo "  de que lo que está corriendo coincide siempre con lo último en disco."
fi

echo "=== 3/6: Ejecutando la suite de tests (red de seguridad, ~35 tests) ==="
# pytest solo vivía en requirements-dev.txt para uso local/CI -- nunca se
# había instalado en el host del VPS (deploy.sh corre fuera de Docker aquí).
# Antes de intentar instalar pytest, comprobar que pip EXISTE de verdad --
# en instalaciones mínimas de Ubuntu server, python3 no trae pip incluido
# (falta el módulo entero, no solo el paquete), y "pip install" fallaría
# con un traceback críptico que no dice qué hacer.
if ! python3 -m pip --version > /dev/null 2>&1; then
    echo "✗ pip no está disponible en este Python (python3 -m pip falla por completo,"
    echo "  no es solo que falte pytest). Esto es un problema del sistema, no del código."
    echo "  Arréglalo UNA VEZ con:"
    echo "    sudo apt-get update && sudo apt-get install -y python3-pip"
    echo "  y vuelve a correr ./deploy.sh. Abortando ANTES de tocar el contenedor."
    exit 1
fi
python3 -m pip show pytest > /dev/null 2>&1 || python3 -m pip install -q -r requirements-dev.txt
if ! (cd backend && python3 -m pytest tests/ -q); then
    echo "✗ La suite de tests ha fallado con el código ya en disco (commit $AFTER_COMMIT)."
    echo "  Abortando ANTES de reconstruir o recrear el contenedor -- el contenedor"
    echo "  viejo sigue corriendo intacto, producción no se ha tocado todavía."
    echo "  Revisa el fallo (arriba) y no despliegues hasta que la suite pase en verde."
    exit 1
fi
echo "✓ Suite de tests en verde."

echo "=== 4/6: Comprobando si cambiaron las dependencias de Python ==="
if git diff --name-only "$BEFORE_COMMIT" "$AFTER_COMMIT" | grep -q "requirements.txt"; then
    echo "  requirements.txt cambió — reconstruyendo la imagen (esto tarda 1-2 min)..."
    docker compose build --no-cache app
else
    echo "  Sin cambios en dependencias — no hace falta reconstruir la imagen."
fi

echo "=== 5/6: Recreando el contenedor ==="
docker compose up -d --force-recreate

echo "=== 6/6: Comprobación rápida de salud (10s de margen para arrancar) ==="
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