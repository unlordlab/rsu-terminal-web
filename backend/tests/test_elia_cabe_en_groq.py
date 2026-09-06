"""
Elia pedía 9.308 fichas a una cuenta con techo de 8.000, y llevaba así desde agosto.

EL CASO, encontrado el 20/08/2026 dentro del propio aviso de cron que se
estaba arreglando. El error era literal:

    Groq error 413: Request too large ... tokens per minute (TPM):
    Limit 8000, Requested 9308

REPRODUCIDO el 06/09 antes de tocar nada, construyendo el prompt real: el
bloque de «lecciones que ya existen» ocupaba **20.847 caracteres** — las 149
lecciones con su título MÁS los primeros 100 caracteres de su introducción —,
o sea ~6.900 fichas, que con las 3.000 de `max_tokens` se pasan del techo.

LA MEDICIÓN QUE DECIDIÓ EL ARREGLO:

    título + 100 chars de intro   6.893 fichas -> 9.893 pedidas   NO CABE
    solo el título                2.287 fichas -> 5.287 pedidas   cabe
    título agrupado por módulo    2.010 fichas -> 5.010 pedidas   cabe   <-

El intro costaba CINCO VECES lo que el título y no servía para nada: ese
bloque existe solo para que el modelo no repita un tema, y el título ya dice
de qué va. Agrupar por módulo, además de ser lo más barato, le da al modelo
justo lo que necesita para elegir `moduleId`.

DOS PRECISIONES SOBRE EL HALLAZGO ORIGINAL, que mezclaba dos cosas:

1. Solo falla la ruta «nueva». «revision» manda UNA lección y siempre cupo, y
   el cron usa `--tipo random`: fallaba la MITAD de los días, no todos.
2. Que la Academia siga en 149 lecciones no es prueba de que la generación
   esté rota — las dos rutas solo dejan una propuesta PENDIENTE que hay que
   aprobar y pegar a mano. Son cosas distintas.

Uso:
    cd backend
    python -m pytest tests/test_elia_cabe_en_groq.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

os.environ.setdefault("GROQ_API_KEY", "solo-para-importar")

import elia_agent as E  # noqa: E402


def _lecciones(n, por_modulo=5, titulo="Título de ejemplo de una lección"):
    return [{"moduleId": i // por_modulo, "lessonIndex": i % por_modulo,
             "title": f"{titulo} {i}",
             "intro": "Una introducción larga que ocupa bastante más que el título "
                      "y que es exactamente lo que sobraba del contexto." * 2}
            for i in range(n)]


# ── El caso real, contra el fichero de verdad ────────────────────────────────

def test_las_lecciones_REALES_caben_con_margen():
    """EL test, y el que sirve de aviso temprano: no usa datos inventados, usa
    `academy_lessons.js`. Si algún día la Academia crece hasta no caber, esto
    se pone rojo ANTES de que el cron empiece a fallar en producción — que es
    justo el aviso que no hubo entre el 20/08 y el 06/09."""
    lec = E._extraer_lecciones_existentes()
    assert len(lec) > 100, f"solo se han detectado {len(lec)} lecciones: ¿ha cambiado el formato del fichero?"
    texto, omitidas = E._contexto_lecciones(lec)
    fichas = E._estimar_fichas(texto)
    assert omitidas == 0, (
        f"{omitidas} lecciones se están omitiendo por espacio. Funciona, pero el "
        f"modelo ya no ve la Academia entera: toca el rediseño que dice el "
        f"comentario de _contexto_lecciones (elegir módulo primero)")
    assert fichas + E.MAX_TOKENS_SALIDA <= E.TPM_LIMITE, (
        f"el prompt de Elia vuelve a no caber: {fichas} fichas de contexto + "
        f"{E.MAX_TOKENS_SALIDA} de salida sobre un techo de {E.TPM_LIMITE}")


def test_el_contexto_ya_no_lleva_las_introducciones():
    """Eran el 75% del bloque y no aportaban nada a «no repitas estos temas»."""
    lec = E._extraer_lecciones_existentes()
    texto, _ = E._contexto_lecciones(lec)
    intros = [l["intro"][:60] for l in lec if len(l["intro"]) > 60]
    assert intros, "no hay introducciones con las que comprobarlo"
    assert not any(i in texto for i in intros[:20]), (
        "el contexto vuelve a incluir las introducciones de las lecciones")


def test_los_titulos_SI_estan_todos():
    """Recortar el coste no puede costar el propósito: si falta un título, el
    modelo puede proponer un tema que ya existe."""
    lec = E._extraer_lecciones_existentes()
    texto, omitidas = E._contexto_lecciones(lec)
    assert omitidas == 0
    faltan = [l["title"] for l in lec if l["title"] not in texto]
    assert not faltan, f"faltan {len(faltan)} títulos en el contexto: {faltan[:3]}"


def test_va_agrupado_por_modulo():
    """Además de ser lo más barato, es lo que el modelo necesita para elegir
    `moduleId`, que es un campo obligatorio de su respuesta."""
    texto, _ = E._contexto_lecciones(_lecciones(40))
    assert texto.startswith("M0:")
    assert texto.count("\n") + 1 == 8, "una línea por módulo, no una por lección"


# ── Cuando la Academia crezca ────────────────────────────────────────────────

def test_si_no_cabe_se_recorta():
    lec = _lecciones(4000)
    texto, omitidas = E._contexto_lecciones(lec)
    assert omitidas > 0
    assert E._estimar_fichas(texto) <= E.TECHO_PROMPT, (
        "se ha recortado y aun así no cabe")


def test_y_se_DICE_cuantas_faltan():
    """Lo importante del recorte. Un listado parcial presentado como completo
    es PEOR que uno corto que se declara incompleto: el modelo daría por libre
    un tema que ya existe y propondría un duplicado."""
    texto, omitidas = E._contexto_lecciones(_lecciones(4000))
    assert f"{omitidas} lecciones mas" in texto, (
        "se recorta en silencio: el modelo cree que está viendo la Academia "
        "entera cuando le faltan cientos de lecciones")


def test_sin_recorte_no_se_anade_la_coletilla():
    """Decir «y 0 lecciones más» cada día sería ruido en el prompt."""
    texto, omitidas = E._contexto_lecciones(_lecciones(20))
    assert omitidas == 0 and "no caben" not in texto


def test_una_academia_vacia_no_revienta():
    texto, omitidas = E._contexto_lecciones([])
    assert texto == "" and omitidas == 0


# ── El presupuesto ───────────────────────────────────────────────────────────

def test_el_techo_deja_sitio_a_la_salida_y_a_un_margen():
    """Groq cuenta con SU tokenizador, no con esta estimación: sin margen, un
    desvío del 10% vuelve a dar 413."""
    assert E.TECHO_PROMPT + E.MAX_TOKENS_SALIDA < E.TPM_LIMITE, (
        "el techo del prompt más la salida llegan justo al límite: no hay "
        "margen para el desvío del tokenizador")


def test_la_estimacion_es_CONSERVADORA():
    """2,9 y no 3,5. Calibrado en el briefing contra el recuento real de Groq:
    se estimaron 5.744 fichas y Groq contó 6.601. Estimar de MENOS provoca un
    413; estimar de más solo recorta contexto que habría cabido."""
    assert E.CHARS_POR_FICHA <= 3.0, (
        f"CHARS_POR_FICHA={E.CHARS_POR_FICHA} subestima el tamaño real del "
        f"prompt, que es lo que provoca el 413")


def test_max_tokens_sale_de_la_constante_no_de_un_numero_suelto():
    """Si el 3000 vuelve a estar escrito a mano en la llamada, el techo del
    prompt deja de corresponderse con lo que de verdad se pide."""
    import inspect
    fuente = inspect.getsource(E._llamar_groq)
    assert "MAX_TOKENS_SALIDA" in fuente and '"max_tokens": 3000' not in fuente


def test_la_ruta_de_REVISION_sigue_mandando_una_sola_leccion():
    """Esa nunca falló -- manda una lección y ya está-- y el arreglo no puede
    haberla engordado de rebote."""
    import inspect
    fuente = inspect.getsource(E.revisar_leccion_existente)
    assert "_contexto_lecciones" not in fuente, (
        "la ruta de revisión ha empezado a mandar el catálogo entero, que es "
        "justo lo que hacía fallar a la otra")
    assert "random.choice(existentes)" in fuente
