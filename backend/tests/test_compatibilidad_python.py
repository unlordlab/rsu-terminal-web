"""
El codigo tiene que compilar con la version de Python que corre el CI, no con
la del portatil.

EL CASO, 26/08/2026. Escribi una f-string con otra f-string dentro usando LA
MISMA comilla:

    f"{f" ({breadth['sp500_pct_al_alza']}% al alza)" if ... else ''}"

Eso es legal desde Python 3.12 (PEP 701) y un SyntaxError en 3.11. En local
(3.13) compilaba y los 805 tests pasaban en verde; en el CI, que corre 3.11, el
modulo entero fallaba al importarse y con el se caian todos sus tests.

`python -m py_compile` en local NO lo detecta: usa el interprete local. Y
`ast.parse(fuente, feature_version=(3, 11))` TAMPOCO -- lo probe y deja pasar
este caso, asi que una comprobacion basada en eso habria sido una guardia que
no guarda nada. Lo que si funciona es el TOKENIZADOR: desde 3.12 una f-string
emite FSTRING_START/END, y una anidada abre un segundo START antes de cerrar
el primero.

Uso:
    cd backend
    python -m pytest tests/test_compatibilidad_python.py -v
"""
import io
import pathlib
import token
import tokenize

# La que declara .github/workflows/tests.yml. Si el CI sube de version, este
# numero sube con el -- no al reves.
VERSION_CI = (3, 11)

RAIZ = pathlib.Path(__file__).resolve().parents[2]
CARPETAS = ("backend", "scripts", "shared")


def _fuentes():
    for carpeta in CARPETAS:
        for f in (RAIZ / carpeta).rglob("*.py"):
            partes = f.parts
            if "__pycache__" in partes or "worktrees" in partes or "venv" in partes:
                continue
            yield f


def fstrings_anidadas(fuente: str) -> list:
    """Lineas con una f-string dentro de otra usando LA MISMA comilla (PEP 701,
    Python 3.12+). Se detecta con el tokenizador porque es lo unico que lo ve:
    una f-string anidada abre un segundo FSTRING_START antes de cerrar el
    primero."""
    fallos, prof = [], 0
    try:
        for tk in tokenize.generate_tokens(io.StringIO(fuente).readline):
            if tk.type == getattr(token, "FSTRING_START", -1):
                prof += 1
                if prof > 1:
                    fallos.append(tk.start[0])
            elif tk.type == getattr(token, "FSTRING_END", -1):
                prof = max(0, prof - 1)
    except (tokenize.TokenError, SyntaxError):
        pass          # un fichero que ni tokeniza ya lo cazan los demas tests
    return fallos


def test_todo_el_codigo_compila_con_la_version_del_CI():
    """EL test. Sin esto, cualquier sintaxis nueva pasa en local y tumba el CI
    -- y el fallo llega DESPUES del push, no antes."""
    malos = []
    for f in _fuentes():
        for linea in fstrings_anidadas(f.read_text(encoding="utf-8")):
            malos.append(f"{f.relative_to(RAIZ)}:{linea}: f-string anidada con la misma comilla")
    assert not malos, (
        f"sintaxis no soportada por Python {VERSION_CI[0]}.{VERSION_CI[1]} "
        f"(la del CI):\n  " + "\n  ".join(malos))


def test_la_version_declarada_aqui_es_la_que_usa_el_CI():
    """Si el workflow sube de version y esta constante no, el test estaria
    protegiendo contra una version que ya no corre nadie."""
    wf = RAIZ / ".github" / "workflows" / "tests.yml"
    texto = wf.read_text(encoding="utf-8")
    esperado = f"'{VERSION_CI[0]}.{VERSION_CI[1]}'"
    assert esperado in texto, (
        f"el workflow no declara python-version {esperado}: actualiza "
        f"VERSION_CI en este fichero para que coincida")


def test_encuentra_de_verdad_una_sintaxis_demasiado_nueva():
    """Que el test pase no significa que sepa detectar nada. Aqui se le pone
    delante el caso exacto que fallo."""
    # Se construye por concatenacion para no pelearse con los escapes: la
    # linea de prueba es literalmente `x = f"{f" hola " if a else 1}"`.
    malo = 'x = f"{f\"hola\" if a else 1}"' + chr(10)
    assert fstrings_anidadas(malo) == [1], (
        "la comprobacion no detecta f-strings anidadas con la misma comilla: "
        "no protege de nada. Es justo lo que pasaba con ast.parse y "
        "feature_version, que deja pasar este caso")
    bueno = 'x = f"{y} hola {z}"' + chr(10)
    assert fstrings_anidadas(bueno) == [], "esta marcando codigo correcto"
