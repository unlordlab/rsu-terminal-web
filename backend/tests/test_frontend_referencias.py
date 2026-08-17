"""
Ningún fichero del frontend puede llamar a una función que no existe.

EL CASO QUE MOTIVA ESTE TEST. El 08/08/2026, el commit que movió el token de
sesión a una cookie httpOnly borró la función local `authHeaderDash()` de
dashboard.js y actualizó UNA de sus seis llamadas. Las otras cinco se quedaron
invocando algo inexistente:

    fetch('/api/v1/market/indices',  { headers: authHeaderDash() })
    fetch('/api/v1/market/briefing', { headers: authHeaderDash() })
    fetch('/api/v1/watchlist',       { headers: authHeaderDash() })

Un `ReferenceError` dentro de una función `async` no revienta la página: hace
que la promesa se rechace, y cada bloque de carga tiene su propio `catch`, así
que las tres secciones simplemente se quedaron vacías. Estuvieron NUEVE DÍAS
así -- la franja de activos del dashboard, el resumen del briefing y el de la
watchlist -- y lo reportó el usuario, no el proyecto.

Ni los tests ni el navegador lo detectaban: los de backend no cargan JS, y en el
navegador el error solo sale por consola, que hay que estar mirando.

POR QUÉ HAY UN TOKENIZADOR AQUÍ. La primera versión de este test troceaba las
cadenas con expresiones regulares y se ahogó en falsos positivos: el CSS que
estas páginas construyen dentro de cadenas (`var(...)`, `rgba(...)`), la prosa
de los tooltips («ACUMULACIÓN (por debajo de 50)»), y sobre todo los apóstrofos
de textos reales del proyecto («d'emmagatzematge»), que descuadraban el resto
del fichero y hacían que definiciones normales pareciesen inexistentes. Un
tokenizador de estado son cuarenta líneas y no falla en ninguno de esos casos.

Uso:
    cd backend
    python -m pytest tests/test_frontend_referencias.py -v
"""
import os
import re

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')

# Librerías de terceros: minificadas, no son código nuestro.
EXCLUIDOS = ("assets", "vendor", "lib")

# Globales del lenguaje y del navegador, que se usan sin importar nada.
GLOBALES = {
    "Object", "Array", "String", "Number", "Boolean", "Math", "JSON", "Date",
    "Map", "Set", "WeakMap", "WeakSet", "Promise", "Error", "TypeError",
    "RegExp", "Symbol", "BigInt", "Proxy", "Reflect", "Intl",
    "parseInt", "parseFloat", "isNaN", "isFinite", "structuredClone",
    "encodeURIComponent", "decodeURIComponent", "encodeURI", "decodeURI",
    "fetch", "alert", "confirm", "prompt", "setTimeout", "setInterval",
    "clearTimeout", "clearInterval", "requestAnimationFrame", "reportError",
    "cancelAnimationFrame", "getComputedStyle", "matchMedia", "atob", "btoa",
    "URLSearchParams", "URL", "FormData", "Blob", "File", "FileReader",
    "Image", "Audio", "WebSocket", "Worker", "Notification", "Response",
    "Request", "Headers", "IntersectionObserver", "MutationObserver",
    "ResizeObserver", "CustomEvent", "Event", "KeyboardEvent", "MouseEvent",
    "AbortController", "TextDecoder", "TextEncoder", "queueMicrotask",
    # librerías que llegan por <script> global
    "Chart", "marked", "hljs", "html2canvas", "jsPDF", "LightweightCharts",
    # palabras clave que preceden a un paréntesis
    "if", "for", "while", "switch", "catch", "return", "typeof", "function",
    "await", "new", "delete", "void", "in", "of", "do", "else", "case",
    "yield", "throw", "super", "import", "constructor", "async", "get", "set",
    "instanceof", "extends",
}

# Solo se vigilan los identificadores en camelCase, que es la forma que tienen
# las funciones de este proyecto (authHeaderDash, renderActiveSection...). Deja
# fuera de un plumazo el ruido que no es codigo: las funciones de CSS (var,
# rgba, calc), la prosa en castellano dentro de las cadenas ("alcista",
# "posicion") y las etiquetas en mayusculas de los graficos de la academia.
CAMELCASE = re.compile(r"[a-z_$][a-z0-9_$]*[A-Z][\w$]*")

LLAMADA = re.compile(r"(?<![.\w$])([A-Za-z_$][\w$]*)\s*\(")
DEFINE = re.compile(
    r"(?:function\s*\*?\s*([A-Za-z_$][\w$]*)"       # function foo()
    r"|(?:const|let|var)\s+([A-Za-z_$][\w$]*)"      # const foo = ...
    r"|class\s+([A-Za-z_$][\w$]*)"                  # class Foo
    r"|([A-Za-z_$][\w$]*)\s*:\s*(?:async\s+)?(?:function|\()"   # foo: () => ...
    r"|([A-Za-z_$][\w$]*)\s*=\s*(?:async\s+)?(?:function|\()"   # foo = () => ...
    # Método abreviado de clase u objeto: `_showPopup(trigger) {`. Sin esto, la
    # propia definición se contaba como una llamada a algo inexistente.
    r"|^[ \t]*(?:async[ \t]+)?([A-Za-z_$][\w$]*)[ \t]*\([^)]*\)[ \t]*\{"
    r")",
    re.M,
)

# `const resY = py(64), breakoutX = px(7);` -- DEFINE solo veía el primero.
DECLARADORES = re.compile(r"(?:const|let|var)\s+([^;\n]+)")
IMPORTA = re.compile(r"import\s+(?:\*\s+as\s+([\w$]+)|([\w$]+)\s*,?\s*)?(?:\{([^}]*)\})?\s*from")
PARAMS = re.compile(r"(?:function\s*[\w$]*\s*\(([^)]*)\)|\(([^)]*)\)\s*=>|([\w$]+)\s*=>)")
DESTRUCTURA = re.compile(r"(?:const|let|var)\s*\{([^}]*)\}\s*=")


def _ficheros():
    for base, dirs, ficheros in os.walk(RAIZ):
        dirs[:] = [d for d in dirs if d not in EXCLUIDOS]
        for f in sorted(ficheros):
            if f.endswith(".js") and not f.endswith(".min.js"):
                yield os.path.join(base, f)


def solo_codigo(src: str) -> str:
    """Sustituye comentarios y el TEXTO de las cadenas por espacios, conservando
    los saltos de línea (para que los números de línea sigan cuadrando) y el
    contenido de las interpolaciones `${...}`, que sí es código.

    Es un recorrido carácter a carácter con estado, no una expresión regular:
    hace falta para no tropezar con apóstrofos dentro de textos, comillas
    dentro de comillas de otro tipo, o barras de división confundidas con el
    inicio de una expresión regular.
    """
    out = []
    i, n = 0, len(src)
    pila_plantillas = 0          # profundidad de `${ ... }` dentro de plantillas
    while i < n:
        c = src[i]
        dos = src[i:i + 2]
        if dos == "//":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(" " * (j - i)); i = j
        elif dos == "/*":
            j = src.find("*/", i + 2)
            j = n if j == -1 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        elif c in "'\"":
            comilla, j = c, i + 1
            while j < n and src[j] != comilla:
                j += 2 if src[j] == "\\" else 1
            j = min(j + 1, n)
            out.append("".join(ch if ch == "\n" else " " for ch in src[i:j])); i = j
        elif c == "`":
            j = i + 1
            out.append(" ")
            while j < n and src[j] != "`":
                if src[j] == "\\":
                    out.append("  "); j += 2; continue
                if src[j:j + 2] == "${":
                    # Se conserva el interior: es código de verdad.
                    prof, k = 1, j + 2
                    out.append("  ")
                    while k < n and prof:
                        if src[k] == "{": prof += 1
                        elif src[k] == "}": prof -= 1
                        if prof: out.append(src[k])
                        k += 1
                    out.append(" "); j = k
                    continue
                out.append("\n" if src[j] == "\n" else " "); j += 1
            out.append(" "); i = min(j + 1, n)
        else:
            out.append(c); i += 1
    return "".join(out)


def _globales_de_window(ficheros) -> set:
    """Funciones que un fichero cuelga de `window` para que otro las invoque
    desde un `onclick` del HTML. Sin esto, todas parecerían inexistentes."""
    nombres = set()
    for ruta in ficheros:
        with open(ruta, encoding="utf-8") as fh:
            for m in re.finditer(r"window\.([A-Za-z_$][\w$]*)\s*=", fh.read()):
                nombres.add(m.group(1))
    return nombres


def _nombres_disponibles(src: str) -> set:
    n = set()
    for m in DEFINE.finditer(src):
        n.update(g for g in m.groups() if g)
    for m in IMPORTA.finditer(src):
        estrella, defecto, llaves = m.groups()
        if estrella: n.add(estrella)
        if defecto:  n.add(defecto)
        if llaves:
            for parte in llaves.split(","):
                parte = parte.strip()
                if parte:
                    n.add(parte.split(" as ")[-1].strip())
    for m in DECLARADORES.finditer(src):
        for trozo in m.group(1).split(","):
            nombre = trozo.split("=")[0].strip()
            if re.fullmatch(r"[A-Za-z_$][\w$]*", nombre):
                n.add(nombre)
    for regex in (PARAMS, DESTRUCTURA):
        for m in regex.finditer(src):
            for grupo in m.groups():
                if not grupo:
                    continue
                for p in grupo.split(","):
                    p = p.strip().lstrip(".").split("=")[0].split(":")[0].strip()
                    if re.fullmatch(r"[A-Za-z_$][\w$]*", p or ""):
                        n.add(p)
    return n


def test_ninguna_llamada_a_una_funcion_que_no_existe():
    ficheros = list(_ficheros())
    de_window = _globales_de_window(ficheros)
    huerfanas = {}
    for ruta in ficheros:
        with open(ruta, encoding="utf-8") as fh:
            src = solo_codigo(fh.read())
        disponibles = _nombres_disponibles(src) | GLOBALES | de_window
        for m in LLAMADA.finditer(src):
            nombre = m.group(1)
            if nombre in disponibles or not CAMELCASE.fullmatch(nombre):
                continue
            linea = src[:m.start()].count("\n") + 1
            huerfanas.setdefault(os.path.relpath(ruta, RAIZ), []).append(
                f"{nombre}() linea {linea}")

    assert not huerfanas, (
        "Llamadas a funciones que no existen. Un ReferenceError dentro de un "
        "async se traga en el catch y la seccion se queda vacia sin avisar:\n"
        + "\n".join(f"  {f}: {', '.join(sorted(set(v)))}"
                    for f, v in sorted(huerfanas.items()))
    )


def test_el_tokenizador_no_confunde_texto_con_codigo():
    """Los tres casos reales que tumbaron las versiones anteriores del test."""
    caso = (
        "const css = 'color: var(--color-accent); background: rgba(0,0,0,.5)';\n"
        "const tesis = \"Supercycle d'emmagatzematge d'IA\";\n"
        "const ayuda = `ACUMULACIÓN (por debajo de 50) mide ${calcular(x)} cosas`;\n"
        "function calcular(x) { return x; }\n"
        "miFuncionReal();\n"
    )
    limpio = solo_codigo(caso)
    for ruido in ("var(", "rgba(", "ACUMULACIÓN ("):
        assert ruido not in limpio, f"{ruido!r} deberia haberse ido con el texto"
    assert "calcular(x)" in limpio, "lo de dentro de ${...} es codigo y debe quedarse"
    assert "miFuncionReal(" in limpio
    assert limpio.count("\n") == caso.count("\n"), "los numeros de linea se descuadran"
