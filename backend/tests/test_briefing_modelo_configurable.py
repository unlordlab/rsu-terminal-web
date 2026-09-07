"""
Cambiar el modelo del briefing NO es cambiar una cadena: cada uno acepta otros parámetros.

DE DÓNDE SALE. El 07/09/2026, buscando salida al techo de fichas de Groq, la
recomendación obvia era pasar de `qwen/qwen3.6-27b` (que es **Preview** — "for
evaluation purposes only", puede cambiar o retirarse con poco aviso, que es
justo lo que pasó) a `openai/gpt-oss-120b`, que es **Production** y más barato.

Al comprobarlo contra la documentación antes de tocar nada, la recomendación se
cayó sola. Los parámetros no son universales:

    qwen3.6-27b   reasoning_effort: none | default          reasoning_format: sí
    qwen3.8-27b   reasoning_effort: none | default | low…    reasoning_format: sí
    gpt-oss-*     reasoning_effort: low | medium | high      reasoning_format: NO
    compound      sistema agéntico: ni uno ni otro

Mandarle a un `gpt-oss` el `reasoning_effort: "none"` que acepta Qwen es un 400,
y el briefing de esa mañana se pierde. Y hay algo peor que un 400: los
`gpt-oss` **no admiten "none"**, o sea que **razonan siempre**. Ese parámetro
está puesto porque el pensamiento interno cuenta dentro de `max_tokens` aunque
se oculte, y con el presupuesto apretado se llegó a gastar entero pensando,
dejando un briefing de CERO palabras. Cambiar a `gpt-oss` reintroduce un fallo
que este proyecto ya cerró.

POR ESO ESTO ES UNA TABLA Y NO UNA CADENA. El modelo se elige por entorno
(`BRIEFING_MODEL`) para poder comparar briefings reales lado a lado, y cada uno
recibe solo lo que acepta. El defecto sigue siendo el que está medido y
funcionando.

Y LO DE `compound`. Declara 70.000 TPM frente a los 8.000 de ahora — 8,75× —, y
con ese margen la escalera de `NIVELES_RECORTE` sobraría entera: hoy el briefing
se escribe a diario en modo «agresivo» y el 28/08 cayó a «mínimo» sin memoria
narrativa. Pero es un sistema **agéntico** y su búsqueda web **no se puede
apagar**, solo acotar por dominio. En un briefing cuyo historial de fallos es
exactamente citar datos que nadie le dio (#33 el IPC de Australia como el de
EE.UU., #40 el oro «en máximos», #41 prensa de Kelowna), eso no se acepta a
ciegas. Las dos salvaguardas: se le acota la búsqueda a los medios que ya damos
por buenos, y se REGISTRA lo que consultó (`executed_tools` trae consulta,
resultado y fuentes), avisando si se sale de la lista.

Uso:
    cd backend
    python -m pytest tests/test_briefing_modelo_configurable.py -v
"""
import importlib
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _respuesta(contenido="briefing " * 200, herramientas=None):
    r = MagicMock(status_code=200, text="")
    r.headers = {}
    mensaje = {"content": contenido}
    if herramientas is not None:
        mensaje["executed_tools"] = herramientas
    r.json.return_value = {
        "choices": [{"message": mensaje, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 6205},
    }
    return r


@pytest.fixture(autouse=True)
def _con_clave(monkeypatch):
    monkeypatch.setattr(D, "GROQ_KEY", "solo-para-no-abortar")


# ── Cada modelo recibe lo que acepta ─────────────────────────────────────────

def test_qwen_recibe_el_none_que_evita_que_piense_con_el_presupuesto():
    """El motivo original: el pensamiento interno cuenta dentro de max_tokens
    aunque se oculte, y se llegó a gastar entero pensando."""
    p = D.parametros_del_modelo("qwen/qwen3.6-27b")
    assert p["reasoning_effort"] == "none"
    assert p["reasoning_format"] == "hidden"


def test_gpt_oss_NO_recibe_none_ni_reasoning_format():
    """Los dos serían un 400. Es el error que habría cometido el cambio de
    modelo hecho a pelo."""
    p = D.parametros_del_modelo("openai/gpt-oss-120b")
    assert p.get("reasoning_effort") != "none", (
        "los gpt-oss no admiten 'none': la llamada devolvería 400 y no habría "
        "briefing esa mañana")
    assert "reasoning_format" not in p, "los gpt-oss no admiten reasoning_format"
    assert p["reasoning_effort"] in ("low", "medium", "high")


def test_compound_no_recibe_parametros_de_razonamiento():
    p = D.parametros_del_modelo("groq/compound")
    assert "reasoning_effort" not in p and "reasoning_format" not in p


def test_un_modelo_desconocido_cae_en_lo_conservador():
    """Sin entrada en la tabla se mandan los parámetros del modelo que está
    medido, no un dict vacío que dejaría al modelo razonando a su aire."""
    assert D.parametros_del_modelo("otro/modelo-nuevo")["reasoning_effort"] == "none"


def test_lo_que_se_ENVIA_sale_de_la_tabla(monkeypatch):
    """No basta con que la tabla esté bien: hay que comprobar que la llamada la
    usa. Es la diferencia entre un test de fuente y uno de comportamiento."""
    monkeypatch.setattr(D, "MODEL", "openai/gpt-oss-120b")
    with patch.object(D.requests, "post", return_value=_respuesta()) as post:
        D.generate_briefing("prompt de prueba")
    enviado = post.call_args.kwargs["json"]
    assert enviado["model"] == "openai/gpt-oss-120b"
    assert enviado.get("reasoning_effort") == "low"
    assert "reasoning_format" not in enviado


def test_el_modelo_se_puede_elegir_por_entorno(monkeypatch):
    """Para comparar briefings reales sin tocar código ni desplegar."""
    monkeypatch.setenv("BRIEFING_MODEL", "groq/compound-mini")
    recargado = importlib.reload(D)
    try:
        assert recargado.MODEL == "groq/compound-mini"
    finally:
        monkeypatch.delenv("BRIEFING_MODEL")
        importlib.reload(D)


def test_el_defecto_es_el_modelo_MEDIDO():
    """El que está funcionando y con el presupuesto calibrado. Cambiarlo es una
    decisión, no un efecto secundario de tocar otra cosa."""
    assert D.MODEL_POR_DEFECTO == "qwen/qwen3.6-27b"


# ── La búsqueda de compound: acotada y registrada ────────────────────────────

def test_a_compound_se_le_acota_la_busqueda_a_los_medios_de_siempre():
    """No se puede apagar (comprobado en las docs: solo hay filtrado por
    dominio), así que al menos que busque donde ya buscamos nosotros."""
    p = D.parametros_del_modelo("groq/compound")
    assert p["search_settings"]["include_domains"] == D.DOMINIOS_FIABLES
    assert "reuters.com" in D.DOMINIOS_FIABLES


def test_lo_que_el_modelo_consulta_queda_REGISTRADO(monkeypatch):
    """Sin esto, un número que el modelo no recibió de nosotros sería
    indistinguible de uno inventado."""
    monkeypatch.setattr(D, "MODEL", "groq/compound")
    tools = [{"type": "search", "output": "https://www.reuters.com/markets/x"}]
    with patch.object(D.requests, "post", return_value=_respuesta(herramientas=tools)):
        _, diag = D.generate_briefing("prompt")
    assert diag["herramientas_usadas"] == tools
    assert diag["modelo"] == "groq/compound"


def test_se_AVISA_cuando_consulta_algo_fuera_de_la_lista(monkeypatch, capsys):
    """El filtro de dominios lo pone Groq; que se cumpla hay que comprobarlo,
    no darlo por hecho."""
    monkeypatch.setattr(D, "MODEL", "groq/compound")
    tools = [{"type": "search", "output": "https://blog-de-alguien.com/oro-maximos"}]
    with patch.object(D.requests, "post", return_value=_respuesta(herramientas=tools)):
        _, diag = D.generate_briefing("prompt")
    assert diag.get("herramientas_fuera_de_lista") == 1
    assert "fuera de la lista" in capsys.readouterr().out


def test_un_subdominio_del_mismo_medio_NO_da_falso_aviso():
    """`uk.reuters.com` es Reuters. Un aviso cada día por esto haría que se
    dejara de mirar, que es como muere cualquier alerta."""
    assert D._busqueda_dentro_de_dominios_fiables(
        {"output": "https://uk.reuters.com/markets/x"})


def test_un_dominio_que_solo_SE_PARECE_si_avisa():
    """`notreuters.com` y `reuters.com.co` no son Reuters. Es la misma trampa
    que ya se cerró en el bloque de prensa internacional (#41)."""
    for malo in ("https://notreuters.com/x", "https://reuters.com.co/x"):
        assert not D._busqueda_dentro_de_dominios_fiables({"output": malo}), malo


def test_una_herramienta_SIN_urls_no_dispara_el_aviso(monkeypatch, capsys):
    """`compound` no solo busca: también ejecuta código y consulta Wolfram, y
    esas llamadas no citan ninguna URL. Si eso contara como «fuente fuera de la
    lista», habría aviso casi a diario — y una alerta que salta siempre se deja
    de mirar, que es como se pierde la que sí importa.

    HUECO QUE ESTE FICHERO NO CUBRÍA: lo cazó el sabotaje «sin URLs se da por
    sospechoso», que se escapó a la primera."""
    monkeypatch.setattr(D, "MODEL", "groq/compound")
    tools = [{"type": "code_execution", "arguments": "2+2", "output": "4"}]
    with patch.object(D.requests, "post", return_value=_respuesta(herramientas=tools)):
        _, diag = D.generate_briefing("prompt")
    assert diag["herramientas_usadas"] == tools, "debe registrarse igualmente"
    assert "herramientas_fuera_de_lista" not in diag, (
        "una ejecución de código sin URLs se está contando como fuente ajena")
    assert "fuera de la lista" not in capsys.readouterr().out


def test_sin_herramientas_no_se_inventa_el_bloque(monkeypatch):
    """Los modelos normales no traen `executed_tools`: no puede aparecer una
    clave vacía que dé a entender que hubo búsqueda."""
    monkeypatch.setattr(D, "MODEL", "qwen/qwen3.6-27b")
    with patch.object(D.requests, "post", return_value=_respuesta()):
        _, diag = D.generate_briefing("prompt")
    assert "herramientas_usadas" not in diag
    assert "herramientas_fuera_de_lista" not in diag
