"""
¿Acierta el sesgo del briefing? Hasta el 25/08/2026, nadie lo había medido.

EL HUECO. El briefing cierra cada mañana con `SESGO: ALCISTA` o `BAJISTA`, lo
leen ~100 personas, y `bias_history.json` guardaba las últimas 14 fechas con su
sesgo... sin comprobar jamás si se cumplió. Es exactamente el mismo hueco que
se cerró en Options Flow el 21/08: un módulo que opina y no se mide.

POR QUÉ UN FICHERO NUEVO Y NO bias_history.json. Ese se poda a 14 días porque
es contexto narrativo para el prompt. Medir sobre una ventana que se poda es no
acumular muestra nunca -- misma lección que DATOS_IRREPRODUCIBLES_PLAN. El
seguimiento vive en `bias_tracking.json`, append-only.

LAS REGLAS, heredadas de lo aprendido midiendo Options Flow:
- NEUTRAL no se evalúa: no hay dirección que juzgar, y contarlo como fallo (o
  como acierto) sería inventar un resultado.
- Un día al que aún no le han pasado las sesiones del horizonte queda
  PENDIENTE, no cuenta como fallo.
- Nada se reescribe: un resultado ya calculado no cambia.
- El porcentaje viaja siempre con su `n` y con `suficiente`.

Uso:
    cd backend
    python -m pytest tests/test_briefing_sesgo.py -v
"""
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _cierres(precios, inicio="2026-08-03"):
    return pd.Series(precios, index=pd.bdate_range(start=inicio, periods=len(precios)), dtype=float)


def _hist(*pares):
    return [{"fecha": f, "sesgo": s} for f, s in pares]


SUBE = _cierres([100, 101, 102, 103, 104, 110, 110, 110])
BAJA = _cierres([100,  99,  98,  97,  96,  90,  90,  90])


# ── El veredicto ─────────────────────────────────────────────────────────────

def test_un_sesgo_alcista_acierta_si_el_indice_sube():
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "ALCISTA")), SUBE)
    assert t[0]["acierto_1d"] is True and t[0]["acierto_5d"] is True
    assert t[0]["ret_1d"] == 1.0


def test_un_sesgo_alcista_falla_si_el_indice_baja():
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "ALCISTA")), BAJA)
    assert t[0]["acierto_1d"] is False and t[0]["acierto_5d"] is False


def test_un_sesgo_bajista_acierta_si_el_indice_baja():
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "BAJISTA")), BAJA)
    assert t[0]["acierto_5d"] is True
    assert t[0]["ret_5d"] == -10.0


# ── Lo que no se puede juzgar ────────────────────────────────────────────────

def test_un_sesgo_NEUTRAL_no_se_evalua():
    """No hay dirección que juzgar. Contarlo como fallo hundiría el porcentaje
    y contarlo como acierto lo inflaría: las dos cosas serían inventadas."""
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "NEUTRAL")), SUBE)
    assert t[0].get("acierto_1d") is None
    r = D.resumen_sesgos(t)
    assert r["horizontes"]["1"]["n"] == 0
    assert r["neutrales"] == 1


def test_un_dia_sin_sesiones_suficientes_queda_pendiente():
    """No ha pasado el horizonte todavía: no es un fallo."""
    corta = _cierres([100, 101, 102])          # solo 2 sesiones después
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "ALCISTA")), corta)
    assert t[0]["acierto_1d"] is True
    assert t[0].get("acierto_5d") is None, "ha juzgado un horizonte que no se ha cumplido"
    assert D.resumen_sesgos(t)["pendientes"] == 1
    # Y tampoco vale rellenarlo con una ventana MAS CORTA bajo otro nombre: un
    # horizonte de 5 sesiones resuelto con 2 es otro horizonte disfrazado.
    extras = [k for k in t[0] if k.startswith(("ret_", "acierto_"))
              and k not in ("ret_1d", "ret_5d", "acierto_1d", "acierto_5d")]
    assert not extras, f"ha inventado horizontes intermedios: {extras}"


def test_sin_precios_no_se_inventa_un_veredicto():
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "ALCISTA")), None)
    assert t[0].get("acierto_1d") is None


# ── El acumulado ─────────────────────────────────────────────────────────────

def test_no_se_pierde_lo_ya_evaluado_ni_se_reescribe():
    """Append-only: el seguimiento crece, y un resultado ya calculado no cambia
    aunque el histórico de 14 días haya podado esa fecha."""
    # MAS DE 14 ENTRADAS a proposito: con dos, una poda a 14 dias no se nota y
    # el sabotaje de podar el seguimiento pasaba en verde.
    previo = [{"fecha": "2026-01-05", "sesgo": "ALCISTA", "ret_1d": 2.0, "acierto_1d": True}]
    previo += [{"fecha": f"2026-02-{d:02d}", "sesgo": "ALCISTA", "ret_1d": 0.5,
                "acierto_1d": True} for d in range(1, 21)]
    t = D.evaluar_sesgos(previo, _hist(("2026-08-03", "BAJISTA")), BAJA)
    assert len(t) == 22, f"se han perdido dias: quedan {len(t)} de 22"
    fechas = [x["fecha"] for x in t]
    assert "2026-01-05" in fechas, "se ha perdido un día ya evaluado al podarse el histórico"
    viejo = next(x for x in t if x["fecha"] == "2026-01-05")
    assert viejo["ret_1d"] == 2.0, "se ha reescrito un resultado ya calculado"


def test_una_muestra_corta_no_se_presenta_como_conclusion():
    """Un 100% sobre dos días no es un 100%."""
    t = D.evaluar_sesgos([], _hist(("2026-08-03", "ALCISTA")), SUBE)
    r = D.resumen_sesgos(t)
    assert r["horizontes"]["1"]["aciertos_pct"] == 100.0
    assert r["horizontes"]["1"]["suficiente"] is False
    assert D.MIN_MUESTRA_SESGO == 30


def test_el_seguimiento_vive_en_su_propio_fichero_sin_podar():
    """bias_history.json se poda a 14 días porque es contexto para el prompt.
    Medir sobre él sería no acumular muestra nunca."""
    assert D.BIAS_TRACKING_FILE != D.BIAS_HISTORY_FILE
    import inspect
    fuente = inspect.getsource(D.save_to_gist)
    assert "BIAS_TRACKING_FILE" in fuente, "el seguimiento no se guarda en el Gist"
    assert "evaluar_sesgos(" in fuente, "nadie evalúa los sesgos al guardar"


def test_la_pantalla_no_pinta_el_porcentaje_sin_muestra():
    """El backend manda `suficiente`; la pantalla tiene que respetarlo o
    volvemos a enseñar un 70% sacado de siete días."""
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "market.js")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    assert "sesgo_track" in fuente
    assert "b.suficiente" in fuente, (
        "la pantalla pinta el acierto sin comprobar si la muestra da para algo")
