"""
Accesibilidad #2 (c): cada campo de formulario tiene un nombre que un lector de
pantalla pueda leer.

EL CASO. El barrido del 06/09 contó 42 `<input>` frente a 18 `<label>`. Un
`placeholder` NO es un nombre: muchos lectores no lo anuncian y desaparece en
cuanto se escribe. Quien navega con lector llegaba a «campo de texto, vacío» en
el buscador de Research, el formulario de alertas de Watchlist o el de
Community, sin saber qué se le pedía.

Lo que cuenta como nombre, en el orden en que lo mira el test:
  · `aria-label` o `aria-labelledby` en la propia etiqueta;
  · estar DENTRO de un `<label>…</label>`;
  · un `<label for="id">` con el mismo id en el mismo fichero;
  · no ser visible para nadie (`type="hidden"` o `display:none`).

Uso:
    cd backend
    python -m pytest tests/test_accesibilidad_formularios.py -v
"""
import os
import re

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')

_CAMPO = re.compile(r"<(input|select|textarea)\b")


def _ficheros():
    for base, _dirs, nombres in os.walk(RAIZ):
        for n in nombres:
            if n.endswith(('.js', '.html')) and '.min.' not in n:
                yield os.path.join(base, n)


def _etiqueta(src, ini):
    """Desde `<input` hasta el primer `>`: la etiqueta de apertura, aunque esté
    partida en varios trozos de string concatenados."""
    fin = src.find('>', ini)
    return src[ini:fin if fin != -1 else len(src)]


def _dentro_de_label(src, ini):
    antes = src[:ini]
    return antes.rfind('<label') > antes.rfind('</label>')


def campos_sin_nombre():
    faltan = []
    for ruta in _ficheros():
        with open(ruta, encoding='utf-8') as f:
            src = f.read()
        fors = set(re.findall(r'for="([^"]+)"', src))
        for m in _CAMPO.finditer(src):
            linea_entera = src[src.rfind('\n', 0, m.start()) + 1:m.start()].lstrip()
            if linea_entera.startswith(('//', '*')):
                continue  # un «<input» dentro de un comentario del código
            tag = _etiqueta(src, m.start())
            if re.search(r'aria-label(ledby)?=', tag):
                continue
            if 'type="hidden"' in tag or re.search(r'display:\s*none', tag):
                continue
            if _dentro_de_label(src, m.start()):
                continue
            mid = re.search(r'\bid="([^"]+)"', tag)
            if mid and mid.group(1) in fors:
                continue
            linea = src.count('\n', 0, m.start()) + 1
            faltan.append(f"{os.path.relpath(ruta, RAIZ)}:{linea}  {tag[:70]}")
    return faltan


def test_todos_los_campos_tienen_nombre_accesible():
    faltan = campos_sin_nombre()
    assert not faltan, "Campos sin nombre accesible:\n" + "\n".join(faltan)


def test_el_detector_ve_los_casos_que_debe_ver():
    # Candado del propio detector: si una regex se rompe y deja pasar todo,
    # el test de arriba pasaría en verde sin mirar nada.
    src = ('<input id="a" placeholder="x">'
           '<label>Uno <input id="b"></label>'
           '<label for="c">Dos</label><input id="c">'
           '<select aria-label="Tres"></select>'
           '<input type="checkbox" style="display:none;">'
           "'<textarea ' + 'placeholder=\"y\">")
    fors = set(re.findall(r'for="([^"]+)"', src))
    sin_nombre = []
    for m in _CAMPO.finditer(src):
        tag = _etiqueta(src, m.start())
        if re.search(r'aria-label(ledby)?=', tag) or re.search(r'display:\s*none', tag):
            continue
        if _dentro_de_label(src, m.start()):
            continue
        mid = re.search(r'\bid="([^"]+)"', tag)
        if mid and mid.group(1) in fors:
            continue
        sin_nombre.append(tag[:15])
    assert sin_nombre == ['<input id="a" p', "<textarea ' + '"], sin_nombre
