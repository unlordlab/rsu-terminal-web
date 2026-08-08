"""
Test del histórico propio de sentimiento (snapshots_service.historico_sentimiento).

Lo importante aquí no es el gráfico, es que el módulo NO pinte una tendencia
con cuatro puntos y que el percentil signifique lo que dice. Cada test usa su
propia base temporal: sembrar filas falsas en snapshots.db contaminaría el
histórico real, que es justo lo que este cambio quiere empezar a acumular.

Uso:
    cd backend
    python -m pytest tests/test_historico_sentimiento.py -v
"""
import sys, os, tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.snapshots_service as S  # noqa: E402


@pytest.fixture
def base(monkeypatch):
    """Base temporal, propia de cada test."""
    ruta = os.path.join(tempfile.mkdtemp(), "snap.db")
    monkeypatch.setattr(S, "DB_PATH", ruta)
    S.init_db()
    yield
    if os.path.exists(ruta):
        os.remove(ruta)


def _sembrar(fg=None, pc=None, n=0, desde=1):
    conn = S._conn()
    for i in range(n):
        conn.execute(
            "INSERT OR REPLACE INTO snapshot_mercado (fecha, fear_greed, put_call) VALUES (?,?,?)",
            (f"2026-06-{desde + i:02d}",
             fg[i] if fg else None,
             pc[i] if pc else None))
    conn.commit()
    conn.close()


def test_con_pocos_dias_no_se_pinta_una_tendencia(base):
    """Cuatro puntos aparentan una tendencia que no existe. Por debajo del
    minimo se dice cuantos dias van, no se dibuja."""
    _sembrar(fg=[30, 40, 50, 60, 55], n=5)
    r = S.historico_sentimiento()
    assert r["ok"] is False
    assert r["dias"] == 5 and r["minimo"] == 15


def test_el_percentil_dice_lo_que_promete(base):
    """'mas alto que el X% de los ultimos dias' tiene que ser literalmente
    eso, comprobado a mano."""
    valores = list(range(20, 40))          # 20 dias, el ultimo es el mayor
    _sembrar(fg=valores, n=len(valores))
    r = S.historico_sentimiento()
    d = r["fear_greed"]
    assert d["n"] == 20 and d["actual"] == 39
    assert d["percentil"] == round(19 / 20 * 100)   # 19 de 20 por debajo -> 95
    assert d["min"] == 20 and d["max"] == 39


def test_una_serie_puede_estar_lista_y_la_otra_no(base):
    """El put/call puede empezar a guardarse antes o despues que el Fear &
    Greed (fuentes distintas, fallos distintos). El que no llegue al minimo
    se devuelve como None en vez de con pocos puntos."""
    _sembrar(fg=list(range(20, 40)), pc=[None] * 20, n=20)
    conn = S._conn()
    for i in range(3):
        conn.execute("UPDATE snapshot_mercado SET put_call = ? WHERE fecha = ?",
                     (0.8, f"2026-06-{i + 1:02d}"))
    conn.commit()
    conn.close()

    r = S.historico_sentimiento()
    assert r["ok"] is True
    assert r["fear_greed"] is not None
    assert r["put_call"] is None, "Con 3 puntos el put/call no debe devolver resumen"


def test_las_filas_sin_ninguno_de_los_dos_no_cuentan(base):
    """Las sesiones anteriores a este cambio tienen los dos campos en NULL:
    no deben contar como historico ni arrastrar el minimo."""
    conn = S._conn()
    for i in range(30):
        conn.execute("INSERT INTO snapshot_mercado (fecha, vix) VALUES (?, ?)",
                     (f"2026-05-{i + 1:02d}", 15.0))
    conn.commit()
    conn.close()
    r = S.historico_sentimiento()
    assert r["ok"] is False and r["dias"] == 0
