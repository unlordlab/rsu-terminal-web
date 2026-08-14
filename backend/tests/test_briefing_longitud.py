"""
El briefing diario se cortaba a mitad de frase TODOS los días.

LA CAUSA, y la aritmética no dejaba lugar a dudas: el prompt pedía «entre 700 y
900 palabras», que en castellano son ~1.570-2.020 tokens, mientras que el techo
de respuesta es 1.800 y un día normal solo deja 1.200 libres tras el prompt. No
cabía ningún día.

Cómo se coló: los topes de salida se calibraron cuando el prompt pedía 500-700
palabras (~1.120-1.570 tokens), que cuadra con el «briefing más largo generado:
~1.350 tokens» que quedó medido en el propio script. Después el prompt pasó a
pedir 700-900 y nadie recalibró el presupuesto.

Y el corte no se veía: `finish_reason` viene en la respuesta de Groq pero nadie
lo miraba, así que un briefing truncado se publicaba con la misma cara que uno
entero. Peor aún, el briefing tiene que terminar con la línea «SESGO: ...» para
alimentar el registro de sesgo -- al cortarse, ese registro perdía el día sin
decir nada.

LO QUE FIJA ESTE FICHERO: que la longitud pedida se derive del hueco real y
quepa siempre, y que un corte no pase inadvertido.

Uso:
    cd backend
    python -m pytest tests/test_briefing_longitud.py -v
"""
import sys, os
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as B  # noqa: E402


def _tokens_de(palabras):
    """Los mismos números que usa el script para convertir palabras a tokens."""
    return palabras * B.CHARS_POR_PALABRA / B.CHARS_POR_TOKEN


# ── La longitud pedida tiene que caber ──────────────────────────────────────

@pytest.mark.parametrize("presupuesto", [1800, 1500, 1350, 1200])
def test_lo_que_se_pide_cabe_en_el_presupuesto(presupuesto):
    """El punto central. Con el prompt viejo («700-900 palabras») esto fallaba
    para todos los presupuestos: 900 palabras son ~2.017 tokens.

    Se prueba desde GROQ_MIN_OUTPUT hacia arriba, que es el rango que el script
    admite: por debajo de eso `generate_briefing` ya se niega a llamar a Groq
    («el prompt deja solo N tokens, por debajo del mínimo»), así que un
    presupuesto menor no llega nunca aquí."""
    assert presupuesto >= B.GROQ_MIN_OUTPUT
    techo = B.palabras_que_caben(presupuesto)
    assert _tokens_de(techo) <= presupuesto, (
        f"pedir {techo} palabras necesita {_tokens_de(techo):.0f} tokens y solo hay {presupuesto}")


def test_el_suelo_de_palabras_cabe_en_el_presupuesto_minimo_admitido():
    """Las dos constantes tienen que ser coherentes entre sí: si alguien sube
    PALABRAS_MINIMAS por encima de lo que caben en GROQ_MIN_OUTPUT, el suelo
    pasaría a pedir más de lo que hay y volveríamos a los cortes. Lo destapó el
    propio test de arriba al probar un presupuesto por debajo del mínimo."""
    assert _tokens_de(B.PALABRAS_MINIMAS) <= B.GROQ_MIN_OUTPUT, (
        f"el suelo de {B.PALABRAS_MINIMAS} palabras necesita "
        f"{_tokens_de(B.PALABRAS_MINIMAS):.0f} tokens y el minimo admitido es {B.GROQ_MIN_OUTPUT}")


def test_el_prompt_viejo_de_900_palabras_no_habria_cabido():
    """Contraste que da sentido al test anterior: se deja escrito por qué se
    dejó de poner la cifra a mano."""
    assert _tokens_de(900) > 1800, "900 palabras no caben ni en el techo absoluto"
    assert _tokens_de(900) > 1200, "y mucho menos en el hueco de un día normal"


def test_con_menos_hueco_se_piden_menos_palabras():
    """Es lo que hace que se ajuste solo los días de calendario cargado."""
    assert B.palabras_que_caben(1800) > B.palabras_que_caben(1200) > B.palabras_que_caben(900)


def test_nunca_se_baja_de_un_minimo_razonable():
    """Con un hueco ridículo no se pide un briefing de dos frases: es preferible
    que salte el aviso de presupuesto insuficiente que ya existe."""
    assert B.palabras_que_caben(50) == B.PALABRAS_MINIMAS


def test_la_instruccion_es_una_banda_no_un_numero_suelto():
    texto = B.instruccion_longitud(1200)
    assert "entre" in texto and "palabras" in texto
    numeros = [int(n) for n in __import__("re").findall(r"\d+", texto)]
    assert len(numeros) == 2 and numeros[0] < numeros[1]


# ── El marcador existe en el prompt real ────────────────────────────────────

def test_el_cierre_del_prompt_trae_el_marcador_a_sustituir():
    """Si alguien vuelve a escribir la longitud a mano, la sustitución deja de
    ocurrir en silencio y volvemos al punto de partida."""
    assert B.MARCA_LONGITUD in B._CIERRE_V2, (
        "el cierre del prompt tiene que llevar el marcador, no una cifra fija")
    assert "700 y 900" not in B._CIERRE_V2


# ── Un corte no puede pasar inadvertido ─────────────────────────────────────

def _respuesta(finish_reason, texto="briefing\n\nSESGO: NEUTRAL"):
    r = MagicMock()
    r.status_code = 200
    r.headers = {}
    r.json.return_value = {"choices": [{"message": {"content": texto},
                                        "finish_reason": finish_reason}]}
    return r


def test_una_respuesta_completa_se_marca_como_no_truncada():
    with patch.object(B, "GROQ_KEY", "clave"), \
         patch.object(B.requests, "post", return_value=_respuesta("stop")):
        texto, diag = B.generate_briefing("prompt corto " + B.MARCA_LONGITUD)
    assert diag["truncado"] is False
    assert diag["finish_reason"] == "stop"


def test_una_respuesta_cortada_se_reintenta_pidiendo_menos():
    """Primer intento cortado, segundo completo: se devuelve el bueno."""
    respuestas = [_respuesta("length", "cortado a mit"), _respuesta("stop")]
    with patch.object(B, "GROQ_KEY", "clave"), \
         patch.object(B.time, "sleep"), \
         patch.object(B.requests, "post", side_effect=respuestas) as post:
        texto, diag = B.generate_briefing("prompt " + B.MARCA_LONGITUD)
    assert post.call_count == 2, "tenía que reintentar"
    assert diag["truncado"] is False
    assert "SESGO" in texto


def test_si_el_segundo_intento_tambien_se_corta_se_publica_pero_queda_anotado():
    """Se decidió publicar antes que quedarse sin briefing, pero el corte tiene
    que quedar registrado en vez de disimularse."""
    with patch.object(B, "GROQ_KEY", "clave"), \
         patch.object(B.time, "sleep"), \
         patch.object(B.requests, "post", side_effect=[_respuesta("length", "a"),
                                                        _respuesta("length", "b")]) as post:
        texto, diag = B.generate_briefing("prompt " + B.MARCA_LONGITUD)
    assert post.call_count == 2, "no puede encadenar reintentos indefinidos"
    assert diag["truncado"] is True
    assert texto == "b"


def test_el_reintento_espera_antes_de_volver_a_llamar():
    """El límite de Groq es por minuto y el primer intento acaba de agotarlo:
    reintentar de inmediato solo daría un 429."""
    with patch.object(B, "GROQ_KEY", "clave"), \
         patch.object(B.time, "sleep") as dormir, \
         patch.object(B.requests, "post", side_effect=[_respuesta("length"), _respuesta("stop")]):
        B.generate_briefing("prompt " + B.MARCA_LONGITUD)
    assert dormir.called, "hay que esperar al siguiente minuto antes de reintentar"
    assert dormir.call_args[0][0] >= 60
