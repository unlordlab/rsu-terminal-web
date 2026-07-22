"""
Test de regresión para services/cache.py::TTLCache -- documenta el
mecanismo exacto del bug real de la sesión 16 (commit beecce7): get_research(),
get_insider_ticker() y get_insider_clusters() cacheaban su resultado, y la
capa L1 de TTLCache devuelve la MISMA referencia de objeto que se pasó a
set() (no una copia) -- mutar el dict devuelto para añadir in_watchlist
habría filtrado el de un usuario a la respuesta cacheada que ve el
siguiente. El fix fue copiar antes de mutar ({**result} en research.py,
ver líneas 18-24).

Uso:
    cd backend
    python -m pytest tests/test_cache.py -v
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.cache import TTLCache  # noqa: E402


def test_copiar_antes_de_mutar_protege_la_entrada_cacheada():
    """Reproduce el patrón correcto que usa research.py: copiar con
    {**result} antes de mutar SÍ aísla al siguiente lector -- confirma que
    el patrón es efectivo, no solo un ritual sin efecto real."""
    cache = TTLCache()
    cache.set("test:k1", {"in_watchlist": False}, ttl=60)

    resultado = cache.get("test:k1")
    resultado_copia = {**resultado}
    resultado_copia["in_watchlist"] = True

    assert cache.get("test:k1")["in_watchlist"] is False


def test_mutar_sin_copiar_filtra_datos_entre_lecturas():
    """Test "canario": documenta que L1 devuelve la MISMA referencia, así
    que mutar el dict devuelto SIN copiar SÍ contamina la entrada
    cacheada -- exactamente el bug real de la sesión 16.

    Si algún día TTLCache.get() cambia a devolver una copia defensiva en
    L1 (decisión razonable en sí misma), este test empezará a fallar --
    eso es una SEÑAL de que hay que revisar los routers que dependen hoy
    del patrón `{**result}` (research.py, insider.py), no un bug nuevo
    que arreglar en el propio test."""
    cache = TTLCache()
    cache.set("test:k2", {"in_watchlist": False}, ttl=60)

    resultado = cache.get("test:k2")
    resultado["in_watchlist"] = True  # mutación directa, sin copiar

    assert cache.get("test:k2")["in_watchlist"] is True
