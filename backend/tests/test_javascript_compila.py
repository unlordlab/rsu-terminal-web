"""
1.198 tests en verde, CI en verde, y la página de login no cargaba en producción.

EL CASO, 09/09/2026. En el commit de accesibilidad escribí un comentario dentro
del HTML de `login.js`:

    <!-- ... El `min-height` ya estaba y aqui importa el doble ... -->

Ese HTML vive dentro de un **template literal** de JavaScript — una cadena
delimitada por acentos graves. El acento grave que puse alrededor de
`min-height` **cerró la cadena**, y a partir de ahí el navegador leyó
`min-height` como código: `SyntaxError: Unexpected identifier 'min'`. El módulo
entero dejaba de cargar, así que **la pantalla de acceso no se pintaba**.

POR QUÉ NO LO VIO NADIE:

  - La suite entera es de Python. **Ningún test de Python puede detectar un
    error de sintaxis en JavaScript**: los tests que miran ficheros `.js` los
    leen como TEXTO y buscan cadenas. El mío comprobaba que `login.js`
    contuviera `role="alert"`. Y lo contenía. En un fichero que no compilaba.
  - El CI pasó en verde por lo mismo.
  - Y la verificación en el navegador que sí hice cubrió el CSS de movimiento
    reducido por CSSOM, pero **nunca cargó `login.js`**.

Tres capas y ninguna miraba lo único que importaba: que el fichero se pueda
parsear.

QUÉ HACE ESTE FICHERO. Parsea DE VERDAD todos los `.js` del frontend con Node,
que es el mismo motor de JavaScript del navegador. No busca patrones peligrosos
—esa lista siempre se queda corta— sino que le pide al parser que lo lea.

Se copia cada fichero a `.mjs` antes de comprobarlo: `node --check` trata los
`.js` como CommonJS, donde un `import` de primer nivel ya es error de sintaxis;
con extensión `.mjs` lo parsea como módulo, que es lo que son.

Si no hay Node, el test se SALTA en vez de fingir que pasa. En el runner de
GitHub Actions siempre lo hay, que es donde de verdad hace falta.

Uso:
    cd backend
    python -m pytest tests/test_javascript_compila.py -v
"""
import glob
import os
import shutil
import subprocess
import tempfile

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
FRONTEND = os.path.join(RAIZ, "frontend")


def _node():
    for nombre in ("node", "node.exe"):
        ruta = shutil.which(nombre)
        if ruta:
            return ruta
    return None


def ficheros_js():
    return sorted(glob.glob(os.path.join(FRONTEND, "**", "*.js"), recursive=True))


def test_en_CI_tiene_que_haber_Node():
    """Sin esto, el día que el runner se quede sin Node los tres tests de abajo
    se SALTAN y el CI sigue en verde — con el comprobador desactivado y nadie
    enterándose. Un skip silencioso es la forma más cómoda de perder una red de
    seguridad. En local sí puede faltar."""
    if os.environ.get("CI", "").lower() in ("true", "1"):
        assert _node() is not None, (
            "Node no está en el runner: el comprobador de JavaScript no se ha "
            "ejecutado. Revisa el paso de setup-node en el workflow.")


def test_se_encuentran_los_ficheros_js():
    """Si el glob dejara de encontrarlos, el test de abajo pasaría sin mirar
    nada — que es exactamente la clase de fallo que este fichero existe para
    evitar."""
    assert len(ficheros_js()) >= 20, f"solo se encuentran {len(ficheros_js())} ficheros .js"


@pytest.mark.skipif(_node() is None, reason="Node no está instalado en esta máquina")
def test_TODOS_los_js_del_frontend_se_pueden_parsear():
    """EL test. Un fichero que no compila no falla al desplegarlo ni al
    ejecutar la suite: falla en el navegador del usuario, y la pantalla se
    queda en blanco."""
    node = _node()
    rotos = []
    with tempfile.TemporaryDirectory() as tmp:
        for ruta in ficheros_js():
            destino = os.path.join(tmp, "comprobar.mjs")
            shutil.copyfile(ruta, destino)
            r = subprocess.run([node, "--check", destino],
                               capture_output=True, text=True)
            if r.returncode != 0:
                error = (r.stderr or "").strip().split("\n")
                # La línea útil del error de Node, sin el volcado de pila.
                detalle = next((l for l in error if "Error" in l), error[0] if error else "?")
                rotos.append(f"{os.path.relpath(ruta, RAIZ)}: {detalle}")
    assert not rotos, "ficheros JavaScript que no compilan:\n  " + "\n  ".join(rotos)


@pytest.mark.skipif(_node() is None, reason="Node no está instalado en esta máquina")
def test_el_comprobador_CAZA_un_fichero_roto():
    """Que el test de arriba pase no significa nada si el comprobador no puede
    fallar. Se le da el fallo exacto del 09/09 — un acento grave dentro de un
    template literal — y tiene que rechazarlo."""
    node = _node()
    roto = "export const html = `<div><!-- el `min-height` de aqui -->></div>`;\n"
    with tempfile.TemporaryDirectory() as tmp:
        destino = os.path.join(tmp, "roto.mjs")
        with open(destino, "w", encoding="utf-8") as f:
            f.write(roto)
        r = subprocess.run([node, "--check", destino], capture_output=True, text=True)
    assert r.returncode != 0, "el comprobador acepta un fichero roto: no sirve de nada"
    assert "min" in (r.stderr or ""), r.stderr


@pytest.mark.skipif(_node() is None, reason="Node no está instalado en esta máquina")
def test_el_comprobador_ACEPTA_un_modulo_normal():
    """El otro lado: si rechazara cualquier cosa, el test de arriba fallaría
    siempre y acabaría desactivado. `import`/`export` de primer nivel tienen
    que valer — son módulos, no CommonJS."""
    node = _node()
    bueno = ("import { x } from './otro.js';\n"
             "export function f() { return `plantilla ${x} valida`; }\n")
    with tempfile.TemporaryDirectory() as tmp:
        destino = os.path.join(tmp, "bueno.mjs")
        with open(destino, "w", encoding="utf-8") as f:
            f.write(bueno)
        r = subprocess.run([node, "--check", destino], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
