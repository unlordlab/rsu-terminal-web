"""
La terminal no tenía NI UN estilo de foco de teclado. Ninguno, en nueve temas.

EL CASO, 06/09/2026, al mirar si el repositorio `ui-ux-pro-max-skill` aportaba
algo aprovechable. Casi nada -- su función estrella genera sistemas de diseño
desde cero y aquí ya hay uno hecho a mano y medido-- pero su lista de 119
reglas de UX sirvió de checklist, y al cruzarla con el frontend salió esto:

    :focus / :focus-visible   ->  0 apariciones en los 9 temas y en todo el JS
    elementos interactivos    ->  112 <button>, 42 <input>, 12 <select>, 15 <a>

181 controles y ninguno mostraba dónde estaba el teclado. Quien navega con Tab
-- por costumbre, por accesibilidad, o simplemente rellenando el formulario de
login-- no veía nada, o veía el contorno por defecto del navegador, que sobre
estos fondos oscuros es prácticamente invisible.

POR QUÉ DOS ANILLOS Y NO UNO. Lo obvio era un anillo del color de acento de
cada tema. Medido, no supuesto: TRES DE NUEVE no llegan al 3:1 que pide la
WCAG para un indicador de foco -- bubblebath 2,45, light 2,65, octogon 1,78.
Un solo color no puede funcionar sobre nueve paletas tan distintas. Así que va
un anillo interior de acento (identidad, se ve bien en 6 de 9) y uno exterior
de `--color-text`, que pasa el 3:1 en los nueve (peor caso 3,35).

LO QUE ESTE FICHERO PROTEGE, y es lo que importa: no que la regla exista --eso
se ve de un vistazo-- sino que **el contraste siga cumpliéndose**. Añadir un
tema nuevo o retocar una paleta puede dejar el foco invisible sin que nadie se
entere, que es exactamente como llegó a haber cero.

Uso:
    cd backend
    python -m pytest tests/test_frontend_foco_teclado.py -v
"""
import glob
import os
import re

import pytest

TEMAS = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'themes')
BASE = os.path.join(TEMAS, 'base.css')
MINIMO_WCAG = 3.0          # SC 1.4.11: indicador de foco, 3:1


def _css(ruta):
    with open(ruta, encoding='utf-8') as fh:
        return fh.read()


def _luminancia(hexa):
    hexa = hexa.lstrip('#')
    canales = [int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (f(c) for c in canales)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contraste(a, b):
    la, lb = _luminancia(a), _luminancia(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _regla_de_foco(base):
    """La REGLA, no la primera vez que aparece la cadena.

    La primera versión hacía `base.index(":focus-visible")` y caía dentro del
    comentario que hay encima -- que menciona `:focus-visible` al contar que
    antes había cero. El test pasaba mirando la prosa en vez del CSS.

    La SEGUNDA versión seguía cayendo en el comentario por un motivo más sutil:
    era `([^\\n{}]*:focus-visible[^{}]*)`, y ese segundo tramo SÍ admite saltos
    de línea. Así que enganchaba `:focus-visible` dentro de la prosa y corría
    veinte líneas hasta la primera llave de verdad -- arrastrando consigo el
    «12 <select>» del propio comentario, con lo que el sabotaje de quitar los
    <select> del selector se le escapó. Un selector CSS cabe en una línea: los
    dos tramos tienen que excluir el salto."""
    m = re.search(r"([^\n{}]*:focus-visible[^\n{}]*)\{([^}]*)\}", base)
    assert m, "no hay ninguna regla :focus-visible en base.css"
    return m.group(1), m.group(2)          # (selector, cuerpo)


def _var(texto, nombre):
    m = re.search(rf"--color-{nombre}:\s*(#[0-9a-fA-F]{{6}})", texto)
    return m.group(1) if m else None


def _temas():
    """Cada tema con su paleta. `base.css` define los valores por defecto y los
    demás solo redefinen variables, así que lo que falte se hereda de ahí."""
    base = _css(BASE)
    out = {}
    for ruta in sorted(glob.glob(os.path.join(TEMAS, '*.css'))):
        t = _css(ruta)
        paleta = {}
        for v in ('accent', 'text', 'bg', 'surface'):
            paleta[v] = _var(t, v) or _var(base, v)
        out[os.path.basename(ruta)] = paleta
    return out


# ── Que la regla exista y sea la que se decidió ──────────────────────────────

def test_hay_indicador_de_foco_de_teclado():
    """EL test. Antes del 06/09 esto no existía en ningún sitio."""
    assert ":focus-visible" in _css(BASE), (
        "no hay ningún estilo de foco: 181 controles interactivos sin indicar "
        "dónde está el teclado")


def test_el_anillo_lleva_los_DOS_colores():
    """Uno solo no vale: el acento no contrasta en tres de los nueve temas."""
    _, cuerpo = _regla_de_foco(_css(BASE))
    assert "--color-text" in cuerpo and "--color-accent" in cuerpo, (
        "el anillo de foco ha vuelto a un solo color; en bubblebath, light y "
        "octogon el acento no llega al 3:1 contra su propio fondo")


def test_se_usa_focus_visible_y_NO_se_anula_focus():
    """`:focus-visible` para que el anillo salga con el teclado y no al hacer
    clic. Y no se anula `:focus`: un navegador que no soporte `:focus-visible`
    debe conservar su contorno por defecto, que es peor que el nuevo pero
    mucho mejor que ninguno."""
    base = _css(BASE)
    assert not re.search(r":focus\s*\{[^}]*outline:\s*(none|0)", base), (
        "se está anulando :focus, así que un navegador sin soporte de "
        ":focus-visible se quedaría sin ningún indicador")


def test_cubre_los_controles_que_de_verdad_hay():
    selector, _ = _regla_de_foco(_css(BASE))
    for etiqueta in ("button", "input", "select", "a", "textarea"):
        assert re.search(rf"\b{etiqueta}\b", selector), (
            f"el selector de foco no cubre <{etiqueta}>: {selector.strip()}")


# ── Lo que de verdad protege este fichero ────────────────────────────────────

@pytest.mark.parametrize("tema", sorted(_temas()))
def test_el_foco_se_VE_en_este_tema(tema):
    """EL test que importa. No comprueba que la regla esté escrita, sino que el
    resultado se ve: al menos uno de los dos anillos tiene que llegar al 3:1
    contra el fondo Y contra la superficie de las tarjetas.

    Un tema nuevo con una paleta desafortunada dejaría el foco invisible sin
    que nadie se entere -- que es exactamente como se llegó a tener cero."""
    p = _temas()[tema]
    assert p['accent'] and p['text'] and p['bg'], f"{tema} no define la paleta"
    for nombre, fondo in (("fondo", p['bg']), ("superficie", p['surface'] or p['bg'])):
        mejor = max(_contraste(p['text'], fondo), _contraste(p['accent'], fondo))
        assert mejor >= MINIMO_WCAG, (
            f"en {tema} ninguno de los dos anillos de foco llega a "
            f"{MINIMO_WCAG}:1 sobre el {nombre} ({fondo}): texto "
            f"{_contraste(p['text'], fondo):.2f}, acento "
            f"{_contraste(p['accent'], fondo):.2f}")


def test_el_anillo_EXTERIOR_es_el_que_aguanta_siempre():
    """El de acento se cae en tres temas; el de texto no se cae en ninguno. Si
    algún día el de texto dejara de cumplir, el diseño de dos anillos ya no
    garantiza nada y hay que replantearlo, no parchear ese tema."""
    for tema, p in _temas().items():
        peor = min(_contraste(p['text'], p['bg']),
                   _contraste(p['text'], p['surface'] or p['bg']))
        assert peor >= MINIMO_WCAG, (
            f"el anillo exterior (--color-text) ya no garantiza visibilidad en "
            f"{tema}: {peor:.2f}:1")


def test_los_tres_temas_del_caso_siguen_necesitando_el_segundo_anillo():
    """Documenta la medición que motivó el diseño. Si un día estos tres
    pasaran por sí solos, el anillo doble seguiría sin estorbar -- pero
    conviene saber que la razón original ha cambiado."""
    temas = _temas()
    for tema in ("bubblebath.css", "light.css", "octogon.css"):
        p = temas[tema]
        assert _contraste(p['accent'], p['bg']) < MINIMO_WCAG, (
            f"{tema} ya no falla el contraste de acento; la medición del "
            f"06/09 ha dejado de ser cierta y conviene revisarla")
