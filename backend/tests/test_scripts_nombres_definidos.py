"""
`NameError: name 'segunda' is not defined`, con los dos briefings ya escritos.

EL CASO, 09/09/2026. El briefing del día se perdió en la ÚLTIMA línea antes de
publicar:

    💾 Guardando en GitHub Gist...
    File "scripts/daily_briefing.py", line 2753, in save_to_gist
        news, major_headlines, segunda_lectura=segunda,
    NameError: name 'segunda' is not defined

Al conectar la segunda lectura y la revisión previa metí `segunda_lectura=segunda`
y `revision=revision` en la llamada a `construir_payload()` — pero esa llamada
vive en `save_to_gist()`, y las dos variables se calculan en `main()`. Los dos
modelos habían escrito ya (580 y 470 palabras, sesgo BAJISTA los dos) y todo se
tiró a la basura en la línea de guardar.

MI COMPROBACIÓN AL EDITAR FUE `assert count == 1` SOBRE EL TEXTO DE LA LLAMADA,
Y ERA CIERTA: solo hay una llamada a `construir_payload` en todo el fichero. Lo
que no miré es **en qué función estaba**.

Y NO LO CAZÓ NADA MÁS. `py_compile` y `ast.parse` pasan — un nombre global que
no existe es un error de EJECUCIÓN, no de sintaxis. La suite tampoco: mis tests
llamaban a `construir_payload` directamente, así que el cableado de main() a
save_to_gist no lo ejercitaba nadie. Y el CI corre esa misma suite.

DE AHÍ ESTE FICHERO. No hay pyflakes ni ruff en el entorno, así que la
comprobación se hace aquí: recorrer cada función de los scripts y buscar
nombres que se LEEN sin estar definidos en ninguna parte alcanzable. Es la
única red que habría parado esto sin depender de que a mí se me ocurra el test
concreto.

Uso:
    cd backend
    python -m pytest tests/test_scripts_nombres_definidos.py -v
"""
import ast
import builtins
import glob
import io
import os

import pytest

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")
SCRIPTS = sorted(glob.glob(os.path.join(RAIZ, "scripts", "*.py"))
                 + glob.glob(os.path.join(RAIZ, "shared", "*.py"))
                 + glob.glob(os.path.join(RAIZ, "agents", "*.py")))

DUNDERS = {"__name__", "__file__", "__doc__", "__package__", "__spec__", "__builtins__"}


def _hijas(nodo):
    """Las funciones definidas DIRECTAMENTE dentro de esta, sin bajar más."""
    fuera = []
    def _mirar(n, raiz=False):
        for hijo in ast.iter_child_nodes(n):
            if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef)):
                fuera.append(hijo)
            elif not isinstance(hijo, ast.ClassDef):
                _mirar(hijo)
    _mirar(nodo, raiz=True)
    return fuera


def _params(args):
    p = {a.arg for a in list(args.args) + list(args.posonlyargs) + list(args.kwonlyargs)}
    if args.vararg:
        p.add(args.vararg.arg)
    if args.kwarg:
        p.add(args.kwarg.arg)
    return p


def _ligados_aqui(nodo, incluir_params=True):
    """Lo que queda definido en ESTE ámbito, sin entrar en funciones anidadas.

    De las anidadas se queda su NOMBRE (que sí es visible desde fuera) pero no
    su interior, que se revisa aparte con el ámbito heredado.

    Los parámetros de `lambda` se recogen aunque técnicamente solo existan
    dentro de ella: no distinguirlos producía cuatro avisos falsos (`x`, `c`,
    `d`) y un comprobador que avisa en falso se desactiva el primer día.
    """
    ligados = set(_params(nodo.args)) if incluir_params and hasattr(nodo, "args") else set()

    def _recorrer(n, raiz=False):
        for hijo in ast.iter_child_nodes(n):
            if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                ligados.add(hijo.name)
                continue                       # su interior se revisa aparte
            if isinstance(hijo, ast.Lambda):
                ligados.update(_params(hijo.args))
            if isinstance(hijo, ast.Name) and isinstance(hijo.ctx, (ast.Store, ast.Del)):
                ligados.add(hijo.id)
            elif isinstance(hijo, (ast.Import, ast.ImportFrom)):
                for alias in hijo.names:
                    ligados.add((alias.asname or alias.name).split(".")[0])
            elif isinstance(hijo, ast.ExceptHandler) and hijo.name:
                ligados.add(hijo.name)
            elif isinstance(hijo, (ast.Global, ast.Nonlocal)):
                ligados.update(hijo.names)
            _recorrer(hijo)
    _recorrer(nodo, raiz=True)
    return ligados


def _leidos_aqui(nodo):
    """Nombres leídos en este ámbito, sin bajar a las funciones anidadas."""
    leidos = set()

    def _recorrer(n):
        for hijo in ast.iter_child_nodes(n):
            if isinstance(hijo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if isinstance(hijo, ast.Name) and isinstance(hijo.ctx, ast.Load):
                leidos.add(hijo.id)
            _recorrer(hijo)
    _recorrer(nodo)
    return leidos


def _sueltos(ruta):
    """Nombres que una función LEE y que no existen en ningún ámbito alcanzable.

    El ámbito se arrastra hacia dentro: una función anidada ve las variables de
    la que la contiene. Sin eso salían nueve avisos falsos solo en
    `daily_briefing.py` — closures perfectamente correctas.
    """
    arbol = ast.parse(io.open(ruta, encoding="utf-8").read())
    fuera = []
    base = _ligados_aqui(arbol, incluir_params=False) | set(dir(builtins)) | DUNDERS

    def _revisar(nodo, heredados):
        disponibles = heredados | _ligados_aqui(nodo)
        for nombre in sorted(_leidos_aqui(nodo) - disponibles):
            fuera.append((nodo.name, nodo.lineno, nombre))
        for hija in _hijas(nodo):
            _revisar(hija, disponibles)

    for n in arbol.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            _revisar(n, base)
        elif isinstance(n, ast.ClassDef):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    _revisar(m, base | _ligados_aqui(n))
    return fuera


@pytest.mark.parametrize("ruta", SCRIPTS, ids=[os.path.basename(r) for r in SCRIPTS])
def test_ninguna_funcion_lee_un_nombre_que_no_existe(ruta):
    """EL test. Habría parado el fallo del 09/09 antes de llegar a producción.

    `py_compile` y `ast.parse` pasan con un global inexistente: es un error de
    ejecución. Y la suite no lo veía porque nadie ejercitaba el camino de
    main() a save_to_gist."""
    sueltos = _sueltos(ruta)
    assert not sueltos, "nombres leídos que no están definidos:\n" + "\n".join(
        f"  {os.path.basename(ruta)}:{linea}  en {func}()  ->  «{nombre}»"
        for func, linea, nombre in sueltos)


def test_la_comprobacion_CAZA_el_fallo_real_del_09_09():
    """Un test de la comprobación, no del código: si esto no cazara nada, el de
    arriba sería verde para siempre sin proteger nada.

    Se reproduce el fallo exacto — una función que usa una variable calculada
    en OTRA — y se exige que salga."""
    codigo = (
        "def main():\n"
        "    segunda = generar()\n"
        "    guardar()\n"
        "\n"
        "def guardar():\n"
        "    return construir(segunda_lectura=segunda)\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(codigo)
        ruta = f.name
    try:
        sueltos = _sueltos(ruta)
    finally:
        os.unlink(ruta)
    nombres = {n for _, _, n in sueltos}
    assert "segunda" in nombres, (
        f"la comprobación no detecta el fallo que costó el briefing del 09/09: {sueltos}")
    assert "guardar" not in nombres and "construir" in nombres, (
        "debe distinguir una función definida en el módulo de una que no existe")


def test_no_se_queja_de_lo_que_SI_esta_definido():
    """Sin esto la comprobación daría avisos a diario y se acabaría quitando —
    que es como muere cualquier guardián de este proyecto."""
    codigo = (
        "import os\n"
        "GLOBAL = 1\n"
        "def f(a, *args, b=2, **kw):\n"
        "    [x for x in range(3)]\n"
        "    with open('x') as fh:\n"
        "        pass\n"
        "    try:\n"
        "        pass\n"
        "    except ValueError as e:\n"
        "        print(e)\n"
        "    y = a + b + GLOBAL + len(args) + len(kw)\n"
        "    return os.path.join(str(y), fh.name)\n"
    )
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     encoding="utf-8") as f:
        f.write(codigo)
        ruta = f.name
    try:
        assert _sueltos(ruta) == []
    finally:
        os.unlink(ruta)


def test_se_revisan_los_scripts_de_verdad():
    """Si el glob dejara de encontrar ficheros, el test de arriba pasaría sin
    mirar nada."""
    assert len(SCRIPTS) >= 10, f"solo se están revisando {len(SCRIPTS)} ficheros"
    assert any(r.endswith("daily_briefing.py") for r in SCRIPTS)
