"""
La barra superior de Market repetía el fallo que ya había costado tres días
en Cartera: dar por sentado que `iloc[-2]` es la sesión anterior.

`_get_quick_prices()` (routers/ws.py) pedía `period="2d"` y calculaba la
variación entre las dos únicas filas que eso devuelve. Con dos filas la
suposición no se puede ni comprobar: no hay margen para VER que falta una
sesión por medio. Cuando yfinance se salta una barra para un símbolo -- pasa
por símbolo, y más desde el VPS, porque Yahoo limita las IP de centro de datos
-- `iloc[-2]` es el cierre de hace DOS sesiones y el porcentaje que se pinta
es el de dos días con la etiqueta del actual.

Es literalmente el mismo patrón de `cartera_service._fetch_price_single`,
arreglado allí el 11, 12 y 13/08/2026 (ver test_cartera_sesion.py y
test_cartera_tick_no_resucita.py). Allí se resolvió mirando la FECHA de las
barras en vez de su posición; aquí se aplica el mismo criterio con el mismo
helper compartido, `shared/market_calendar.py`.

QUÉ SE MIDIÓ ANTES DE TOCAR NADA (13/08/2026, 10:36-10:52 Nueva York): de los
14 símbolos de PRICE_TICKERS, 0 tenían hueco en ese momento, y en un mes de
historial (24 sesiones × 14 símbolos) no faltaba ninguna barra. El fallo NO se
estaba produciendo al medirlo desde una IP residencial. Estos tests no
documentan un síntoma observado, entonces, sino una defensa que no existía: el
código anterior era incapaz de detectar la condición aunque se diera.

POR QUÉ HAY UN TEST QUE MIRA EL `period=`: es la única parte del arreglo que
no se puede comprobar por su efecto. Los tests inyectan las barras a mano, así
que con un `period="2d"` de vuelta seguirían todos en verde mientras en
producción el hueco vuelve a ser invisible. Se detectó saboteando justo eso.

Uso:
    cd backend
    python -m pytest tests/test_market_barra_superior_sesion.py -v
"""
import sys, os
import json
from datetime import date
from unittest.mock import patch

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

import routers.ws as W            # noqa: E402
import market_calendar as MC      # noqa: E402


# Agosto de 2026, para tener los días de la semana claros:
#   vie 07 · sáb 08 · dom 09 · lun 10 · mar 11 · mié 12 · jue 13
VIE, SAB, DOM = "2026-08-07", "2026-08-08", "2026-08-09"
LUN, MAR, MIE, JUE = "2026-08-10", "2026-08-11", "2026-08-12", "2026-08-13"


def _precios(fechas, cierres, ticker="AAPL", sesion_esperada=date(2026, 8, 12)):
    """Ejecuta _get_quick_prices() con unas barras diarias controladas.

    Se fija también cuál es la última sesión esperada, para que el resultado no
    dependa del día en que se ejecute el test -- un test que caduca es peor que
    no tenerlo (misma lección que test_cartera_sesion.py)."""
    idx = pd.to_datetime(fechas)
    df  = pd.DataFrame({"Close": cierres}, index=idx)

    class _Tk:
        def history(self, **kw):
            return df

    with patch.dict(W.PRICE_TICKERS, {ticker: ticker}, clear=True), \
         patch.object(W.yf, "Ticker", return_value=_Tk()), \
         patch.object(MC, "ultima_sesion_esperada", return_value=sesion_esperada):
        filas = W._get_quick_prices()
    return filas[0] if filas else None


# ── El fallo en sí ──────────────────────────────────────────────────────────

def test_con_una_sesion_de_hueco_no_se_inventa_el_porcentaje_del_dia():
    """El caso que el código anterior no podía ni ver: hay barra del miércoles
    y del lunes, falta la del martes. `iloc[-2]` es el cierre de hace DOS
    sesiones, así que el porcentaje son dos días presentados como uno.

    Con estos números el cálculo viejo daba +20,00%; el movimiento real del
    miércoles (que no se puede conocer sin la barra del martes) no es ese."""
    r = _precios([LUN, MIE], [100.0, 120.0])
    assert r["chg"] is None, f"se inventó un {r['chg']}% con una sesión de hueco"
    assert r["sin_datos_hoy"] is True
    assert r["ultimo_cierre"] == LUN, "se dice de cuándo es el cierre que hay"


def test_el_precio_si_se_publica_aunque_no_haya_porcentaje():
    """No se tira la fila entera: el precio es un dato real y es el que la
    gente mira. Lo que se calla es la variación, que es lo que no se sabe."""
    r = _precios([LUN, MIE], [100.0, 120.0])
    assert r["price"] == 120.0
    assert r["ticker"] == "AAPL"


def test_con_varias_sesiones_de_hueco_tampoco():
    r = _precios([VIE, MIE], [100.0, 120.0])
    assert r["chg"] is None
    assert r["ultimo_cierre"] == VIE


# ── Y el camino bueno sigue funcionando ─────────────────────────────────────
#
# Un guardia que salta siempre es tan inútil como no tenerlo: dejaría la barra
# superior entera en "—" para siempre y nadie volvería a ver un porcentaje.

def test_con_las_dos_sesiones_consecutivas_el_porcentaje_sale_normal():
    r = _precios([MAR, MIE], [100.0, 120.0])
    assert r["chg"] == pytest.approx(20.0, abs=0.01)
    assert r["sin_datos_hoy"] is False
    assert r["chg_fecha"] == MIE


def test_el_fin_de_semana_no_es_un_hueco():
    """Viernes -> lunes son sesiones CONSECUTIVAS. Si el sábado y el domingo
    contaran como sesiones perdidas, el guardia saltaría todos los lunes."""
    r = _precios([VIE, LUN], [100.0, 110.0], sesion_esperada=date(2026, 8, 10))
    assert r["chg"] == pytest.approx(10.0, abs=0.01)
    assert r["sin_datos_hoy"] is False


def test_solo_se_miran_las_dos_ultimas_barras():
    """La ventana es ancha para poder comprobar fechas, no para cambiar el
    cálculo: un hueco viejo dentro de la ventana no afecta a la variación del
    día, que se mide entre las dos últimas."""
    r = _precios([VIE, MAR, MIE], [50.0, 100.0, 120.0])
    assert r["chg"] == pytest.approx(20.0, abs=0.01)


# ── Cripto: cotiza los siete días ───────────────────────────────────────────
#
# Las dos ramas del calendario, por separado. Aplicar el calendario bursátil a
# BTC descartaría un dato bueno cada lunes; aplicar el de días naturales a una
# acción daría por bueno un hueco de fin de semana. Se detectó saboteando
# `cotiza_todos_los_dias()` para que devolviera siempre lo mismo.

def test_en_cripto_el_domingo_es_una_sesion_normal():
    """Domingo -> lunes es consecutivo para BTC. Con el calendario bursátil,
    «la anterior al lunes» sería el viernes y esto se descartaría."""
    r = _precios([DOM, LUN], [100.0, 110.0], ticker="BTC-USD",
                 sesion_esperada=date(2026, 8, 10))
    assert r["chg"] == pytest.approx(10.0, abs=0.01)
    assert r["sin_datos_hoy"] is False


def test_en_cripto_un_dia_natural_perdido_si_es_un_hueco():
    """La otra mitad: a BTC no se le perdona el hueco, solo se le mide con el
    calendario que le toca. Falta el domingo."""
    r = _precios([SAB, LUN], [100.0, 110.0], ticker="BTC-USD",
                 sesion_esperada=date(2026, 8, 10))
    assert r["chg"] is None
    assert r["ultimo_cierre"] == SAB


def test_a_una_accion_no_se_le_aplica_el_calendario_de_cripto():
    """Sábado -> lunes en una ACCIÓN no puede darse por bueno: el sábado no es
    una sesión, así que esa barra es una anomalía del proveedor, no la sesión
    anterior."""
    r = _precios([SAB, LUN], [100.0, 110.0], sesion_esperada=date(2026, 8, 10))
    assert r["chg"] is None


# ── La ventana de descarga ──────────────────────────────────────────────────

def test_la_ventana_es_lo_bastante_ancha_para_ver_el_hueco():
    """EL SABOTAJE QUE NO SE VE DE OTRA FORMA.

    Con `period="2d"` yfinance devuelve como mucho dos filas, y entonces las
    dos últimas barras son las dos únicas que hay: la comprobación de fechas
    se vuelve un adorno que nunca puede fallar, porque no existe la tercera
    fila que revelaría el hueco. Todos los demás tests de este fichero
    seguirían en verde -- inyectan las barras a mano -- mientras en producción
    el fallo vuelve intacto.

    Por eso se afirma sobre la petición y no sobre el resultado."""
    visto = {}

    class _Tk:
        def history(self, **kw):
            visto.update(kw)
            return pd.DataFrame({"Close": [100.0, 110.0]},
                                index=pd.to_datetime([MAR, MIE]))

    with patch.dict(W.PRICE_TICKERS, {"AAPL": "AAPL"}, clear=True), \
         patch.object(W.yf, "Ticker", return_value=_Tk()):
        W._get_quick_prices()

    assert visto.get("interval") == "1d"
    dias = int(str(visto.get("period", "")).rstrip("d") or 0)
    assert dias >= 5, (
        f'period="{visto.get("period")}" no deja margen para detectar un hueco: '
        "hacen falta al menos 5 días para que existan más de dos barras"
    )


# ── Datos rancios: el número es correcto, pero no es de hoy ─────────────────

def test_si_la_ultima_sesion_es_vieja_se_marca_el_desfase():
    """Las dos barras son consecutivas, así que el porcentaje es correcto...
    para el lunes. Con el proveedor degradado sale internamente coherente y de
    hace días: así estuvo Cartera cuatro días congelada en el viernes 7 sin
    que nada lo dijera. Aquí el número se publica, pero marcado."""
    r = _precios([VIE, LUN], [100.0, 110.0], sesion_esperada=date(2026, 8, 13))
    assert r["chg"] == pytest.approx(10.0, abs=0.01)
    assert r["sesion_desfasada"] is True
    assert r["chg_fecha"] == LUN, "la pantalla necesita saber de qué sesión habla"


def test_un_dia_de_retraso_no_marca_desfase():
    """Mismo margen que _estado_de_los_precios() en Cartera: un día puede ser
    un festivo, que el calendario no conoce. A partir de dos ya no es
    calendario."""
    r = _precios([LUN, MAR], [100.0, 110.0], sesion_esperada=date(2026, 8, 12))
    assert r["chg"] is not None
    assert "sesion_desfasada" not in r


def test_al_dia_no_se_marca_nada():
    r = _precios([MAR, MIE], [100.0, 110.0], sesion_esperada=date(2026, 8, 12))
    assert "sesion_desfasada" not in r


# ── Datos rotos: nada de esto puede tumbar el WebSocket ─────────────────────

def test_un_nan_en_la_ultima_fila_no_se_propaga():
    """Yahoo devuelve la fila de la sesión en curso con el cierre a NaN
    mientras no ha asentado (verificado en vivo con AAPL y NVDA el
    25/07/2026). Ese NaN no es serializable en JSON y rompería el mensaje
    entero del WebSocket, no solo esta fila."""
    r = _precios([MAR, MIE, JUE], [100.0, 110.0, float("nan")])
    assert r["price"] == 110.0, "el precio es el último cierre REAL"
    assert r["chg"] == pytest.approx(10.0, abs=0.01)


def test_con_una_sola_barra_la_fila_se_omite():
    """Sin cierre de referencia no hay variación posible, y no se fabrica."""
    assert _precios([MIE], [120.0]) is None


def test_un_cierre_anterior_a_cero_no_revienta():
    """Dividir por cero tumbaría _build_payload() entero y con él el broadcast
    a todos los clientes conectados."""
    assert _precios([MAR, MIE], [0.0, 120.0]) is None


@pytest.mark.parametrize("cierres,caso", [
    ([float("inf"), 120.0], "el cierre de referencia es infinito"),
    ([100.0, float("inf")], "el último cierre es infinito"),
])
def test_un_infinito_no_sale_en_el_mensaje(cierres, caso):
    """El `math.isfinite` del guardia, que el `except` de arriba NO cubre.

    Un cero lanza ZeroDivisionError y la fila se cae sola, así que quitar el
    guardia no cambiaba nada y ningún test lo notaba (detectado saboteándolo).
    Un infinito es distinto: no lanza NADA. `(120-inf)/inf*100` es NaN, se
    publica tan tranquilo, y entonces json.dumps() escupe `NaN`/`Infinity` --
    que no son JSON válido. El JSON.parse del navegador revienta y se queda
    sin mensaje la barra superior ENTERA, no solo este símbolo. Es el mismo
    accidente que ya dejó /api/v1/watchlist devolviendo un 500 en texto plano.

    Por eso se afirma sobre el mensaje serializado: es donde duele."""
    r = _precios([MAR, MIE], cierres)
    if r is not None:
        texto = json.dumps(r)
        assert "NaN" not in texto and "Infinity" not in texto, (
            f"{caso}: el mensaje deja de ser JSON válido -> {texto}")


def test_un_simbolo_roto_no_arrastra_a_los_demas():
    """Un fallo por símbolo no puede vaciar la barra superior entera."""
    class _TkRoto:
        def history(self, **kw):
            raise RuntimeError("Yahoo dijo que no")

    class _TkBueno:
        def history(self, **kw):
            return pd.DataFrame({"Close": [100.0, 110.0]},
                                index=pd.to_datetime([MAR, MIE]))

    def _ticker(sym):
        return _TkRoto() if sym == "ROTO" else _TkBueno()

    with patch.dict(W.PRICE_TICKERS, {"ROTO": "ROTO", "AAPL": "AAPL"}, clear=True), \
         patch.object(W.yf, "Ticker", side_effect=_ticker), \
         patch.object(MC, "ultima_sesion_esperada", return_value=date(2026, 8, 12)):
        filas = W._get_quick_prices()

    assert [f["ticker"] for f in filas] == ["AAPL"]


# ── El helper compartido, que es lo que evita que esto se vuelva a separar ──

def test_la_barra_superior_usa_el_mismo_calendario_que_cartera():
    """Si alguien vuelve a escribir aquí su propia versión de «cuál es la
    sesión anterior», el arreglo se separa del de Cartera y vuelve a pasar lo
    de siempre: se corrige en un sitio y no en el otro."""
    import services.cartera_service as C
    assert C._ultima_sesion_esperada is MC.ultima_sesion_esperada


@pytest.mark.parametrize("dia,anterior,motivo", [
    (date(2026, 8, 12), date(2026, 8, 11), "miércoles -> martes"),
    (date(2026, 8, 10), date(2026, 8, 7),  "lunes -> viernes, saltando el fin de semana"),
])
def test_sesion_anterior_a(dia, anterior, motivo):
    assert MC.sesion_anterior_a(dia) == anterior, motivo


def test_que_cotiza_todos_los_dias():
    assert MC.cotiza_todos_los_dias("BTC-USD") is True
    assert MC.cotiza_todos_los_dias("AAPL") is False
    assert MC.cotiza_todos_los_dias("CL=F") is False
