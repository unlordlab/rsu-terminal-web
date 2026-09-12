"""
Auditoría del panel «Movimientos del percentil RS» (12/09/2026).

LO QUE SE COMPROBÓ PRIMERO, y salió bien: los 20 valores del panel de ese día
—los diez que cruzaban el 80 al alza y los diez que lo perdían— se reprodujeron
EXACTOS recalculando el percentil del universo entero (498 valores) desde los
precios reales a las dos fechas de la ventana (27/08 y 10/09). Mismos números,
mismos tickers, mismo orden. Los dos hallazgos son de lo que hay alrededor:

  #23  El «(10)» del título contaba las filas que caben, no los cruces que
       hubo. El servicio corta en 20 por lado. Medido sobre 263 ventanas de 10
       sesiones del último año: mediana 15 cruces por lado, máximo 32, y el
       15% de los días pasa de 20 — esos días el título decía «(20)» como si
       fueran todos.
  #24  Entre los «nuevos líderes» hay valores cuya fuerza relativa ha BAJADO:
       cruzan el 80 porque el resto cae más. Ese día eran dos de diez, ARES
       (-8,27% en la ventana) y REGN (-1,79%), presentados igual que SWKS, que
       había subido un 24,75%. El dato que los distingue ya estaba guardado en
       `snapshot_ticker.rs_score`; solo no se leía.

Uso:
    cd backend
    python -m pytest tests/test_rsrw_movimientos_1209.py -v
"""
import os
import sqlite3
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.rsrw_service as R  # noqa: E402
import services.snapshots_service as S  # noqa: E402

ANTES, HOY = "2026-08-27", "2026-09-10"

# Los seis casos reales de ese día: percentil y fuerza en crudo a las dos
# fechas, medidos recalculando el universo.
#          ticker   pct_antes  pct_hoy  score_antes  score_hoy
REALES = [("SWKS",     46.2,     83.1,      -3.34,      9.28),   # sube de verdad
          ("CF",       78.6,     89.0,       8.27,     12.78),   # sube de verdad
          ("ARES",     79.1,     80.7,       8.35,      8.16),   # entra con la fuerza cayendo
          ("REGN",     78.6,     80.3,       8.27,      7.82),   # idem
          ("AXON",     94.8,     50.0,      28.36,     -3.58),   # se hunde de verdad
          ("BKNG",     90.6,     65.3,      16.80,      1.34)]


class _NoCierra:
    """La función de producción cierra la conexión en su `finally`; aquí hace
    falta seguir consultándola después."""

    def __init__(self, c):
        self._c = c

    def __getattr__(self, n):
        return getattr(self._c, n)

    def close(self):
        pass


@pytest.fixture
def base(monkeypatch):
    """Una snapshots.db en memoria con el esquema real."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE snapshot_ticker (
            fecha TEXT NOT NULL, ticker TEXT NOT NULL, sector TEXT, precio REAL,
            rvol REAL, rs_pct REAL, rs_score REAL, phase INTEGER,
            PRIMARY KEY (fecha, ticker))
    """)
    monkeypatch.setattr(S, "_conn", lambda: _NoCierra(conn))
    monkeypatch.setattr(R, "_tag_cartera", lambda filas: filas)
    return conn


def _guardar(conn, filas, fechas=(ANTES, HOY)):
    """`filas` = [(ticker, pct_antes, pct_hoy, score_antes, score_hoy)]. Entre
    las dos fechas se rellenan las sesiones intermedias, que es lo que hace que
    la ventana de 10 exista."""
    for t, pa, ph, sa, sh in filas:
        conn.execute("INSERT INTO snapshot_ticker (fecha, ticker, rs_pct, rs_score) "
                     "VALUES (?, ?, ?, ?)", (fechas[0], t, pa, sa))
        conn.execute("INSERT INTO snapshot_ticker (fecha, ticker, rs_pct, rs_score) "
                     "VALUES (?, ?, ?, ?)", (fechas[1], t, ph, sh))
    conn.commit()


def _por_ticker(lista):
    return {m["ticker"]: m for m in lista}


# ── Lo que ya funcionaba: la cuenta ──────────────────────────────────────────

def test_los_cruces_se_detectan_como_antes(base):
    _guardar(base, REALES)
    d = R.get_rs_movimientos(ventana=10)
    assert d["ok"] and d["comparados"] == len(REALES)
    assert [m["ticker"] for m in d["nuevos_lideres"]] == ["CF", "SWKS", "ARES", "REGN"]
    assert [m["ticker"] for m in d["lideres_perdidos"]] == ["AXON", "BKNG"]
    cf = _por_ticker(d["nuevos_lideres"])["CF"]
    assert (cf["rs_previo"], cf["rs_actual"], cf["variacion"]) == (78.6, 89.0, 10.4)


# ── #24: quién sube y quién solo asciende porque los demás caen ──────────────

def test_los_que_entran_con_la_fuerza_cayendo_van_marcados(base):
    """EL test del caso: ARES perdió un 8,27% en la ventana y aun así aparecía
    entre los nuevos líderes igual que SWKS, que había ganado un 24,75%."""
    _guardar(base, REALES)
    nuevos = _por_ticker(R.get_rs_movimientos(ventana=10)["nuevos_lideres"])
    assert nuevos["ARES"]["contra_corriente"] is True
    assert nuevos["REGN"]["contra_corriente"] is True
    assert nuevos["ARES"]["fuerza"] == pytest.approx(-0.19, abs=0.01)


def test_los_que_suben_de_verdad_NO_se_marcan(base):
    """Si se marcara a todos, la marca no distinguiría nada."""
    _guardar(base, REALES)
    nuevos = _por_ticker(R.get_rs_movimientos(ventana=10)["nuevos_lideres"])
    assert nuevos["SWKS"]["contra_corriente"] is False
    assert nuevos["CF"]["contra_corriente"] is False
    assert nuevos["SWKS"]["fuerza"] == pytest.approx(12.62, abs=0.01)


def test_los_que_caen_de_verdad_tampoco(base):
    _guardar(base, REALES)
    perdidos = _por_ticker(R.get_rs_movimientos(ventana=10)["lideres_perdidos"])
    assert perdidos["AXON"]["contra_corriente"] is False
    assert perdidos["AXON"]["fuerza"] == pytest.approx(-31.94, abs=0.01)


def test_tambien_se_marca_al_reves(base):
    """La otra cara: pierde puesto mientras su fuerza sube, porque el resto
    sube más. Es igual de engañoso en el bloque de los que pierden liderazgo."""
    _guardar(base, [("XYZ", 85.0, 78.0, 4.0, 5.5)])
    perdidos = R.get_rs_movimientos(ventana=10)["lideres_perdidos"]
    assert perdidos[0]["contra_corriente"] is True and perdidos[0]["fuerza"] == 1.5


def test_sin_fuerza_guardada_no_se_marca_nada(base):
    """Las sesiones anteriores a que existiera la columna traen `rs_score` a
    NULL. Un hueco no puede convertirse en «este sube por mérito propio» ni en
    lo contrario: se deja sin marca y sin número."""
    _guardar(base, [("ARES", 79.1, 80.7, None, None)])
    m = R.get_rs_movimientos(ventana=10)["nuevos_lideres"][0]
    assert m["fuerza"] is None and m["contra_corriente"] is False


def test_una_fuerza_plana_no_es_contradiccion(base):
    _guardar(base, [("ABC", 79.0, 81.0, 5.0, 5.0)])
    m = R.get_rs_movimientos(ventana=10)["nuevos_lideres"][0]
    assert m["fuerza"] == 0.0 and m["contra_corriente"] is False


# ── #23: el recuento del título ──────────────────────────────────────────────

def _muchos(n_alza, n_baja):
    """n_alza valores que cruzan el 80 al alza y n_baja que lo pierden."""
    filas = []
    for i in range(n_alza):
        filas.append((f"UP{i}", 70.0 + i * 0.1, 81.0 + i * 0.1, 1.0, 2.0))
    for i in range(n_baja):
        filas.append((f"DN{i}", 85.0 + i * 0.1, 79.0 - i * 0.1, 2.0, 1.0))
    return filas


def test_el_total_de_cruces_viaja_aunque_la_lista_se_corte(base):
    """EL test del #23. Con 27 cruces al alza la lista lleva 20 y el total
    dice 27: sin eso, la pantalla rotula «(20)» como si fueran todos."""
    _guardar(base, _muchos(27, 24))
    d = R.get_rs_movimientos(ventana=10)
    assert len(d["nuevos_lideres"]) == 20 and d["total_alza"] == 27
    assert len(d["lideres_perdidos"]) == 20 and d["total_baja"] == 24


def test_cuando_caben_todos_el_total_coincide(base):
    """Que es el caso normal —la mediana son 15 por lado— y ahí la pantalla no
    tiene que enseñar ningún «de N»."""
    _guardar(base, REALES)
    d = R.get_rs_movimientos(ventana=10)
    assert d["total_alza"] == len(d["nuevos_lideres"]) == 4
    assert d["total_baja"] == len(d["lideres_perdidos"]) == 2


def test_el_que_no_estaba_en_la_fecha_vieja_no_cuenta(base):
    """Un valor que entró al índice a mitad de ventana no tiene variación, y
    arrastrarlo como si viniera de 0 sería una subida inventada de 80 puntos."""
    _guardar(base, REALES)
    base.execute("INSERT INTO snapshot_ticker (fecha, ticker, rs_pct, rs_score) "
                 "VALUES (?, 'NUEVO', 95.0, 20.0)", (HOY,))
    base.commit()
    d = R.get_rs_movimientos(ventana=10)
    assert d["comparados"] == len(REALES)
    assert "NUEVO" not in [m["ticker"] for m in d["nuevos_lideres"]]


# ── Que la pantalla use de verdad lo que el servicio manda ───────────────────

def test_la_pantalla_rotula_con_el_total_y_pinta_la_marca():
    """Mirar el fuente aquí es lo correcto: el hallazgo #23 ERA que la pantalla
    contaba `filas.length` teniendo el total al lado."""
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "rsrw.js")
    js = open(ruta, encoding="utf-8").read()
    assert "d.total_alza" in js and "d.total_baja" in js, "el total no llega al bloque"
    assert "' de ' + esc(total)" in js, "no se escribe «20 de 27» cuando se recorta"
    assert "m.contra_corriente" in js and "↓fuerza" in js, "la marca no se pinta"
