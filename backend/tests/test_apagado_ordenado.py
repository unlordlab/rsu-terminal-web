"""
Trece tareas de fondo se cancelaban al apagar y ninguna se esperaba.

EL CASO, 09/09/2026, verificando la bolsa de «sin comprobar» de
Infraestructura (#16). El `lifespan` de `main.py` llamaba a `.cancel()` sobre
las trece tareas y salía.

CANCELAR NO PARA NADA POR SÍ SOLO. `Task.cancel()` marca la tarea; el bucle no
se entera hasta que vuelve a un `await`, y si el proceso se cierra antes, eso
no llega a pasar. El resultado es un apagado con trece tareas a medias — una
escribiendo en SQLite se queda a mitad de operación — y Python rematando con
«Task was destroyed but it is pending!» en los registros.

EL ARREGLO ES UNA LÍNEA: `await asyncio.gather(*tareas, return_exceptions=True)`
después de cancelarlas. El `return_exceptions` no es adorno: una tarea
cancelada levanta `CancelledError` **por diseño**, así que sin él la primera
abortaría la espera de las otras doce — el mismo apagado a medias con otra
forma.

Y LA OTRA MITAD, QUE ES LA QUE SE ROMPE SOLA CON EL TIEMPO: crear y cancelar
son dos listas de trece líneas que hay que mantener a mano. Hoy cuadran. El día
que alguien añada una tarea de fondo y no toque el apagado, esa tarea se queda
sin cancelar y nada lo dirá. Por eso aquí se comprueba **por AST** que las dos
cuentas coinciden.

Uso:
    cd backend
    python -m pytest tests/test_apagado_ordenado.py -v
"""
import ast
import io
import os

RUTA = os.path.join(os.path.dirname(__file__), "..", "main.py")


def _arbol():
    return ast.parse(io.open(RUTA, encoding="utf-8").read())


def _lifespan():
    for n in ast.walk(_arbol()):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "lifespan":
            return n
    raise AssertionError("no se encuentra lifespan() en main.py")


# ── Se esperan, no solo se cancelan ──────────────────────────────────────────

def test_las_tareas_se_ESPERAN_despues_de_cancelarlas():
    """EL test. Sin el `gather`, el proceso se cierra con las tareas a medias."""
    cuerpo = _lifespan()
    gathers = [n for n in ast.walk(cuerpo)
               if isinstance(n, ast.Call)
               and getattr(n.func, "attr", "") == "gather"]
    assert gathers, (
        "se cancelan las tareas pero no se espera a ninguna: cancelar solo las "
        "marca, y si el proceso se cierra antes del siguiente await, no se "
        "enteran")


def test_el_gather_NO_aborta_a_la_primera_cancelacion():
    """Una tarea cancelada levanta CancelledError por diseño. Sin
    `return_exceptions=True`, la primera se lleva por delante la espera de las
    otras doce y el apagado vuelve a quedarse a medias, solo que más difícil de
    ver."""
    gather = next(n for n in ast.walk(_lifespan())
                  if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "gather")
    kw = {k.arg: k.value for k in gather.keywords}
    assert "return_exceptions" in kw, "falta return_exceptions en el gather"
    assert getattr(kw["return_exceptions"], "value", False) is True


def test_se_espera_DESPUES_de_cancelar_no_antes():
    """Al revés no apagaría nada: esperar a tareas que corren para siempre
    dejaría el apagado colgado indefinidamente."""
    cuerpo = _lifespan()
    linea_cancel = max(n.lineno for n in ast.walk(cuerpo)
                       if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "cancel")
    linea_gather = next(n.lineno for n in ast.walk(cuerpo)
                        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "gather")
    assert linea_gather > linea_cancel, (
        "se espera a las tareas ANTES de cancelarlas: el apagado se colgaría")


# ── Que crear y apagar no se desincronicen ───────────────────────────────────

def test_se_cancelan_TODAS_las_tareas_que_se_crean():
    """La comprobación que sobrevive al tiempo. Crear y apagar son dos listas
    que hay que mantener a mano; el día que alguien añada un bucle de fondo y
    no toque el apagado, esa tarea se queda viva y nada lo dice."""
    cuerpo = _lifespan()
    creadas = {n.targets[0].id for n in ast.walk(cuerpo)
               if isinstance(n, ast.Assign)
               and isinstance(n.value, ast.Call)
               and getattr(n.value.func, "attr", "") == "create_task"
               and n.targets and isinstance(n.targets[0], ast.Name)}
    esperadas = {n.id for n in ast.walk(cuerpo)
                 if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load)
                 and n.id in creadas}
    olvidadas = creadas - esperadas
    assert not olvidadas, (
        f"tareas creadas y nunca apagadas: {sorted(olvidadas)}. Se quedan vivas "
        f"al cerrar el proceso")
    assert len(creadas) >= 13, f"solo se detectan {len(creadas)} tareas de fondo"


def test_todas_las_tareas_de_fondo_van_SUPERVISADAS():
    """Lo que cerró el #7: si una muere, tiene que decirlo. Un `create_task`
    directo sobre un bucle largo lo devolvería al silencio."""
    cuerpo = _lifespan()
    for n in ast.walk(cuerpo):
        if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "create_task":
            interna = n.args[0] if n.args else None
            assert isinstance(interna, ast.Call), "create_task sin llamada dentro"
            nombre = getattr(interna.func, "attr", "") or getattr(interna.func, "id", "")
            assert nombre == "supervisar", (
                f"una tarea de fondo se crea sin supervisar ({nombre}): si muere, "
                f"muere en silencio")
