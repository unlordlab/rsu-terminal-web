"""
La terminal ignoraba «reducir movimiento» y no anunciaba nada a un lector de pantalla.

EL CASO, Accesibilidad #2, remedido el 09/09/2026 antes de tocar nada:

    prefers-reduced-motion   1 de 9 temas (solo octogon, y solo sus adornos)
    aria-live                0 en todo el frontend
    role="alert"             0 en todo el frontend
    transiciones CSS         46
    animaciones CSS          12

QUÉ SIGNIFICA ESO EN LA PRÁCTICA. Windows, macOS, iOS y Android tienen una
casilla de «reducir movimiento» que activa gente con migraña, vértigo,
trastorno vestibular o epilepsia fotosensible. El navegador se lo cuenta a cada
web. Alguien con vértigo abría Cartera, llegaba un tick por WebSocket, la fila
pulsaba, y se mareaba: lo había pedido y se ignoraba.

Y un lector de pantalla lee lo que HAY, no lo que aparece después. Sin
`role="alert"`, quien escribía mal la contraseña no entraba y **no oía por
qué**; un módulo caído y un módulo lento sonaban exactamente igual, porque los
dos se quedaban con el «Cargando...» que el lector leyó al llegar.

TRES DECISIONES QUE NO SON OBVIAS:

  1. **0.01ms y no 0.** Con duración cero algunos navegadores NO disparan
     `transitionend` / `animationend`, y el código que espera esos eventos se
     quedaría colgado. 0.01ms es instantáneo para el ojo y sigue disparándolos.
  2. **`!important`.** Este código lleva 16 transiciones escritas en atributos
     `style=` en línea; sin `!important` la regla no las alcanza. Verificado en
     el navegador: 0,2s → 0,00001s sobre un estilo en línea.
  3. **Los gráficos se apagan aparte.** Chart.js anima dentro de un `<canvas>`
     y el CSS no llega ahí — y son el movimiento más grande de la pantalla.

LO QUE NO SE MARCA, A PROPÓSITO: los precios que cambian solos. Marcar la tabla
de Cartera haría que el lector recitara las 46 posiciones en cada tick. Eso es
peor que el silencio, y es como se acaba desactivando el lector en una web
entera. Se anuncian los ERRORES y los CAMBIOS DE ESTADO, no el flujo continuo.

Uso:
    cd backend
    python -m pytest tests/test_frontend_movimiento_y_anuncios.py -v
"""
import glob
import io
import os
import re

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
TEMAS = sorted(glob.glob(os.path.join(RAIZ, "frontend", "themes", "*.css")))


def _leer(*partes):
    return io.open(os.path.join(RAIZ, *partes), encoding="utf-8").read()


def _bloque_reduced_motion(css):
    m = re.search(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{(.*?)\n\}",
                  css, re.S)
    return m.group(1) if m else ""


# ── Reducir movimiento ───────────────────────────────────────────────────────

def test_la_regla_vive_en_base_css_que_cargan_los_NUEVE_temas():
    """EL test. Ponerla tema a tema es exactamente como se llegó a tenerla en
    1 de 9: `octogon` la tenía y los otros ocho no."""
    assert _bloque_reduced_motion(_leer("frontend", "themes", "base.css")), (
        "no hay regla de prefers-reduced-motion en base.css: los temas que no "
        "la traigan seguirán animando a quien pidió que no")


def test_alcanza_a_TODO_incluido_lo_que_lleva_estilo_en_linea():
    """Los 16 `style=\"transition:...\"` del código no se alcanzan sin
    `!important`. Verificado en el navegador: 0,2s pasa a 0,00001s."""
    b = _bloque_reduced_motion(_leer("frontend", "themes", "base.css"))
    assert "*" in b.split("{")[0], "la regla no aplica al selector universal"
    for prop in ("animation-duration", "transition-duration", "animation-iteration-count"):
        assert re.search(prop + r":[^;]*!important", b), (
            f"{prop} sin !important: no alcanza a los estilos en línea")


def test_la_duracion_NO_es_cero():
    """Con 0, algunos navegadores no disparan `transitionend`/`animationend` y
    el código que los espera se cuelga. Es la trampa clásica de esta regla."""
    b = _bloque_reduced_motion(_leer("frontend", "themes", "base.css"))
    m = re.search(r"transition-duration:\s*([0-9.]+)(m?s)", b)
    assert m, "no se fija transition-duration"
    valor, unidad = float(m.group(1)), m.group(2)
    assert valor > 0, "duración 0: transitionend puede no dispararse nunca"
    ms = valor if unidad == "ms" else valor * 1000
    assert ms < 1, f"{ms} ms sigue siendo movimiento perceptible"


def test_se_cortan_los_bucles_infinitos():
    """El pulso de una fila al llegar un precio es `animation: ... infinite`, y
    es justo el que marea."""
    b = _bloque_reduced_motion(_leer("frontend", "themes", "base.css"))
    assert re.search(r"animation-iteration-count:\s*1\b", b)


def test_los_GRAFICOS_tambien_se_frenan():
    """Chart.js anima en `<canvas>`: el CSS no llega. Y una línea de seis meses
    dibujándose es el movimiento más grande de la pantalla."""
    js = _leer("frontend", "core", "ui.js")
    # LA CONSULTA REAL, no que la cadena aparezca por ahi: mi primera version
    # buscaba "prefers-reduced-motion" en todo el fichero y el sabotaje de
    # cambiar la consulta a otra cosa se escapaba, porque el texto seguia en mi
    # propio comentario de encima. Van ocho veces esta semana.
    consulta = re.search(r"matchMedia\(\s*'([^']+)'\s*\)", js)
    assert consulta, "no se consulta matchMedia en ninguna parte"
    assert consulta.group(1) == "(prefers-reduced-motion: reduce)", (
        f"los graficos consultan <{consulta.group(1)}>, que no es la preferencia "
        f"de movimiento reducido: seguirian animandose")
    assert "Chart.defaults.animation = false" in js


def test_la_consulta_de_la_preferencia_no_puede_reventar():
    """`matchMedia` no existe en navegadores muy viejos. Una excepción aquí
    impediría cargar Chart.js y con él media terminal."""
    js = _leer("frontend", "core", "ui.js")
    i = js.index("function _sinMovimiento")
    assert "try" in js[i:i + 400] and "catch" in js[i:i + 400]


def test_sin_la_preferencia_NO_cambia_nada():
    """La regla vive dentro del `@media`. Si se sacara fuera, la terminal se
    quedaría sin animaciones para todo el mundo."""
    css = _leer("frontend", "themes", "base.css")
    fuera = re.sub(r"@media\s*\(prefers-reduced-motion:\s*reduce\)\s*\{.*?\n\}", "", css, flags=re.S)
    assert "animation-iteration-count: 1 !important" not in fuera, (
        "la regla está fuera del media query: afectaría a todo el mundo")


# ── Anuncios a lector de pantalla ────────────────────────────────────────────

def test_el_error_de_LOGIN_se_anuncia():
    """Sin esto, escribes mal la contraseña, no entras, y no oyes por qué."""
    js = _leer("frontend", "pages", "login.js")
    i = js.index('id="login-error"')
    cabecera = js[max(0, i - 200):i + 200]
    assert 'role="alert"' in cabecera, (
        "el error de login no se anuncia: el lector lee lo que había al llegar")


def test_el_error_de_un_MODULO_se_anuncia():
    """~20 paneles de Market pasan por `widgetError`. Un módulo caído y uno
    lento sonaban igual: los dos se quedaban con el «Cargando...»."""
    js = _leer("frontend", "pages", "market.js")
    i = js.index("function widgetError")
    cuerpo = js[i:i + 1200]
    assert cuerpo.count('role="alert"') >= 2, (
        "alguna rama de widgetError no se anuncia (hay dos: rate limit y error "
        "normal)")


def test_los_precios_en_vivo_NO_se_anuncian():
    """La mitad del trabajo, y la que se olvida. Marcar la tabla de Cartera
    haría que el lector recitara las 46 posiciones en cada tick — peor que el
    silencio, y es como se acaba desactivando el lector en una web entera."""
    js = _leer("frontend", "pages", "cartera.js")
    assert "aria-live" not in js, (
        "se ha marcado como región viva algo que cambia con cada tick: el "
        "lector recitaría la cartera entera continuamente")


def test_la_decision_de_NO_marcarlo_esta_escrita():
    """Si no está el porqué, el siguiente que pase «arreglará» el hueco y
    convertirá la Cartera en un recitado continuo."""
    js = _leer("frontend", "pages", "market.js")
    i = js.index("function widgetError")
    assert "flujo continuo" in js[max(0, i - 1400):i], (
        "no se explica por qué los precios en vivo no llevan aria-live")


# ── Que no se pierda al añadir un tema ───────────────────────────────────────

def test_ningun_tema_deshace_la_regla():
    """Un tema que reponga `transition-duration` con `!important` dentro de su
    propio media query devolvería el movimiento a quien pidió que no."""
    culpables = []
    for ruta in TEMAS:
        if os.path.basename(ruta) == "base.css":
            continue
        b = _bloque_reduced_motion(io.open(ruta, encoding="utf-8").read())
        if re.search(r"(transition|animation)-duration:\s*(?!0)", b):
            culpables.append(os.path.basename(ruta))
    assert not culpables, f"estos temas reponen movimiento bajo la preferencia: {culpables}"


def test_se_revisan_los_temas_de_verdad():
    """Si el glob dejara de encontrarlos, el test de arriba pasaría sin mirar."""
    assert len(TEMAS) >= 9, f"solo se encuentran {len(TEMAS)} temas"
