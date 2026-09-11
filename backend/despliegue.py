"""
Qué versión del código está corriendo.

deploy.sh sella el commit en backend/VERSION justo antes de construir la
imagen. Lo leen /health (para saber qué hay desplegado) y la caché de
Research (para que un despliegue no sirva durante 15 minutos datos con la
forma de la versión anterior).
"""
import os


def version_desplegada() -> dict:
    try:
        with open(os.path.join(os.path.dirname(__file__), "VERSION"), encoding="utf-8") as f:
            lineas = [l.strip() for l in f if l.strip()]
        return {"commit": lineas[0], "desplegado": lineas[1] if len(lineas) > 1 else None}
    except Exception:
        # Sin fichero: se está ejecutando fuera de un despliegue (desarrollo
        # local) o la imagen se construyó sin pasar por deploy.sh. Se dice, en
        # vez de inventar un número de versión.
        return {"commit": "desconocida", "desplegado": None}


# Se lee UNA vez: dentro del contenedor el fichero no cambia mientras el
# proceso vive.
COMMIT = version_desplegada()["commit"]
