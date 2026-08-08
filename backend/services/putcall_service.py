"""
putcall_service.py -- ratio put/call de CBOE, para el bloque de sentimiento.

QUÉ MIDE
Cuántas opciones de venta se negocian por cada opción de compra. Por encima de
1 se compran más puts que calls (cobertura o apuesta bajista); muy por debajo,
más calls (apetito por subidas). Se lee como termómetro de miedo, y con la
lógica contraria a la intuición: los extremos altos suelen aparecer cerca de
suelos, no de techos.

DE DÓNDE SALE, Y POR QUÉ ASÍ
CBOE lo publica en su página de estadísticas diarias. Su CDN de JSON devuelve
403 desde el servidor (probado), pero la página normal responde 200 y trae los
valores YA EMBEBIDOS en el HTML que sirve el servidor, dentro del payload de
Next.js -- no hace falta ejecutar JavaScript ni levantar un navegador, basta
una petición normal y extraer el bloque.

FRAGILIDAD, DICHA DE FRENTE
Esto es raspado de una página, no una API con contrato. Un rediseño del sitio
lo rompe. Por eso: si el bloque no aparece o los números no son plausibles, se
devuelve `ok: False` y la tarjeta desaparece -- nunca un valor inventado ni el
último conocido haciéndose pasar por el de hoy. Es dato de cierre, no intradía.

Ver hallazgo #31 de la auditoría de Market.
"""
import re
import requests

URL = "https://www.cboe.com/us/options/market_statistics/daily/"

_CABECERAS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# Los nombres tal y como los publica CBOE -> la clave con la que se sirven.
_INTERESAN = {
    "TOTAL PUT/CALL RATIO":                        "total",
    "INDEX PUT/CALL RATIO":                        "indices",
    "EQUITY PUT/CALL RATIO":                       "acciones",
    "EXCHANGE TRADED PRODUCTS PUT/CALL RATIO":     "etfs",
    "CBOE VOLATILITY INDEX (VIX) PUT/CALL RATIO":  "vix",
}

# Un ratio put/call fuera de este rango no es un dato, es un error de lectura:
# históricamente se mueve entre 0,3 y 2 largos. Sirve para no publicar basura
# si CBOE cambia el formato y la extracción pesca otro número de la página.
_MIN, _MAX = 0.05, 5.0


def _extraer(html: str) -> dict:
    """Saca los pares nombre/valor del bloque de ratios. Se busca por el nombre
    de cada ratio y no por la estructura del JSON a propósito: el payload de
    Next.js viene escapado y troceado entre varios `<script>`, así que
    intentar parsearlo entero sería más frágil que buscar lo que interesa."""
    fuera = {}
    for etiqueta, clave in _INTERESAN.items():
        # \\" en el HTML porque el JSON va escapado dentro de una cadena JS
        m = re.search(re.escape(etiqueta) + r'\\?"\s*,\s*\\?"value\\?"\s*:\s*\\?"([\d.]+)\\?"', html)
        if not m:
            continue
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if _MIN <= v <= _MAX:
            fuera[clave] = v
    return fuera


def get_put_call_ratio() -> dict:
    from services.cache import cache
    from time_utils import get_timestamp

    try:
        r = requests.get(URL, headers=_CABECERAS, timeout=20)
        if r.status_code != 200:
            return {"ok": False, "error": f"CBOE respondió {r.status_code}"}
        ratios = _extraer(r.text)
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # El total es el que se enseña en grande; sin él no hay tarjeta.
    if "total" not in ratios:
        return {"ok": False, "error": "CBOE no devolvió el ratio total (¿cambió la página?)"}

    total = ratios["total"]
    # Umbrales convencionales del sector, no medidos aquí: por encima de 1 se
    # compran más puts que calls, y por debajo de 0,7 se suele hablar de
    # complacencia. Se etiquetan como referencia, no como señal.
    if total >= 1.0:
        zona = "miedo"
    elif total <= 0.7:
        zona = "complacencia"
    else:
        zona = "normal"

    resultado = {"ok": True, "zona": zona, "timestamp": get_timestamp(), **ratios}
    cache.set("market:putcall", resultado, 1800)
    return resultado
