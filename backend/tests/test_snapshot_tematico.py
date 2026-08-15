"""
Histórico por cesta temática: qué temas ROTAN, no cuáles están arriba.

DE DÓNDE SALE. El Gist del scan temático se sobrescribe cada noche, así que el
módulo solo sabía decir cómo está una cesta HOY. Una cesta que lleva meses
arriba ya no es una oportunidad; una que gana 18 puntos en cinco sesiones es una
rotación en curso -- y esa segunda pregunta no se podía contestar.

Mismo problema que ya resolvieron las otras tres tablas de snapshots.db,
aplicado al único scan que faltaba.

SOBRE LA RETENCIÓN. El usuario pidió 30 días por espacio. Medido antes de
elegir: son 29 filas al día -- una por cesta, no 500 como snapshot_ticker -- así
que 30 días son 91 KB, un año 768 KB y veinte años 15 MB. El espacio no es la
restricción; lo que decide es para qué sirve. Con 400 días se puede comparar
contra el mismo mes del año anterior por unos 840 KB.

LO QUE FIJA ESTE FICHERO:
1. La purga cuenta desde la fecha de SESIÓN, no desde el reloj del proceso.
2. Sin histórico suficiente para una ventana se devuelve None, NO se compara
   contra la fila más antigua que haya -- eso daría una variación inventada.
   Lo que se sigue es la AMPLITUD, que es la métrica que ordena el módulo.
3. Escribir dos veces el mismo día no duplica ni altera nada.

Uso:
    cd backend
    python -m pytest tests/test_snapshot_tematico.py -v
"""
import sys, os, sqlite3
from datetime import date, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.snapshots_service as S  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    """Base temporal: no se toca la real."""
    ruta = str(tmp_path / "snapshots.db")
    monkeypatch.setattr(S, "DB_PATH", ruta)
    S.init_db()
    return ruta


def _cestas(n=3, base=50.0):
    return {"ok": True, "sectors": [
        {"sector": f"C{i}", "avg_score": base + i * 10, "avg_momentum": 40,
         "basket": 10, "breadth": base + i * 10}
        for i in range(n)]}


def _escribir(fecha, datos):
    with patch("services.thematic_service.get_thematic_composition", return_value=datos):
        conn = S._conn()
        try:
            S._maybe_write_tematico(conn, fecha)
        finally:
            conn.close()


# ── 1. Escritura ────────────────────────────────────────────────────────────

def test_guarda_una_fila_por_cesta(db):
    _escribir("2026-08-14", _cestas(3))
    conn = S._conn()
    assert conn.execute("SELECT COUNT(*) FROM snapshot_tematico").fetchone()[0] == 3


def test_escribir_dos_veces_el_mismo_dia_no_duplica(db):
    """La clave primaria (fecha, cesta) ya lo garantiza -- este test fija la
    invariante, no el guardián de arriba (ver el siguiente)."""
    _escribir("2026-08-14", _cestas(3))
    _escribir("2026-08-14", _cestas(3, base=99.0))   # otro valor, mismo día
    conn = S._conn()
    assert conn.execute("SELECT COUNT(*) FROM snapshot_tematico").fetchone()[0] == 3
    v = conn.execute("SELECT avg_score FROM snapshot_tematico WHERE cesta='C0'").fetchone()[0]
    assert v == 50.0, "el primero manda; el día ya estaba escrito"


def test_el_dia_ya_escrito_ni_siquiera_relee_el_scan(db):
    """Esto corre en el bucle de 4 minutos: sin el guardián, cada pasada
    volvería a pedir la composición temática entera para acabar descartándola
    en el INSERT OR IGNORE. El test anterior no lo detecta, porque la clave
    primaria protege el resultado igualmente -- lo cazó el sabotaje."""
    _escribir("2026-08-14", _cestas(3))
    with patch("services.thematic_service.get_thematic_composition",
               return_value=_cestas(3)) as leer:
        conn = S._conn()
        try:
            S._maybe_write_tematico(conn, "2026-08-14")
        finally:
            conn.close()
    leer.assert_not_called()


def test_una_cesta_sin_score_no_se_guarda(db):
    """Guardar un None dejaría un hueco que luego se compara mal."""
    datos = {"ok": True, "sectors": [
        {"sector": "BUENA", "avg_score": 60.0, "avg_momentum": 40, "basket": 10, "breadth": 60.0},
        {"sector": "VACIA", "avg_score": None, "avg_momentum": None, "basket": 0, "breadth": None}]}
    _escribir("2026-08-14", datos)
    conn = S._conn()
    cestas = [r[0] for r in conn.execute("SELECT cesta FROM snapshot_tematico")]
    assert cestas == ["BUENA"]


def test_sin_scan_valido_no_se_escribe_nada(db):
    """La respuesta lleva `sectors` PERO `ok: False`. Es el caso que hay que
    probar: con un `{"ok": False, "error": ...}` a secas, quitar el guardián
    también dejaría la tabla vacía, pero por un KeyError accidental al buscar
    "sectors", no por la comprobación. El sabotaje lo destapó."""
    _escribir("2026-08-14", {"ok": False, "error": "el Gist no responde",
                             "sectors": _cestas(3)["sectors"]})
    conn = S._conn()
    assert conn.execute("SELECT COUNT(*) FROM snapshot_tematico").fetchone()[0] == 0


# ── 2. La purga ─────────────────────────────────────────────────────────────

def test_la_purga_retira_lo_que_cae_fuera_de_la_ventana(db):
    hoy = date(2026, 8, 14)
    vieja = (hoy - timedelta(days=S.TEMATICO_RETENCION_DIAS + 10)).strftime("%Y-%m-%d")
    dentro = (hoy - timedelta(days=S.TEMATICO_RETENCION_DIAS - 10)).strftime("%Y-%m-%d")
    conn = S._conn()
    for f in (vieja, dentro):
        conn.execute("INSERT INTO snapshot_tematico (fecha,cesta,avg_score,avg_momentum,basket,breadth) VALUES (?,?,?,?,?,?)", (f, "C0", 50.0, 40, 10, 50.0))
    conn.commit(); conn.close()

    _escribir(hoy.strftime("%Y-%m-%d"), _cestas(1))

    conn = S._conn()
    fechas = {r[0] for r in conn.execute("SELECT DISTINCT fecha FROM snapshot_tematico")}
    assert vieja not in fechas, "lo de fuera de la ventana tiene que irse"
    assert dentro in fechas, "lo de dentro se queda"


def test_la_purga_cuenta_desde_la_sesion_no_desde_el_reloj(db):
    """Si contara desde datetime.now(), la ventana se movería según cuándo se
    reinició el contenedor -- el mismo error que ya se corrigió una vez en
    Options Flow con un bucle de 24h."""
    conn = S._conn()
    conn.execute("INSERT INTO snapshot_tematico (fecha,cesta,avg_score,avg_momentum,basket,breadth) VALUES ('2020-01-01','C0',50.0,40,10,50.0)")
    conn.commit()
    # Sesión antigua: contra ella, 2020-01-01 está DENTRO de la ventana
    borradas = S._purgar_tematico(conn, "2020-06-01")
    assert borradas == 0
    # Sesión de hoy: ahora sí queda fuera
    assert S._purgar_tematico(conn, "2026-08-14") == 1
    conn.close()


def test_una_fecha_corrupta_no_borra_nada(db):
    conn = S._conn()
    conn.execute("INSERT INTO snapshot_tematico (fecha,cesta,avg_score,avg_momentum,basket,breadth) VALUES ('2026-08-14','C0',50.0,40,10,50.0)")
    conn.commit()
    assert S._purgar_tematico(conn, "no-es-una-fecha") == 0
    assert conn.execute("SELECT COUNT(*) FROM snapshot_tematico").fetchone()[0] == 1
    conn.close()


# ── 3. La variación ─────────────────────────────────────────────────────────

def _sembrar(conn, dias, score_por_dia):
    base = date(2026, 8, 14)
    for i in range(dias):
        f = (base - timedelta(days=i)).strftime("%Y-%m-%d")
        conn.execute("INSERT INTO snapshot_tematico (fecha,cesta,avg_score,avg_momentum,basket,breadth) VALUES (?,?,?,?,?,?)",
                     (f, "C0", score_por_dia(i), 40, 10, score_por_dia(i)))
    conn.commit()


def test_la_variacion_compara_contra_la_sesion_correcta(db):
    conn = S._conn()
    # hoy 70; hace 5 sesiones 50; hace 20 sesiones 65
    _sembrar(conn, 25, lambda i: 70.0 if i == 0 else (50.0 if i == 5 else (65.0 if i == 20 else 60.0)))
    conn.close()
    v = S.variacion_por_cesta()["C0"]
    assert v["d5"] == 20.0
    assert v["d20"] == 5.0


def test_sin_historico_suficiente_no_se_inventa_una_variacion(db):
    """Lo evidente sería comparar contra la fila más antigua que haya. Eso
    daría un número con pinta de real calculado sobre una ventana distinta de
    la que dice la columna."""
    conn = S._conn()
    _sembrar(conn, 7, lambda i: 60.0 + i)   # solo 7 sesiones
    conn.close()
    v = S.variacion_por_cesta()["C0"]
    assert v["d5"] is not None, "para 5 sesiones sí hay histórico"
    assert v["d20"] is None, "para 20 no, y no se aproxima con lo que haya"


def test_una_cesta_nueva_no_arrastra_la_variacion_de_otra(db):
    conn = S._conn()
    _sembrar(conn, 10, lambda i: 60.0)
    # Una cesta que solo existe hoy
    conn.execute("INSERT INTO snapshot_tematico (fecha,cesta,avg_score,avg_momentum,basket,breadth) VALUES ('2026-08-14','NUEVA',80.0,40,10,80.0)")
    conn.commit(); conn.close()
    assert S.variacion_por_cesta()["NUEVA"]["d5"] is None


def test_sin_datos_devuelve_vacio_sin_excepcion(db):
    assert S.variacion_por_cesta() == {}


# ── 4. Persistencia: cuanto LLEVA en cabeza ─────────────────────────────────

def _sembrar_serie(conn, cesta, amplitudes):
    """amplitudes[0] es la sesión MÁS RECIENTE."""
    base = date(2026, 8, 14)
    for i, a in enumerate(amplitudes):
        if a is None:
            continue
        f = (base - timedelta(days=i)).strftime("%Y-%m-%d")
        conn.execute("INSERT OR REPLACE INTO snapshot_tematico "
                     "(fecha,cesta,avg_score,avg_momentum,basket,breadth) VALUES (?,?,?,?,?,?)",
                     (f, cesta, 50.0, 40, 10, a))
    conn.commit()


def test_la_racha_cuenta_sesiones_seguidas_desde_hoy(db):
    conn = S._conn()
    # 4 seguidas por encima de 40, y antes por debajo
    _sembrar_serie(conn, "C0", [70, 65, 60, 55, 20, 80, 90])
    conn.close()
    assert S.persistencia_por_cesta()["C0"]["racha"] == 4


def test_una_cesta_que_no_esta_en_cabeza_tiene_racha_cero(db):
    conn = S._conn()
    _sembrar_serie(conn, "C0", [10, 70, 70, 70, 70, 70])
    conn.close()
    p = S.persistencia_por_cesta()["C0"]
    assert p["racha"] == 0, "hoy no está: la racha se rompió"
    assert p["en_ventana"] == 5, "pero sí estuvo en cinco de las seis"


def test_sin_historico_suficiente_no_se_inventa_una_racha(db):
    """Una racha de 2 sobre 2 sesiones no dice nada, y enseñar «2» invitaría a
    leerla como si dijera algo."""
    conn = S._conn()
    _sembrar_serie(conn, "C0", [70, 70])
    conn.close()
    assert S.persistencia_por_cesta()["C0"]["racha"] is None


def test_un_hueco_rompe_la_racha_no_la_encadena(db):
    """Se recorre la lista de SESIONES, no las filas de la cesta. Si se
    recorrieran las filas, una cesta que faltó un día se saltaría esa sesión y
    encadenaría una racha que en realidad se rompió."""
    conn = S._conn()
    _sembrar_serie(conn, "OTRA", [50, 50, 50, 50, 50, 50])   # marca las 6 sesiones
    _sembrar_serie(conn, "C0",   [70, 70, None, 70, 70, 70])  # falta la 3ª
    conn.close()
    assert S.persistencia_por_cesta()["C0"]["racha"] == 2


def test_la_ventana_dice_sobre_cuantas_sesiones_se_ha_mirado(db):
    """Mientras el histórico se llena, un «8» a secas se leería como 8 de 30
    cuando puede ser 8 de 10."""
    conn = S._conn()
    _sembrar_serie(conn, "C0", [70, 70, 10, 70, 10, 70, 70, 10])
    conn.close()
    p = S.persistencia_por_cesta()["C0"]
    assert p["en_ventana"] == 5
    assert p["ventana_real"] == 8, "8 sesiones de histórico, no 30"


def test_la_serie_va_de_la_mas_antigua_a_la_mas_reciente(db):
    """La minigráfica se dibuja de izquierda a derecha: invertido, mostraría la
    tendencia al revés -- una caída se vería como una subida."""
    conn = S._conn()
    _sembrar_serie(conn, "C0", [90, 60, 30])   # hoy 90, antes 60, antes 30
    conn.close()
    assert S.persistencia_por_cesta()["C0"]["serie"] == [30.0, 60.0, 90.0]


def test_una_serie_demasiado_corta_no_se_dibuja(db):
    conn = S._conn()
    _sembrar_serie(conn, "C0", [90, 60])
    conn.close()
    assert S.persistencia_por_cesta()["C0"]["serie"] is None


def test_sin_datos_devuelve_vacio(db):
    assert S.persistencia_por_cesta() == {}
