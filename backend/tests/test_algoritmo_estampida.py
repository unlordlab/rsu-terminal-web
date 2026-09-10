"""
El Dashboard provocaba una estampida contra Yahoo cada vez que caducaba la caché del Algoritmo.

EL CASO, Páginas Contenido #7, 10/09/2026. La auditoría (21/07) decía que el
Dashboard —la página de aterrizaje de todos— llamaba a `/api/v1/algoritmo` y
que ese endpoint hacía ~13 llamadas de red sin caché y escribía en SQLite en
cada carga. Verificado contra el código actual: eso YA estaba resuelto (caché
de 10 min desde julio, y el cálculo en vivo ya no escribe ni avisa).

Pero quedaba la ESTAMPIDA. Medido con red real, 10 cargas simultáneas con la
caché vacía:

    antes:  10 × SPY 15 años, 10 × VIX, 10 × VIX3M, 10 × FRED (serie desde 1996)
    ahora:   1 ×             1 ×       1 ×         1 ×

para devolver el mismo resultado diez veces. Y los fallos no se guardaban:
con Yahoo caído, cada carga del Dashboard repetía el cálculo entero.

LO QUE ATA ESTE FICHERO:
  - Un solo cálculo a la vez (`cache.single_flight`).
  - Los fallos se recuerdan un minuto. Sin eso, single_flight solo pone en
    fila a los que esperan, y cada uno vuelve a intentar contra el proveedor
    caído, uno detrás de otro.
  - Que el decorador está en LA función que toca. Al añadir una función junto
    a otra decorada ya le robé el decorador a la vecina una vez (market,
    09/09): el endpoint se quedó sin caché y los tests locales pasaban porque
    la caché estaba vacía.

Uso:
    cd backend
    python -m pytest tests/test_algoritmo_estampida.py -v
"""
import os
import sys
import threading
import time

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.rsu_algoritmo_service as S  # noqa: E402
from services.cache import cache  # noqa: E402


def _serie(n=300):
    idx = pd.bdate_range(end="2026-09-09", periods=n)
    return pd.DataFrame({"Close": [100.0 + i * 0.1 for i in range(n)],
                         "High": [101.0] * n, "Low": [99.0] * n, "Volume": [1e6] * n}, index=idx)


@pytest.fixture
def yahoo(monkeypatch):
    """Un Yahoo lento (como el de verdad) que cuenta cada descarga. Lo pesado
    del cálculo se sustituye: aquí se mide cuántas veces se CALCULA, no qué."""
    llamadas = {"history": 0, "fred": 0}
    candado = threading.Lock()
    estado = {"falla": False}

    class Ticker:
        def __init__(self, simbolo):
            self.s = simbolo

        def history(self, **k):
            with candado:
                llamadas["history"] += 1
            time.sleep(0.15)
            if estado["falla"]:
                raise ConnectionError("Yahoo caído")
            return _serie()

    def fred():
        with candado:
            llamadas["fred"] += 1
        return None

    monkeypatch.setattr(S.yf, "Ticker", Ticker)
    monkeypatch.setattr(S, "_fetch_hy_spread_cached", fred)
    monkeypatch.setattr(S, "_fetch_breadth_real", lambda: [{"advances": 1, "declines": 1}] * 50)
    monkeypatch.setattr(S, "_credit_stress_gate", lambda h: None)
    monkeypatch.setattr(S, "_calcular_score_punto", lambda *a, **k: {"estado": "AMBAR"})
    cache.delete(S.ALGORITMO_CACHE_KEY)
    yield llamadas, estado
    cache.delete(S.ALGORITMO_CACHE_KEY)


def _a_la_vez(n=10):
    resultados = []
    hilos = [threading.Thread(target=lambda: resultados.append(S.get_rsu_algoritmo())) for _ in range(n)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    return resultados


def test_diez_cargas_a_la_vez_calculan_UNA_sola_vez(yahoo):
    """EL test. Antes: 10 × (SPY + VIX + VIX3M) y 10 × FRED."""
    llamadas, _ = yahoo
    resultados = _a_la_vez(10)
    assert all(r["ok"] for r in resultados)
    assert llamadas["history"] == 3, f"{llamadas['history']} descargas: se ha calculado más de una vez"
    assert llamadas["fred"] == 1


def test_todas_reciben_el_MISMO_resultado(yahoo):
    resultados = _a_la_vez(6)
    assert len({r["timestamp"] for r in resultados}) == 1


def test_con_Yahoo_caido_se_intenta_UNA_vez_no_diez(yahoo):
    """Sin recordar el fallo, single_flight solo los pondría en fila y cada
    uno volvería a intentarlo contra el proveedor caído."""
    llamadas, estado = yahoo
    estado["falla"] = True
    resultados = _a_la_vez(10)
    assert all(r["ok"] is False for r in resultados)
    assert llamadas["history"] <= 3, f"{llamadas['history']} intentos contra un Yahoo caído"


def test_el_fallo_se_recuerda_UN_MINUTO_no_diez(yahoo):
    """Recordarlo tanto como un acierto dejaría el Dashboard sin algoritmo diez
    minutos por un tropiezo de un segundo."""
    _, estado = yahoo
    estado["falla"] = True
    S.get_rsu_algoritmo()
    assert S.TTL_FALLO == 60
    guardado = cache.get(S.ALGORITMO_CACHE_KEY)
    assert guardado is not None and guardado["ok"] is False


def test_un_resultado_bueno_se_sigue_guardando_10_minutos(yahoo, monkeypatch):
    ttls = []
    real_set = cache.set
    monkeypatch.setattr(cache, "set", lambda k, v, t=None: (ttls.append((k, t)), real_set(k, v, t))[1])
    S.get_rsu_algoritmo()
    assert (S.ALGORITMO_CACHE_KEY, 600) in ttls


def test_el_decorador_esta_en_LA_funcion_que_toca():
    """La lección del 09/09: el decorador se lo quedó la función de al lado."""
    assert hasattr(S.get_rsu_algoritmo, "__wrapped__")
    assert S.get_rsu_algoritmo.__wrapped__.__name__ == "get_rsu_algoritmo"
    for vecina in ("_fetch_breadth_real", "_fallo"):
        assert not hasattr(getattr(S, vecina), "__wrapped__"), f"{vecina} ha heredado el decorador"
