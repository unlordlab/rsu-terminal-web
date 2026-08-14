"""
Presión vendedora diaria (fichero de ventas en corto de FINRA).

DE DÓNDE SALE: el módulo de estrangulamiento se entregó apoyado en el dato de
posiciones cortas, que se publica dos veces al mes y con retraso -- el
14/08/2026 lo más reciente era del 31/07, catorce días antes. FINRA publica
ADEMÁS, cada día hacia las 18:00 de Nueva York, qué parte del volumen de cada
valor se marcó como venta en corto. Un fichero, ~12.000 valores, mismo día.

EL ERROR QUE ESTE FICHERO EXISTE PARA IMPEDIR: enseñar ese porcentaje en crudo
como si fuera interés corto. Medido sobre el fichero real del 13/08/2026:

    IWM   58,9% del volumen marcado como venta en corto
    GME   59,6%
    ONDS  59,6%

Un fondo del Russell 2000 no está «59% vendido en corto» -- son creadores de
mercado cubriendo operaciones que cierran el mismo día. Contra la media del
propio valor, esos tres se separan de verdad: IWM ×0,89 y GME ×0,93 (por
DEBAJO de lo normal en ellos), ONDS ×1,28 (por encima). El porcentaje crudo los
hacía indistinguibles.

LO QUE FIJA ESTE FICHERO:
1. La media excluye el día evaluado (si hoy entra en su propio promedio, acerca
   el cociente a 1 y disimula justo los días anómalos que se buscan).
2. La señal mira el salto, no el porcentaje -- un 59% habitual no la dispara.
3. Sin serie suficiente no hay dato, y eso BAJA el denominador de señales.
4. Las claves diarias de caché se retiran: se crea una nueva cada día laborable
   y la caché del proyecto no purga nada por su cuenta.

Uso:
    cd backend
    python -m pytest tests/test_presion_corto_finra.py -v
"""
import sys, os
from datetime import date, timedelta
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402
from services.cache import cache      # noqa: E402


CABECERA = "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market"


def _fichero(filas):
    """filas: [(ticker, volumen_corto, volumen_total)] -- mismo formato de
    tubería y mismos decimales que el fichero real de FINRA."""
    cuerpo = "\n".join(f"20260813|{t}|{c}|0|{tot}|B,Q,N" for t, c, tot in filas)
    r = MagicMock(); r.status_code = 200
    r.text = f"{CABECERA}\n{cuerpo}\n"
    return r


@pytest.fixture(autouse=True)
def _sin_cache():
    """Las claves diarias llevan fecha, así que hay que barrerlas por rango."""
    def limpiar():
        cache.delete("market:shvol:agregado")
        for i in range(0, 70):
            cache.delete(f"market:shvol:{date.today() - timedelta(days=i):%Y%m%d}")
    limpiar()
    yield
    limpiar()


# ── 1. Lectura del fichero ──────────────────────────────────────────────────

def test_lee_los_cocientes_del_fichero():
    with patch.object(M.requests, "get", return_value=_fichero([
            ("AAA", "300000.5", "1000000.25"), ("BBB", "900000", "1000000")])):
        d = M._shvol_dia(date(2026, 8, 13))
    assert d["AAA"] == 0.3
    assert d["BBB"] == 0.9


def test_descarta_lo_ilíquido_donde_el_cociente_es_ruido():
    """Con 900 acciones negociadas, un cociente del 100% no dice nada."""
    with patch.object(M.requests, "get", return_value=_fichero([
            ("LIQ", "500000", "1000000"), ("ILQ", "900", "1000")])):
        d = M._shvol_dia(date(2026, 8, 13))
    assert "LIQ" in d and "ILQ" not in d


def test_un_dia_sin_fichero_no_es_un_fallo():
    """Fin de semana o festivo: no hay fichero y nunca lo habrá. Devuelve None
    y se cachea, para no repreguntar en cada refresco."""
    r = MagicMock(); r.status_code = 404
    with patch.object(M.requests, "get", return_value=r) as g:
        assert M._shvol_dia(date(2026, 8, 9)) is None
        M._shvol_dia(date(2026, 8, 9))
    assert g.call_count == 1, "la segunda llamada tenía que salir de la caché"


# ── 2. El cálculo del salto ─────────────────────────────────────────────────

def _montar_mercado(hoy_ratio, historico_ratios, ticker="ZZZ"):
    """Devuelve un `requests.get` falso: la sesión más reciente con
    `hoy_ratio` y las anteriores con `historico_ratios`."""
    hoy = date.today()
    por_fecha = {}
    por_fecha[hoy] = _fichero([(ticker, str(hoy_ratio * 1_000_000), "1000000")])
    for i, r in enumerate(historico_ratios, start=1):
        por_fecha[hoy - timedelta(days=i)] = _fichero(
            [(ticker, str(r * 1_000_000), "1000000")])
    vacio = MagicMock(); vacio.status_code = 404

    def falso(url, **kw):
        fecha = url.split("CNMSshvol")[1][:8]
        for f, resp in por_fecha.items():
            if f"{f:%Y%m%d}" == fecha:
                return resp
        return vacio
    return falso


def test_la_media_excluye_el_dia_que_se_evalua():
    """Hoy 0,60 con diez sesiones previas a 0,30: el salto es 2,00. Si hoy
    entrara en su propio promedio, la media subiría a ~0,33 y el salto bajaría
    a 1,82 -- justo el día anómalo quedaría disimulado."""
    with patch.object(M.requests, "get", side_effect=_montar_mercado(0.60, [0.30] * 10)):
        mapa = M._presion_corto_map()
    p = mapa["ZZZ"]
    assert p["media"] == 30.0
    assert p["salto"] == 2.0
    assert p["sesiones"] == 10


def test_un_porcentaje_alto_pero_habitual_no_dispara_la_senal():
    """El caso IWM: 59% del volumen en corto, y aun así por debajo de lo normal
    en ese valor. Es la razón de ser de todo el fichero.

    Se comprueba hasta la SEÑAL, no solo hasta el cálculo: mirando el
    porcentaje crudo (>= 50%) este valor dispararía, y comprobar únicamente
    que `salto < SHVOL_SALTO` no detectaría ese cambio."""
    with patch.object(M.requests, "get", side_effect=_montar_mercado(0.589, [0.662] * 10)):
        mapa = M._presion_corto_map()
    p = mapa["ZZZ"]
    assert p["hoy"] == 58.9, "el porcentaje crudo es alto"
    assert p["salto"] < 1.0, "pero contra su propia costumbre está por debajo"
    assert M._senales_squeeze(None, None, None, p)["n"] == 0


def test_pocas_sesiones_en_todo_el_mercado_no_dan_dato():
    with patch.object(M.requests, "get",
                      side_effect=_montar_mercado(0.60, [0.30] * (M.SHVOL_MINIMO_SERIE - 2))):
        assert M._presion_corto_map() == {}


def test_un_ticker_con_pocas_sesiones_propias_tampoco_lo_da():
    """Guardián distinto del anterior: aquí el mercado SÍ tiene sesiones de
    sobra, pero un valor concreto solo aparece en tres (recién cotizado, o solo
    algunos días supera el suelo de volumen). No se le puede calcular una media
    con eso, aunque a su alrededor haya histórico."""
    hoy = date.today()
    fechas = [hoy - timedelta(days=i) for i in range(0, 12)]
    respuestas = {}
    for i, f in enumerate(fechas):
        filas = [("VIEJO", "300000", "1000000")]
        if i < 3:                                  # NUEVO solo en las 3 últimas
            filas.append(("NUEVO", "300000", "1000000"))
        respuestas[f"{f:%Y%m%d}"] = _fichero(filas)
    vacio = MagicMock(); vacio.status_code = 404

    def falso(url, **kw):
        return respuestas.get(url.split("CNMSshvol")[1][:8], vacio)

    with patch.object(M.requests, "get", side_effect=falso):
        mapa = M._presion_corto_map()
    assert "VIEJO" in mapa, "con 11 sesiones propias sí tiene media"
    assert "NUEVO" not in mapa, "con 2 sesiones propias no se le inventa una"


def test_las_claves_diarias_viejas_se_retiran():
    """La caché del proyecto marca caducidad pero NO borra: una clave vencida
    que nadie relee se queda para siempre. Aquí se crea una nueva cada día
    laborable, así que tienen que retirarse explícitamente."""
    vieja = f"market:shvol:{date.today() - timedelta(days=45):%Y%m%d}"
    cache.set(vieja, {"AAA": 0.5}, 604800)
    assert cache.get(vieja) is not None
    with patch.object(M.requests, "get", side_effect=_montar_mercado(0.60, [0.30] * 10)):
        M._presion_corto_map()
    assert cache.get(vieja) is None, "una clave fuera de la ventana debe borrarse"


# ── 3. La señal ─────────────────────────────────────────────────────────────

def test_un_salto_grande_suma_senal_y_se_puede_nombrar():
    n = M._senales_squeeze(None, None, None,
                           {"hoy": 72.7, "media": 51.4, "salto": 1.41 * 1.1,
                            "fecha": "2026-08-13", "sesiones": 20})
    assert n["de"] == 1 and n["n"] == 1
    assert any("presión vendedora" in c for c in n["cumplidas"])


def test_estar_por_debajo_de_su_media_no_suma_pero_si_cuenta_como_evaluable():
    n = M._senales_squeeze(None, None, None,
                           {"hoy": 58.9, "media": 66.2, "salto": 0.89,
                            "fecha": "2026-08-13", "sesiones": 20})
    assert n["de"] == 1, "el dato existe: es una señal evaluada, no ausente"
    assert n["n"] == 0


def test_sin_dato_de_presion_baja_el_denominador():
    """Un valor sin serie en el fichero no puede aparentar que suspende algo
    que no se le ha podido medir."""
    con = M._senales_squeeze(None, 1.0, None, {"salto": 1.0, "hoy": 40, "media": 40})
    sin = M._senales_squeeze(None, 1.0, None, None)
    assert con["de"] == 2 and sin["de"] == 1
    assert con["n"] == sin["n"] == 0


def test_el_corte_deja_fuera_a_la_gran_mayoria_del_mercado():
    """Calibrado sobre los 5.240 valores reales del 13/08/2026: la mediana del
    salto es 1,00 y el corte de 1,50 deja fuera al 95%. Con el 1,25 inicial
    disparaba uno de cada seis valores -- demasiado corriente para ser señal."""
    assert M.SHVOL_SALTO >= 1.5
