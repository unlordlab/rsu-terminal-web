"""
El módulo VIX NIVELES salía en blanco porque `period="6mo"` — y solo ese — venía vacío.

EL CASO, 08/09/2026, reportado por el usuario: el panel mostraba «✗ Sin
histórico de VIX» y nada más. Reproducido en el acto contra Yahoo:

    period=5d    5 filas        period=6mo   0 filas   <-- VACÍO
    period=1mo   22 filas       period=1y    254 filas
    period=3mo   65 filas       period=2y    503 filas

`6mo` —y solo `6mo`— devolvía vacío mientras sus vecinos por los dos lados
funcionaban. No era que el VIX no estuviera: el resto de la terminal lo pintaba
sin problema (el panel de amplitud lo daba a 15,74 esa misma mañana), porque
los demás sitios piden `5d` o `3mo`.

EL ARREGLO, en dos capas:

  1. La ventana se pide por **fechas calculadas aquí**, no por un alias. Así no
     depende de cómo Yahoo interprete una etiqueta, que es exactamente lo que
     falló. Si aun así viniera vacío, se cae a `period="1y"` recortado — dos
     formas distintas de pedir lo mismo.
  2. **Sin histórico ya no se cae el módulo entero.** El gauge de zonas, que es
     lo que se mira, solo necesita el valor de hoy. Antes un histórico vacío
     devolvía `ok:False` y dejaba el panel en blanco con un aspa roja; ahora se
     pierde la línea de 6 meses y se conserva el resto.

Uso:
    cd backend
    python -m pytest tests/test_market_vix_niveles.py -v
"""
import os
import sys
from datetime import date, timedelta
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402


def _barras(n, valor=15.0):
    idx = pd.date_range(end=date.today(), periods=n, freq="D")
    return pd.DataFrame({"Close": [valor + i * 0.01 for i in range(n)]}, index=idx)


class _TickerFalso:
    """Reproduce la rareza: responde a unas ventanas y a otras no."""

    def __init__(self, por_periodo=None, por_fechas=None, explota_fechas=False):
        self.por_periodo = por_periodo or {}
        self.por_fechas = por_fechas
        self.explota_fechas = explota_fechas
        self.pedidos = []

    def history(self, period=None, start=None, end=None, **kw):
        if period is not None:
            self.pedidos.append(("period", period))
            return self.por_periodo.get(period, pd.DataFrame())
        self.pedidos.append(("fechas", (start, end)))
        if self.explota_fechas:
            raise RuntimeError("Yahoo ha dicho que no")
        return self.por_fechas if self.por_fechas is not None else pd.DataFrame()


@pytest.fixture(autouse=True)
def _sin_cache():
    from services.cache import cache
    cache.set("market:vix_levels", None, 0)
    yield
    cache.set("market:vix_levels", None, 0)


# ── La ventana se pide por fechas, no por alias ──────────────────────────────

def test_NO_se_pide_la_ventana_con_el_alias_que_fallaba():
    """EL test. `period="6mo"` es lo que dejó el panel en blanco."""
    falso = _TickerFalso(por_fechas=_barras(130))
    with patch.object(M.yf, "Ticker", return_value=falso):
        M._historico_vix()
    assert ("period", "6mo") not in falso.pedidos, (
        "se sigue pidiendo period=6mo, que es justo el alias que Yahoo "
        "devolvía vacío mientras 3mo y 1y funcionaban")
    assert falso.pedidos[0][0] == "fechas", "la primera petición debe ir por fechas"


def test_la_ventana_pedida_cubre_de_verdad_seis_meses():
    """Si se quedara corta, el gráfico diría «6 meses» enseñando dos."""
    falso = _TickerFalso(por_fechas=_barras(130))
    with patch.object(M.yf, "Ticker", return_value=falso):
        M._historico_vix()
    _, (ini, fin) = falso.pedidos[0]
    assert (fin - ini).days >= 180, f"la ventana pedida son {(fin - ini).days} días"


def test_si_las_fechas_vienen_vacias_se_cae_a_un_ANO_recortado():
    """Dos formas distintas de pedir lo mismo. La lección del 08/09 es que una
    puede fallar sola mientras la otra funciona."""
    falso = _TickerFalso(por_periodo={"1y": _barras(254)}, por_fechas=pd.DataFrame())
    with patch.object(M.yf, "Ticker", return_value=falso):
        h = M._historico_vix()
    assert ("period", "1y") in falso.pedidos
    assert len(h) == 130, "debe recortarse a ~6 meses, no devolver el año entero"


def test_una_excepcion_pidiendo_fechas_tampoco_lo_tumba():
    falso = _TickerFalso(por_periodo={"1y": _barras(254)}, explota_fechas=True)
    with patch.object(M.yf, "Ticker", return_value=falso):
        assert len(M._historico_vix()) == 130


def test_si_falla_TODO_devuelve_vacio_sin_reventar():
    """Quien llama decide qué hacer; esta función no puede levantar."""
    falso = _TickerFalso(explota_fechas=True)
    with patch.object(M.yf, "Ticker", return_value=falso):
        h = M._historico_vix()
    assert hasattr(h, "empty") and h.empty


# ── Sin histórico, el módulo NO se cae ───────────────────────────────────────

def test_sin_historico_el_gauge_SIGUE_funcionando():
    """Lo que reportó el usuario: el panel entero en blanco con un aspa roja.
    El gauge de zonas solo necesita el valor de hoy."""
    falso = _TickerFalso(por_periodo={"5d": _barras(5, 22.0)}, por_fechas=pd.DataFrame())
    with patch.object(M, "_historico_vix", return_value=pd.DataFrame()), \
         patch.object(M.yf, "Ticker", return_value=falso):
        r = M.get_vix_levels()
    assert r["ok"] is True, "un histórico vacío sigue tumbando el módulo entero"
    assert r["zone"] == "PRECAUCIÓN", r
    assert r["current"] > 0


def test_pero_si_no_hay_NADA_se_dice_que_no_hay_nada():
    """Inventar un VIX sería mucho peor que un panel vacío."""
    falso = _TickerFalso()
    with patch.object(M, "_historico_vix", return_value=pd.DataFrame()), \
         patch.object(M.yf, "Ticker", return_value=falso):
        r = M.get_vix_levels()
    assert r["ok"] is False and "VIX" in r["error"]


# ── Las zonas, que es lo que se lee ──────────────────────────────────────────

def test_cada_zona_en_su_sitio():
    """Los cortes son <12 · 12-20 · 20-25 · 25-35 · 35+."""
    esperado = [(9.0, "COMPLACENCIA"), (11.99, "COMPLACENCIA"), (12.0, "NORMAL"),
                (19.9, "NORMAL"), (20.0, "PRECAUCIÓN"), (24.9, "PRECAUCIÓN"),
                (25.0, "MIEDO"), (34.9, "MIEDO"), (35.0, "PÁNICO"), (80.0, "PÁNICO")]
    for valor, zona in esperado:
        # Barras PLANAS: `_barras` sube 0,01 por fila, y con eso el valor que
        # llega al corte no es el que dice el test. Mi primera versión lo tapó
        # con un `or r["current"] != valor` que hacía pasar el test SIEMPRE --
        # una comprobación de zonas que no comprobaba ninguna zona.
        plano = pd.DataFrame({"Close": [valor, valor]},
                             index=pd.date_range(end=date.today(), periods=2, freq="D"))
        # La caché se limpia en CADA vuelta: `get_vix_levels` guarda su
        # resultado, así que sin esto la segunda iteración devolvía la primera y
        # el bucle comprobaba diez veces la misma zona. Salió al quitar el `or`
        # que hacía pasar el test siempre -- el fallo estaba tapado por partida
        # doble.
        from services.cache import cache
        cache.set("market:vix_levels", None, 0)
        with patch.object(M, "_historico_vix", return_value=plano):
            r = M.get_vix_levels()
        assert r["ok"] and r["zone"] == zona, (valor, zona, r.get("zone"))


def test_la_variacion_se_calcula_contra_la_barra_ANTERIOR():
    with patch.object(M, "_historico_vix", return_value=_barras(3, 15.0)):
        r = M.get_vix_levels()
    assert r["current"] == 15.02 and r["prev"] == 15.01
    assert r["change"] == 0.01


def test_con_una_sola_barra_no_se_inventa_una_variacion():
    """`prev` a un valor distinto daría un porcentaje falso el primer día."""
    with patch.object(M, "_historico_vix", return_value=_barras(1, 15.0)):
        r = M.get_vix_levels()
    assert r["change"] == 0 and r["pct"] == 0


def test_el_historico_que_se_publica_esta_acotado():
    """El gráfico son ~6 meses de diarios; mandar dos años sería peso muerto en
    cada carga de la página."""
    with patch.object(M, "_historico_vix", return_value=_barras(400)):
        r = M.get_vix_levels()
    assert len(r["history"]) <= 130
    assert set(r["history"][0]) == {"date", "value"}
