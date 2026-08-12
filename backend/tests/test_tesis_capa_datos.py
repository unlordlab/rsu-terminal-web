"""
Test de la capa de datos de Tesis (12/08/2026, hallazgos #6, #7, #8 y #9 de
la auditoría de Tesis + Admin).

Los cuatro son del mismo tipo: nada visiblemente roto, pero el módulo hace
más trabajo del necesario y devuelve resultados que no son los que el usuario
pidió.

  #6  `get_tesis_list` traía TODAS las filas aprobadas con `SELECT *` y luego
      cortaba la página en Python. `SELECT *` incluye `contenido`, que es el
      markdown ENTERO de la tesis: con 120 tesis de tamaño realista eso son
      ~2,2 MB movidos de disco en cada carga para pintar 9 tarjetas que solo
      usan 300 caracteres del resumen.
  #7  `datetime.now()` en el VPS es UTC. Una tesis creada a las 00:30 de
      Madrid se guardaba con la fecha del día anterior.
  #8  La búsqueda se interpolaba en LIKE sin escapar comodines: buscar `%`
      devolvía las 120 tesis como si no hubieras filtrado (medido).
  #9  Cada apertura de tesis podía disparar una descarga de yfinance nueva,
      con una cuota que comparte toda la terminal.

Uso:
    cd backend
    python -m pytest tests/test_tesis_capa_datos.py -v
"""
import os
import sqlite3
import sys
import time
from datetime import date, datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.tesis_service as T  # noqa: E402


@pytest.fixture()
def db(tmp_path):
    """Base temporal con tesis aprobadas. `contenido` va largo a propósito:
    es lo que hace caro el `SELECT *` que este fichero fija."""
    ruta = str(tmp_path / "tesis_test.db")
    conn = sqlite3.connect(ruta)
    conn.execute("""CREATE TABLE tesis (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT NOT NULL, nombre TEXT,
        fecha TEXT NOT NULL, rating TEXT NOT NULL DEFAULT 'HOLD', sector TEXT,
        autor TEXT, titulo TEXT, resumen TEXT, imagen TEXT, riesgo TEXT,
        precio_objetivo REAL, contenido TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'pending', fuente TEXT NOT NULL DEFAULT 'manual',
        criterio TEXT, doc_url TEXT, created_at REAL NOT NULL)""")
    filas = [(f"TK{i:03d}", f"Empresa {i}", f"2026-01-{(i % 28) + 1:02d}",
              ["BUY", "HOLD", "SELL"][i % 3], "Tech", "RSU", f"Titulo {i}",
              "Resumen. " * 50, "", "MEDIO", 100.0 + i, "X" * 5000,
              "approved", "manual", "", "", time.time())
             for i in range(25)]
    # Una sin aprobar: no debe aparecer nunca
    filas.append(("ZZZ", "Pendiente", "2026-01-01", "BUY", "Tech", "RSU", "T",
                  "R", "", "MEDIO", 1.0, "X", "pending", "manual", "", "", time.time()))
    conn.executemany("""INSERT INTO tesis (ticker,nombre,fecha,rating,sector,autor,titulo,
        resumen,imagen,riesgo,precio_objetivo,contenido,status,fuente,criterio,doc_url,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", filas)
    conn.commit()
    conn.close()
    with patch.object(T, "DB_PATH", ruta):
        yield ruta


# ── #6: paginar en SQL, y sin arrastrar el markdown entero ───────────────────

def test_la_tarjeta_no_arrastra_el_markdown_de_la_tesis():
    """Lo que hacía cara la lista no era el número de filas, era el payload:
    `SELECT *` incluye `contenido`, el texto íntegro de cada tesis, para
    pintar una tarjeta que solo enseña 300 caracteres del resumen."""
    assert "contenido" not in T._COLS_LISTA
    for col in ("ticker", "nombre", "fecha", "rating", "resumen", "titulo"):
        assert col in T._COLS_LISTA, f"la tarjeta necesita {col}"


def test_la_consulta_pagina_en_sql(db):
    """Comprobación de verdad, no por inspección del código: se cuenta cuántas
    filas devuelve SQLite. Con la versión anterior eran las 25 (fetchall y
    corte en Python); ahora tienen que ser las 9 de la página."""
    filas_leidas = []
    real = T._conn

    class _Cursor:
        """Devuelve las filas ya materializadas: hay que consumir el cursor
        para poder contarlas, así que se guardan y se sirven desde aquí."""
        def __init__(self, filas): self._f = filas
        def fetchall(self): return self._f
        def fetchone(self): return self._f[0] if self._f else None

    class _ConnEspia:
        def __init__(self, c): self._c = c
        def execute(self, sql, *a, **kw):
            filas = self._c.execute(sql, *a, **kw).fetchall()
            if " FROM tesis " in f" {sql} ":
                filas_leidas.append((sql, len(filas)))
            return _Cursor(filas)
        def close(self): self._c.close()

    with patch.object(T, "_conn", lambda: _ConnEspia(real())):
        T.get_tesis_list(page=1, per_page=9)

    lecturas = [n for sql, n in filas_leidas
                if "COUNT(" not in sql.upper() and "DISTINCT" not in sql.upper()]
    assert lecturas == [9], f"se leyeron {lecturas} filas, deberían ser las 9 de la página"


def test_el_total_cuenta_todas_aunque_la_pagina_muestre_nueve(db):
    r = T.get_tesis_list(page=1, per_page=9)
    assert r["total"] == 25, "el total es del conjunto, no de la página"
    assert len(r["items"]) == 9
    assert r["total_pages"] == 3


def test_las_paginas_no_se_solapan_ni_se_dejan_nada(db):
    vistos = []
    for p in (1, 2, 3):
        vistos += [i["id"] for i in T.get_tesis_list(page=p, per_page=9)["items"]]
    assert len(vistos) == 25
    assert len(set(vistos)) == 25, "una tesis no puede salir en dos páginas"


def test_una_pagina_fuera_de_rango_cae_en_la_ultima(db):
    r = T.get_tesis_list(page=99, per_page=9)
    assert r["page"] == 3 and len(r["items"]) == 7


def test_las_no_aprobadas_no_salen(db):
    ids = [i["ticker"] for i in T.get_tesis_list(per_page=100)["items"]]
    assert "ZZZ" not in ids


# ── #8: los comodines del buscador ───────────────────────────────────────────

def test_buscar_un_porcentaje_no_devuelve_la_lista_entera(db):
    """El fallo medido: `%` es «cualquier cosa» en LIKE, así que la búsqueda
    se anulaba a sí misma y el usuario veía las 25 creyendo haber filtrado."""
    assert T.get_tesis_list(search="%")["total"] == 0


def test_el_guion_bajo_tampoco_es_un_comodin(db):
    assert T.get_tesis_list(search="_")["total"] == 0
    assert T.get_tesis_list(search="TK00_")["total"] == 0, "TK00_ no debe casar con TK005"


def test_la_barra_invertida_no_rompe_la_busqueda(db):
    """Se escapa con '\\', así que el propio carácter de escape hay que
    escaparlo primero o una búsqueda que lo contenga da error de SQL."""
    assert T.get_tesis_list(search="\\")["total"] == 0


def test_una_busqueda_normal_sigue_funcionando(db):
    assert T.get_tesis_list(search="TK005")["total"] == 1
    assert T.get_tesis_list(search="tk005")["total"] == 1, "el ticker se busca en mayúsculas"
    assert T.get_tesis_list(search="Empresa 1")["total"] > 1


# ── #7: la fecha es la de Madrid, no la del contenedor ───────────────────────

def test_la_fecha_de_hoy_es_la_de_madrid():
    """Comparar contra `datetime.now(Madrid).date()` NO vale como test: esta
    máquina ya está en Madrid, así que pasaría igual con `datetime.now()` a
    secas y el fallo solo aparecería en el VPS, que corre en UTC. Hay que
    congelar el reloj en un instante donde las dos zonas estén en días
    distintos: 23:30 UTC del 11 son las 01:30 del 12 en Madrid (CEST, +2)."""
    from datetime import timezone as _tz

    instante = datetime(2026, 8, 11, 23, 30, tzinfo=_tz.utc)

    class _RelojUTC(datetime):
        @classmethod
        def now(cls, tz=None):
            # Sin tz devuelve la hora del contenedor (UTC), que es justo lo
            # que hacía el código viejo.
            return instante.replace(tzinfo=None) if tz is None else instante.astimezone(tz)

    with patch.object(T, "datetime", _RelojUTC):
        assert T._hoy_madrid() == date(2026, 8, 12), \
            "con el reloj del contenedor saldría el día 11, un día menos"


def test_es_nuevo_usa_esa_misma_fecha():
    hoy = T._hoy_madrid()
    assert T._es_nuevo(hoy.strftime("%Y-%m-%d")) is True
    assert T._es_nuevo((hoy - timedelta(days=7)).strftime("%Y-%m-%d")) is True
    assert T._es_nuevo((hoy - timedelta(days=8)).strftime("%Y-%m-%d")) is False


def test_una_fecha_ilegible_no_revienta():
    assert T._es_nuevo("no soy una fecha") is False
    assert T._es_nuevo("") is False


# ── #9: el precio de la tesis se cachea ──────────────────────────────────────

def test_abrir_la_misma_tesis_cinco_veces_baja_el_precio_una_vez(db):
    """La cuota de Yahoo la comparte toda la terminal. Un `upside` contra un
    precio objetivo a semanas vista no necesita frescura de un minuto."""
    from services.cache import cache
    import services.cartera_service as C
    cache.delete("tesis:precio:TK005")
    llamadas = []

    def _fake(tickers):
        llamadas.append(tuple(tickers))
        return {tickers[0]: {"price": 123.45}}

    try:
        with patch.object(C, "fetch_live_prices", side_effect=_fake):
            for _ in range(5):
                r = T.get_tesis_detail("TK005")
        assert len(llamadas) == 1, f"bajó el precio {len(llamadas)} veces"
        assert r["precio_actual"] == 123.45
    finally:
        cache.delete("tesis:precio:TK005")


def test_un_fallo_de_red_no_se_cachea(db):
    """Guardar el fallo dejaría la tesis sin upside quince minutos. Se
    reintenta en la siguiente apertura."""
    from services.cache import cache
    import services.cartera_service as C
    cache.delete("tesis:precio:TK006")
    llamadas = []

    def _sin_precio(tickers):
        llamadas.append(1)
        return {}

    try:
        with patch.object(C, "fetch_live_prices", side_effect=_sin_precio):
            for _ in range(3):
                r = T.get_tesis_detail("TK006")
        assert len(llamadas) == 3, "sin precio real no hay nada que cachear"
        assert r["precio_actual"] is None
        assert r["upside"] is None, "sin precio no se inventa un upside"
    finally:
        cache.delete("tesis:precio:TK006")
