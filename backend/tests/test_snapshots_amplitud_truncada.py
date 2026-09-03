"""
Una fila de amplitud guardada desde un escaneo roto era permanente.

EL CASO, 02/09/2026. El escaneo nocturno publicó esa sesión con 24 valores de
~2.400 (Scanner #22) y `snapshot_mercado` la guardó como una sesión normal:
20 avances contra 4 descensos, en una tabla que alimenta cualquier lectura
histórica de amplitud.

POR QUÉ NO SE ARREGLABA SOLA. La tabla es append-only por diseño: cada
sub-función comprueba «¿ya hay fila para esta fecha?» y, si la hay, no hace
nada — y encima el INSERT es `OR IGNORE`. Las dos cosas juntas significan que
una ejecución posterior con datos buenos **no toca** la fila mala. Se queda.

POR QUÉ SÍ SE PUEDE REPARAR, que es lo que cambia el plan: el historial de
amplitud se **recalcula desde cero cada noche** sobre 150 sesiones (ver
`_compute_breadth_history`), así que el Gist se cura solo en cuanto la descarga
vuelve completa. El 02/09 estaba truncado esa noche y a la siguiente ya no. No
hace falta borrar a mano: hace falta copiar el valor bueno encima del malo.

QUÉ NO ES ESTO. No es reescribir historia. Se toca únicamente una fila cuya
cobertura es una fracción de la mediana -- demostrablemente rota-- y solo
cuando el Gist trae para esa misma fecha una sesión completa con la que
sustituirla. Y se dice por el log.

Uso:
    cd backend
    python -m pytest tests/test_snapshots_amplitud_truncada.py -v
"""
import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.snapshots_service as S  # noqa: E402


def _sesion(fecha, adv, dec, total=None):
    return {"date": fecha, "advances": adv, "declines": dec,
            "pct_above_sma50": 46.6, "new_highs": 24, "new_lows": 43,
            "total_valores": total if total is not None else adv + dec}


# Once sesiones normales y la del caso, con los números reales.
NORMALES = [_sesion(f"2026-08-{d:02d}", 1200, 1180) for d in range(17, 29)]
ROTA = _sesion("2026-09-02", 20, 4)


@pytest.fixture
def conn():
    ruta = os.path.join(tempfile.mkdtemp(), "snap.db")
    c = sqlite3.connect(ruta)
    c.execute("CREATE TABLE snapshot_mercado (fecha TEXT PRIMARY KEY, "
              "advances INTEGER, declines INTEGER, pct_above_sma50 REAL, "
              "new_highs INTEGER, new_lows INTEGER)")
    c.commit()
    yield c
    c.close()


def _guardada(conn, fecha):
    f = conn.execute("SELECT advances, declines FROM snapshot_mercado WHERE fecha=?",
                     (fecha,)).fetchone()
    return f


# ── La reparación ────────────────────────────────────────────────────────────

def test_la_fila_del_02_09_se_corrige_cuando_el_Gist_ya_la_trae_bien(conn):
    """EL test. La noche siguiente el escaneo recalcula los 150 días y esa
    sesión vuelve completa; entonces se puede copiar encima."""
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-09-02',20,4,46.6,24,43)")
    conn.commit()
    buena = _sesion("2026-09-02", 681, 1707)
    S._corregir_amplitud_truncada(conn, NORMALES + [buena])
    assert _guardada(conn, "2026-09-02") == (681, 1707), (
        "la fila rota sigue ahí: el INSERT OR IGNORE no la reescribe y sin esto "
        "contamina cualquier lectura histórica de amplitud")


def test_una_fila_BUENA_no_se_toca(conn):
    """Lo que más importa de todo: esto no puede convertirse en un reescritor
    de historia. Solo se corrige lo demostrablemente roto."""
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-08-28',928,1444,60.0,80,22)")
    conn.commit()
    distinta = _sesion("2026-08-28", 111, 222)   # el Gist trae otra cosa
    S._corregir_amplitud_truncada(conn, NORMALES + [distinta])
    assert _guardada(conn, "2026-08-28") == (928, 1444), (
        "se ha sobrescrito una fila que no estaba rota")


def test_si_el_Gist_TAMBIEN_viene_roto_no_se_toca_nada(conn):
    """Copiar una sesión truncada encima de otra truncada no arregla nada y
    borraría la evidencia de que hubo un problema.

    OJO al montaje: la sesión rota del Gist trae valores DISTINTOS de los
    guardados (9/2 frente a 20/4). La primera versión de este test usaba los
    mismos en los dos sitios, así que copiar una encima de otra era
    indetectable y el sabotaje se le escapó."""
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-09-02',20,4,46.6,24,43)")
    conn.commit()
    otra_rota = _sesion("2026-09-02", 9, 2)
    S._corregir_amplitud_truncada(conn, NORMALES + [otra_rota])
    assert _guardada(conn, "2026-09-02") == (20, 4), (
        "se ha copiado una sesión truncada encima de otra: no arregla nada y "
        "borra la evidencia de que hubo un problema")


def test_no_se_inventan_filas_que_no_estaban(conn):
    """La reparación corrige, no rellena: una fecha sin fila se queda sin fila
    (la escribirá `_maybe_write_mercado` cuando toque, con todo lo demás)."""
    S._corregir_amplitud_truncada(conn, NORMALES + [_sesion("2026-09-02", 681, 1707)])
    assert _guardada(conn, "2026-09-02") is None


def test_sin_historial_no_hace_nada(conn):
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-09-02',20,4,46.6,24,43)")
    conn.commit()
    S._corregir_amplitud_truncada(conn, [])
    assert _guardada(conn, "2026-09-02") == (20, 4)


def test_corrige_TODAS_las_columnas_de_amplitud_no_solo_los_avances(conn):
    """new_highs y new_lows salen del mismo recuento crudo y venían igual de
    rotos; dejarlos sería arreglar la mitad."""
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-09-02',20,4,46.6,1,0)")
    conn.commit()
    buena = _sesion("2026-09-02", 681, 1707)
    buena.update({"new_highs": 24, "new_lows": 43, "pct_above_sma50": 50.8})
    S._corregir_amplitud_truncada(conn, NORMALES + [buena])
    f = conn.execute("SELECT new_highs, new_lows, pct_above_sma50 FROM "
                     "snapshot_mercado WHERE fecha='2026-09-02'").fetchone()
    assert f == (24, 43, 50.8)


def test_se_dice_por_el_log_lo_que_se_ha_cambiado(conn, capsys):
    """Una corrección silenciosa de datos guardados es indistinguible de una
    corrupción silenciosa."""
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-09-02',20,4,46.6,24,43)")
    conn.commit()
    S._corregir_amplitud_truncada(conn, NORMALES + [_sesion("2026-09-02", 681, 1707)])
    salida = capsys.readouterr().out
    assert "2026-09-02" in salida and "CORREGIDA" in salida
    assert "20/4" in salida and "681/1707" in salida, (
        "el log no dice el valor viejo y el nuevo, que es lo que permite "
        "auditar la corrección después")


# ── El guardián de entrada ───────────────────────────────────────────────────

def test_una_sesion_truncada_no_se_llega_a_guardar(conn):
    """Segunda línea: el escáner ya no las publica desde el 04/09, pero un Gist
    escrito por una versión anterior sí puede traerlas."""
    S._maybe_write_mercado(conn, "2026-09-02", ROTA, incompleto=True)
    assert _guardada(conn, "2026-09-02") is None, (
        "se ha guardado una sesión de un escaneo incompleto, y en esta tabla "
        "eso es permanente")


def test_el_flag_se_calcula_donde_estan_los_datos_para_calcularlo():
    """La primera versión del guardián miraba `breadth_row.get('escaneo_
    incompleto')` -- y esas filas vienen CRUDAS del Gist y nunca traen ese
    campo. Un guardián que no puede dispararse es peor que ninguno, porque da
    confianza falsa."""
    import inspect
    fuente = inspect.getsource(S.maybe_write_daily_snapshot)
    assert "cobertura_insuficiente(" in fuente, (
        "el flag de escaneo incompleto no se calcula en el punto de entrada: "
        "el guardián de _maybe_write_mercado nunca se dispararía")


def test_la_regla_es_la_MISMA_que_usan_el_escaner_y_el_briefing():
    """Una copia por consumidor es como se acaba con dos umbrales del mismo
    número contradiciéndose."""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
    import cobertura_amplitud
    assert S.cobertura_insuficiente is cobertura_amplitud.cobertura_insuficiente

def test_el_punto_de_entrada_llama_a_la_reparacion(conn, monkeypatch):
    """Que la función repare no sirve de nada si nadie la invoca. Se comprueba
    EJECUTANDO `maybe_write_daily_snapshot()` con el Gist y la base simulados,
    no mirando el fuente -- que es como se han escapado ya cuatro sabotajes
    esta semana."""
    conn.execute("INSERT INTO snapshot_mercado VALUES ('2026-09-02',20,4,46.6,24,43)")
    conn.commit()
    historial = NORMALES + [_sesion("2026-09-02", 681, 1707)]

    import services.scanner_service as SC
    monkeypatch.setattr(SC, "get_breadth_history", lambda: historial, raising=False)
    # `close` es de solo lectura en sqlite3.Connection, así que se pasa un
    # envoltorio: la función de producción cierra la conexión en su `finally` y
    # aquí hace falta seguir consultándola después.
    class _NoCierra:
        def __init__(self, c): self._c = c
        def __getattr__(self, n): return getattr(self._c, n)
        def close(self): pass
    monkeypatch.setattr(S, "_conn", lambda: _NoCierra(conn))
    for f in ("_maybe_write_mercado", "_maybe_write_ticker",
              "_maybe_write_cartera", "_maybe_write_tematico"):
        monkeypatch.setattr(S, f, lambda *a, **k: None)

    S.maybe_write_daily_snapshot()
    assert _guardada(conn, "2026-09-02") == (681, 1707), (
        "el punto de entrada no repara: la fila rota sobrevive a una ejecución "
        "con datos buenos")
