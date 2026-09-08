"""
El mismo día contado por dos modelos, publicado uno debajo del otro.

DE DÓNDE SALE. El 07/09/2026 se generaron tres briefings con el MISMO prompt y
se auditaron cifra a cifra contra los datos de entrada. Ninguno inventó un
número — pero cada uno leyó mal algo distinto:

    gpt-oss-120b   «mantienen al índice BAJO la SMA20 (7 708,70)» cuando había
                   cerrado en 7.718,60. Toda su conclusión bajista colgaba de
                   una comparación invertida, y su nivel de invalidación
                   describía una condición que YA se cumplía.
    qwen y compound  leyeron «+162k empleos, mes anterior +21k» como una
                   desaceleración. Es multiplicar por casi ocho.

Ninguna lectura automática es de fiar por sí sola, y esa es la razón de esto:
cuando las dos coinciden, la lectura del día es más sólida; cuando discrepan,
la discrepancia ES el aviso. Enseñar solo una sería venderla con aire de verdad
única, que es justo lo que esta terminal le reprocha a las demás herramientas.

LAS DOS COSAS QUE NO PUEDE ROMPER, y que son el grueso de este fichero:

  1. EL REGISTRO DE ACIERTOS (#34). Mide si acierta EL briefing. Meterle una
     segunda opinión contaminaría la única serie de aciertos que hay, y encima
     hacia atrás: los días ya registrados no llevan segunda lectura.
  2. LA MAÑANA. Si la segunda lectura falla, el briefing principal se publica
     igual. Hoy mismo se perdió un briefing entero por un límite de Groq
     (#45), así que la lección está reciente: una segunda opinión no puede
     costar la primera.

Uso:
    cd backend
    python -m pytest tests/test_briefing_segunda_lectura.py -v
"""
import io
import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

MARKET = "frontend/pages/market.js"


def _respuesta(contenido, motivo="stop", herramientas=None):
    r = MagicMock(status_code=200, text="")
    r.headers = {}
    mensaje = {"content": contenido}
    if herramientas is not None:
        mensaje["executed_tools"] = herramientas
    r.json.return_value = {
        "choices": [{"message": mensaje, "finish_reason": motivo}],
        "usage": {"prompt_tokens": 6205},
    }
    return r


BRIEFING = ("Un briefing de prueba con suficientes palabras para pasar el suelo. " * 12
            + "\n\nSESGO: BAJISTA")


@pytest.fixture(autouse=True)
def _con_clave(monkeypatch):
    monkeypatch.setattr(D, "GROQ_KEY", "solo-para-no-abortar")


def _js():
    ruta = os.path.join(os.path.dirname(__file__), "..", "..", *MARKET.split("/"))
    return io.open(ruta, encoding="utf-8").read()


# ── Que salga, y con el mismo prompt ─────────────────────────────────────────

def test_se_genera_con_OTRO_modelo_y_el_MISMO_prompt():
    """Comparar dos textos escritos con datos distintos no dice nada. Es la
    misma razón por la que el comparador construye el prompt una sola vez."""
    with patch.object(D.requests, "post", return_value=_respuesta(BRIEFING)) as post:
        segunda = D.generar_segunda_lectura("el prompt de hoy")
    enviado = post.call_args.kwargs["json"]
    assert enviado["model"] == D.MODELO_SEGUNDA_LECTURA != D.MODEL, (
        "la segunda lectura usa el mismo modelo que la primera: no aporta nada")
    assert enviado["messages"][0]["content"] == "el prompt de hoy"
    assert segunda["bias"] == "BAJISTA"
    assert "SESGO:" not in segunda["text"], "la etiqueta debe salir del cuerpo"


def test_recibe_los_parametros_de_SU_modelo_no_los_del_otro():
    """`compound` no admite `reasoning_effort`, que es lo que se le manda a
    Qwen. Mandárselo es un 400 — y el fallo se lo comería el `except`, así que
    aparecería como «la segunda lectura ha fallado» sin decir por qué."""
    with patch.object(D.requests, "post", return_value=_respuesta(BRIEFING)) as post:
        D.generar_segunda_lectura("prompt", modelo="groq/compound")
    enviado = post.call_args.kwargs["json"]
    assert "reasoning_effort" not in enviado and "reasoning_format" not in enviado
    assert "search_settings" in enviado


def test_va_al_Gist_como_clave_APARTE():
    """Mezclarla dentro de `text` rompería el modal de cualquier cliente que no
    la conozca. El backend lee por clave, así que añadir una es inocuo."""
    segunda = {"model": "groq/compound", "text": "otra lectura", "bias": "ALCISTA"}
    payload = D.construir_payload("el briefing", {"date": "2026-09-07", "time": "08:00"},
                                  "BAJISTA", None, {}, segunda_lectura=segunda)
    assert payload["segunda_lectura"] == segunda
    assert "otra lectura" not in payload["text"], "se ha mezclado con el principal"
    assert payload["bias"] == "BAJISTA", "el sesgo publicado sigue siendo el del principal"


def test_sin_segunda_lectura_la_clave_NO_aparece_vacia():
    """Una clave presente pero vacía se pinta en el frontend como un título con
    un hueco debajo. Mejor que no esté."""
    payload = D.construir_payload("el briefing", {"date": "2026-09-07", "time": "08:00"},
                                  "BAJISTA", None, {})
    assert "segunda_lectura" not in payload


# ── Lo que NO puede romper ───────────────────────────────────────────────────

def test_un_fallo_de_la_segunda_NO_cuesta_el_briefing():
    """EL test de esta tanda. El 07/09 se perdió un briefing entero por un
    límite de Groq: una segunda opinión no puede costar la primera."""
    with patch.object(D.requests, "post", side_effect=RuntimeError("Groq caido")):
        assert D.generar_segunda_lectura("prompt") is None


def test_y_el_fallo_se_DICE_en_vez_de_tragarse(capsys):
    """Un `except` mudo convierte un fallo permanente en silencio."""
    with patch.object(D.requests, "post", side_effect=RuntimeError("Groq caido")):
        D.generar_segunda_lectura("prompt")
    salida = capsys.readouterr().out
    assert "segunda lectura" in salida.lower() and "Groq caido" in salida


def test_una_segunda_lectura_vacia_se_descarta():
    """Si el modelo agota el presupuesto pensando devuelve casi nada. Publicar
    ese hueco bajo un título es peor que no publicar nada — es el mismo criterio
    que ya aplica el briefing principal."""
    with patch.object(D.requests, "post", return_value=_respuesta("Dos palabras.")):
        assert D.generar_segunda_lectura("prompt") is None


def test_el_registro_de_ACIERTOS_solo_ve_el_briefing_principal():
    """#34 mide si acierta EL briefing. Meterle una segunda opinión rompería la
    única serie de aciertos que hay, y encima hacia atrás: los días ya
    registrados no llevan segunda lectura."""
    historial = D._append_bias([], "2026-09-07", "BAJISTA")
    assert len(historial) == 1 and historial[-1]["bias"] == "BAJISTA"
    import inspect
    assert "segunda" not in inspect.getsource(D._append_bias).lower()
    assert "segunda" not in inspect.getsource(D._append_briefing_history).lower()


def test_se_puede_apagar_sin_desplegar():
    """Si mañana empieza a escribir cualquier cosa, hay que poder quitarla del
    producto sin esperar a un despliegue.

    SE COMPRUEBA QUE NO SE LLAMA A GROQ, no solo que devuelva None. La primera
    versión miraba únicamente el valor de retorno y **pasaba por el motivo
    equivocado**: con el interruptor saboteado, la llamada salía de verdad, el
    `conftest` le cortaba el socket, y el `except` convertía esa excepción en
    None. Un test verde sobre un interruptor que no apagaba nada."""
    with patch.object(D, "MODELO_SEGUNDA_LECTURA", ""), \
         patch.object(D.requests, "post") as post:
        assert D.generar_segunda_lectura("prompt") is None
    post.assert_not_called()


# ── El backend: lo que llega al navegador ────────────────────────────────────

def test_el_backend_desescapa_los_saltos_de_linea():
    """El principal ya lo hacía. Sin esto, la segunda lectura sale con los
    `\\n` literales impresos en pantalla."""
    from services.market_service import _segunda_lectura_limpia
    limpia = _segunda_lectura_limpia({"text": "linea1\\nlinea2", "bias": "ALCISTA",
                                      "model": "groq/compound"})
    assert limpia["text"] == "linea1\nlinea2"


def test_el_backend_descarta_lo_que_no_se_puede_pintar():
    from services.market_service import _segunda_lectura_limpia
    for basura in (None, "", [], {"text": ""}, {"text": "   "}, "una cadena"):
        assert _segunda_lectura_limpia(basura) is None, basura


# ── El frontend ──────────────────────────────────────────────────────────────

def test_el_modal_pinta_la_segunda_lectura():
    js = _js()
    assert "segundaLecturaHTML" in js
    assert "htmlContent + segundaLecturaHTML(data) + pie" in js, (
        "la función existe pero no se llama desde el cuerpo del modal")


def _cuerpo_segunda_lectura():
    """Solo el cuerpo de la función, no el fichero entero.

    Buscar una palabra en todo `market.js` es lo que dejó escapar el sabotaje
    de quitar el veredicto: la palabra «discrepan» seguía apareciendo en el
    COMENTARIO que hay encima de la función. Es la cuarta vez esta semana que
    comprobar una regla contra su silueta en el código deja pasar el sabotaje."""
    js = _js()
    i = js.index("function segundaLecturaHTML")
    return js[i:js.index("\nfunction ", i + 10)]


def test_se_DICE_cuando_las_dos_lecturas_discrepan():
    """Es lo único que convierte dos textos en información. Sin esto, el lector
    se queda con «¿a cuál hago caso?», que es la pregunta que hay que responder
    en la propia etiqueta."""
    cuerpo = _cuerpo_segunda_lectura()
    assert "discrepan" in cuerpo, (
        "el cuerpo de la función ya no distingue el caso en que los dos "
        "modelos dan sesgos distintos")
    assert "coinciden" in cuerpo
    # Y que sean DOS ramas de verdad, no la misma frase para los dos casos.
    assert cuerpo.count("veredicto =") >= 2
    assert "principal === otro" in cuerpo, (
        "no se comparan los dos sesgos: el veredicto sería siempre el mismo")


def test_el_texto_de_la_segunda_pasa_por_el_MISMO_renderizador():
    """Concatenar HTML a mano con texto del modelo es una inyección esperando a
    pasar. `renderMarkdown` es por donde ya pasa el principal."""
    js = _js()
    i = js.index("function segundaLecturaHTML")
    bloque = js[i:i + 2500]
    assert "renderMarkdown(sl.text)" in bloque
    assert "esc(sl.model)" in bloque, "el nombre del modelo se concatena sin escapar"


def test_no_se_pinta_nada_cuando_no_hay_segunda_lectura():
    """Los días que falle, el modal tiene que quedar exactamente como estaba."""
    js = _js()
    i = js.index("function segundaLecturaHTML")
    assert "if (!sl || !sl.text) return '';" in js[i:i + 700]
