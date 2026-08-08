"""
Test del historial del RSU Score por ticker (rsu_score_tracking_service).

Fija lo mismo que en el histórico de sentimiento: que no se pinte una
tendencia con dos puntos, y que el resumen diga lo que promete. Base temporal
por test -- sembrar en rsu_score_history.db contaminaría el registro real.

Uso:
    cd backend
    python -m pytest tests/test_score_historial_ticker.py -v
"""
import sys, os, tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.rsu_score_tracking_service as S  # noqa: E402


@pytest.fixture
def base(monkeypatch):
    ruta = os.path.join(tempfile.mkdtemp(), "score.db")
    monkeypatch.setattr(S, "DB_PATH", ruta)
    S.init_db()
    yield
    if os.path.exists(ruta):
        os.remove(ruta)


def _sembrar(ticker, scores, desde=1):
    conn = S._conn()
    for i, sc in enumerate(scores):
        conn.execute(
            "INSERT OR REPLACE INTO score_tracked "
            "(ticker, fecha, score, label, breakdown, n_categorias, precio_entrada, creado_en) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ticker, f"2026-07-{desde + i:02d}", sc, "NEUTRAL", "[]", 5, 100.0, "x"))
    conn.commit()
    conn.close()


def test_con_pocos_dias_no_se_pinta_tendencia(base):
    _sembrar("AAPL", [50, 55])
    r = S.historial_ticker("AAPL")
    assert r["ok"] is False and r["dias"] == 2 and r["minimo"] == 5


def test_la_serie_sale_en_orden_cronologico(base):
    _sembrar("AAPL", [40, 45, 50, 55, 60])
    r = S.historial_ticker("AAPL")
    fechas = [p["fecha"] for p in r["serie"]]
    assert fechas == sorted(fechas), "La serie debe ir de más antigua a más reciente para pintarla"
    assert [p["score"] for p in r["serie"]] == [40, 45, 50, 55, 60]


def test_el_resumen_dice_lo_que_promete(base):
    _sembrar("AAPL", [40, 70, 55, 62, 58])
    r = S.historial_ticker("AAPL")
    assert r["actual"] == 58
    assert r["cambio"] == 58 - 62, "El cambio es contra el registro anterior, no contra el primero"
    assert r["min"] == 40 and r["max"] == 70 and r["n"] == 5


def test_cada_ticker_ve_solo_lo_suyo(base):
    _sembrar("AAPL", [40, 45, 50, 55, 60])
    _sembrar("MSFT", [90, 91, 92, 93, 94])
    assert S.historial_ticker("AAPL")["max"] == 60
    assert S.historial_ticker("MSFT")["min"] == 90


def test_el_ticker_se_normaliza_a_mayusculas(base):
    _sembrar("AAPL", [40, 45, 50, 55, 60])
    assert S.historial_ticker("aapl")["ok"] is True


def test_un_ticker_sin_registros_no_falla(base):
    r = S.historial_ticker("NOEXISTE")
    assert r["ok"] is False and r["dias"] == 0
