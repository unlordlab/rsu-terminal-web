"""
Groq puso un techo a las fichas de SALIDA y el briefing no sabía que existía.

EL CASO, 07/09/2026. El briefing murió con un 429 -- no un 413 -- y el mensaje
era de un límite del que este script no tenía noticia:

    Request too large for model `qwen/qwen3.6-27b` in organization `org_...`
    service tier `on_demand` on output tokens per minute (OTPM): Limit 1000

El registro del Action lo deja sin dudas:

    🧮 Presupuesto Groq: prompt ~6205 tokens · respuesta hasta 1445 (límite 8000 TPM)
    📉 Groq dice: límite real 8000 TPM · restante 8000

Del TPM de 8.000 sobraban **las 8.000 enteras**. Lo que no cabía eran las
**1.445 fichas de salida** contra un techo de **1.000**. Por eso la escalera de
recorte del prompt no llegó a activarse -- y tampoco habría servido: recortar
la ENTRADA no reduce la SALIDA.

POR QUÉ FUE INVISIBLE HASTA QUE MATÓ LA EJECUCIÓN. El diagnóstico leía tres
cabeceras concretas (`limit-tokens`, `remaining-tokens`, `limit-requests`) y
este límite viaja en otra. Ahora se guardan TODAS las `x-ratelimit-*`.

DOS HIPÓTESIS MÍAS QUE ERAN FALSAS, y que este fichero deja escritas para no
repetirlas:

1. «Habrá sido el cambio de persona del 04/09» -- era el primer briefing que lo
   incluía, así que parecía el sospechoso obvio. No tenía nada que ver.
2. «Se arregla cambiando de modelo» -- Groq documenta que los topes separados
   de entrada y salida son POR ORGANIZACIÓN, no por modelo.

CONSECUENCIA DE PRODUCTO, que no es un detalle: el briefing pasa de pedir
entre 437 y 547 palabras a pedir entre 288 y 360. Un tercio menos, y forzado
por una limitación de infraestructura, no por criterio editorial.

Uso:
    cd backend
    python -m pytest tests/test_briefing_techo_de_salida.py -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

# El mensaje literal que devolvió Groq ese día.
ERROR_OTPM = ('{"error":{"message":"Request too large for model `qwen/qwen3.6-27b` in '
              'organization `org_01kjypqp7vehxt5wqbhn25h050` service tier `on_demand` on '
              'output tokens per minute (OTPM): Limit 1000, Requested 1445"}}')


def _respuesta(status=200, texto="", cabeceras=None, contenido="briefing " * 200,
               motivo="stop"):
    r = MagicMock(status_code=status, text=texto)
    r.headers = cabeceras or {}
    r.json.return_value = {
        "choices": [{"message": {"content": contenido}, "finish_reason": motivo}],
        "usage": {"prompt_tokens": 6205},
    }
    return r


@pytest.fixture(autouse=True)
def _con_clave(monkeypatch):
    """`generate_briefing` aborta sin clave antes de llegar al presupuesto.
    Es una cadena cualquiera: no se sale a la red en ningún test de aquí."""
    monkeypatch.setattr(D, "GROQ_KEY", "solo-para-no-abortar")


# ── El presupuesto de salida ─────────────────────────────────────────────────

def test_no_se_piden_mas_fichas_de_salida_de_las_que_caben():
    """EL test. El día del fallo se pidieron 1.445 contra un techo de 1.000."""
    assert D.GROQ_OTPM_LIMIT - D.GROQ_OTPM_SAFETY <= D.GROQ_OTPM_LIMIT
    with patch.object(D.requests, "post", return_value=_respuesta()) as post:
        D.generate_briefing("prompt corto " * 100)
    pedido = post.call_args.kwargs["json"]["max_tokens"]
    assert pedido <= D.GROQ_OTPM_LIMIT, (
        f"se piden {pedido} fichas de salida y el techo de la organización es "
        f"{D.GROQ_OTPM_LIMIT}: la petición sería rechazada siempre")


def test_el_tope_de_salida_manda_aunque_sobre_TPM():
    """Lo que engañaba: del TPM de 8.000 sobraban las 8.000 enteras. Un
    presupuesto de entrada holgado no autoriza una salida larga."""
    with patch.object(D.requests, "post", return_value=_respuesta()) as post:
        D.generate_briefing("x")          # prompt minúsculo, TPM de sobra
    assert post.call_args.kwargs["json"]["max_tokens"] <= D.GROQ_OTPM_LIMIT


def test_el_REINTENTO_tras_una_respuesta_cortada_tambien_respeta_el_techo():
    """UN FALLO DE MI PRIMERA VERSIÓN DEL ARREGLO, encontrado por este test.

    Puse el tope de salida solo dentro del `if MARCA_LONGITUD in prompt`. Pero
    cuando una respuesta sale cortada, la función se llama a sí misma con el
    prompt en el que la marca YA está sustituida -- así que esa rama no se
    ejecuta y el reintento volvía a pedir hasta 1.800 fichas. O sea: el arreglo
    funcionaba en el camino normal y dejaba vivo el fallo justo en el camino
    que más se acerca al límite."""
    respuestas = [_respuesta(motivo="length"), _respuesta(motivo="stop")]
    with patch.object(D.time, "sleep"), \
         patch.object(D.requests, "post", side_effect=respuestas) as post:
        D.generate_briefing(f"prompt de prueba {D.MARCA_LONGITUD} y cierre")
    assert post.call_count == 2, "no se ha llegado a reintentar"
    for i, llamada in enumerate(post.call_args_list):
        pedido = llamada.kwargs["json"]["max_tokens"]
        assert pedido <= D.GROQ_OTPM_LIMIT, (
            f"la llamada {i + 1} pide {pedido} fichas de salida contra un techo "
            f"de {D.GROQ_OTPM_LIMIT}")


def test_el_minimo_no_bloquea_el_briefing_corto():
    """`GROQ_MIN_OUTPUT` valía 1200 y estaba calibrado para el briefing largo.
    Dejarlo ahí haría que el script se negara a escribir el corto -- cambiar un
    briefing acortado por ninguno."""
    assert D.GROQ_MIN_OUTPUT <= D.GROQ_OTPM_LIMIT - D.GROQ_OTPM_SAFETY, (
        f"GROQ_MIN_OUTPUT ({D.GROQ_MIN_OUTPUT}) está por encima de lo que el "
        f"techo de salida permite pedir: el script abortaría siempre")


def test_la_instruccion_de_longitud_se_ajusta_sola():
    """El prompt pide palabras derivadas de `max_salida`, así que al bajar el
    techo se pide un texto más corto AUTOMÁTICAMENTE. Si no fuera así, el
    modelo escribiría de más y saldría cortado a mitad de frase -- que es
    exactamente el fallo que se cerró en su día (Newsfeed #30)."""
    largo = D.palabras_que_caben(1445)                       # lo que se pidió el día del fallo
    corto = D.palabras_que_caben(D.GROQ_OTPM_LIMIT - D.GROQ_OTPM_SAFETY)
    assert corto < largo, (
        f"con el techo bajado se siguen pidiendo {corto} palabras: la petición "
        f"no cabría y la respuesta saldría cortada")
    assert str(corto) in D.instruccion_longitud(D.GROQ_OTPM_LIMIT - D.GROQ_OTPM_SAFETY), (
        "la frase de longitud del prompt no sale del presupuesto, está escrita a mano")
    assert corto >= D.PALABRAS_MINIMAS, (
        f"{corto} palabras ya no es una nota de mercado; si el techo baja más "
        f"hay que replantear el producto, no seguir recortando")


# ── El error, cuando llega ───────────────────────────────────────────────────

def test_un_429_por_OTPM_dice_QUE_hacer_y_no_parece_pasajero():
    """Una petición que pide más salida de la que cabe en un minuto falla
    SIEMPRE: reintentar no arregla nada. El mensaje tiene que decirlo, o el
    siguiente que lo lea perderá el tiempo con un backoff."""
    with patch.object(D.requests, "post",
                      return_value=_respuesta(429, ERROR_OTPM)):
        with pytest.raises(ValueError) as e:
            D.generate_briefing("prompt")
    msg = str(e.value)
    assert "OTPM" in msg or "SALIDA" in msg
    assert "reintent" in msg.lower(), "el mensaje no aclara que reintentar no sirve"
    assert "la entrada no cuenta" in msg.lower() or "recortando el prompt" in msg.lower()


def test_un_429_que_NO_sea_de_OTPM_no_se_disfraza():
    """Un límite de peticiones por minuto sí es pasajero y se arregla
    esperando: no puede llevar el mensaje de «esto no se arregla solo»."""
    with patch.object(D.requests, "post",
                      return_value=_respuesta(429, '{"error":{"message":"rate limit RPM"}}')):
        with pytest.raises(ValueError) as e:
            D.generate_briefing("prompt")
    assert "OTPM" not in str(e.value)


def test_un_413_sigue_bajando_de_nivel_de_recorte():
    """El 413 es la condición que SÍ se sabe degradar; no puede confundirse con
    la nueva."""
    with patch.object(D.requests, "post", return_value=_respuesta(413, "too large")):
        with pytest.raises(D.PromptDemasiadoGrande):
            D.generate_briefing("prompt")


# ── Que el próximo límite no vuelva a ser invisible ──────────────────────────

def test_se_guardan_TODAS_las_cabeceras_de_limite():
    """La causa de que esto costara un incidente: se leían tres cabeceras
    concretas y el límite nuevo viajaba en otra."""
    cabeceras = {
        "x-ratelimit-limit-tokens": "8000",
        "x-ratelimit-remaining-tokens": "8000",
        "x-ratelimit-limit-requests": "1000",
        "x-ratelimit-limit-output-tokens": "1000",      # el que faltaba
        "content-type": "application/json",
    }
    d = D._diagnostico_ratelimit(_respuesta(cabeceras=cabeceras))
    assert "limites_groq" in d
    assert d["limites_groq"].get("x-ratelimit-limit-output-tokens") == "1000", (
        "sigue sin registrarse el límite de fichas de salida")
    assert "content-type" not in d["limites_groq"], "se están guardando cabeceras que no son límites"


def test_las_tres_de_siempre_siguen_estando():
    """El bloque nuevo no puede llevarse por delante lo que ya se publicaba en
    `briefing.json`."""
    d = D._diagnostico_ratelimit(_respuesta(cabeceras={
        "x-ratelimit-limit-tokens": "8000", "x-ratelimit-remaining-tokens": "530",
        "x-ratelimit-limit-requests": "1000"}))
    assert d["tpm_limite_real"] == "8000" and d["tpm_restante"] == "530"
    assert d["rpm_limite_real"] == "1000"
