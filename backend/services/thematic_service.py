"""
Composición Sectorial Temática — 29 cestas inspiradas en dashboards tipo AION
Index (BIOTECH, SEMIS, MAG7, SPACE...), con un universo de tickers propio
(no limitado al S&P 500).

IMPORTANTE: este módulo NO calcula nada on-demand. El scan pesado (descarga de
~290 tickers vía yfinance) corre 1x/día por GitHub Actions
(scripts/thematic_scan.py + .github/workflows/thematic_scan.yml) y sube el
resultado a un Gist. Aquí solo se LEE ese Gist — así ninguna petición de un
usuario real dispara llamadas a Yahoo Finance, evitando rate limits y tiempos
de carga largos en la página. Mismo patrón que usa el Daily Briefing.

Si quieres editar las 29 cestas o sus tickers, edita
scripts/thematic_scan.py (es la única fuente de verdad del scan) — este
archivo no tiene la lista de tickers porque no la necesita.
"""
from services.gist_client import cabeceras_gist
import json
import requests
from services.cache import cache

GIST_ID    = "2baff1038ff2bf57b34f7f5ca3f846aa"  # ← rellenar con el ID del Gist (ver instrucciones de configuración)
GIST_FILE  = "thematic_scan.json"
CACHE_KEY  = "market:thematic_breadth"
CACHE_TTL  = 1800  # 30 min — el dato en sí solo cambia 1x/día, esto es caché local extra


def _load_gist() -> dict | None:
    if not GIST_ID:
        return None
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            timeout=10,
            headers=cabeceras_gist()
        )
        r.raise_for_status()
        content = r.json()["files"][GIST_FILE]["content"]
        data = json.loads(content)
        return data if data.get("ok") and data.get("sectors") else None
    except Exception as e:
        print(f"[Thematic] Error leyendo Gist: {e}")
        return None


def _normalizar(fila: dict) -> dict:
    """Puente entre el Gist que hay AHORA y el que publicará el próximo scan.

    El scan pasa a mandar `avg_momentum` en porcentaje (43) en vez de en
    fracción (0.43), y añade `definidos`/`faltan` para poder decir cuántos
    valores de la cesta han dejado de cotizar. Pero el Gist solo se reescribe
    una vez al día: entre el despliegue y ese scan, el backend leería el
    formato viejo y la pantalla mostraría "0%" en todas las cestas.

    Una fracción nunca pasa de 1 y un porcentaje útil casi nunca baja de ahí,
    así que el corte distingue los dos formatos sin ambigüedad. Se puede
    quitar en cuanto haya corrido un scan (ver `generated_at` del Gist).
    """
    fila = dict(fila)
    m = fila.get("avg_momentum")
    if m is not None and m <= 1:
        fila["avg_momentum"] = round(m * 100)
    fila.setdefault("definidos", fila.get("basket", 0))
    fila.setdefault("faltan", 0)
    return fila


def get_thematic_composition() -> dict:
    cached = cache.get(CACHE_KEY)
    if cached:
        return cached

    data = _load_gist()
    if not data:
        return {
            "ok": False,
            "error": "Composición sectorial no disponible todavía — el scan diario (GitHub Action) "
                     "aún no ha generado datos, o el Gist no está configurado (ver THEMATIC_GIST_ID).",
        }

    # Formato de salida idéntico al que ya consume el frontend (market.js),
    # solo renombramos timestamp para reflejar que es el momento del scan,
    # no el momento de esta petición.
    # Variación contra el histórico propio. Va FUERA de la caché de arriba a
    # propósito: el scan temático es diario, pero el histórico crece cada
    # sesión y no tiene por qué esperar al TTL de esta respuesta.
    try:
        from services.snapshots_service import variacion_por_cesta
        variaciones = variacion_por_cesta()
    except Exception as e:
        print(f"[Thematic] Sin variación histórica esta vuelta: {type(e).__name__}: {e}")
        variaciones = {}

    sectores = []
    for s in data["sectors"]:
        fila = _normalizar(s)
        fila.update(variaciones.get(fila["sector"], {"d5": None, "d20": None}))
        sectores.append(fila)

    result = {
        "ok":              True,
        "sectors":         sectores,
        "strongest":       data.get("strongest"),
        "weakest":         data.get("weakest"),
        "sectors_tracked": data.get("sectors_tracked", 0),
        "sectors_empty":   data.get("sectors_empty", 0),
        "universe_size":   data.get("universe_size", 0),
        "accelerating":    data.get("accelerating", []),
        "decelerating":    data.get("decelerating", []),
        "freshness":       data.get("generated_at", ""),
        "timestamp":       data.get("generated_at", ""),
    }
    cache.set(CACHE_KEY, result, CACHE_TTL)
    return result