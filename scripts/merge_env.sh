#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Fusiona backend/.env dentro de .env (raíz) y deja un único archivo real.
# Ver Plan Maestro 2.3 / auditoría 19/07/2026 #13.
#
# Por qué: docker-compose solo inyecta como variables de entorno REALES del
# contenedor las de .env (raíz) -- backend/.env solo lo lee pydantic-settings
# desde dentro de la app, así que un script aparte (Gael, cron, docker exec)
# nunca las ve. Esto ya causó confusión real dos veces esta semana (GIST_TOKEN
# en el archivo equivocado). Tras esta fusión, TODO vive en un único sitio,
# real para cualquier proceso.
#
# De paso corrige dos cosas encontradas hoy:
#   - ENVIRONMENT=development en el .env de producción -- esto DESACTIVA el
#     guardia de seguridad de config.py (el que impide arrancar con
#     SECRET_KEY/ADMIN_KEY por defecto). Se corrige a "production".
#   - TELEGRAM_BOT_TOKEN duplicado en backend/.env -- se queda una sola vez.
#
# No imprime NINGÚN valor en pantalla ni los envía a ningún sitio -- todo
# ocurre en archivos locales del propio servidor.
#
# Uso (desde ~/rsu-terminal-web):
#   chmod +x scripts/merge_env.sh
#   ./scripts/merge_env.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ] || [ ! -f backend/.env ]; then
    echo "ERROR: no se encuentran .env y backend/.env en las rutas esperadas."
    exit 1
fi

# Copia de seguridad antes de tocar nada
cp .env ".env.bak.$(date +%Y%m%d_%H%M%S)"
cp backend/.env "backend/.env.bak.$(date +%Y%m%d_%H%M%S)"
echo "Copias de seguridad creadas (.env.bak.* y backend/.env.bak.*)"

python3 - <<'PY'
import re

def leer_variables(ruta):
    """Devuelve {NOMBRE: linea_completa} preservando la PRIMERA aparición
    de cada nombre (si hay duplicados, como TELEGRAM_BOT_TOKEN, se
    descarta la repetida)."""
    variables = {}
    orden = []
    with open(ruta, encoding='utf-8') as f:
        for linea in f:
            m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*)=', linea.rstrip('\n'))
            if m:
                nombre = m.group(1).upper()  # normaliza casing (url_cartera -> URL_CARTERA, etc.)
                valor = linea.split('=', 1)[1].rstrip('\n')
                if nombre not in variables:
                    orden.append(nombre)
                variables[nombre] = valor  # si se repite, se queda con la ULTIMA (más probable que sea la vigente)
    return variables, orden

raiz_vars, raiz_orden = leer_variables('.env')
backend_vars, backend_orden = leer_variables('backend/.env')

# Fusion: empieza por lo que ya habia en la raiz, añade lo nuevo de backend/.env
fusion = dict(raiz_vars)
orden_final = list(raiz_orden)
for nombre in backend_orden:
    if nombre not in fusion:
        orden_final.append(nombre)
    fusion[nombre] = backend_vars[nombre]

# Correccion: ENVIRONMENT debe ser production (estaba en development,
# desactivando el guardia de seguridad de config.py)
if fusion.get('ENVIRONMENT', '').strip().lower() != 'production':
    print(f"Corrigiendo ENVIRONMENT: '{fusion.get('ENVIRONMENT', '(no existia)')}' -> 'production'")
    fusion['ENVIRONMENT'] = 'production'
    if 'ENVIRONMENT' not in orden_final:
        orden_final.append('ENVIRONMENT')

with open('.env', 'w', encoding='utf-8') as f:
    f.write("# .env consolidado -- fusion de .env + backend/.env, 20/07/2026 (Plan Maestro 2.3)\n")
    f.write("# Unico archivo de variables de entorno real -- backend/.env queda VACIO\n")
    f.write("# a proposito (docker-compose solo carga este). No borrar backend/.env\n")
    f.write("# del todo por si algun script antiguo aun lo referencia por error.\n\n")
    for nombre in orden_final:
        f.write(f"{nombre}={fusion[nombre]}\n")

with open('backend/.env', 'w', encoding='utf-8') as f:
    f.write("# VACIO A PROPOSITO desde el 20/07/2026 -- todas las variables viven ahora\n")
    f.write("# en el .env de la raiz del proyecto (~/rsu-terminal-web/.env), la unica que\n")
    f.write("# docker-compose inyecta de verdad al contenedor. Ver Plan Maestro 2.3.\n")

print(f"\nFusion completa: {len(orden_final)} variables en total en .env (raiz).")
print(f"backend/.env vaciado a proposito (solo comentario explicativo).")
PY

echo ""
echo "=== Nombres de variables en el .env final (sin valores) ==="
grep -o '^[A-Za-z_]*=' .env
echo ""
echo "Revisa esa lista. Si falta o sobra algo, hay copias de seguridad (.env.bak.*)."