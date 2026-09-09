"""
El umbral rebajado para la cartera no se activó NUNCA: 470 señales, cero por debajo de 100.000.

EL CASO, Options Flow #31, remedido el 09/09/2026. `MIN_PREMIUM_CARTERA =
25_000` se puso para que las small caps de la cartera pudieran aparecer pese al
corte general de 100.000. La medición del 18/08 decía que no había hecho
aparecer ninguna, pero salía de un escaneo en premarket con 19 registros — poca
muestra para cerrar nada.

Con la base entera, 470 señales guardadas:

    prima < 25.000           0 señales
    25.000 – 100.000         0 señales
    100.000 – 500.000       87 señales
    > 500.000              383 señales

**Ni una sola por debajo de 100.000.** El umbral rebajado es código muerto que
además promete una capacidad que el módulo no tiene.

LA RAZÓN ES EL ORDEN DE LOS FILTROS, y es estructural, no de muestra:

    if vol < MIN_VOLUME or oi < MIN_OI or price_o < 0.10: continue   # corta aquí
    premium = vol * price_o * 100
    if premium < min_premium: continue                               # el rebajado, después

Una posición ilíquida se descarta mucho antes de llegar al umbral que se rebajó
para ella.

LA DECISIÓN — y el hallazgo la planteaba como decisión, no como arreglo. Se
podían bajar también `MIN_VOLUME` y `MIN_OI` para los tickers de cartera. **No
se hace**: `MIN_VOLUME` subió de 10 a 200 precisamente porque 10 metía ruido
(muy por debajo del estándar; Barchart usa 500), y `MIN_OI` existe porque un
contrato con OI=5 y volumen 20 no dice nada de la intención de nadie. Bajarlos
para un subconjunto deshace un arreglo deliberado. Y una «actividad inusual»
sobre 20 contratos no es accionable aunque se pinte.

LO QUE SÍ SE HACE ES DECIRLO. Un ticker cuyo `oi_max` no llega a `MIN_OI` no
puede generar una señal jamás. Que la pantalla diga cuántas de tus posiciones
están en ese caso convierte un silencio ambiguo —«no hay flujo en mi small
cap»— en un dato: «esa posición no puede aparecer aquí». Es la diferencia entre
no saber y saber que no se sabe.

Uso:
    cd backend
    python -m pytest tests/test_options_cobertura_cartera.py -v
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.options_service import (  # noqa: E402
    MIN_OI, MIN_PREMIUM_CARTERA, cobertura_de_cartera)

OPTIONS_JS = os.path.join(os.path.dirname(__file__), "..", "..",
                          "frontend", "pages", "options.js")


def _r(ticker, oi_max, ok=True):
    return {"ticker": ticker, "ok": ok, "oi_max": oi_max}


# ── Quién puede aparecer y quién no ──────────────────────────────────────────

def test_separa_las_liquidas_de_las_que_no_llegan():
    """EL test. `oi_max` por debajo de `MIN_OI` significa que ese ticker no
    puede producir una señal ningún día."""
    c = cobertura_de_cartera(
        [_r("AAPL", 50_000), _r("NVDA", 30_000), _r("SMALL", 12), _r("OTRA", 0)],
        {"AAPL", "NVDA", "SMALL", "OTRA"})
    assert c["total"] == 4 and c["visibles"] == 2
    assert c["invisibles"] == ["OTRA", "SMALL"]


def test_el_limite_es_MIN_OI_exacto():
    """Justo en el umbral SÍ pasa: el filtro del escaneo es `oi < MIN_OI`."""
    c = cobertura_de_cartera([_r("JUSTO", MIN_OI), _r("UNO_MENOS", MIN_OI - 1)],
                             {"JUSTO", "UNO_MENOS"})
    assert c["visibles"] == 1 and c["invisibles"] == ["UNO_MENOS"]


def test_un_ticker_sin_cadena_NO_cuenta_como_invisible():
    """No poder leer la cadena es otro problema —el del muro de Yahoo— y ya
    tiene su propio aviso. Mezclarlos haría que un día de rate limit pareciera
    una cartera ilíquida."""
    c = cobertura_de_cartera([_r("AAPL", 50_000), {"ticker": "FALLO", "ok": False}],
                             {"AAPL", "FALLO"})
    assert c["total"] == 1 and c["invisibles"] == []


def test_sin_cartera_no_se_inventa_un_bloque():
    """Sin posiciones no hay nada que decir, y un «de tus 0 posiciones» sería
    ruido en pantalla."""
    assert cobertura_de_cartera([_r("AAPL", 50_000)], set())["total"] == 0


def test_solo_mira_los_tickers_de_CARTERA():
    """El escaneo cubre ~579 valores. Si contara todos, el número no diría nada
    del usuario."""
    c = cobertura_de_cartera([_r("AAPL", 50_000), _r("AJENA", 5)], {"AAPL"})
    assert c["total"] == 1 and c["visibles"] == 1


def test_los_invisibles_van_ORDENADOS_y_por_nombre():
    """Se pintan en pantalla: un orden estable evita que la lista baile entre
    escaneos y parezca que ha cambiado algo."""
    # DIEZ tickers, no tres. Con tres, el orden en que Python recorre un `set`
    # coincidia por casualidad con el alfabetico y el sabotaje de quitar
    # `sorted()` se escapaba -- el test pasaba sin comprobar nada.
    nombres = ["ZZZ", "AAA", "MMM", "QQQ", "BBB", "YYY", "CCC", "NNN", "DDD", "XXX"]
    c = cobertura_de_cartera([_r(n, 1) for n in nombres], set(nombres))
    assert c["invisibles"] == sorted(nombres), c["invisibles"]


# ── Que llegue al escaneo y a la pantalla ────────────────────────────────────

def test_el_escaneo_PUBLICA_la_cobertura():
    """Calcularlo no sirve de nada si no sale del backend."""
    import inspect
    import services.options_service as O
    fuente = inspect.getsource(O.scan_options_flow) if hasattr(O, "scan_options_flow") else ""
    if not fuente:
        fuente = io.open(O.__file__, encoding="utf-8").read()
    assert '"cobertura_cartera": cobertura_de_cartera(' in fuente, (
        "el escaneo no publica la cobertura: la pantalla no puede decir nada")


def test_la_pantalla_lo_DICE():
    js = io.open(OPTIONS_JS, encoding="utf-8").read()
    assert "data.cobertura_cartera" in js
    assert "carteraTxt" in js
    i = js.index("return fechaDatos")
    assert "carteraTxt" in js[i:i + 200], (
        "se construye el bloque pero no se concatena en la salida")


def test_la_pantalla_explica_POR_QUE_no_aparecen():
    """«No van a salir» a secas se lee como un fallo. Lo que evita la confusión
    es la causa: no es que no haya actividad, es que no llegan al mínimo."""
    js = io.open(OPTIONS_JS, encoding="utf-8").read()
    i = js.index("let carteraTxt")
    bloque = js[i:i + 1800]
    assert "no es que no haya actividad" in bloque
    assert "contratos abiertos" in bloque


def test_no_se_bajan_los_minimos_de_liquidez():
    """La decisión que se tomó, atada. Bajarlos deshace el arreglo que subió
    `MIN_VOLUME` de 10 a 200 por meter ruido, y mete de vuelta contratos sobre
    los que no se puede leer ninguna intención."""
    import services.options_service as O
    assert O.MIN_VOLUME >= 200, (
        f"MIN_VOLUME ha bajado a {O.MIN_VOLUME}: vuelve el ruido que el 200 quitó")
    assert O.MIN_OI >= 100


def test_el_umbral_rebajado_sigue_documentado_como_lo_que_es():
    """No se borra —si algún día una posición líquida trae una prima entre
    25.000 y 100.000, ahí está— pero no puede volver a leerse como si cubriera
    las small caps, que es lo que hizo creer durante un mes."""
    assert MIN_PREMIUM_CARTERA == 25_000
    import inspect
    import services.options_service as O
    doc = inspect.getdoc(O.cobertura_de_cartera) or ""
    # LA AFIRMACION, no solo el numero suelto. Mi primera version pedia que
    # apareciera "470" y el sabotaje de borrar la conclusion se escapaba,
    # porque el numero seguia estando unas lineas mas arriba.
    assert "470" in doc, "falta el tamano de la muestra"
    assert "MIN_PREMIUM_CARTERA" in doc, "no se nombra el umbral del que se habla"
    # LA FRASE ENTERA, normalizando espacios. Buscar "100.000" y "ni una" por
    # separado no valia: "100.000" sale TRES veces en el docstring, asi que
    # borrar la conclusion dejaba las dos palabras vivas en otras frases y el
    # sabotaje se escapaba.
    plano = " ".join(doc.split())
    assert "ni una sola baja de 100.000 de prima" in plano, (
        "falta la conclusion medida --ninguna senal baja de 100.000--, que es lo "
        "que impide volver a leer ese umbral como si cubriera las small caps")
