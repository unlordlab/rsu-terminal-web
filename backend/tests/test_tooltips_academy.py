"""
Cada tooltip de Research, Options y el Algoritmo lleva a su lección de Academy.

EL CASO, Páginas Contenido #19, 10/09/2026. Los tooltips explicaban conceptos
que Academy desarrolla en profundidad, y no había nada que los conectara:
ningún módulo enlazaba a Academy. Ahora, al pulsar el «?», la ventana con la
explicación completa termina con «📚 Aprender más en Academy: <lección> →», y
Academy abre esa lección directamente (`/academy?leccion=20-2`).

POR QUÉ LA TABLA ES A MANO. Emparejar por nombre falla: de los 179 tooltips,
solo 10 aparecían tal cual en el título de una lección y 3 de esos 10 salían
mal («Score» de Options → la lección del RSU Score). Cada enlace se comprobó en
el TEXTO de la lección: solo se enlaza cuando la lección explica el concepto.

ALCANCE (decisión del usuario): primero Research, Options y el Algoritmo, 42
tooltips; 31 con lección. Los otros 11 son huecos de contenido de Academy. El
resto de los 179 tooltips queda pendiente.

Verificado en el navegador: el enlace aparece en la ventana, navega dentro de
la terminal y la cierra; un tooltip sin lección no lo pinta; la ventana del
resumen de Market (que no es un tooltip) tampoco; y en Academy un enlace
bueno abre la lección, uno inexistente o con código inyectado enseña el índice.

Uso:
    cd backend
    python -m pytest tests/test_tooltips_academy.py -v
"""
import io
import os
import re

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _js(*partes):
    return io.open(os.path.join(RAIZ, "frontend", *partes), encoding="utf-8").read()


TOOLTIP_JS = _js("components", "tooltip.js")
MANIFEST = _js("pages", "academy_manifest.js")
ACADEMY_JS = _js("pages", "academy.js")

# `:\s*` y no `:\s+`: dos filas quedan pegadas a los dos puntos por la
# alineación, y la primera versión de este patrón se las saltaba en silencio.
TABLA = dict(re.findall(r"^\s+'([a-z0-9-]+)':\s*'(\d+-\d+)',", TOOLTIP_JS[
    TOOLTIP_JS.index("export const LECCION_ACADEMY"):TOOLTIP_JS.index("export function enlaceAcademy")], re.M))
TOOLTIPS = set(re.findall(r'^    "([a-z0-9-]+)": \{', TOOLTIP_JS, re.M))
LECCIONES = set(re.findall(r"^\s+'(\d+-\d+)': \{ title:", MANIFEST, re.M))

# Los que NO tienen una lección que los explique, comprobado en el texto de
# Academy el 10/09/2026. Son huecos de contenido, no olvidos.
SIN_LECCION = {
    "algoritmo-historial-real", "algoritmo-importancia",
    "options-categories", "options-dia-bias", "options-sesgo-sesion", "options-net-score",
    "options-put-call", "options-large-oi",
    "days-to-cover", "market-cap", "payout-ratio",
}


def _usados(pagina):
    return set(re.findall(r"tt\('([a-z0-9-]+)'\)", _js("pages", pagina + ".js")))


ALCANCE = _usados("research") | _usados("options") | _usados("algoritmo")


def test_la_tabla_se_ha_leido_de_verdad():
    """Si el patrón dejara de encontrar filas, los tests de abajo pasarían sin
    mirar nada."""
    assert len(TABLA) >= 31 and len(TOOLTIPS) >= 179 and len(LECCIONES) >= 149


def test_cada_tooltip_enlazado_existe():
    assert not set(TABLA) - TOOLTIPS, set(TABLA) - TOOLTIPS


def test_cada_leccion_enlazada_existe_en_Academy():
    """Una lección renombrada o retirada dejaría un enlace que no abre nada.
    (enlaceAcademy tampoco lo pintaría, pero aquí se entera quien lo cambie.)"""
    assert not set(TABLA.values()) - LECCIONES, set(TABLA.values()) - LECCIONES


def test_cada_tooltip_del_alcance_esta_DECIDIDO():
    """EL test. Cada tooltip de Research, Options y el Algoritmo tiene que
    estar enlazado O en la lista explícita de «sin lección». Un tooltip nuevo
    en esos módulos obliga a decidir, en vez de quedarse sin enlace en
    silencio."""
    sin_decidir = ALCANCE - set(TABLA) - SIN_LECCION
    assert not sin_decidir, f"tooltips sin decidir si llevan lección: {sorted(sin_decidir)}"


def test_ninguno_esta_a_la_vez_enlazado_y_sin_leccion():
    assert not set(TABLA) & SIN_LECCION


def test_no_vuelven_los_emparejamientos_automaticos_que_salian_mal():
    """Lo que dio el cruce por nombre y era falso."""
    assert TABLA.get("options-score") != "20-1", "el Score de Options no es el RSU Score"
    assert TABLA.get("canslim-scan-score") != "20-1"
    assert TABLA.get("social-signal") != "2-1"


def test_la_ventana_pinta_el_enlace_con_la_clave_del_tooltip():
    """El click pasa la clave; sin ella no hay forma de saber qué lección."""
    assert "this.openModal(data, key);" in TOOLTIP_JS
    assert "(key ? enlaceAcademy(key) : '')" in TOOLTIP_JS


def test_academy_lee_el_enlace_antes_de_cualquier_await_y_lo_valida():
    """Antes de cualquier await: una navegación en medio (un redirect a /login)
    reescribiría la URL. Y solo vale una clave que exista en el manifiesto."""
    render = ACADEMY_JS[ACADEMY_JS.index("export async function render"):]
    render = render[:render.index("\n}\n")]
    lectura = render.index("get('leccion')")
    assert lectura < render.index("await "), "el parámetro se lee después de un await"
    assert "hasOwnProperty.call(LESSON_INDEX, leccionPedida)" in render
