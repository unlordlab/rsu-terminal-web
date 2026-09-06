"""
El track record de CANSLIM solo se escribía si alguien abría el módulo.

EL CASO, 06/09/2026, al ir a montar Breakout Alerts. Lo primero era ver cuánta
muestra había acumulado `canslim_history.db` en producción, porque de eso
dependía todo el plan de medición. Salió esto:

    sesiones : 13          desde 2026-08-02  hasta 2026-09-03
    filas    : 6484        con resultado a 20 días: 2483
    últimas  : 09-03, 08-26, 08-24, 08-20, 08-18, 08-17

Trece sesiones registradas en ~24 días de mercado, con un hueco de CINCO
sesiones seguidas entre el 26/08 y el 03/09.

LA CAUSA. `_registrar_scan_para_track_record()` se llama desde dentro de
`get_canslim_from_gist()` -- o sea, en la LECTURA del Gist, que solo ocurre
cuando alguien pide el escáner. El bucle de precalentamiento de 4 minutos
refresca amplitud, Fed Macro, credit spreads y el snapshot diario, pero NO
llamaba a CANSLIM. Así que el registro colgaba del tráfico.

Y LO QUE IMPORTA NO ES QUE FALTEN DÍAS, SINO CUÁLES. La gente abre el escáner
más cuando el mercado hace algo, así que el track record se estaba midiendo
sobre un subconjunto sesgado hacia sesiones movidas. Es la misma familia del
sesgo de selección de Options Flow, donde los contratos sin vencer solo
recibían veredicto si ya habían tocado el strike y salía un 100% por
construcción. Para calcular una tasa base -- que es lo que decide si Breakout
Alerts llega a existir-- eso lo invalida.

POR QUÉ EN EL BUCLE DE 4 MIN Y NO EN UNO DE 24H. La decisión original de
evitar un bucle diario era correcta y está comentada en el código: «cada 24h
desde que arrancó» deriva de cuándo se reinició el contenedor, no de una fecha
real (Options Flow, sesión 35). El bucle de 4 minutos no tiene ese problema
porque `registrar_scan` es idempotente por FECHA DE SESIÓN: registra en cuanto
el Gist trae una sesión nueva, den igual los reinicios. Es el mismo patrón con
el que ya cuelga `maybe_write_daily_snapshot`.

UN ERROR MÍO, CORREGIDO ANTES DE COMMITEAR: la primera versión llamaba a
`scan_canslim()`, que está ochenta líneas más abajo y NO registra nada. Habría
sido un arreglo que no arregla -- exactamente el guardián que no puede
dispararse del día anterior. Por eso el test de abajo EJECUTA el bucle en vez
de mirar el fuente.

Uso:
    cd backend
    python -m pytest tests/test_canslim_registro_no_depende_del_trafico.py -v
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import routers.ws as W  # noqa: E402
import services.canslim_service as C  # noqa: E402


class _Reloj:
    """Deja correr N vueltas del bucle y lo corta. `asyncio.sleep` se sustituye
    por esto para no esperar 4 minutos por iteración."""

    def __init__(self, vueltas, vuelta):
        self.quedan = vueltas
        self.vuelta = vuelta

    async def __call__(self, s):
        self.vuelta[0] += 1
        self.quedan -= 1
        if self.quedan < 0:
            raise asyncio.CancelledError


class _Llamadas(list):
    """Lista de (vuelta, nombre) que sigue respondiendo a `in` y `count` por
    nombre, para no reescribir los tests que solo miran quien fue llamado."""

    def __contains__(self, nombre):
        return any(n == nombre for _, n in self)

    def count(self, nombre):
        return sum(1 for _, n in self if n == nombre)

    def vueltas_de(self, nombre):
        return {v for v, n in self if n == nombre}


def _correr(monkeypatch, vueltas, canslim=None):
    """Ejecuta el bucle real de precalentamiento contando a quién llama.

    Se parchea lo que sale a la red, no el bucle: lo que se comprueba es el
    bucle de producción, no una copia suya.

    `canslim` permite sustituir esa llamada concreta (por ejemplo por una que
    explota). La primera versión no lo tenía y los tests que parcheaban la
    función ANTES de llamar aquí veían su parche PISADO por el de dentro --
    así que comprobaban el camino feliz creyendo que probaban el fallo."""
    llamadas = []
    vuelta = [0]

    def _stub(nombre):
        def f(*a, **k):
            llamadas.append((vuelta[0], nombre))
            return {}
        return f

    monkeypatch.setattr(C, "get_canslim_from_gist", canslim or _stub("canslim"),
                        raising=False)
    import services.market_service as M
    for n in ("get_market_breadth", "get_fed_macro", "get_credit_spreads"):
        monkeypatch.setattr(M, n, _stub(n), raising=False)
    import services.snapshots_service as S
    monkeypatch.setattr(S, "maybe_write_daily_snapshot", _stub("snapshot"), raising=False)

    reloj = _Reloj(vueltas, vuelta)
    monkeypatch.setattr(W.asyncio, "sleep", reloj)
    try:
        asyncio.run(W.market_cache_warm_loop())
    except asyncio.CancelledError:
        pass
    return _Llamadas(llamadas)


# ── Que se registre sin que nadie abra nada ──────────────────────────────────

def test_el_bucle_pide_el_scan_de_CANSLIM_sin_intervencion_de_nadie(monkeypatch):
    """EL test. Antes del 06/09 el registro solo ocurría si un usuario abría el
    módulo, y en producción eso dejó 13 sesiones de ~24."""
    llamadas = _correr(monkeypatch, vueltas=10)     # 10 x 4 min = 40 min
    assert "canslim" in llamadas, (
        "el bucle de precalentamiento no pide el scan de CANSLIM, así que el "
        "track record sigue dependiendo de que alguien abra la página")


def test_llama_a_la_funcion_que_REGISTRA_y_no_a_la_de_al_lado():
    """El registro vive en `get_canslim_from_gist()`. La primera versión de
    este arreglo llamaba a `scan_canslim()`, que está ochenta líneas más abajo
    y no registra nada: un arreglo que no arregla.

    Se comprueba sobre el servicio, no sobre el bucle: lo que se afirma es
    dónde está la llamada al registro."""
    import inspect
    fuente = inspect.getsource(C.get_canslim_from_gist)
    assert "_registrar_scan_para_track_record" in fuente, (
        "el registro ya no está en get_canslim_from_gist: hay que actualizar a "
        "quién llama el bucle de precalentamiento")
    assert "_registrar_scan_para_track_record" not in inspect.getsource(C.scan_canslim)


def test_se_pide_de_forma_periodica_no_una_sola_vez(monkeypatch):
    """Una sola llamada al arrancar registraría la sesión de ese momento y
    ninguna más: el contenedor puede llevar días levantado."""
    pocas = _correr(monkeypatch, vueltas=6)      # 24 min
    muchas = _correr(monkeypatch, vueltas=30)    # 2 h
    assert muchas.count("canslim") > pocas.count("canslim"), (
        "el scan solo se pide una vez; con el contenedor levantado varios días "
        "no se registraría ninguna sesión nueva")


def test_no_se_pide_en_CADA_vuelta_de_cuatro_minutos(monkeypatch):
    """El dato cambia una vez al día. Pedirlo cada 4 minutos sería una lectura
    del Gist cada 4 minutos para nada -- y la API de GitHub va limitada."""
    llamadas = _correr(monkeypatch, vueltas=30)   # 2 h de bucle
    assert llamadas.count("canslim") <= 6, (
        f"se ha pedido {llamadas.count('canslim')} veces en 2 h: demasiado "
        f"para un dato que cambia una vez al día")


def test_no_coincide_con_Fed_Macro_en_el_mismo_ciclo(monkeypatch):
    """Dos lecturas de red en la misma vuelta alargan el ciclo sin motivo: la
    cadencia va desplazada media ventana a propósito.

    La primera versión de este test solo contaba llamadas -- o sea, no
    comprobaba nada de lo que dice su nombre y habría pasado con las dos
    cadencias idénticas."""
    llamadas = _correr(monkeypatch, vueltas=60)   # 4 h
    cans = llamadas.vueltas_de("canslim")
    fed = llamadas.vueltas_de("get_fed_macro")
    assert len(cans) >= 3 and len(fed) >= 3, "no hay suficientes llamadas para juzgarlo"
    assert not (cans & fed), (
        f"CANSLIM y Fed Macro caen en las mismas vueltas ({sorted(cans & fed)}): "
        f"dos lecturas de red en el mismo ciclo")


# ── Que no se lleve por delante lo que ya hacía el bucle ─────────────────────

def test_lo_que_el_bucle_ya_precalentaba_sigue_precalentandose(monkeypatch):
    """Añadir una tarea a un bucle compartido es una forma fácil de romper las
    que ya estaban."""
    llamadas = _correr(monkeypatch, vueltas=30)
    for n in ("get_market_breadth", "get_fed_macro", "get_credit_spreads", "snapshot"):
        assert n in llamadas, f"el bucle ha dejado de refrescar {n}"


def test_un_fallo_del_scan_no_tumba_el_resto_del_bucle(monkeypatch):
    """Que el tracking falle no puede dejar sin amplitud ni sin snapshot a
    quien solo quería mirar la pantalla."""
    def _explota(*a, **k):
        raise RuntimeError("Gist caido")
    llamadas = _correr(monkeypatch, vueltas=30, canslim=_explota)
    assert "get_market_breadth" in llamadas and "snapshot" in llamadas, (
        "un fallo leyendo el Gist de CANSLIM ha tumbado el resto del bucle")


def test_el_fallo_se_DICE_en_vez_de_tragarse(monkeypatch, capsys):
    """Un `except` mudo alrededor de una dependencia externa convierte un fallo
    permanente en silencio -- es lo que dejó muerta la fecha de resultados de
    yfinance durante meses."""
    def _explota(*a, **k):
        raise RuntimeError("Gist caido")
    _correr(monkeypatch, vueltas=30, canslim=_explota)
    salida = capsys.readouterr().out
    assert "CANSLIMTracking" in salida and "Gist caido" in salida, (
        "el fallo al precalentar el scan se traga en silencio")
