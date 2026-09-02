"""
«El oro alcanza máximos históricos» — estaba un 17,3% por debajo.

EL CASO, 02/09/2026. El briefing ABRÍA así, en la primera frase:

    «... mientras el oro alcanza máximos históricos impulsado por el miedo
     a la inflación»

y lo repetía en el cuerpo. El oro cotizaba a 4.379,80 dólares. Su máximo de
seis meses fue 5.294,40 el 02/03/2026 y el de cinco años 5.318,40 el
29/01/2026: estaba un 17,3% POR DEBAJO. Y no venía subiendo — llevaba cuatro
sesiones cayendo (4.609,7 → 4.478,1 → 4.431,1 → 4.348,0).

EL DATO DEL SCRIPT ERA CORRECTO. Comprobado contra el bloque `datos` que
`briefing.json` guarda desde el 01/09: precio 4.379,80, variación +0,73%,
previo 4.348,0. Todo exacto. Lo falso era la INTERPRETACIÓN, y el modelo no
tenía forma de comprobarla: al prompt le llega el precio de hoy y su variación
de un día, y NADA de histórico. Un superlativo sobre una serie que no has
visto solo se puede inventar.

NO ES UN CASO AISLADO. El 01/09, la víspera, el briefing abrió con «los tipos
de los bonos soberanos han disparado sus rendimientos hasta MÁXIMOS DESDE
ENERO DE 2025» — otra afirmación sobre un histórico que tampoco recibía. Dos
días seguidos, y las dos veces en el titular o la entradilla.

EL SEGUNDO FALLO DEL MISMO DÍA, de la misma familia: «El Russell 2000, con su
caída del 1,23%, sufre más que el Nasdaq 100 (-1,29%)». Los dos números están
en la misma frase y dicen lo contrario de lo que afirma: -1,23% es MENOS caída
que -1,29%.

LA LECCIÓN: el modelo no distingue entre lo que sabe y lo que le suena. Si un
dato no está en el prompt, la regla tiene que decir explícitamente que no se
puede afirmar -- describir los datos que SÍ hay no basta.

Uso:
    cd backend
    python -m pytest tests/test_briefing_superlativos.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

RUTA_SCRIPT = os.path.join(os.path.dirname(__file__), '..', '..', 'scripts',
                           'daily_briefing.py')


def _prompt():
    return D.build_prompt(
        {"date": "02/09/2026", "time": "07:47", "sectors": {}, "calendar": [],
         "sesion": {"en_curso": False, "fecha": "2026-09-01", "hora_et": "07:47"}},
        [], [], [], {}, [], [], [])


def test_el_prompt_prohibe_afirmar_maximos_y_minimos():
    """EL test. Sin esta regla, «el oro alcanza máximos históricos» abrió un
    briefing con el oro un 17,3% por debajo de su máximo."""
    p = _prompt()
    assert "SIN HISTÓRICO" in p, (
        "nada le dice al modelo que no tiene el histórico: puede volver a "
        "afirmar máximos o mínimos que no ha podido comprobar")
    assert "máximos" in p and "mínimos" in p


def test_deja_la_puerta_abierta_a_un_titular_que_SI_lo_diga():
    """Si Reuters dice que el oro está en máximos, contarlo es legítimo -- pero
    atribuido. Prohibirlo del todo empobrecería el briefing sin motivo."""
    p = _prompt()
    regla = [l for l in p.splitlines() if "SIN HISTÓRICO" in l][0]
    assert "titular" in regla and "atribú" in regla


def test_el_prompt_pide_comparar_antes_de_decir_que_uno_cae_mas():
    """«El Russell 2000, con su caída del 1,23%, sufre más que el Nasdaq 100
    (-1,29%)»: los dos números en la misma frase, y dicen lo contrario."""
    p = _prompt()
    regla = [l for l in p.splitlines() if "SIN HISTÓRICO" in l][0]
    assert "compara" in regla.lower() and "cae más" in regla


def test_la_regla_esta_en_LAS_DOS_versiones_del_prompt():
    """Hay dos bloques de reglas (v1 y v2) y `BRIEFING_PROMPT_VERSION` elige.
    Ponerla solo en la activa la perdería en cuanto se cambie de versión --
    que es exactamente cómo se pierden las reglas."""
    with open(RUTA_SCRIPT, encoding="utf-8") as fh:
        fuente = fh.read()
    assert fuente.count("SIN HISTÓRICO") == 2, (
        "la regla no está en las dos versiones del prompt")


def test_la_regla_no_se_come_el_presupuesto():
    """Este prompt lleva semanas sin caber en el límite de Groq: una regla de
    150 fichas se paga TODOS los días. La primera versión costaba 149 y se
    reescribió hasta 84."""
    p = _prompt()
    regla = [l for l in p.splitlines() if "SIN HISTÓRICO" in l][0]
    assert D.estimar_tokens(regla) < 100, (
        f"la regla cuesta {D.estimar_tokens(regla)} fichas en un prompt que ya "
        f"no cabe; hay que decir lo mismo con menos")


def test_las_reglas_que_ya_estaban_siguen_estando():
    """Insertar una regla renumerando a mano es una forma fácil de pisar otra."""
    p = _prompt()
    assert "ESTADO DE LA SESIÓN" in p, "se ha perdido la regla de la sesión"
    assert "Futuros" in p, "se ha perdido la regla de los futuros pre-market"
