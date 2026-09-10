"""
El Roadmap 2026 acertó su «caída de primavera» y la página no lo decía.

EL CASO, Páginas Contenido #9 y #10, 10/09/2026. El Roadmap es la previsión
personal del autor para 2026, escrita el 20/12/2025 (fecha que da él: en este
repositorio el texto aparece por primera vez el 12/06/2026, en la migración).
Su núcleo era una corrección del 8% al 15% en primavera y un rebote fuerte
después. Medido con cierres diarios de Yahoo Finance a 9/09/2026:

    S&P 500       −9,1%  (27/01 → 30/03)   rebote +20,4%   año +11,6%
    Nasdaq 100   −11,8%  (28/01 → 30/03)   rebote +28,2%   año +16,5%
    Russell 2000 −11,2%  (22/01 → 30/03)   rebote +21,0%   año +17,7%

Se cumplió en tamaño y en forma; el calendario se adelantó unas semanas. Y la
página seguía hablando en futuro de una primavera que ya había pasado.

LO QUE ATA ESTE FICHERO:
  - Que el texto ORIGINAL sigue intacto. Una previsión retocada después de
    conocer el resultado deja de valer como previsión.
  - Que la revisión lleva sus cifras, su fecha y la fecha en que se escribió.
  - Que el descargo está donde se lee la previsión (#10), y también en Tesis,
    que lleva rating y precio objetivo sobre valores concretos y no tenía
    ningún aviso en la página.

Las cifras son una foto fechada, no un dato vivo: no hay test que las
recalcule contra Yahoo, porque la suite corre sin red a propósito y esto no
cambia con el tiempo.

Uso:
    cd backend
    python -m pytest tests/test_roadmap_revision.py -v
"""
import io
import os
import re

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _js(nombre):
    return io.open(os.path.join(RAIZ, "frontend", "pages", nombre), encoding="utf-8").read()


ROADMAP = _js("roadmap.js")
TESIS = _js("tesis.js")


# ── El texto original, intacto ───────────────────────────────────────────────

ORIGINAL = [
    "Cuando pienso en 2026 no veo un año lineal.",
    "03 // LA CAÍDA DE PRIMAVERA: NÚCLEO TÁCTICO DEL AÑO",
    "No como posibilidad remota. Como elemento central del año.",
    "Correcciones del <b style=\"color:var(--color-accent)\">8% al 15%</b> en índices principales",
    "La primavera es mi momento de acumulación estratégica.",
    "Rebote fuerte tras la caída primaveral",
    "NO TEMO LA CAÍDA DE PRIMAVERA",
    "Fase 1: Inicio constructivo (enero–febrero)",
]


def test_el_texto_ORIGINAL_sigue_tal_cual():
    """EL test. La revisión se AÑADE; la previsión no se toca."""
    faltan = [f for f in ORIGINAL if f not in ROADMAP]
    assert not faltan, f"se ha retocado el texto original: {faltan}"


# ── La revisión ──────────────────────────────────────────────────────────────

def test_la_revision_existe_y_va_antes_de_las_secciones():
    assert "REVISIÓN · SEPTIEMBRE 2026 · LO QUE PASÓ" in ROADMAP
    assert "return header() + revision() + sections() + footer();" in ROADMAP


def test_lleva_la_fecha_en_que_se_ESCRIBIO_la_prevision():
    """Es lo que da valor al acierto: 3 meses y 10 días antes del suelo."""
    assert "const ESCRITO_EL = '20 de diciembre de 2025';" in ROADMAP
    assert "Texto original escrito el ' + ESCRITO_EL" in ROADMAP


def test_las_cifras_son_las_verificadas_el_10_09():
    """Si alguien toca una cifra, tiene que volver a medirla: este test la ata
    al valor comprobado contra Yahoo en la auditoría."""
    filas = re.findall(r"\['(S&P 500|Nasdaq 100|Russell 2000)',\s*'([^']+)',\s*'([^']+)',\s*'([^']+)',"
                       r"\s*'([^']+)',\s*'([^']+)'\]", ROADMAP)
    assert dict((f[0], f[1:]) for f in filas) == {
        "S&P 500":      ("−9,1%",  "27/01", "30/03", "+20,4%", "+11,6%"),
        "Nasdaq 100":   ("−11,8%", "28/01", "30/03", "+28,2%", "+16,5%"),
        "Russell 2000": ("−11,2%", "22/01", "30/03", "+21,0%", "+17,7%"),
    }
    assert "const REVISION_FECHA = '9 de septiembre de 2026';" in ROADMAP


def test_dice_tambien_lo_que_NO_salio_como_estaba_escrito():
    """Publicar solo los aciertos es vender humo. El calendario se adelantó."""
    assert "◐ El calendario:" in ROADMAP
    assert "duró solo enero" in ROADMAP


def test_la_seccion_de_la_caida_remite_a_la_revision():
    i = ROADMAP.index("03 // LA CAÍDA DE PRIMAVERA")
    assert "Revisión septiembre 2026: se cumplió" in ROADMAP[i:i + 600]


# ── El descargo donde se lee la previsión (#10) ──────────────────────────────

def _llamadas(js, funcion):
    codigo = "\n".join(l for l in js.splitlines() if not l.strip().startswith("//"))
    return len(re.findall(r"\b" + funcion + r"\(\)", codigo)) - len(re.findall(r"function " + funcion + r"\(\)", codigo))


def test_el_roadmap_enlaza_al_descargo_arriba_y_abajo():
    assert "Escenario personal, no recomendación de inversión" in ROADMAP
    assert "window.__navigate(\\'/disclaimer\\')" in ROADMAP
    assert _llamadas(ROADMAP, "avisoLegal") >= 2, "falta el aviso bajo el título o en el pie"


def test_tesis_tambien_lleva_el_descargo_en_la_lista_y_en_el_detalle():
    """Rating y precio objetivo sobre valores concretos, y hasta hoy ningún
    aviso en la página: solo el PDF descargado lo llevaba."""
    assert "no recomendación de inversión" in TESIS
    assert "window.__navigate(\\'/disclaimer\\')" in TESIS
    detalle = TESIS[TESIS.index("function renderDetail"):]
    detalle = detalle[:detalle.index("\n}\n")]
    assert "avisoLegal()" in detalle, "el detalle de una tesis no lleva el aviso"
    cabecera = TESIS[TESIS.index("function header()"):]
    assert "avisoLegal()" in cabecera[:cabecera.index("\n}\n")]
