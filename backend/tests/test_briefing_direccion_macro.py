"""
«+162k empleos, mes anterior +21k» y dos de tres modelos escribieron «desaceleración».

EL CASO, 07/09/2026, y es el hallazgo más valioso de comparar tres modelos sobre
el mismo prompt. La fila de nóminas del bloque macro decía, literal:

    | Nóminas no agrícolas | publicado 2026-09-04 ← RECIÉN PUBLICADO
    | +162k empleos | mes anterior +21k |

Y esto es lo que escribieron:

    qwen/qwen3.6-27b   «una creación de empleo de SOLO 162.000 puestos, frente a
                       los 21.000 del mes anterior [...] la DEBILIDAD en las
                       nóminas es una señal clara de ENFRIAMIENTO económico»
    groq/compound      «Los últimos datos laborales confirman una
                       DESACELERACIÓN: nóminas no agrícolas +162k (vs +21k)»

162k frente a 21k es multiplicar por casi ocho. Las dos lecturas están
invertidas.

Y LO IMPORTANTE ES QUE FUERON DOS FAMILIAS DE MODELO DISTINTAS. Eso descarta
«ese modelo lee mal» y señala a la fila: da dos números sueltos y deja que el
modelo elija el sentido. Por defecto elige el que encaja con el relato bajista
del resto del briefing, porque un dato de empleo en una nota bajista «tiene que»
ser malo.

ES EL MISMO ARREGLO QUE YA FUNCIONÓ DOS VECES en este fichero, y por eso se
sabía que funcionaría: cuando el prompt decía «% S&P 500 sobre SMA50: 46.6%» el
briefing escribió «el 46,6% está POR DEBAJO» (invertido), y se arregló dando las
dos caras — «51.2% POR ENCIMA (o sea 48.8% por debajo)». Calcular la dirección y
DECIRLA cuesta ~10 fichas; discutir con el modelo en las reglas no funciona.

EL SEGUNDO ERROR DEL MISMO DÍA, y también medido:

    prompt:      Peticiones semanales de paro | 206.000 | previo 204.000
    compound:    «206k, ligeramente superiores a las 204 k ESPERADAS»
    qwen:        «muy por debajo de las EXPECTATIVAS»

No hay ni una expectativa en todo el prompt. Uno convirtió el PREVIO en
consenso; el otro se inventó el consenso entero. De ahí la regla nueva, que va
en las DOS versiones del prompt — v1 no tenía ninguna regla de macro, y dejarla
solo en la activa es como se pierden al cambiar `BRIEFING_PROMPT_VERSION`.

Uso:
    cd backend
    python -m pytest tests/test_briefing_direccion_macro.py -v
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _macro(observaciones, tipo="cambio_miles", nombre="Nóminas no agrícolas"):
    """Ejecuta el constructor real de la tabla macro con observaciones dadas.

    Se parchea lo que sale a FRED, no la función que se quiere probar."""
    with patch.object(D, "FRED_KEY", "solo-para-no-abortar"), \
         patch.object(D, "FRED_SERIES", [("SERIE", nombre, tipo)]), \
         patch.object(D, "_fred_observaciones", return_value=observaciones), \
         patch.object(D, "_fred_publicado_el", return_value="2026-09-04"):
        return D.get_macro_indicators()[0]


# El caso real: 162k este mes (2.000 - 1.838), 21k el anterior (1.838 - 1.817).
REAL_07_09 = [("2026-08-01", 2000.0), ("2026-07-01", 1838.0), ("2026-06-01", 1817.0)]


# ── La dirección, dicha y no deducida ────────────────────────────────────────

def test_la_fila_DICE_que_la_creacion_de_empleo_sube():
    """EL test. Con la fila vieja, dos de tres modelos leyeron lo contrario."""
    fila = _macro(REAL_07_09)
    assert fila["dato"] == "+162k empleos"
    assert "SUBE" in fila["extra"], (
        f"la fila sigue dando dos números sueltos sin decir el sentido: "
        f"«{fila['extra']}» — es lo que produjo «desaceleración» con +162k "
        f"frente a +21k")
    # Y la sube CON LAS CIFRAS QUE EXISTEN, no con la diferencia. La primera
    # versión metía «+141k» (162 − 21) y el 11/09/2026 la segunda lectura la
    # citó como si fuera el mes anterior: «+162.000, una mejora respecto al mes
    # anterior (+141.000)». El mes anterior fueron +21k. Ver Newsfeed #64.
    assert "+162k frente a +21k" in fila["extra"], "no se dice CUÁNTO sube"
    assert "141" not in fila["extra"], (
        f"la diferencia vuelve a ser un número citable: «{fila['extra']}»")


def test_y_dice_BAJA_cuando_de_verdad_baja():
    """La otra cara: si el arreglo dijera «SUBE» siempre, sería peor que no
    decir nada — convertiría un aviso en ruido."""
    peor = [("2026-08-01", 1838.0), ("2026-07-01", 2000.0), ("2026-06-01", 1500.0)]
    fila = _macro(peor)             # -162k este mes, +500k el anterior
    assert "BAJA" in fila["extra"] and "SUBE" not in fila["extra"]


def test_dos_meses_iguales_no_se_presentan_como_movimiento():
    igual = [("2026-08-01", 2000.0), ("2026-07-01", 1900.0), ("2026-06-01", 1800.0)]
    fila = _macro(igual)            # +100k los dos meses
    assert "IGUAL" in fila["extra"]


def test_el_previo_SIGUE_estando():
    """Añadir la dirección no puede costar el dato: el modelo necesita las dos
    cifras para escribir la comparación."""
    fila = _macro(REAL_07_09)
    assert "+21k" in fila["extra"]


def test_sin_tercer_mes_no_se_inventa_una_direccion():
    """Con solo dos observaciones no hay «mes anterior» con el que comparar.
    Decir «SUBE» ahí sería inventarse el sentido, que es justo el fallo."""
    fila = _macro([("2026-08-01", 2000.0), ("2026-07-01", 1838.0)])
    assert fila["extra"] == "sin mes anterior"
    assert "SUBE" not in fila["extra"] and "BAJA" not in fila["extra"]


def test_las_otras_filas_macro_no_se_han_roto():
    """El bloque macro lo comparten peticiones de paro, tasa de paro e IPC."""
    paro = _macro([("2026-08-29", 206.0), ("2026-08-22", 204.0),
                   ("2026-08-15", 208.0), ("2026-08-08", 211.0)],
                  tipo="nivel_miles", nombre="Peticiones semanales de paro")
    assert "previo 204" in paro["extra"] and "media 4 semanas" in paro["extra"]

    ipc = _macro([("2026-07-01", 332.5), ("2026-06-01", 331.77)] +
                 [("x", 323.3)] * 12, tipo="mm_aa", nombre="IPC subyacente")
    assert ipc["dato"] == "+0.22% m/m"
    # La cifra, no la palabra: «sin interanual» también contiene «interanual»,
    # y con esa comprobación el sabotaje de quitarlo se escapaba.
    assert ipc["extra"] == "+2.85% interanual", ipc["extra"]


# ── El consenso que no existe ────────────────────────────────────────────────

def test_se_prohibe_inventarse_un_consenso_en_LAS_DOS_versiones():
    """`qwen` escribió «muy por debajo de las expectativas» y `compound` llamó
    «204k esperadas» a un PREVIO. No hay ni una previsión en el prompt.

    Va en v1 y v2: v1 no tenía ninguna regla de macro, y una regla que solo
    está en la versión activa se pierde al cambiar BRIEFING_PROMPT_VERSION --
    que es exactamente como se perdieron otras (#44)."""
    for nombre, texto in (("v1", D._ESTILO_V1), ("v2", D._ESTILO_V2)):
        assert "consenso" in texto and "expectativas" in texto, (
            f"{nombre} no prohíbe inventarse un consenso")
        assert "PREVIO" in texto, f"{nombre} no dice que solo hay dato y previo"


def test_la_prohibicion_es_ACCIONABLE_y_no_un_principio_vago():
    """Nombra las frases exactas que se colaron. Una regla que dice «sé
    riguroso» no evita nada."""
    for texto in (D._ESTILO_V1, D._ESTILO_V2):
        assert "frente a lo esperado" in texto
        assert "por debajo de las expectativas" in texto


def test_la_regla_llega_al_prompt_que_se_ENVIA():
    """Que esté en la constante no basta: hay que comprobar que build_prompt la
    mete. Es la diferencia entre un test de fuente y uno de comportamiento."""
    prompt = D.build_prompt({"date": "2026-09-07", "time": "08:00"},
                            [], [], [], {}, [], [], [])
    assert "por debajo de las expectativas" in prompt
