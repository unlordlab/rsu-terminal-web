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


# ── Estampida: varias peticiones recalculando lo mismo a la vez ──────────────
# Medido antes del fix con 5 peticiones simultáneas a los sectores y la caché
# vacía: 5 descargas reales en vez de 1. `_lock` protege el diccionario, no el
# recálculo, que vive en el llamador. Ver hallazgo #21 de la auditoría de Market.

def test_solo_uno_recalcula_y_los_demas_esperan_su_resultado():
    import threading, time
    cache = TTLCache()
    cache.delete("test:stampede")      # L1 y L2: el cache.db se comparte
    calculos = {"n": 0}

    @cache.single_flight("test:stampede")
    def caro():
        calculos["n"] += 1
        time.sleep(0.4)                       # simula la descarga
        r = {"valor": 7}
        cache.set("test:stampede", r, 60)
        return r

    respuestas = []
    hilos = [threading.Thread(target=lambda: respuestas.append(caro())) for _ in range(6)]
    for h in hilos: h.start()
    for h in hilos: h.join()

    assert calculos["n"] == 1, (
        f"Seis peticiones simultáneas debían provocar UN cálculo, hubo {calculos['n']}."
    )
    assert len(respuestas) == 6 and all(r == {"valor": 7} for r in respuestas), (
        "Los que esperan turno tienen que recibir el resultado, no un vacío."
    )


def test_el_que_espera_turno_no_recalcula_aunque_llegue_tarde():
    """La segunda mirada a la caché dentro del turno es lo que evita que el
    que esperaba recalcule igualmente: sin ella no se habría ganado nada."""
    import threading, time
    cache = TTLCache()
    cache.delete("test:stampede2")
    calculos = {"n": 0}

    @cache.single_flight("test:stampede2")
    def caro():
        calculos["n"] += 1
        time.sleep(0.3)
        cache.set("test:stampede2", {"v": 1}, 60)
        return {"v": 1}

    t = threading.Thread(target=caro)
    t.start()
    time.sleep(0.05)          # el segundo llega con el primero ya calculando
    segundo = caro()
    t.join()

    assert calculos["n"] == 1
    assert segundo == {"v": 1}


def test_los_candados_no_se_acumulan_clave_a_clave():
    """Una entrada por ticker consultado y para siempre sería una fuga: el
    candado se retira cuando no queda nadie esperando esa clave."""
    cache = TTLCache()
    for i in range(50):
        cache.delete(f"test:sf:T{i}")

    @cache.single_flight(lambda t: f"test:sf:{t}")
    def por_ticker(t):
        cache.set(f"test:sf:{t}", {"t": t}, 60)
        return {"t": t}

    for i in range(50):
        por_ticker(f"T{i}")

    assert len(cache._key_locks) == 0, (
        f"Quedaron {len(cache._key_locks)} candados sin retirar."
    )
