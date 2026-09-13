"""
Accesibilidad #2, huecos (d) a (g) del barrido de las 119 reglas de UX.

  (d) Toda <img> lleva `alt`. Sin él, un lector de pantalla lee el nombre del
      fichero o la URL entera. Las decorativas llevan `alt=""`, que es la forma
      de decir «sáltala».
  (e) Las palabras largas se parten cuando no caben (`overflow-wrap`). Había
      cero reglas en todo el frontend, con tickers, nombres de empresa, URLs y
      emails por todas partes.
  (f) Con el dedo, cada control mide al menos 44px de alto. Ninguno llegaba.
  (g) «Saltar al contenido»: quien navega con teclado pasaba por toda la
      barra lateral y la superior en CADA página.

La parte visual se comprobó en el navegador el 13/09/2026 con un móvil emulado
(375px, puntero táctil): barra lateral, login, Scanner, Watchlist, Options,
Community, CANSLIM y SPXL, sin ningún control por debajo de 44px y sin scroll
horizontal nuevo. Este fichero es el candado para que no se deshaga.

Uso:
    cd backend
    python -m pytest tests/test_accesibilidad_resto.py -v
"""
import os
import re

FRONT = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')


def _leer(*partes):
    with open(os.path.join(FRONT, *partes), encoding='utf-8') as f:
        return f.read()


def _ficheros():
    for base, _dirs, nombres in os.walk(FRONT):
        for n in nombres:
            if n.endswith(('.js', '.html')) and '.min.' not in n:
                yield os.path.join(base, n)


def _regla(css, selector_regex):
    # Sin comentarios: el texto que explica por qué NO se usa algo lo nombra.
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    m = re.search(selector_regex + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else None


# ── (d) ─────────────────────────────────────────────────────────────────────

def test_todas_las_imagenes_llevan_alt():
    faltan = []
    for ruta in _ficheros():
        with open(ruta, encoding='utf-8') as f:
            src = f.read()
        for m in re.finditer(r"<img\b", src):
            linea = src[src.rfind('\n', 0, m.start()) + 1:m.start()].lstrip()
            if linea.startswith(('//', '*')):
                continue
            fin = src.find('>', m.start())
            if not re.search(r'\balt=', src[m.start():fin]):
                faltan.append(f"{os.path.relpath(ruta, FRONT)}:{src.count(chr(10), 0, m.start()) + 1}")
    assert not faltan, "Imágenes sin alt: " + ", ".join(faltan)


# ── (e) ─────────────────────────────────────────────────────────────────────

def test_las_palabras_largas_se_parten_sin_cambiar_anchos():
    body = _regla(_leer('themes', 'base.css'), r"(?m)^body")
    assert body and re.search(r"overflow-wrap:\s*break-word", body), \
        "base.css debe llevar overflow-wrap: break-word en body"
    # `anywhere` cambia el ancho mínimo de las celdas y de los elementos flex:
    # encogería columnas de tablas en toda la terminal.
    assert "anywhere" not in body


def test_ningun_tema_lo_deshace():
    for n in os.listdir(os.path.join(FRONT, 'themes')):
        if n.endswith('.css') and n != 'base.css':
            assert not re.search(r"overflow-wrap:\s*normal|word-wrap:\s*normal", _leer('themes', n)), n


# ── (f) ─────────────────────────────────────────────────────────────────────

def test_con_el_dedo_los_controles_miden_44px():
    css = _leer('themes', 'base.css')
    bloque = re.search(r"@media \(pointer: coarse\)\s*\{(.*?)\n\}", css, re.S)
    assert bloque, "falta el bloque @media (pointer: coarse)"
    reglas = dict((sel.strip(), cuerpo) for sel, cuerpo in re.findall(r"([^{}]+)\{([^}]*)\}", bloque.group(1)))
    grande = [s for s, c in reglas.items() if re.search(r"min-height:\s*44px", c)]
    assert len(grande) == 1, reglas
    selector = grande[0]
    assert selector.startswith(":where("), "sin :where() la regla pisaría los estilos de temas y páginas"
    for control in ("button", "select", "textarea", ".nav-item", "input:not("):
        assert control in selector, f"{control} no llega a 44px"
    # Las casillas no se estiran a 44px, pero tampoco se quedan fuera: 24px.
    casillas = [c for s, c in reglas.items() if 'checkbox' in s and ':not(' not in s]
    assert casillas and re.search(r"min-height:\s*24px", casillas[0])


def test_el_boton_del_menu_movil_mide_44px():
    html = _leer('index.html')
    regla = re.search(r"#nav-toggle\s*\{[^}]*display:\s*inline-flex[^}]*\}", html).group(0)
    assert re.search(r"width:\s*44px", regla) and re.search(r"height:\s*44px", regla)


# ── (g) ─────────────────────────────────────────────────────────────────────

def test_el_enlace_de_salto_es_lo_primero_del_body():
    html = _leer('index.html')
    tras_body = html[html.index('<body>') + len('<body>'):].lstrip()
    assert tras_body.startswith('<a href="#main" class="saltar-al-contenido">'), tras_body[:80]
    assert '<main id="main">' in html


def test_el_enlace_esta_escondido_sin_sacarlo_del_teclado():
    css = _leer('themes', 'base.css')
    oculto = _regla(css, r"\.saltar-al-contenido")
    assert oculto and "translateY(" in oculto
    # display:none o visibility:hidden lo quitarían del orden del tabulador.
    assert "display" not in oculto and "visibility" not in oculto
    visible = _regla(css, r"\.saltar-al-contenido:focus")
    assert visible and re.search(r"transform:\s*none", visible)


def test_el_salto_enfoca_el_contenido_sin_tocar_la_url():
    js = _leer('core', 'router.js')
    i = js.index("closest('.saltar-al-contenido')")
    manejador = js[i:js.index("});", i)]
    # Sin preventDefault el hash cambia, salta popstate y el router repinta.
    assert "e.preventDefault()" in manejador
    assert "setAttribute('tabindex', '-1')" in manejador
    assert "main.focus()" in manejador
