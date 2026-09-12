"""
Scanner #25: el escaneo nocturno publicaba los precios de ANTEAYER.

EL CASO. Del 05 al 12/09/2026, en 5 de 7 noches, la descarga en lote volvía sin
la barra de la sesión que acababa de cerrar. La noche del 11 al 12 quedó
instrumentada: de 2.426 valores, **27 traían la sesión del 11 y 2.397 se
quedaban en la del 10** — y en el mismo minuto `Ticker("A").history(period="5d")`
sí la traía, así que el dato existía y la descarga no lo veía. De ahí salían
Market con la amplitud de anteayer, el briefing narrando una sesión con las
tripas de otra (Newsfeed #61), y RS/RW, CANSLIM y Temáticos con un día de
retraso.

EL ARREGLO es una segunda pasada, solo de la barra que falta y solo para los
que no la traen, con las dos diferencias que cubren las dos explicaciones
posibles: rango corto (si la petición larga no la sirve, la corta sí) y
`auto_adjust=False` (si Yahoo manda el `adjclose` de la última barra a null,
`auto_adjust=True` lo convierte en NaN y el `dropna()` borra la fila; sin
ajustar no hay nada que anular, y para la ÚLTIMA barra el cierre ajustado es
el cierre a secas, porque el ajuste solo va hacia atrás).

VERIFICADO CONTRA DATOS REALES antes de escribir estos tests: se descargaron 19
tickers de verdad, se les quitó la última barra —que es exactamente lo que hace
la noche mala— y la segunda pasada recuperó las 19 con el cierre, el volumen y
el OHLC idénticos a los de la descarga ajustada (diferencia < 0,01%).

Uso:
    cd backend
    python -m pytest tests/test_scanner_ultima_sesion.py -v
"""
import ast
import os
import sys
from datetime import date, datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(RAIZ, 'shared'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))

import yf_batch as Y  # noqa: E402
from festivos_mercado import ultima_sesion_cerrada  # noqa: E402

ET = ZoneInfo("America/New_York")
JUEVES, VIERNES = date(2026, 9, 10), date(2026, 9, 11)


def _serie(fechas, valores, tz=ET):
    idx = pd.DatetimeIndex([pd.Timestamp(f, tz=tz) for f in fechas])
    return pd.Series(valores, index=idx)


@pytest.fixture
def datos():
    """Tres tickers sin la barra del viernes y uno con ella, como la noche mala."""
    dias = [date(2026, 9, 8), date(2026, 9, 9), JUEVES]
    close_d = {t: _serie(dias, [10.0, 11.0, 12.0]) for t in ("A", "AAPL", "AAP")}
    close_d["ADEA"] = _serie(dias + [VIERNES], [10.0, 11.0, 12.0, 13.0])
    vol_d = {t: _serie(dias, [100.0, 110.0, 120.0]) for t in ("A", "AAPL", "AAP")}
    vol_d["ADEA"] = _serie(dias + [VIERNES], [100.0, 110.0, 120.0, 130.0])
    hl_d = {t: pd.DataFrame({"Open": [1.0, 2.0, 3.0], "High": [2.0, 3.0, 4.0],
                             "Low": [0.5, 1.5, 2.5]},
                            index=_serie(dias, [0, 0, 0]).index)
            for t in ("A", "AAPL", "AAP")}
    return close_d, vol_d, hl_d


def _yahoo(monkeypatch, filas, columnas=("Open", "High", "Low", "Close", "Adj Close", "Volume")):
    """Simula `yf.download` multi-ticker: `filas` = {ticker: {campo: valor}} para
    la barra del viernes. Un ticker ausente = Yahoo tampoco la trae ahora."""
    llamadas = []

    def falso(tickers, **kw):
        llamadas.append({"tickers": list(tickers), **kw})
        idx = pd.DatetimeIndex([pd.Timestamp(JUEVES, tz=ET), pd.Timestamp(VIERNES, tz=ET)])
        cols, datos = [], {}
        for t in tickers:
            for c in columnas:
                cols.append((c, t))
                previo = {"Volume": 120.0}.get(c, 12.0)
                datos[(c, t)] = [previo, filas.get(t, {}).get(c, float("nan"))]
        df = pd.DataFrame(datos, index=idx)
        df.columns = pd.MultiIndex.from_tuples(cols)
        return df

    monkeypatch.setattr(Y.yf, "download", falso)
    return llamadas


# ── Lo que hace la segunda pasada ────────────────────────────────────────────

def test_rellena_la_barra_que_faltaba(monkeypatch, datos):
    """EL test del caso: los tres que se habían quedado en el jueves acaban con
    la barra del viernes, y con sus valores."""
    close_d, vol_d, hl_d = datos
    _yahoo(monkeypatch, {t: {"Close": 13.5, "Volume": 999.0, "Open": 13.0,
                             "High": 14.0, "Low": 12.5}
                         for t in ("A", "AAPL", "AAP")})
    faltaban, recuperados = Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, batch_sleep=0)
    assert (faltaban, recuperados) == (3, 3)
    for t in ("A", "AAPL", "AAP"):
        assert close_d[t].index[-1].date() == VIERNES
        assert close_d[t].iloc[-1] == 13.5
        assert vol_d[t].iloc[-1] == 999.0
        assert list(hl_d[t].iloc[-1][["Open", "High", "Low"]]) == [13.0, 14.0, 12.5]
        assert close_d[t].index.is_monotonic_increasing
        assert not close_d[t].index.duplicated().any()


def test_al_que_ya_la_traia_no_se_le_toca(monkeypatch, datos):
    """Los 27 buenos de aquella noche no pueden acabar con la barra duplicada."""
    close_d, vol_d, hl_d = datos
    antes = close_d["ADEA"].copy()
    llamadas = _yahoo(monkeypatch, {t: {"Close": 13.5} for t in ("A", "AAPL", "AAP")})
    Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, batch_sleep=0)
    assert close_d["ADEA"].equals(antes)
    assert "ADEA" not in llamadas[0]["tickers"], "se ha vuelto a pedir uno que ya estaba"


def test_si_el_reintento_tampoco_la_trae_NO_se_inventa_nada(monkeypatch, datos):
    """Un valor suspendido o retirado no cotizó ese día: la barra no existe y
    rellenarla con el cierre anterior sería inventar una sesión plana."""
    close_d, vol_d, hl_d = datos
    _yahoo(monkeypatch, {})          # Yahoo no trae ningún cierre del viernes
    monkeypatch.setattr(Y, "_diagnosticar_uno", lambda t, f: f"{t}: sin datos")
    faltaban, recuperados = Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, batch_sleep=0)
    assert (faltaban, recuperados) == (3, 0)
    for t in ("A", "AAPL", "AAP"):
        assert close_d[t].index[-1].date() == JUEVES and len(close_d[t]) == 3


def test_la_segunda_pasada_pide_rango_corto_y_SIN_ajustar(monkeypatch, datos):
    """Las dos diferencias son el arreglo entero: si se piden los mismos 2 años
    ajustados, se vuelve a recibir exactamente lo mismo que falló."""
    close_d, vol_d, hl_d = datos
    llamadas = _yahoo(monkeypatch, {"A": {"Close": 13.5}})
    Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, batch_sleep=0)
    assert llamadas and llamadas[0]["period"] == "5d"
    assert llamadas[0]["auto_adjust"] is False


def test_sin_nadie_a_quien_reparar_no_se_toca_la_red(monkeypatch, datos):
    """Las noches buenas no pueden costar una pasada extra."""
    close_d, vol_d, hl_d = datos
    llamadas = _yahoo(monkeypatch, {})
    faltaban, recuperados = Y.reparar_ultima_sesion(close_d, vol_d, hl_d, JUEVES, batch_sleep=0)
    assert (faltaban, recuperados) == (0, 0) and llamadas == []


def test_un_cierre_vacio_no_cuenta_como_barra(monkeypatch, datos):
    """Que es justo la forma del fallo: la fila existe pero el cierre viene a
    NaN. Colarla dejaría un agujero en mitad de la serie."""
    close_d, vol_d, hl_d = datos
    _yahoo(monkeypatch, {"A": {"Close": float("nan")}, "AAPL": {"Close": 13.5}})
    monkeypatch.setattr(Y, "_diagnosticar_uno", lambda t, f: "")
    _, recuperados = Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, batch_sleep=0)
    assert recuperados == 1 and close_d["A"].index[-1].date() == JUEVES


def test_el_cache_se_reescribe_con_la_barra_nueva(monkeypatch, datos, tmp_path):
    """Los otros tres scans de la noche leen ese caché: si no se reescribe, el
    arreglo dura solo para el primero."""
    close_d, vol_d, hl_d = datos
    _yahoo(monkeypatch, {"A": {"Close": 13.5, "Volume": 999.0}})
    escrituras = []
    monkeypatch.setattr(Y.price_cache, "escribir",
                        lambda d, t, c, v=None, h=None: escrituras.append((t, len(c))))
    Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, cache_dir=str(tmp_path), batch_sleep=0)
    assert escrituras == [("A", 4)]


def test_sin_cache_no_se_escribe_nada(monkeypatch, datos):
    close_d, vol_d, hl_d = datos
    _yahoo(monkeypatch, {"A": {"Close": 13.5}})
    monkeypatch.setattr(Y.price_cache, "escribir",
                        lambda *a, **k: pytest.fail("ha escrito en el caché sin directorio"))
    Y.reparar_ultima_sesion(close_d, vol_d, hl_d, VIERNES, batch_sleep=0)


# ── Qué sesión debería estar ────────────────────────────────────────────────
#
# Mirar el máximo de lo DESCARGADO no vale: la noche que falle para todos, ese
# máximo es la sesión anterior y el hueco no se ve.

@pytest.mark.parametrize("ahora,esperada", [
    (datetime(2026, 9, 11, 20, 15, tzinfo=ET), date(2026, 9, 11)),  # el scan, tras el cierre
    (datetime(2026, 9, 11, 15, 59, tzinfo=ET), date(2026, 9, 10)),  # aún en sesión
    (datetime(2026, 9, 12, 10, 0, tzinfo=ET),  date(2026, 9, 11)),  # sábado
    (datetime(2026, 9, 13, 10, 0, tzinfo=ET),  date(2026, 9, 11)),  # domingo
    (datetime(2026, 9, 8, 3, 0, tzinfo=ET),    date(2026, 9, 4)),   # martes tras Labor Day
])
def test_la_ultima_sesion_cerrada_sale_del_calendario(ahora, esperada):
    assert ultima_sesion_cerrada(ahora) == esperada


# ── Que alguien la llame ────────────────────────────────────────────────────

def _un_ticker_descargado(monkeypatch):
    """Una descarga que SÍ trae datos: con el diccionario vacío no se distingue
    «no repara porque no se lo piden» de «no repara porque no hay nada»."""
    idx = pd.DatetimeIndex([pd.Timestamp(JUEVES, tz=ET)])
    df = pd.DataFrame({("Close", "A"): [12.0], ("Volume", "A"): [1.0]}, index=idx)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    monkeypatch.setattr(Y.yf, "download", lambda *a, **k: df)


def test_download_batch_solo_repara_si_se_le_pide(monkeypatch):
    """Las llamadas del backend corren dentro de una petición web: no pueden
    llevarse una pasada extra de sorpresa."""
    _un_ticker_descargado(monkeypatch)
    monkeypatch.setattr(Y, "reparar_ultima_sesion",
                        lambda *a, **k: pytest.fail("ha reparado sin que se lo pidan"))
    close_d, _ = Y.download_batch(["A"], period="1y", min_history=1, batch_sleep=0)
    assert close_d, "la prueba no vale: la descarga simulada no ha traído nada"


def test_download_batch_repara_con_la_sesion_del_calendario(monkeypatch):
    vistos = {}

    def falso_reparar(close_d, vol_d, hl_d, esperada, *a, **k):
        vistos["esperada"] = esperada
        return 0, 0
    monkeypatch.setattr(Y, "reparar_ultima_sesion", falso_reparar)
    _un_ticker_descargado(monkeypatch)
    Y.download_batch(["A"], period="1y", min_history=1, batch_sleep=0, reparar_ultima=True,
                     ahora_et=datetime(2026, 9, 11, 20, 15, tzinfo=ET))
    assert vistos["esperada"] == VIERNES


@pytest.mark.parametrize("script", ["scanner_universe", "rsrw_scan", "canslim_scan", "thematic_scan"])
def test_los_cuatro_scans_nocturnos_la_piden(script):
    """Los cuatro comparten el mismo caché de precios y los cuatro iban una
    sesión por detrás. Que la función exista no sirve de nada si no la llaman."""
    ruta = os.path.join(RAIZ, "scripts", f"{script}.py")
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call)
                and getattr(n.func, "id", None) == "download_batch"]
    assert llamadas, f"{script} ya no descarga por lotes"
    for c in llamadas:
        kw = {k.arg: k.value for k in c.keywords}
        assert "reparar_ultima" in kw and getattr(kw["reparar_ultima"], "value", False) is True, \
            f"{script} descarga sin pedir la barra de la última sesión (línea {c.lineno})"
