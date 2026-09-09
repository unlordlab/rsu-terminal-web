"""
Cada tesis pedida desde el Meeting Room contestaba «No he podido: NameError».

EL CASO, encontrado el 09/09/2026 por el comprobador de nombres sueltos que se
escribió para otra cosa — ver `test_scripts_nombres_definidos.py`.

`procesar_meeting_room()` leía `fallback`, que se calcula en `main()`. Cada
petición de tesis desde el Meeting Room lanzaba `NameError`, lo tragaba el
`except Exception as e` de esa función, y Gael respondía:

    «No he podido generar la tesis de X: NameError. Lo intento de nuevo en la
     próxima ejecución si me lo vuelves a pedir.»

Un fallo PERMANENTE con cara de fallo puntual del proveedor — y con una
invitación a reintentar que no podía funcionar nunca.

LO QUE SE COMPRUEBA AQUÍ, y no lo cubre el comprobador de nombres: que `main()`
le PASE el fallback. Con el parámetro ya declarado y su valor por defecto (`""`)
la llamada sin argumento no da error — simplemente deja el respaldo apagado en
silencio, que es el mismo tipo de fallo mudo pero un escalón más abajo. El
sabotaje «main() deja de pasarle el fallback» se escapó de todo lo demás.

Uso:
    cd backend
    python -m pytest tests/test_bull_meeting_room_fallback.py -v
"""
import ast
import inspect
import os
import sys
import textwrap

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'agents'))

os.environ.setdefault("GROQ_API_KEY", "solo-para-importar")

import bull_agent as B  # noqa: E402


def test_el_fallback_es_un_PARAMETRO_no_un_global_prestado():
    """La firma tiene que declararlo. Leerlo del ámbito de otra función es lo
    que rompía cada petición."""
    firma = inspect.signature(B.procesar_meeting_room)
    assert "fallback" in firma.parameters, (
        "procesar_meeting_room no recibe `fallback`: lo leería del ámbito de "
        "main(), donde no existe, y cada petición moriría con NameError")


def test_y_main_SE_LO_PASA():
    """Que la función sepa recibirlo no basta. Con el valor por defecto vacío,
    olvidarse de pasarlo no da error: solo apaga el respaldo en silencio, y por
    eso hace falta comprobarlo aparte del NameError."""
    arbol = ast.parse(textwrap.dedent(inspect.getsource(B.main)))
    llamadas = [n for n in ast.walk(arbol)
                if isinstance(n, ast.Call)
                and getattr(n.func, "id", "") == "procesar_meeting_room"]
    assert llamadas, "main() no llama a procesar_meeting_room"
    pasa_fallback = any(
        any(k.arg == "fallback" for k in ll.keywords) or len(ll.args) >= 3
        for ll in llamadas)
    assert pasa_fallback, (
        "main() no le pasa el fallback: el respaldo de proveedor queda apagado "
        "para las peticiones del Meeting Room, en silencio")


def test_el_valor_por_defecto_deja_el_respaldo_APAGADO():
    """Coherente con el resto del agente: el fallback se activa a propósito con
    `--fallback`, no por descuido. Un defecto distinto de vacío haría que el
    cron empezara a gastar en otro proveedor sin que nadie lo decidiera."""
    assert inspect.signature(B.procesar_meeting_room).parameters["fallback"].default == ""


def test_generar_tesis_sigue_recibiendolo_en_tercera_posicion():
    """Es donde lo pone la llamada. Si cambiara el orden de los parámetros, el
    proveedor de respaldo pasaría a ser otra cosa sin que nadie lo note."""
    params = list(inspect.signature(B.generar_tesis).parameters)
    assert params[:3] == ["ticker", "provider", "fallback"], params
