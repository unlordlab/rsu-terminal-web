"""
Groq impone a veces un techo de fichas de SALIDA, y hay que reaccionar, no suponerlo.

EL CASO, 07/09/2026. El briefing murió con un 429 -- no un 413 -- por un límite
del que este script no tenía noticia:

    Request too large for model `qwen/qwen3.6-27b` in organization `org_...`
    service tier `on_demand` on output tokens per minute (OTPM): Limit 1000

El registro del Action no dejaba lugar a dudas:

    🧮 Presupuesto Groq: prompt ~6205 tokens · respuesta hasta 1445 (límite 8000 TPM)
    📉 Groq dice: límite real 8000 TPM · restante 8000

Del TPM de 8.000 sobraban las 8.000 enteras. Lo que no cabía eran las **1.445
fichas de SALIDA** contra un techo de **1.000**. Por eso la escalera de recorte
del prompt no llegó a activarse -- y tampoco habría servido: recortar la
ENTRADA no reduce la SALIDA.

Y EL LÍMITE ES INTERMITENTE, medido ese mismo día unas horas después contra la
API real: las mismas 1.445 fichas, al mismo modelo y con la misma cuenta,
devolvieron 200. También las 2.000. Se probó en varios modelos y ninguno lo
rechazó.

DE AHÍ QUE ESTE FICHERO CAMBIARA DE OPINIÓN. Mi primera versión clavaba el tope
en 950 para siempre, y estos tests exigían que NUNCA se pidiera más. Eso
convertía un límite ocasional en un impuesto diario: briefing de ~360 palabras
en vez de ~547 todos los días, incluidos aquellos en que Groq habría dejado
escribir el largo. El arreglo era seguro y caro.

Ahora se pide la longitud completa y, si llega el 429, se lee el techo DEL
PROPIO MENSAJE (que trae el número) y se reintenta en el acto -- el rechazo
ocurre antes de generar nada, así que no ha consumido presupuesto y no hay que
esperar el minuto que sí espera el reintento por respuesta cortada.

POR QUÉ NO SE PUEDE PREVER. Se comprobó llamada a llamada: ni la página de
límites de la consola ni las cabeceras `x-ratelimit-*` de la respuesta traen
este tope. Solo publican peticiones y tokens totales. La única fuente es el
error. Por eso, además, se guardan TODAS las cabeceras `x-ratelimit-*`: el
próximo límite que Groq añada no debería costar otro incidente.

Uso:
    cd backend
    python -m pytest tests/test_briefing_techo_de_salida.py -v
"""
import os
import re
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


def _prompt(texto="Redacta el briefing de hoy. "):
    """Un prompt con la marca de longitud, como el real."""
    return texto * 40 + D.MARCA_LONGITUD + " Termina con SESGO:."


@pytest.fixture(autouse=True)
def _con_clave(monkeypatch):
    """`generate_briefing` aborta sin clave antes de llegar al presupuesto.
    Es una cadena cualquiera: no se sale a la red en ningún test de aquí."""
    monkeypatch.setattr(D, "GROQ_KEY", "solo-para-no-abortar")


def _pedidas(post):
    return [c.kwargs["json"]["max_tokens"] for c in post.call_args_list]


# ── El día normal: nada de impuestos preventivos ─────────────────────────────

def test_sin_techo_impuesto_se_pide_la_longitud_COMPLETA():
    """LA REGRESIÓN QUE ESTE FICHERO DEJÓ PASAR EN SU PRIMERA VERSIÓN. El límite
    va y viene; suponerlo acorta el briefing un tercio TODOS los días, también
    los que Groq no lo aplica."""
    with patch.object(D.requests, "post", return_value=_respuesta()) as post:
        D.generate_briefing(_prompt())
    assert _pedidas(post) == [D.GROQ_MAX_OUTPUT], (
        f"se piden {_pedidas(post)} fichas de salida en un día sin techo: algo "
        f"está aplicando un tope preventivo que el límite real no exige")


def test_no_hay_ninguna_constante_haciendo_de_tope_de_salida():
    """El presupuesto solo se recorta con lo que Groq haya DICHO."""
    assert D._presupuesto_salida(5000) == D.GROQ_MAX_OUTPUT
    assert D._presupuesto_salida(900) == 900, "manda el hueco que deja el prompt"
    assert D._presupuesto_salida(5000, 1000) == 1000 - D.GROQ_OTPM_SAFETY


# ── El día con techo: leerlo y reintentar en el acto ─────────────────────────

def test_se_lee_el_techo_del_error_y_se_reintenta_SIN_ESPERAR():
    """EL test. El rechazo ocurre antes de generar nada, así que no consume
    presupuesto del minuto: esperar 65 s sería regalar el briefing de la
    mañana por nada."""
    respuestas = [_respuesta(429, ERROR_OTPM), _respuesta()]
    with patch.object(D.time, "sleep") as dormir, \
         patch.object(D.requests, "post", side_effect=respuestas) as post:
        texto, diag = D.generate_briefing(_prompt())

    assert len(_pedidas(post)) == 2, "no se ha reintentado tras el 429"
    assert _pedidas(post)[1] <= 1000, (
        f"el reintento pide {_pedidas(post)[1]} contra el techo de 1000 que "
        f"Groq acababa de decir")
    assert texto, "no se ha publicado briefing pese a que el reintento fue bien"
    dormir.assert_not_called()


def test_el_dia_con_techo_queda_ANOTADO_en_el_diagnostico():
    """Si no, un briefing de 360 palabras parece que el modelo tuvo un mal día.
    Es el mismo motivo por el que se anota el nivel de recorte (Newsfeed #32)."""
    respuestas = [_respuesta(429, ERROR_OTPM), _respuesta()]
    with patch.object(D.time, "sleep"), \
         patch.object(D.requests, "post", side_effect=respuestas):
        _, diag = D.generate_briefing(_prompt())
    assert diag.get("otpm_impuesto") == 1000
    assert diag.get("otpm_salida_recortada_a") <= 1000


def test_al_reintentar_se_pide_MENOS_TEXTO_no_solo_menos_fichas():
    """Recortar `max_tokens` sin recortar la longitud pedida da un briefing
    cortado a mitad de frase -- el fallo que se cerró en su día. La frase del
    prompt tiene que bajar con el presupuesto."""
    respuestas = [_respuesta(429, ERROR_OTPM), _respuesta()]
    with patch.object(D.time, "sleep"), \
         patch.object(D.requests, "post", side_effect=respuestas) as post:
        D.generate_briefing(_prompt())
    primero, segundo = (c.kwargs["json"]["messages"][0]["content"] for c in post.call_args_list)
    assert D.instruccion_longitud(D.GROQ_MAX_OUTPUT) in primero
    assert D.instruccion_longitud(1000 - D.GROQ_OTPM_SAFETY) in segundo, (
        "el reintento pide menos fichas pero sigue pidiendo el texto largo")


def test_no_se_encadenan_reintentos_si_el_techo_se_mueve_otra_vez():
    """Un bucle de reintentos contra un límite que sigue bajando agotaría las
    peticiones del día sin publicar nada."""
    with patch.object(D.time, "sleep"), \
         patch.object(D.requests, "post",
                      return_value=_respuesta(429, ERROR_OTPM)) as post:
        with pytest.raises(ValueError) as e:
            D.generate_briefing(_prompt())
    assert len(_pedidas(post)) == 2, f"se ha llamado {len(_pedidas(post))} veces"
    assert "movido" in str(e.value)


def test_un_techo_que_no_deja_ni_el_minimo_falla_claro():
    """Por debajo de `GROQ_MIN_OUTPUT` ya no es una nota de mercado. Mejor no
    publicar que publicar un titular suelto, y decir por qué."""
    error = ERROR_OTPM.replace("Limit 1000", "Limit 300")
    with patch.object(D.requests, "post", return_value=_respuesta(429, error)) as post:
        with pytest.raises(ValueError) as e:
            D.generate_briefing(_prompt())
    assert len(_pedidas(post)) == 1, "no debe reintentar algo que no cabe"
    assert "300" in str(e.value) and str(D.GROQ_MIN_OUTPUT) in str(e.value)


# ── Sacar el número del mensaje ──────────────────────────────────────────────

def test_el_limite_se_saca_del_mensaje_REAL():
    assert D.limite_otpm_del_error(ERROR_OTPM) == 1000


def test_y_None_cuando_el_mensaje_no_lo_trae():
    """Si Groq cambia el formato, mejor fallar diciendo que no se pudo leer que
    inventarse un techo."""
    assert D.limite_otpm_del_error('{"error":{"message":"rate limit RPM"}}') is None
    assert D.limite_otpm_del_error("") is None
    assert D.limite_otpm_del_error(None) is None


def test_sin_numero_legible_no_se_reintenta_a_ciegas():
    with patch.object(D.requests, "post",
                      return_value=_respuesta(429, "OTPM exceeded")) as post:
        with pytest.raises(ValueError) as e:
            D.generate_briefing(_prompt())
    assert len(_pedidas(post)) == 1
    assert "no trae el número" in str(e.value)


# ── Lo que ya funcionaba y no se puede romper ────────────────────────────────

def test_un_429_que_NO_sea_de_OTPM_no_se_disfraza():
    """Un límite de peticiones por minuto sí es pasajero: no puede acabar en la
    rama que recorta la salida."""
    with patch.object(D.requests, "post",
                      return_value=_respuesta(429, '{"error":{"message":"rate limit RPM"}}')):
        with pytest.raises(ValueError) as e:
            D.generate_briefing(_prompt())
    assert "OTPM" not in str(e.value)


def test_un_413_sigue_bajando_de_nivel_de_recorte():
    with patch.object(D.requests, "post", return_value=_respuesta(413, "too large")):
        with pytest.raises(D.PromptDemasiadoGrande):
            D.generate_briefing(_prompt())


def test_el_reintento_por_respuesta_cortada_SI_espera_y_pide_menos_TEXTO():
    """Ese sí gastó la salida entera, y el límite de Groq es por minuto:
    reintentar de inmediato solo daría un 429. Es lo contrario del de OTPM, y
    los dos caminos tienen que seguir distinguiéndose.

    UN ERROR MÍO AL ESCRIBIR ESTE TEST, que casi me lleva a «arreglar» código
    correcto: di por hecho que el reintento debía bajar `max_tokens`, y no debe.
    Bajar el presupuesto hace la respuesta MÁS propensa a salir cortada, no
    menos. Lo que evita el corte es pedir menos TEXTO con el mismo presupuesto,
    que es justo lo que hace el código (`recorte` alimenta la instrucción de
    longitud, no el `max_tokens`)."""
    respuestas = [_respuesta(motivo="length"), _respuesta(motivo="stop")]
    with patch.object(D.time, "sleep") as dormir, \
         patch.object(D.requests, "post", side_effect=respuestas) as post:
        D.generate_briefing(_prompt())

    assert len(_pedidas(post)) == 2
    dormir.assert_called_once()
    primero, segundo = (c.kwargs["json"]["messages"][0]["content"]
                        for c in post.call_args_list)
    palabras = lambda t: int(re.search(r"entre \d+ y (\d+) palabras", t).group(1))
    assert palabras(segundo) < palabras(primero), (
        f"el reintento sigue pidiendo {palabras(segundo)} palabras: volvería a "
        f"salir cortado por el mismo motivo")
    assert _pedidas(post)[1] >= _pedidas(post)[0], (
        "el reintento ha bajado el presupuesto de fichas, que es lo contrario "
        "de lo que evita el corte")


def test_el_minimo_deja_sitio_a_un_briefing_corto():
    """`GROQ_MIN_OUTPUT` estaba en 1200, calibrado para el briefing largo. Con
    un techo de 1.000 eso haría que el script se negara a escribir el corto --
    cambiar un briefing acortado por ninguno."""
    assert D.GROQ_MIN_OUTPUT <= D.GROQ_OTPM_VISTO - D.GROQ_OTPM_SAFETY


# ── Que el próximo límite no vuelva a ser invisible ──────────────────────────

def test_se_guardan_TODAS_las_cabeceras_de_limite():
    """La causa de que esto costara un incidente: se leían tres cabeceras
    concretas y el límite nuevo viajaba en otra -- o en ninguna."""
    d = D._diagnostico_ratelimit(_respuesta(cabeceras={
        "x-ratelimit-limit-tokens": "8000",
        "x-ratelimit-remaining-tokens": "8000",
        "x-ratelimit-limit-requests": "1000",
        "x-ratelimit-limit-output-tokens": "1000",      # el que faltaba
        "content-type": "application/json",
    }))
    assert d["limites_groq"].get("x-ratelimit-limit-output-tokens") == "1000"
    assert "content-type" not in d["limites_groq"], "se guardan cabeceras que no son límites"


def test_las_tres_de_siempre_siguen_estando():
    """El bloque nuevo no puede llevarse por delante lo que ya se publicaba en
    `briefing.json`."""
    d = D._diagnostico_ratelimit(_respuesta(cabeceras={
        "x-ratelimit-limit-tokens": "8000", "x-ratelimit-remaining-tokens": "530",
        "x-ratelimit-limit-requests": "1000"}))
    assert d["tpm_limite_real"] == "8000" and d["tpm_restante"] == "530"
    assert d["rpm_limite_real"] == "1000"
