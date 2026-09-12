"""
Dos días seguidos el briefing llamó «jueves» a una sesión que era viernes.

EL CASO. El prompt daba la fecha desnuda —`cierre del 2026-09-04`— y el modelo
tenía que deducir el día de la semana. Lo dedujo mal dos veces:

    07/09  «Los mercados cerraron el JUEVES con una divergencia clara...»
    08/09  «Tecnología (XLK) subió un 0,70% en el cierre del JUEVES»
           «Solo el 35,0% de las acciones del S&P subieron en la sesión del JUEVES»

Los datos de los dos días eran del **viernes 4 de septiembre**.

Y NO ES COSMÉTICO. El jueves 3 la amplitud del S&P fue **337 avances / 159
descensos — un 67,9% al alza**. El viernes 4 fue **174 / 323, un 35,0%**. Casi
lo contrario. Atribuir la foto de un día a otro cambia lo que el briefing dice
del mercado, no solo cómo lo dice.

EL ARREGLO NO ES UNA REGLA, ES ARITMÉTICA. Traducir una fecha a día de la
semana no requiere criterio: se hace aquí y se le da hecho. Cuesta **4 fichas**
y evita un error de dos días — mucho más barato que cualquier instrucción que
se lo pida, en un prompt que lleva semanas en modo «mínimo».

DE PASO, LA OTRA MITAD DEL MISMO PROBLEMA. La etiqueta decía «cierre del
anterior» sin distinguir qué datos son de ese cierre y cuáles de hoy — y el
briefing del 08/09 usó la subida del petróleo de HOY para explicar el cierre
del viernes («Esto explica por qué el S&P 500 cerró el 4 de septiembre [...]
cayendo un 0,38%»), una causa cuatro días posterior a su efecto. Ahora la
etiqueta dice qué bloque es de cuándo.

Uso:
    cd backend
    python -m pytest tests/test_briefing_dia_semana.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _prompt(sesion):
    return D.build_prompt({"date": "2026-09-08", "time": "11:49", "sesion": sesion},
                          [], [], [], {}, [], [], [])


# ── El día de la semana, dado hecho ──────────────────────────────────────────

def test_el_4_de_septiembre_de_2026_es_VIERNES():
    """EL test. El modelo escribió «jueves» dos días seguidos."""
    assert D.con_dia_semana("2026-09-04") == "2026-09-04 (viernes)"


def test_y_el_3_es_jueves():
    """Que la función no diga «viernes» siempre."""
    assert D.con_dia_semana("2026-09-03") == "2026-09-03 (jueves)"
    assert D.con_dia_semana("2026-09-07") == "2026-09-07 (lunes)"


def test_una_fecha_ilegible_no_revienta_el_briefing():
    """Un formato inesperado no puede costar la mañana entera: se devuelve lo
    que haya y el prompt sigue siendo válido."""
    assert D.con_dia_semana("") == ""
    assert D.con_dia_semana(None) == ""
    assert D.con_dia_semana("no es una fecha") == "no es una fecha"


def test_cuesta_lo_que_dice_que_cuesta():
    """Este prompt lleva semanas sin caber. Si el día de la semana costara 40
    fichas, la decisión sería otra."""
    assert D.estimar_tokens(" (viernes)") <= 6


# ── Llega al prompt que se envía ─────────────────────────────────────────────

def test_la_etiqueta_de_sesion_CERRADA_lleva_el_dia():
    p = _prompt({"fecha": "2026-09-04", "en_curso": False})
    assert "2026-09-04 (viernes)" in p, (
        "el prompt sigue dando la fecha desnuda: el modelo tiene que deducir el "
        "día de la semana y ya lo ha hecho mal dos veces")


def test_la_etiqueta_de_sesion_EN_CURSO_tambien():
    p = _prompt({"fecha": "2026-09-08", "en_curso": True, "hora_et": "11:30"})
    assert "2026-09-08 (martes)" in p


def test_se_dice_que_hay_que_citarla_por_ESE_dia():
    p = _prompt({"fecha": "2026-09-04", "en_curso": False})
    assert "no por hoy" in p


# ── La causa cuatro días posterior a su efecto ───────────────────────────────

def test_se_separa_lo_que_es_del_CIERRE_de_lo_que_es_de_HOY():
    """El briefing del 08/09 explicó el cierre del viernes con la subida del
    petróleo del martes, y se arregló con una FRASE: «Índices, sectores y
    amplitud son el cierre; materias primas, futuros y divisas SÍ son de hoy».

    El 10/09 esa frase fue falsa dos veces. El VIX es un índice y su barra era
    del jueves en curso; la amplitud era del martes. El briefing publicó «el VIX
    sube un 1,03%» (el miércoles subió +4,71%) y «el dólar sube… refugio» (el
    miércoles BAJÓ). Ahora el día de cada fila sale de la fecha de SU barra, y
    este test lo comprueba con el caso real: dos grupos de fechas."""
    barras = {"SPX": ("2026-09-08", "2026-09-09"), "VIX": ("2026-09-09", "2026-09-10"),
              "DXY": ("2026-09-09", "2026-09-10")}
    md = {"date": "2026-09-10", "time": "11:54", "barras": barras,
          "sesion": {"fecha": "2026-09-09", "en_curso": False, "hora_et": "07:54"},
          "SPX": {"price": 7636.36, "chg_pct": -0.48, "prev": 7673.52},
          "VIX": {"price": 16.63, "chg_pct": 1.03, "prev": 16.46,
                  "en_sesion": {"desde": "2026-09-08", "prev": 15.72, "cierre": 16.46, "chg_pct": 4.71}},
          "DXY": {"price": 98.91, "chg_pct": 0.14, "prev": 98.77,
                  "en_sesion": {"desde": "2026-09-08", "prev": 98.84, "cierre": 98.77, "chg_pct": -0.07}}}
    p = D.build_prompt(md, [], [], [], {}, [], [], [])
    # La fecha de la sesion la da la linea de estado; el bloque remite a ella.
    assert "la del 2026-09-09 (miercoles)" in p
    cierre = p.index("CIERRE DE ESA SESION")
    hoy = p.index("EN CURSO HOY 2026-09-10 (jueves)")
    # El S&P va con el cierre; el VIX y el dólar, con hoy -- y con lo que
    # hicieron EN la sesión, que es la que cuenta el briefing.
    assert cierre < p.index("- S&P 500:") < hoy
    assert p.index("- VIX:") > hoy and p.index("- Dólar Index (DXY):") > hoy
    # Desde el 12/09 (Newsfeed #63) el cierre va DELANTE y con su nombre, para
    # que no se pueda citar el precio de ahora como si fuera el cierre.
    assert "- VIX: CIERRE 16.46 (▲4.71%) · ahora 16.63" in p, \
        "falta lo que hizo el VIX el miércoles, y por delante"
    assert "- Dólar Index (DXY): CIERRE 98.77 (▼0.07%) · ahora 98.91" in p, \
        "falta que el dólar BAJÓ el miércoles, y por delante"
    assert "CIERRE = el del 2026-09-09 (miercoles)" in p, "la cabecera no dice de qué día"


def test_la_linea_de_estado_ya_no_afirma_de_que_dia_es_cada_cosa():
    """La frase general era la que se contradecía con la etiqueta correcta de
    la amplitud dos líneas más abajo, y el modelo creyó a la frase general."""
    p = _prompt({"fecha": "2026-09-04", "en_curso": False})
    assert "Indices, sectores y amplitud son el cierre" not in p
    assert "SI son de hoy" not in p
    assert "Cada bloque de abajo dice de que dia es su dato" in p


def test_la_sesion_EN_CURSO_sigue_prohibiendo_decir_que_cerro():
    """Lo que arregló el #36 no se puede perder al reescribir la etiqueta."""
    p = _prompt({"fecha": "2026-09-08", "en_curso": True, "hora_et": "11:30"})
    assert "NO son cierres" in p and "INTRADIA" in p
