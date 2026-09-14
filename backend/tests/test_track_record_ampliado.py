"""
Track Record, ampliación del 14/09/2026 (a petición del usuario):

  2. El ACIERTO DEL SESGO DEL BRIEFING, que ya se medía pero solo se veía dentro
     del briefing. Con el listón al lado: lo que habría acertado decir ALCISTA
     siempre. Con datos reales salió 58,8% de aciertos a 1 día… con los 17 días
     evaluados BAJISTAS: ese número solo mide hacia dónde fue el mercado, y la
     página tiene que decirlo.
  3. El RSU SCORE CONTRA EL S&P 500 de la misma ventana. Era el único
     seguimiento sin baseline. Al probarlo con datos reales apareció un
     desajuste: el precio de entrada es casi siempre el cierre ANTERIOR (se
     registra antes de la apertura), y la primera versión arrancaba el índice
     en el cierre SIGUIENTE, dejando fuera un día que el valor sí contaba.
  5. La CURVA DE LA CARTERA RSU contra el S&P 500, pública: solo porcentajes,
     sin dólares ni posiciones. Con datos reales: +9,40% frente a +10,99%.

Uso:
    cd backend
    python -m pytest tests/test_track_record_ampliado.py -v
"""
import inspect
import os
import re
import sqlite3
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.rsu_score_tracking_service as S  # noqa: E402
import services.track_record_service as T  # noqa: E402

FRONT = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')


# ── 3. RSU Score contra el S&P 500 ──────────────────────────────────────────

@pytest.fixture
def base(monkeypatch):
    ruta = os.path.join(tempfile.mkdtemp(), "score.db")
    monkeypatch.setattr(S, "DB_PATH", ruta)
    S.init_db()
    yield ruta


def _serie(valores, desde="2026-07-20"):
    return pd.Series(valores, index=pd.bdate_range(desde, periods=len(valores)))


def _sembrar(ticker, fecha, precio, **resultados):
    conn = S._conn()
    cols = ["ticker", "fecha", "score", "label", "breakdown", "n_categorias", "precio_entrada", "creado_en", *resultados]
    conn.execute(f"INSERT INTO score_tracked ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})",
                 (ticker, fecha, 70, "COMPRA", "[]", 5, precio, "x", *resultados.values()))
    conn.commit()
    conn.close()


def _fila(ticker):
    conn = S._conn()
    r = dict(conn.execute("SELECT * FROM score_tracked WHERE ticker = ?", (ticker,)).fetchone())
    conn.close()
    return r


def _descarga(monkeypatch, series):
    import yf_batch
    monkeypatch.setattr(yf_batch, "download_batch", lambda tickers, **k: ({t: series[t] for t in tickers if t in series}, {}))


def test_el_indice_parte_del_cierre_ANTERIOR_como_el_precio_de_entrada(base, monkeypatch):
    """Registrado el domingo 26/07 con el cierre del viernes 24/07. El valor y
    el índice tienen que medir la MISMA ventana: del viernes al cierre 5
    sesiones después de la primera sesión en o tras el domingo."""
    #          lun20 mar21 mie22 jue23 vie24 | lun27 mar28 mie29 jue30 vie31 lun03 ...
    spy  = _serie([100, 100, 100, 100, 100,    110,  111,  112,  113,  114,  120, 121, 122, 123, 124, 125])
    accn = _serie([ 50,  50,  50,  50,  50,     55,   56,   57,   58,   59,   60,  61,  62,  63,  64,  65])
    _sembrar("ACCN", "2026-07-26", 50.0)
    _descarga(monkeypatch, {"SPY": spy, "ACCN": accn})
    S.actualizar_resultados_pendientes()
    f = _fila("ACCN")
    # primera sesión >= 26/07 es el lun 27 (pos 5); +5 sesiones = lun 03 (pos 10)
    assert f["resultado_5d"] == 20.0          # 50 → 60
    assert f["spy_5d"] == 20.0, "el índice desde el viernes (100), no desde el lunes (110)"


def test_rellena_el_indice_de_filas_que_ya_tenian_resultado(base, monkeypatch):
    spy = _serie([100] * 5 + [110, 111, 112, 113, 114, 120] + [121] * 60)
    _sembrar("VIEJA", "2026-07-26", 50.0, resultado_5d=20.0, resultado_10d=25.0)
    _descarga(monkeypatch, {"SPY": spy, "VIEJA": _serie([50] * 71)})
    S.actualizar_resultados_pendientes()
    f = _fila("VIEJA")
    assert f["resultado_5d"] == 20.0, "lo ya calculado no se reescribe"
    assert f["spy_5d"] == 20.0
    assert f["spy_10d"] is not None


def test_rellena_tambien_las_filas_ya_cerradas(base, monkeypatch):
    """Las que tienen resultado a 60 días ya no están «pendientes», y eran justo
    las más valiosas para comparar: sin esto se quedaban sin índice para siempre."""
    spy = _serie([100] * 5 + [110 + i for i in range(70)])
    _sembrar("CERRADA", "2026-07-26", 50.0, resultado_5d=1.0, resultado_10d=2.0, resultado_20d=3.0, resultado_60d=4.0)
    _descarga(monkeypatch, {"SPY": spy, "CERRADA": _serie([50] * 75)})
    S.actualizar_resultados_pendientes()
    f = _fila("CERRADA")
    assert f["spy_60d"] is not None and f["resultado_60d"] == 4.0


def test_un_plazo_sin_resultado_del_valor_no_recibe_indice(base, monkeypatch):
    """Un baseline sin el dato que compara no sirve: el valor solo llega a 5
    sesiones, el índice llegaría a 60."""
    spy = _serie([100] * 5 + [110 + i for i in range(80)])
    _sembrar("CORTA", "2026-07-26", 50.0)
    _descarga(monkeypatch, {"SPY": spy, "CORTA": _serie([50] * 12)})
    S.actualizar_resultados_pendientes()
    f = _fila("CORTA")
    assert f["resultado_5d"] is not None and f["spy_5d"] is not None
    assert f["resultado_10d"] is None and f["spy_10d"] is None


def test_no_se_sobrescribe_un_indice_ya_guardado(base, monkeypatch):
    spy = _serie([100] * 5 + [200] * 20)
    _sembrar("FIJA", "2026-07-26", 50.0, resultado_5d=10.0, spy_5d=3.21)
    _descarga(monkeypatch, {"SPY": spy, "FIJA": _serie([50] * 25)})
    S.actualizar_resultados_pendientes()
    assert _fila("FIJA")["spy_5d"] == 3.21


def test_sin_cierre_anterior_del_indice_no_hay_comparacion(base, monkeypatch):
    """Registro de antes del primer dato del S&P 500: no hay cierre anterior del
    que partir. Coger `iloc[-1]` leería el ÚLTIMO dato de la serie."""
    spy = _serie([100 + i for i in range(30)], desde="2026-07-27")
    _sembrar("PRIMERA", "2026-07-26", 50.0)
    _descarga(monkeypatch, {"SPY": spy, "PRIMERA": _serie([50 + i for i in range(30)], desde="2026-07-27")})
    S.actualizar_resultados_pendientes()
    f = _fila("PRIMERA")
    assert f["resultado_5d"] is not None and f["spy_5d"] is None


def test_una_segunda_pasada_no_toca_lo_relleno(base, monkeypatch):
    spy = _serie([100] * 5 + [110 + i for i in range(80)])
    _sembrar("OTRA", "2026-07-26", 50.0)
    _descarga(monkeypatch, {"SPY": spy, "OTRA": _serie([50 + i for i in range(85)])})
    S.actualizar_resultados_pendientes()
    antes = _fila("OTRA")
    assert S.actualizar_resultados_pendientes()["actualizadas"] == 0
    assert _fila("OTRA") == antes


def test_las_columnas_se_anaden_a_una_tabla_antigua(monkeypatch):
    """En producción la tabla ya existe sin las columnas del índice."""
    ruta = os.path.join(tempfile.mkdtemp(), "vieja.db")
    conn = sqlite3.connect(ruta)
    conn.execute("CREATE TABLE score_tracked (id INTEGER PRIMARY KEY, ticker TEXT, fecha TEXT, score INTEGER, "
                 "label TEXT, breakdown TEXT, n_categorias INTEGER, precio_entrada REAL, resultado_5d REAL, "
                 "resultado_10d REAL, resultado_20d REAL, resultado_60d REAL, resultado_actualizado TEXT, "
                 "creado_en TEXT, UNIQUE(ticker, fecha))")
    conn.commit()
    conn.close()
    monkeypatch.setattr(S, "DB_PATH", ruta)
    S.init_db()
    S.init_db()   # dos veces: no puede fallar por columna duplicada
    conn = sqlite3.connect(ruta)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(score_tracked)")}
    conn.close()
    assert {"spy_5d", "spy_10d", "spy_20d", "spy_60d"} <= cols


def test_el_resumen_por_tramo_da_la_diferencia_con_el_indice(base):
    conn = S._conn()
    for i, (res, spy) in enumerate([(10.0, 4.0), (6.0, 4.0), (8.0, None)]):
        conn.execute("INSERT INTO score_tracked (ticker, fecha, score, label, breakdown, n_categorias, precio_entrada, "
                     "creado_en, resultado_20d, spy_20d) VALUES (?,?,?,?,?,?,?,?,?,?)",
                     (f"T{i}", "2026-07-01", 85, "COMPRA FUERTE", "[]", 5, 10.0, "x", res, spy))
    conn.commit()
    conn.close()
    fuerte = next(b for b in S.obtener_resumen_por_bucket() if b["bucket"] == "COMPRA FUERTE")
    assert fuerte["vs_spy_20d"] == 4.0, "(10-4 + 6-4) / 2: la fila sin índice no entra"
    assert fuerte["n_vs_spy_20d"] == 2
    assert fuerte["avg_20d"] == 8.0


# ── 2. Sesgo del briefing ───────────────────────────────────────────────────

def _dia(fecha, sesgo, ret1, ret5=None):
    f = {"fecha": fecha, "sesgo": sesgo}
    if ret1 is not None:
        f["ret_1d"], f["acierto_1d"] = ret1, (ret1 > 0) == (sesgo == "ALCISTA")
    if ret5 is not None:
        f["ret_5d"], f["acierto_5d"] = ret5, (ret5 > 0) == (sesgo == "ALCISTA")
    return f


def test_el_acierto_va_con_su_liston_decir_siempre_alcista():
    filas = [_dia("2026-08-01", "BAJISTA", -1.0), _dia("2026-08-02", "BAJISTA", 0.5),
             _dia("2026-08-03", "BAJISTA", -0.2), _dia("2026-08-04", "NEUTRAL", 1.0),
             _dia("2026-08-05", "ALCISTA", None)]
    r = T.resumen_sesgo_briefing(filas)
    h = r["horizontes"]["1"]
    assert h["n"] == 3 and h["aciertos_pct"] == 66.7
    assert h["siempre_alcista_pct"] == 33.3, "de los 3 días evaluados, el mercado subió 1"
    assert h["por_direccion"]["bajista"]["n"] == 3 and h["por_direccion"]["alcista"]["n"] == 0
    assert h["suficiente"] is False
    assert r["neutrales"] == 1 and r["dias_registrados"] == 5
    assert r["pendientes"] == 4, "sin resultado a 5 días todavía"


def test_los_ultimos_dias_van_del_mas_reciente_y_son_como_mucho_20():
    filas = [_dia(f"2026-07-{d:02d}", "BAJISTA", -0.1) for d in range(1, 31)]
    ultimos = T.resumen_sesgo_briefing(filas)["ultimos"]
    assert len(ultimos) == 20 and ultimos[0]["fecha"] == "2026-07-30"


def test_con_muestra_suficiente_se_marca():
    filas = [_dia(f"2026-{m:02d}-{d:02d}", "ALCISTA", 1.0) for m in (6, 7) for d in range(1, 16)]
    assert T.resumen_sesgo_briefing(filas)["horizontes"]["1"]["suficiente"] is True


# ── 5. Curva de la Cartera contra el S&P 500 ────────────────────────────────

def test_la_curva_parte_de_100_y_compara_las_mismas_fechas():
    historia = [{"fecha": "2026-07-20", "retorno": 100.0, "valor": 50000, "invertido": 40000},
                {"fecha": "2026-07-21", "retorno": 110.0, "valor": 60000, "invertido": 45000},
                {"fecha": "2026-07-22", "retorno": 99.0,  "valor": 55000, "invertido": 45000},
                {"fecha": "2026-07-25", "retorno": 115.5, "valor": 70000, "invertido": 50000}]
    spy = _serie([400.0, 404.0, 408.0, 420.0], desde="2026-07-20")   # lun-jue: el sábado 25 toma el jueves
    c = T.curva_cartera_vs_spy(historia, spy)
    assert c["serie"][0] == {"fecha": "2026-07-20", "cartera": 100.0, "spy": 100.0}
    assert c["cartera_pct"] == 15.5 and c["spy_pct"] == 5.0 and c["diferencia_pp"] == 10.5
    assert c["peor_caida_cartera"] == -10.0, "de 110 a 99"
    assert c["peor_caida_spy"] == 0.0


def test_la_curva_publica_no_lleva_dolares_ni_posiciones():
    historia = [{"fecha": "2026-07-20", "retorno": 100.0, "valor": 50000, "invertido": 40000},
                {"fecha": "2026-07-21", "retorno": 101.0, "valor": 51000, "invertido": 40000}]
    c = T.curva_cartera_vs_spy(historia, _serie([400.0, 401.0]))
    texto = repr(c)
    assert "50000" not in texto and "invertido" not in texto and "valor" not in texto
    assert set(c["serie"][0]) == {"fecha", "cartera", "spy"}


def test_sin_historia_no_se_inventa_curva():
    assert T.curva_cartera_vs_spy([{"fecha": "2026-07-20", "retorno": 100.0}], _serie([1.0]))["serie"] == []


def test_briefing_y_cartera_entran_en_el_track_record(monkeypatch):
    from services.cache import cache
    monkeypatch.setattr(cache, "get", lambda *a, **k: None)
    monkeypatch.setattr(cache, "set", lambda *a, **k: None)
    for f in ("_track_record_algoritmo", "_track_record_tesis", "_track_record_canslim",
              "_track_record_rsu_score", "_track_record_options"):
        monkeypatch.setattr(T, f, lambda: None)
    monkeypatch.setattr(T, "_track_record_briefing", lambda: {"dias_registrados": 3})
    monkeypatch.setattr(T, "_track_record_cartera", lambda: {"n_dias": 9})
    r = T.get_track_record()
    assert r["ok"] and r["briefing"] == {"dias_registrados": 3} and r["cartera"] == {"n_dias": 9}


# ── Frontend ────────────────────────────────────────────────────────────────

def _js():
    with open(os.path.join(FRONT, 'pages', 'track_record.js'), encoding='utf-8') as f:
        return f.read()


def test_la_pagina_pinta_cartera_y_briefing_arriba():
    js = _js()
    i = js.index("body.innerHTML = avisoVisitante(data)")
    orden = js[i:i + 400]
    assert orden.index("seccionCartera(data.cartera)") < orden.index("seccionAlgoritmo(")
    assert "seccionBriefing(data.briefing)" in orden


def test_el_briefing_avisa_cuando_todos_los_dias_tienen_el_mismo_sesgo():
    js = _js()
    f = js[js.index("function seccionBriefing"):]
    assert "unSoloSesgo" in f and "DECIR SIEMPRE «ALCISTA»" in f
    assert "siempre_alcista_pct" in f


def test_rsu_score_enseña_la_columna_contra_el_indice():
    js = _js()
    f = js[js.index("function seccionRsuScore"):]
    f = f[:f.index("\n}\n")]
    assert "pct(b.vs_spy_20d, ' pp')" in f and "pct(b.vs_spy_60d, ' pp')" in f
