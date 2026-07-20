#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Backup diario de TODAS las bases de datos SQLite de RSU Terminal.
# Ver PLAN_MAESTRO_MEJORAS 0.1 y auditoría 19/07/2026 (crítico #3: cero
# backups de users.db, tesis.db, cache.db, meeting_room.db, etc.).
#
# Cómo funciona:
#   - Descubre automáticamente todos los *.db de backend/ (no hay lista
#     hardcodeada que se quede corta cuando añadas la próxima BD).
#   - Usa la API .backup() de SQLite DESDE DENTRO del contenedor — es la
#     única forma segura de copiar una BD viva en modo WAL; un cp normal
#     puede producir una copia corrupta si hay escrituras en ese momento.
#   - Guarda en ./backups/ (bind-mounted, así que visible en el host).
#   - Rotación: borra backups de más de 14 días.
#
# Instalación (una vez, en el VPS):
#   chmod +x scripts/backup_dbs.sh
#   crontab -e   →   30 4 * * * /home/rsu/rsu-terminal-web/scripts/backup_dbs.sh >> /home/rsu/backup_dbs.log 2>&1
#
# PENDIENTE (anotado en Plan Maestro): copia EXTERNA al VPS (rclone a B2/S3,
# scp a otra máquina, etc.) — un backup en el mismo disco protege de errores
# humanos y borrados, pero no de un fallo del disco/VPS entero.
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backups

# El flag -i es IMPRESCINDIBLE: sin él, docker exec no conecta stdin y el
# bloque Python de abajo nunca llega al intérprete (python arranca, lee
# entrada vacía y sale sin error y sin hacer nada — fallo silencioso
# detectado en la primera ejecución real, 20/07/2026).
docker exec -i rsu-terminal-web-app-1 python3 - <<'PY'
import sqlite3, glob, os, datetime

os.makedirs('/app/backups', exist_ok=True)
stamp = datetime.date.today().isoformat()
dbs = sorted(glob.glob('/app/backend/*.db'))

if not dbs:
    print("AVISO: no se encontró ninguna .db en /app/backend — revisar rutas.")

for path in dbs:
    name = os.path.basename(path)[:-3]
    dest = f'/app/backups/{name}_{stamp}.db'
    try:
        src = sqlite3.connect(path)
        dst = sqlite3.connect(dest)
        with dst:
            src.backup(dst)   # API oficial de copia segura, consistente con WAL
        dst.close(); src.close()
        size_kb = os.path.getsize(dest) // 1024
        print(f'  OK {name} -> {os.path.basename(dest)} ({size_kb} KB)')
    except Exception as e:
        # Un fallo en una BD no debe impedir el backup de las demás
        print(f'  ERROR {name}: {type(e).__name__}: {e}')
PY

# Rotación en el host: conservar 14 días
find backups -name "*.db" -mtime +14 -delete 2>/dev/null || true

echo "Backup completado: $(date '+%Y-%m-%d %H:%M:%S') — $(ls backups/*.db 2>/dev/null | wc -l) archivos en ./backups/"