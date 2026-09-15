"""
Auditoría del briefing del 15/09/2026: futuros, escaneo nocturno, medias y miles con espacio.

EL CASO. El usuario pidió auditar el briefing de las 13:33 UTC. Contra Yahoo,
contrato a contrato y minuto a minuto, salieron cuatro fallos que no eran del
modelo sino de los datos o de la revisión:

  #70  «los futuros abrieron con un gap alcista del 0,85% y 0,92%». `ES=F` era
       el contrato de SEPTIEMBRE hasta el 14/09 y el de DICIEMBRE el 15/09: se
       comparaban dos contratos. El de diciembre contra sí mismo, −0,15%.
  #26  (Scanner) la reparación de la última sesión recuperó 0 de 2.402. A esa
       hora Yahoo sirve la barra diaria con el cierre vacío por CUALQUIER
       camino diario; las velas de 30 min sí lo traen.
  #71  «apenas por encima de su SMA50 (7.611,41)» con el S&P en 7.604,91. Las
       dos versiones del día lo escribieron, y la revisión no miraba el lado.
  #73  la revisión leía «7 611,50» como 7 y 611,5 y denunciaba como inventados
       niveles reales.

Uso:
    cd backend
    python -m pytest tests/test_briefing_auditoria_1509.py -v
"""
import inspect
import os
import sys
from datetime import date, datetime

import pandas as pd
import pytest

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))
sys.path.insert(0, os.path.join(RAIZ, 'shared'))

import daily_briefing as D  # noqa: E402
import yf_batch as Y  # noqa: E402

ET = "America/New_York"


def _diaria(fechas, cierres):
    idx = pd.DatetimeIndex([pd.Timestamp(f, tz=ET) for f in fechas])
    return pd.DataFrame({"Close": cierres}, index=idx)


def _minutos(marcas, cierres):
    idx = pd.DatetimeIndex([pd.Timestamp(m, tz=ET) for m in marcas])
    return pd.DataFrame({"Close": cierres}, index=idx)


# ── #70 Futuros: la variación, del mismo contrato ────────────────────────────

LUNES, MARTES = "2026-09-14", "2026-09-15"
# Los cierres reales del 14 y el 15/09 (el del 15, a las 09:53 ET).
CONTINUO = _diaria([LUNES, MARTES], [7625.00, 7679.25])          # septiembre -> diciembre
SEPTIEMBRE = _diaria([LUNES, MARTES], [7625.00, 7612.75])
DICIEMBRE = _diaria([LUNES, MARTES], [7692.75, 7679.25])


def _yahoo(series, minutos=None):
    def descargar(ticker, intervalo):
        if intervalo == "1m":
            return (minutos or {}).get(ticker)
        return series.get(ticker)
    return descargar


def test_los_candidatos_son_los_proximos_contratos_de_cada_futuro():
    hoy = date(2026, 9, 15)
    assert D.contratos_candidatos("ES=F", hoy)[:2] == ["ESU26.CME", "ESZ26.CME"]
    assert D.contratos_candidatos("CL=F", hoy)[:3] == ["CLU26.NYM", "CLV26.NYM", "CLX26.NYM"]
    assert D.contratos_candidatos("GC=F", hoy)[:2] == ["GCV26.CMX", "GCZ26.CMX"]
    assert D.contratos_candidatos("NQ=F", date(2026, 12, 20))[:2] == ["NQZ26.CME", "NQH27.CME"], (
        "en diciembre el siguiente es el de marzo del año que viene")


def test_EL_CASO_el_gap_sale_del_contrato_de_diciembre_contra_si_mismo():
    """El continuo daba +0,71%; el contrato que hay detrás, −0,18%."""
    hist, contrato = D.serie_del_contrato("ES=F", CONTINUO, date(2026, 9, 15),
                                          _yahoo({"ESU26.CME": SEPTIEMBRE, "ESZ26.CME": DICIEMBRE}))
    assert contrato == "ESZ26.CME"
    prev, last = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
    assert round((last / prev - 1) * 100, 2) == -0.18
    assert round((CONTINUO["Close"].iloc[-1] / CONTINUO["Close"].iloc[-2] - 1) * 100, 2) == 0.71, (
        "el caso de partida: el continuo cosía dos contratos")


def test_si_no_se_sabe_que_contrato_es_NO_se_da_variacion():
    """Un gap inventado es peor que un hueco."""
    otro = _diaria([LUNES, MARTES], [7000.0, 7010.0])
    assert D.serie_del_contrato("ES=F", CONTINUO, date(2026, 9, 15),
                                _yahoo({"ESU26.CME": otro, "ESZ26.CME": otro})) == (None, None)
    assert D.serie_del_contrato("ES=F", CONTINUO, date(2026, 9, 15), _yahoo({})) == (None, None)


def test_un_contrato_de_otra_fecha_no_vale_aunque_el_precio_se_parezca():
    viejo = _diaria(["2026-09-10", "2026-09-11"], [7600.0, 7679.25])
    assert D.serie_del_contrato("ES=F", CONTINUO, date(2026, 9, 15),
                                _yahoo({"ESZ26.CME": viejo})) == (None, None)


def test_la_ultima_barra_se_pone_al_dia_con_el_ultimo_minuto():
    """El WTI salió a 102,18 cuando ese minuto cotizaba a ~103,6: la barra
    diaria de un futuro va con retraso a media sesión."""
    minutos = {"ESZ26.CME": _minutos(["2026-09-15 09:52", "2026-09-15 09:53"], [7680.0, 7681.5])}
    hist, _ = D.serie_del_contrato("ES=F", CONTINUO, date(2026, 9, 15),
                                   _yahoo({"ESZ26.CME": DICIEMBRE}, minutos))
    assert hist["Close"].iloc[-1] == 7681.5
    assert DICIEMBRE["Close"].iloc[-1] == 7679.25, "no puede tocar la serie original"


def test_un_minuto_de_la_sesion_SIGUIENTE_no_pisa_la_barra():
    """A las 19:00 ET del lunes el CME ya está en la sesión del martes."""
    assert D.fecha_de_sesion_futuro(pd.Timestamp("2026-09-14 19:00", tz=ET)) == date(2026, 9, 15)
    assert D.fecha_de_sesion_futuro(pd.Timestamp("2026-09-15 03:00", tz=ET)) == date(2026, 9, 15)
    minutos = {"ESZ26.CME": _minutos(["2026-09-15 18:30"], [7700.0])}
    hist, _ = D.serie_del_contrato("ES=F", CONTINUO, date(2026, 9, 15),
                                   _yahoo({"ESZ26.CME": DICIEMBRE}, minutos))
    assert hist["Close"].iloc[-1] == 7679.25


def test_get_market_data_lo_usa_para_los_cuatro_futuros():
    fuente = inspect.getsource(D.get_market_data)
    assert "serie_del_contrato(" in fuente and "if ticker in CONTRATOS_FUTUROS" in fuente
    assert set(D.CONTRATOS_FUTUROS) == {"ES=F", "NQ=F", "CL=F", "GC=F"}
    i = fuente.index("serie_del_contrato(")
    assert fuente.index("cierres[name] =") > i, (
        "los cierres de la sesión (en_sesion) tienen que salir del contrato, no del continuo")


def test_el_archivo_de_auditoria_guarda_los_futuros():
    """Hoy no se pudo ver el ES del prompt de las 13:33: no se guardaba."""
    guardado = D.construir_datos({"ES": {"price": 1, "chg_pct": 0.1, "contrato": "ESZ26.CME"},
                                     "NQ": {"price": 2, "chg_pct": 0.2}}, [], [])
    assert guardado["indices"]["ES"]["contrato"] == "ESZ26.CME" and "NQ" in guardado["indices"]


# ── #26 Scanner: el cierre desde las velas de 30 min ─────────────────────────

VIERNES, LUNES_D = date(2026, 9, 11), date(2026, 9, 14)


def _velas(desde="09:30", hasta="15:30", dia="2026-09-14", tickers=("A", "B")):
    marcas = pd.date_range(f"{dia} {desde}", f"{dia} {hasta}", freq="30min", tz=ET).tz_convert("UTC")
    n = len(marcas)
    datos = {}
    for t in tickers:
        datos[("Open", t)] = [10.0 + i for i in range(n)]
        datos[("High", t)] = [11.0 + i for i in range(n)]
        datos[("Low", t)] = [9.0 + i for i in range(n)]
        datos[("Close", t)] = [10.5 + i for i in range(n)]
        datos[("Volume", t)] = [100.0] * n
    df = pd.DataFrame(datos, index=marcas)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    return df


def _cierres(tickers=("A", "B")):
    idx = pd.DatetimeIndex([pd.Timestamp("2026-09-10"), pd.Timestamp("2026-09-11")])
    close_d = {t: pd.Series([9.0, 10.0], index=idx) for t in tickers}
    vol_d = {t: pd.Series([500.0, 600.0], index=idx) for t in tickers}
    hl_d = {t: pd.DataFrame({"Open": [1.0, 1.0], "High": [2.0, 2.0], "Low": [0.5, 0.5]}, index=idx)
            for t in tickers}
    return close_d, vol_d, hl_d


def test_la_barra_sale_de_la_ultima_vela_y_el_ohlc_de_todas():
    barra = Y._barra_desde_velas(_velas().xs("A", axis=1, level=1), LUNES_D)
    assert barra == {"Open": 10.0, "High": 23.0, "Low": 9.0, "Close": 22.5}


def test_una_sesion_a_medias_no_se_pega():
    """Si la última vela no es la de las 15:30, el día no ha terminado."""
    assert Y._barra_desde_velas(_velas(hasta="14:00").xs("A", axis=1, level=1), LUNES_D) is None
    assert Y._barra_desde_velas(_velas(dia="2026-09-11").xs("A", axis=1, level=1), LUNES_D) is None


def test_EL_CASO_se_pega_cierre_y_ohlc_pero_NO_el_volumen(monkeypatch):
    """El volumen de las velas sale un 17% corto (sin la subasta de cierre):
    mejor el de la víspera que uno falso."""
    close_d, vol_d, hl_d = _cierres()
    n = Y.reparar_con_velas(close_d, hl_d, ["A", "B"], LUNES_D, batch_sleep=0, vol_d=vol_d,
                            descargar=lambda lote: _velas(tickers=lote))
    assert n == 2
    for t in ("A", "B"):
        assert close_d[t].index[-1].date() == LUNES_D and close_d[t].iloc[-1] == 22.5
        assert list(hl_d[t].iloc[-1]) == [10.0, 23.0, 9.0]
        assert len(vol_d[t]) == 2, "se ha pegado el volumen de las velas"


def test_la_reparacion_prueba_las_velas_con_los_que_siguen_sin_barra(monkeypatch):
    """La noche del 14 al 15: la segunda pasada diaria no trae nada (cierre
    vacío) y la tercera, de velas, sí."""
    close_d, vol_d, hl_d = _cierres()
    pedidos = []

    def falso(tickers, **kw):
        pedidos.append(kw.get("interval", "1d"))
        if kw.get("interval") == "30m":
            return _velas(tickers=tickers)
        idx = pd.DatetimeIndex([pd.Timestamp("2026-09-11", tz=ET), pd.Timestamp("2026-09-14", tz=ET)])
        datos = {(c, t): [10.0, float("nan")] for t in tickers for c in ("Open", "High", "Low", "Close", "Volume")}
        df = pd.DataFrame(datos, index=idx)
        df.columns = pd.MultiIndex.from_tuples(df.columns)
        return df

    monkeypatch.setattr(Y.yf, "download", falso)
    monkeypatch.setattr(Y, "_diagnosticar_uno", lambda t, f: "")
    faltaban, recuperados = Y.reparar_ultima_sesion(close_d, vol_d, hl_d, LUNES_D, batch_sleep=0)
    assert pedidos == ["1d", "30m"]
    assert (faltaban, recuperados) == (2, 2)
    assert close_d["A"].index[-1].date() == LUNES_D


def test_si_las_velas_tampoco_estan_no_se_inventa_nada():
    close_d, vol_d, hl_d = _cierres()
    n = Y.reparar_con_velas(close_d, hl_d, ["A"], LUNES_D, batch_sleep=0,
                            descargar=lambda lote: pd.DataFrame())
    assert n == 0 and close_d["A"].index[-1].date() == VIERNES


def test_las_velas_reescriben_el_cache(monkeypatch, tmp_path):
    close_d, vol_d, hl_d = _cierres(("A",))
    escrituras = []
    monkeypatch.setattr(Y.price_cache, "escribir",
                        lambda d, t, c, v=None, h=None: escrituras.append((t, len(c), len(v))))
    Y.reparar_con_velas(close_d, hl_d, ["A"], LUNES_D, batch_sleep=0, cache_dir=str(tmp_path),
                        vol_d=vol_d, descargar=lambda lote: _velas(tickers=lote))
    assert escrituras == [("A", 3, 2)]


# ── #71 El lado de la media ──────────────────────────────────────────────────

PROMPT_1333 = ("- S&P 500: Último: 7,604.91 (+3.10% vs SMA200) | SMA20: 7,669.86 | SMA50: 7,611.41 | "
               "SMA200: 7,376.20 | Rango 20d: 7,520.00 – 7,780.00\n"
               "- Nasdaq 100: Último: 29,119.21 (+9.00% vs SMA200) | SMA20: 29,300.00 | SMA50: 28,900.00 | "
               "SMA200: 26,700.00 | Rango 20d: 28,500.00 – 29,800.00")
PROMPT_1341 = PROMPT_1333.replace("7,604.91", "7,608.90").replace("7,669.86", "7,670.09").replace(
    "7,611.41", "7,611.50")


@pytest.mark.parametrize("texto,prompt", [
    ("El S&P 500 está ahora por debajo de su SMA20 (7.669,86) y apenas por encima de su SMA50 (7.611,41).",
     PROMPT_1333),
    ("El S&P 500 cotiza por debajo de su SMA20 (7.670,09) y apenas por encima de su SMA50 (7.611,50).",
     PROMPT_1341),
])
def test_EL_CASO_las_dos_versiones_del_dia_se_cazan(texto, prompt):
    r = D.revisar_briefing(texto, prompt)
    assert len(r["hechos"]) == 1 and "SMA50" in r["hechos"][0] and "por debajo" in r["hechos"][0]


def test_lo_que_esta_bien_no_se_denuncia():
    assert D.lado_de_la_media_invertido(
        "El S&P 500 cotiza por debajo de su SMA20 (7.670) y por debajo de su SMA50.", PROMPT_1333) == []
    assert D.lado_de_la_media_invertido(
        "El Nasdaq 100 se mantiene por encima de su SMA50 y bajo la SMA20.", PROMPT_1333) == []


def test_una_condicion_no_es_una_afirmacion():
    """«Un cierre por encima de la SMA20 invalidaría» no dice dónde está."""
    for frase in ("El nivel que invalidaría mi postura es un cierre por encima de la SMA50 en 7.611,41.",
                  "Mientras el S&P 500 siga por encima de su SMA50, la tesis aguanta.",
                  "Si el S&P 500 se mantiene por encima de su SMA50 hoy, cambia la lectura."):
        assert D.lado_de_la_media_invertido(frase, PROMPT_1333) == [], frase


def test_la_amplitud_con_las_mismas_palabras_no_cuenta():
    """Era la mitad de las frases candidatas en los briefings desde julio."""
    for frase in ("Solo el 39,4% del S&P 500 está por encima de su SMA50.",
                  "El 60% de las acciones del S&P 500 cotiza por encima de su SMA50."):
        assert D.lado_de_la_media_invertido(frase, PROMPT_1333) == [], frase


def test_sin_indice_claro_no_se_acusa_a_ninguno():
    assert D.lado_de_la_media_invertido("El índice ya está por encima de su SMA50.", PROMPT_1333) == []
    assert D.lado_de_la_media_invertido(
        "El S&P 500 y el Nasdaq 100 están por encima de su SMA50.", PROMPT_1333) == []


def test_el_tecnologico_es_el_nasdaq():
    fallos = D.lado_de_la_media_invertido("El índice tecnológico está por debajo de su SMA50.", PROMPT_1333)
    assert len(fallos) == 1 and "Nasdaq 100" in fallos[0]


def test_pegado_a_la_media_vale_cualquier_lado():
    prompt = PROMPT_1333.replace("7,604.91", "7,611.00")
    assert D.lado_de_la_media_invertido("El S&P 500 está por encima de su SMA50.", prompt) == []


def test_una_segunda_lectura_con_el_lado_invertido_se_descarta():
    """Va en «hechos», que es lo que descarta la segunda lectura."""
    fuente = inspect.getsource(D.generar_segunda_lectura)
    assert 'revision["hechos"]' in fuente
    assert "lado_de_la_media_invertido(texto, prompt)" in inspect.getsource(D.revisar_briefing)


# ── #73 Miles con espacio ────────────────────────────────────────────────────

@pytest.mark.parametrize("texto,esperado", [
    ("7 611,50", [7611.5]),
    ("7 611,50", [7611.5]),
    ("7 604,91", [7604.91]),
    ("1 234 567,89", [1234567.89]),
    ("SMA50 (7.611,50)", [50.0, 7611.5]),
    ("entre 395 y 494 palabras", [395.0, 494.0]),
    ("el S&P 500 200 puntos por debajo", [500.0, 200.0]),
])
def test_los_numeros_con_espacio_de_miles(texto, esperado):
    assert D._numeros(texto) == esperado


def test_EL_CASO_la_sma_real_escrita_con_espacio_no_es_un_nivel_inventado():
    texto = "El nivel que invalida mi lectura es la SMA50 del S&P 500 en 7 611,50."
    otros = D.revisar_briefing(texto, PROMPT_1341)["otros"]
    assert not [o for o in otros if "NIVEL INVENTADO" in o], otros


# ── Huecos que dejó el primer sabotaje ───────────────────────────────────────

def test_sobre_su_media_tambien_es_por_encima():
    """«Sobre» es la forma corta, y la que usan los briefings de julio."""
    fallos = D.lado_de_la_media_invertido("El S&P 500 está sobre su SMA50 (7.611,41).", PROMPT_1333)
    assert len(fallos) == 1 and "por encima" in fallos[0]


def test_el_maximo_del_dia_es_el_de_todas_las_velas_no_el_de_la_ultima():
    marcas = pd.date_range("2026-09-14 09:30", "2026-09-14 15:30", freq="30min", tz=ET)
    n = len(marcas)
    velas = pd.DataFrame({"Open": [10.0] * n, "High": [11.0] * n, "Low": [9.0] * n,
                          "Close": [10.5] * n}, index=marcas)
    velas.iloc[3, velas.columns.get_loc("High")] = 30.0
    velas.iloc[5, velas.columns.get_loc("Low")] = 2.0
    barra = Y._barra_desde_velas(velas, LUNES_D)
    assert barra["High"] == 30.0 and barra["Low"] == 2.0


def test_el_dato_del_futuro_dice_de_que_contrato_sale():
    """Para poder auditarlo al día siguiente sin volver a Yahoo."""
    assert 'data[name]["contrato"] = contrato' in inspect.getsource(D.get_market_data)
