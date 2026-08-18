"""
Options Flow: por qué el escaneo leía la mitad del universo (18/08/2026).

EL DIAGNÓSTICO, medido y no supuesto -- y el primero que probé era falso.
En producción el escaneo leía 306 de 579 tickers (52,8%) mientras la MISMA
función en local leía 528. Parecía cosa de la IP del VPS, así que el primer
arreglo fue "reintentar enseguida los que fallaron". Recuperó 0 de 234.

Al reproducirlo aquí apareció el mecanismo de verdad: los que fallan no son
tickers sueltos con un tropiezo, son TODO lo que viene detrás de cierto punto.
Yahoo no rechaza peticiones una a una: corta a la IP entera. Comprobado
pidiendo AAPL justo después de un escaneo caído -- también fallaba, con
YFRateLimitError, siendo el ticker más líquido que existe y el primero del
universo. Medido además cuánto dura el corte: ~61 s con una sola petición de
sondeo, pero MÁS de 90 s después de un escaneo completo -- cada petición
inútil contra el muro le reinicia la cuenta.

Medido con el universo real: de 345/579 (59,6%) a 575/579 (99,3%).

Con eso, el arreglo que sí corresponde al mecanismo tiene tres piezas, y son
las tres que se protegen aquí:

  1. Un corte se distingue de cualquier otro fallo (`rate_limited`) y NO se
     reintenta dentro del ticker: insistir tres veces seguidas es pedir el
     triple de peticiones justo cuando el muro acaba de levantarse.
  2. El reintento va por rondas, ESPERANDO de verdad a que el corte baje
     (180 s la primera), y cada ronda solo pide lo que sigue faltando.
  3. Si el muro sigue en pie, la ronda se corta en cuanto se ve; y hay un
     presupuesto de tiempo, porque un día de opciones no se puede reintentar
     mañana -- las cadenas solo existen mientras están vivas, y más vale
     publicar el 90% que agotar el temporizador sin guardar nada.

Uso:
    cd backend
    python -m pytest tests/test_options_segunda_pasada.py -v
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402
from yfinance.exceptions import YFRateLimitError  # noqa: E402

TICKERS = ["AAA", "BBB", "CCC", "DDD"]


def _ok(ticker):
    """Respuesta mínima con la forma que devuelve _process_chain al acertar."""
    return {
        "ticker": ticker, "ok": True, "price": 10.0,
        "sentiment": "NEUTRAL", "sentiment_prem": "NEUTRAL",
        "net_prem_score": 0.0, "pc_ratio_prem": 1.0,
        "bull_prem": 0.0, "bear_prem": 0.0,
        "total_call_prem": 0.0, "total_put_prem": 0.0, "total_prem": 0.0,
        "oi_max": 100, "oi_snapshot": [],
        "calls_bought": [], "puts_bought": [], "calls_sold": [], "puts_sold": [],
        "next_earnings": None,
    }


def _cortado(ticker):
    return {"ticker": ticker, "ok": False, "rate_limited": True, "error": "corte"}


class _Chain:
    """_process_chain falso. `muro_hasta` imita el mecanismo real: mientras el
    reloj simulado no lo supere, TODO ticker sale cortado, sea cual sea."""

    def __init__(self, muro_hasta=0.0, sin_cadena=(), muro_permanente=False):
        self.muro_hasta = muro_hasta
        self.sin_cadena = set(sin_cadena)
        self.muro_permanente = muro_permanente
        self.llamadas = []

    def __call__(self, ticker, min_premium=0, min_score=0):
        self.llamadas.append((ticker, O.time.time()))
        if self.muro_permanente or O.time.time() < self.muro_hasta:
            return _cortado(ticker)
        if ticker in self.sin_cadena:
            return {"ticker": ticker, "ok": False, "error": "sin cadena"}
        return _ok(ticker)


class _Reloj:
    """Reloj falso: dormir avanza el tiempo en vez de gastarlo, para poder
    probar esperas de 90/180/300 s sin que el test tarde 10 minutos."""

    def __init__(self):
        self.t = 1000.0
        self.dormido = []

    def time(self):
        return self.t

    def sleep(self, s):
        self.dormido.append(s)
        self.t += s


def _correr(chain, reloj=None, esperas=(90, 180, 300), presupuesto=20 * 60):
    reloj = reloj or _Reloj()
    with patch.object(O, "_process_chain", chain), \
         patch.object(O, "REINTENTO_ESPERAS", list(esperas)), \
         patch.object(O, "REINTENTO_PAUSA_ENTRE", 0.1), \
         patch.object(O, "PRESUPUESTO_SEGUNDOS", presupuesto), \
         patch.object(O.time, "time", reloj.time), \
         patch.object(O.time, "sleep", reloj.sleep), \
         patch("services.cartera_service.get_cartera_tickers", return_value=set()):
        return O.get_options_flow(tickers=list(TICKERS)), reloj


# ── 1. Un corte no es un fallo cualquiera ────────────────────────────────────

def test_un_corte_de_yahoo_se_declara_y_no_se_confunde_con_no_tener_cadena():
    """Sin distinguirlos no hay forma de decidir si esperar o seguir: "este
    ticker no tiene opciones" y "Yahoo ha cortado a esta IP" piden lo
    contrario."""
    class TkCortado:
        @property
        def fast_info(self):
            raise YFRateLimitError()

        def history(self, **kw):
            raise YFRateLimitError()

        @property
        def options(self):
            raise YFRateLimitError()

    with patch.object(O.yf, "Ticker", return_value=TkCortado()):
        r = O._process_chain("AAPL")
    assert r["ok"] is False
    assert r.get("rate_limited") is True, \
        "un corte de Yahoo debe declararse como tal, no como un fallo generico"


def test_un_fallo_normal_no_se_marca_como_corte():
    import pandas as pd

    class TkVacio:
        @property
        def fast_info(self):
            raise Exception("nada")

        def history(self, **kw):
            return pd.DataFrame()

        @property
        def options(self):
            return []

    with patch.object(O.yf, "Ticker", return_value=TkVacio()):
        r = O._process_chain("XYZ")
    assert r["ok"] is False
    assert not r.get("rate_limited")


# ── 2. Esperar de verdad, y recuperar ────────────────────────────────────────

def test_se_recupera_lo_que_cayo_por_el_corte_una_vez_este_baja():
    """EL test. El primer intento de arreglo reintentaba a los 5 segundos y
    recuperaba 0 de 234, porque el muro seguía en pie."""
    reloj = _Reloj()
    # El muro cae a los 61 s (lo medido en sondeo); la primera ronda espera 180.
    chain = _Chain(muro_hasta=reloj.t + 61)
    r, _ = _correr(chain, reloj)
    assert r["respondidos"] == 4, \
        f"solo {r['respondidos']} de 4: no se ha recuperado lo que tumbo el corte"


def test_la_primera_espera_supera_la_duracion_medida_del_corte():
    """Reintentar antes de tiempo es tirar el intento -- es exactamente lo que
    hacía la primera versión de este arreglo (5 s: 0 recuperados de 234).

    El número salió de medirlo dos veces, y la segunda corrigió a la primera:
    con una sola petición de sondeo el corte se levanta a los ~61 s, pero tras
    un escaneo completo a los 90 s seguía en pie. De ahí 180."""
    assert O.REINTENTO_ESPERAS, "sin esperas configuradas no hay reintento que valga"
    assert O.REINTENTO_ESPERAS[0] >= 180, \
        f"la primera espera ({O.REINTENTO_ESPERAS[0]}s) no llega: con 90s el muro seguia en pie"
    assert O.REINTENTO_ESPERAS == sorted(O.REINTENTO_ESPERAS), \
        "las esperas deben ir a mas, no a menos"


def test_no_se_vuelve_a_pedir_lo_que_ya_habia_respondido():
    """Reintentar el universo entero duplicaría el tráfico, que es justo lo
    que dispara el corte que esto viene a esquivar."""
    reloj = _Reloj()
    chain = _Chain(muro_hasta=reloj.t + 61)
    _correr(chain, reloj)
    pedidos = [t for t, _ in chain.llamadas]
    # Los 4 caen por el muro en la primera pasada y los 4 se reintentan una
    # vez, ya con el corte bajado. Ninguno una tercera.
    for t in TICKERS:
        assert pedidos.count(t) == 2, f"{t} pedido {pedidos.count(t)} veces"


# ── 3. No darse contra la pared, y no quedarse sin publicar ──────────────────

def test_si_el_muro_sigue_en_pie_la_ronda_se_corta_pronto():
    """Con el corte activo, seguir pidiendo los 579 no recupera nada y alarga
    el bloqueo. Se corta en cuanto se ve y se pasa a la siguiente espera."""
    chain = _Chain(muro_permanente=True)
    with patch.object(O, "REINTENTO_ABORTAR_TRAS", 2):
        r, _ = _correr(chain, esperas=(90,))
    reintentos = len(chain.llamadas) - len(TICKERS)
    assert reintentos <= 2, f"{reintentos} reintentos contra un muro que no baja"
    assert r["respondidos"] == 0


def test_lo_que_nunca_tuvo_cadena_no_dispara_rondas_infinitas():
    """Un ticker sin opciones no las va a tener por insistir. Se intenta en
    cada ronda pero nunca cuenta como leído -- la cobertura tiene que decirlo."""
    chain = _Chain(sin_cadena=["CCC"])
    r, _ = _correr(chain, esperas=(90, 180))
    assert r["respondidos"] == 3
    assert r["scanned"] == 4
    pedidos = [t for t, _ in chain.llamadas]
    assert pedidos.count("CCC") == 3, "una vez en la primera pasada y una por ronda"


def test_con_el_presupuesto_agotado_se_publica_en_vez_de_seguir_esperando():
    """Un día de opciones no se puede reintentar mañana: las cadenas solo
    existen mientras están vivas. Más vale volver con lo que haya que agotar
    el temporizador del disparador sin guardar nada."""
    chain = _Chain(muro_permanente=True)
    r, reloj = _correr(chain, esperas=(90, 180, 300), presupuesto=100)
    assert r["ok"] is True, "debe devolver resultado igualmente"
    assert sum(reloj.dormido) < 300, \
        f"ha esperado {sum(reloj.dormido)}s con un presupuesto de 100s"


def test_sin_fallos_no_se_espera_nada():
    """El camino normal no paga ni un segundo por este arreglo."""
    chain = _Chain()
    r, reloj = _correr(chain)
    assert r["respondidos"] == 4
    assert len(chain.llamadas) == 4
    assert reloj.dormido == [], f"ha esperado sin motivo: {reloj.dormido}"
