"""
Watchlist #22: ningún dato dentro de un onclick.

EL CASO. 24 enlaces en 11 páginas llevaban el ticker metido en el propio
atributo — onclick="goToResearch('NVDA')" — y dentro de un onclick escapar HTML
no protege: el navegador descodifica el atributo (`&#39;` vuelve a ser una
comilla) ANTES de ejecutar el JavaScript, así que una comilla en el dato cierra
el string y lo que venga detrás se ejecuta. Cuatro de esos 24 ni siquiera
escapaban. Y el del News Feed usaba encodeURIComponent, que tampoco sirve:
no codifica la comilla simple.

Hoy no había un vector abierto conocido, pero la seguridad de 24 enlaces
dependía de que ninguna fuente de datos cambiara nunca.

EL ARREGLO: el dato va en un atributo data-* (el navegador lo entrega como
texto y nunca lo ejecuta) y un único escuchador en core/router.js decide qué
hacer. Este test es el candado para que no vuelva: recorre TODO el frontend y
falla si algún onclick concatena algo que no esté en la lista corta de
identificadores internos permitidos.

Uso:
    cd backend
    python -m pytest tests/test_onclick_sin_datos.py -v
"""
import os
import re

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')

# Lo único que se permite concatenar dentro de un onclick: identificadores que
# fabrica el propio código (ids de tabla, claves de columna, ids de iframe) y
# que no pueden venir de fuera. Añadir algo aquí es una decisión, no un atajo.
PERMITIDOS = {"tvFrameId", "tableId", "c.key"}

# El atributo acaba en la comilla doble que va seguida de espacio, `>`, `/`, o
# del cierre de un string JS (' o `). Sin la comilla invertida, un
# `onclick="…"` dentro de una plantilla se comía el resto de la línea y daba
# falsos positivos.
_ONCLICK = re.compile(r'onclick="(.*?)"(?=[\s>/\'`])', re.S)
_CONCAT  = re.compile(r"'\s*\+\s*(.+?)\s*\+\s*'")
_PLANTILLA = re.compile(r"\$\{(.+?)\}")


def _ficheros():
    for base, _, nombres in os.walk(RAIZ):
        if "node_modules" in base:
            continue
        for n in nombres:
            if n.endswith(".js"):
                yield os.path.join(base, n)


def test_ningun_onclick_lleva_datos_dentro():
    malos = []
    for ruta in _ficheros():
        texto = open(ruta, encoding="utf-8").read()
        for m in _ONCLICK.finditer(texto):
            cuerpo = m.group(1)
            exprs = _CONCAT.findall(cuerpo) + _PLANTILLA.findall(cuerpo)
            fuera = [e for e in exprs if e.strip() not in PERMITIDOS]
            if fuera:
                linea = texto[:m.start()].count("\n") + 1
                malos.append(f"{os.path.relpath(ruta, RAIZ)}:{linea} → {fuera}")
    assert not malos, (
        "onclick con datos dentro (usa data-research / data-add-watchlist / data-ir):\n  "
        + "\n  ".join(malos))


def test_el_candado_detecta_de_verdad_lo_que_prohibe():
    """Un test que no puede fallar no protege nada: se le enseñan las formas
    exactas que había antes del arreglo."""
    ejemplos = [
        """'<div onclick="goToResearch(\\'' + esc(c.ticker) + '\\')" class="x">'""",
        """'<span onclick="window.__navigate(\\'/research?ticker=' + w.ticker + '\\')">'""",
        """`<span onclick="window.__optionsSearchTicker('${esc(t.ticker)}')" style="x">`""",
    ]
    for ej in ejemplos:
        m = _ONCLICK.search(ej)
        assert m, f"el patrón ni siquiera encuentra el onclick en: {ej}"
        exprs = _CONCAT.findall(m.group(1)) + _PLANTILLA.findall(m.group(1))
        assert any(e.strip() not in PERMITIDOS for e in exprs), f"no lo detecta: {ej}"


def test_el_escuchador_global_atiende_los_tres_atributos():
    js = open(os.path.join(RAIZ, "core", "router.js"), encoding="utf-8").read()
    assert "document.addEventListener('click'" in js
    for attr in ("data-research", "data-add-watchlist", "data-ir"):
        assert attr in js, f"el escuchador global no atiende {attr}"


def test_data_ir_solo_navega_a_rutas_internas():
    """Un data-ir con «//otro-dominio.com» o «javascript:» no puede salir de la
    app: la ruta tiene que empezar por una sola barra."""
    js = open(os.path.join(RAIZ, "core", "router.js"), encoding="utf-8").read()
    assert "ruta.startsWith('/') && !ruta.startsWith('//')" in js


def test_nadie_engancha_un_segundo_escuchador_a_data_ir():
    """El Dashboard le ponía uno propio al botón de Academy: con el global
    delante, navegaba DOS veces y «atrás» no volvía."""
    for ruta in _ficheros():
        if ruta.endswith("router.js"):
            continue
        texto = open(ruta, encoding="utf-8").read()
        assert not re.search(r"querySelector\(\s*'\[data-ir\]'\s*\)", texto), (
            f"{os.path.relpath(ruta, RAIZ)} vuelve a engancharse a data-ir por su cuenta")
