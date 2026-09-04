"""
El briefing decía «venderé cualquier rebote en el Nasdaq» a ~100 suscriptores.

EL CASO, 04/09/2026, **a petición del usuario tras leer el briefing de ese
día**. La conclusión terminaba así:

    «Si el NFP supera los 55.000, VENDERÉ cualquier rebote en el Nasdaq [...]
     NO ENTRO EN LARGO hasta que no vea una ruptura clara por encima de la
     SMA50 (7.584,49) con volumen.»

Eso ya no es una lectura del mercado: es una instrucción de operar dirigida a
gente que paga por leerlo. Y no era una salida suelta del modelo — se la pedía
el prompt. En v1, literalmente:

    «es tu lectura personal, en primera persona, CON TU PROPIO POSICIONAMIENTO
     INCLUIDO ("mi cartera", "he cerrado las coberturas", "mantengo el
     objetivo de...")»

y en v2, en el bloque MI CONCLUSIÓN: «Qué haces TÚ con esto».

LA DISTINCIÓN QUE HAY QUE MANTENER, y es la razón de que este fichero exista:
lo valioso del briefing es que SE MOJA. Dice «lo más probable es X y se
invalida en 7.710,65», y eso tiene que quedarse — si al quitar las operaciones
se quedara en un informe neutro que no se compromete con nada, habríamos
cambiado un problema por otro peor. Lo que se va es la ORDEN; lo que se queda
es la LECTURA y su nivel de invalidación.

UNA ASIMETRÍA QUE LO REFUERZA: desde el 25/08 se mide si el `SESGO` acierta
(Newsfeed #34). Nadie medía si «venderé el rebote» habría ganado dinero. El
briefing afirmaba operaciones de las que no rendía cuentas, en un producto
cuyo argumento es la honestidad con los datos.

Uso:
    cd backend
    python -m pytest tests/test_briefing_sin_operaciones_propias.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

MD = {"date": "05/09/2026", "time": "07:47", "sectors": {}, "calendar": [],
      "sesion": {"en_curso": False, "fecha": "2026-09-04", "hora_et": "07:47"}}


def _prompt():
    """El prompt RENDERIDO, no la constante: si algún día el bloque dejara de
    incluirse, mirar la constante no lo detectaría."""
    return D.build_prompt(MD, [], [], [], {}, [], [], [])


@pytest.fixture(params=["v1", "v2"])
def version(request, monkeypatch):
    """Las DOS versiones. Poner una regla solo en la activa es como se pierden
    al cambiar `BRIEFING_PROMPT_VERSION` -- ya pasó con la de superlativos."""
    monkeypatch.setattr(D, "PROMPT_VERSION", request.param)
    return request.param


# ── Lo que ya no se pide ─────────────────────────────────────────────────────

def test_el_prompt_ya_no_pide_que_cuente_su_posicionamiento(version):
    """EL test. En v1 estaba pedido con todas las letras."""
    p = _prompt()
    # Sin apellidos: la palabra NO puede aparecer en ninguna de sus formas.
    # La primera versión buscaba «posicionamiento incluido» (v1 estilo) y se le
    # escapó «con tu propio posicionamiento si aplica», que está en el CIERRE de
    # v1 y pide exactamente lo mismo con otras palabras.
    assert "posicionamiento" not in p, (
        "el prompt sigue pidiendo que el briefing cuente las posiciones "
        "propias del autor")
    assert "he cerrado las coberturas" not in p


def test_la_conclusion_ya_no_pregunta_que_HACES_tu(version):
    """«Qué haces tú con esto» es lo que producía «venderé cualquier rebote»."""
    assert "Qué haces tú con esto" not in _prompt()


def test_se_prohibe_explicitamente_y_con_las_palabras_concretas(version):
    """Una prohibición abstracta («no des recomendaciones») no funciona; las
    palabras literales sí -- es lo que se aprendió con la banda del McClellan
    y la dirección del ABI."""
    p = _prompt()
    assert "operaciones tuyas" in p or "no una orden" in p, (
        "no hay ninguna prohibición explícita de contar operaciones propias")
    assert "mi cartera" in p, (
        "la prohibición no nombra las palabras concretas que hay que evitar")


# ── Lo que NO se puede haber perdido por el camino ───────────────────────────

def test_el_briefing_SIGUE_mojandose(version):
    """Si al quitar las operaciones se quedara en un informe neutro habríamos
    cambiado un problema por otro peor: la convicción es el producto."""
    p = _prompt()
    assert "te mojas" in p or "mojarse" in p.lower(), (
        "se ha perdido la instrucción de comprometerse con una postura")
    assert "informe neutro" in p


def test_sigue_pidiendo_un_nivel_de_invalidacion_concreto(version):
    """«Se invalida en 7.710,65» es una lectura, no una orden — y es lo que
    hace el briefing falsable."""
    p = _prompt()
    # Las dos versiones lo piden con palabras distintas, así que se comprueba
    # la EXIGENCIA en cada una -- no un «invalid» suelto en cualquier parte del
    # prompt, que es lo que dejó escapar el sabotaje de cambiar la conclusión
    # por «una valoración general».
    assert "que la invalidaría" in p or "invalidaría la tesis" in p, (
        "la conclusión ya no exige un nivel exacto que invalide la lectura")
    assert "SMA20" in p
    assert "nunca uno inventado" in p or "no inventes soportes" in p, (
        "se ha perdido la exigencia de usar un nivel técnico real y no uno "
        "inventado")


def test_la_linea_de_SESGO_sigue_siendo_obligatoria(version):
    """El sesgo es una lectura del mercado, no una operación, y encima se mide
    desde el 25/08 (Newsfeed #34). Quitarlo dejaría sin sentido el seguimiento
    de aciertos."""
    p = _prompt()
    assert "SESGO: ALCISTA" in p and "BAJISTA" in p


def test_sigue_escribiendo_en_primera_persona(version):
    """No se trata de despersonalizarlo: se trata de que la primera persona
    sea para la lectura, no para la orden."""
    assert "primera persona" in _prompt()


# ── Coste, que aquí siempre importa ──────────────────────────────────────────

def test_el_cambio_no_engorda_el_prompt_de_forma_apreciable():
    """Este prompt lleva ocho días sin caber en el límite de Groq. La primera
    versión del cambio costaba +96 fichas porque repetía la prohibición en dos
    sitios; apretada a una sola, cuesta +35."""
    fijo = D.estimar_tokens(D._ESTILO_V2) + D.estimar_tokens(D._CIERRE_V2)
    assert fijo < 3260, (
        f"el bloque fijo se ha ido a {fijo} fichas; antes del cambio eran "
        f"3.183 y el techo del prompt entero es {D.TECHO_PROMPT}")
