"""
Auditoría del briefing del 16/09/2026: cortado a mitad de frase, sin sesgo, y una condición tomada por un hecho.

EL CASO. Groq impuso un techo de 1.000 fichas de salida; el prompt pedía 288-360
palabras y `qwen3.8-27b` escribió 590 hasta quedarse sin espacio, dos veces.
Se publicó terminando en «La clave es la reacción al anuncio de» y SIN la línea
«SESGO:» del final: el Dashboard sin sesgo y el registro con «N/D» un día en que
el texto decía «Mantengo mi sesgo bajista» (#75).

Además la revisión denunció como PUBLICADA la decisión de la Fed por dos
condicionales («Si la Fed confirma la subida…», «Si la Fed mantiene el 4,00%…»):
gastó el reintento del principal y tiró la segunda lectura entera (#76).

Uso:
    cd backend
    python -m pytest tests/test_briefing_auditoria_1609.py -v
"""
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

FRONT = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')

CORTADO = ("**MI CONCLUSIÓN**\nMantengo mi sesgo bajista. El mercado está en una posición vulnerable. "
           "No busco vender a ciegas, pero no veo razones para estar largo en un entorno donde los tipos "
           "suben y la amplitud falla. La clave es la reacción al anuncio de")


# ── #75 Cortado ──────────────────────────────────────────────────────────────

def test_EL_CASO_se_publica_hasta_la_ultima_frase_completa():
    t = D.recortar_a_frase_completa(CORTADO)
    assert t.endswith("la amplitud falla.")
    assert "La clave es la reacción" not in t


@pytest.mark.parametrize("texto,final", [
    ("Primera frase. Segunda con cita «así».", "«así»."),
    ("Primera frase. ¿Pregunta? Resto sin terminar", "¿Pregunta?"),
    ("Frase (entre paréntesis.) y un trozo", "(entre paréntesis.)"),
    ("Sin ningún punto en todo el texto", "Sin ningún punto en todo el texto"),
])
def test_los_finales_de_frase(texto, final):
    assert D.recortar_a_frase_completa(texto).endswith(final)


def test_un_numero_con_decimales_no_es_final_de_frase():
    """«7.611,04» lleva un punto y no termina nada."""
    assert D.recortar_a_frase_completa("El nivel es 7.611,04 y luego") == "El nivel es 7.611,04 y luego"


def test_EL_CASO_sin_etiqueta_el_sesgo_sale_de_la_conclusion():
    assert D.extract_bias_tag(CORTADO)[1] is None, "el caso de partida: la etiqueta se cortó"
    assert D.sesgo_de_la_conclusion(CORTADO) == "BAJISTA"


def test_la_postura_de_la_invalidacion_no_cuenta():
    """Los 5 que se contradecían en el Gist: «la tesis alcista se invalida» en
    un briefing NEUTRAL."""
    texto = ("**MI CONCLUSIÓN**\nHoy me quedo al margen. Mi nivel de invalidación para la tesis alcista "
             "a corto plazo es la SMA50.")
    assert D.sesgo_de_la_conclusion(texto) is None


def test_si_dice_dos_sesgos_no_elige():
    texto = "**MI CONCLUSIÓN**\nMi sesgo alcista de fondo sigue, pero hoy mi postura es bajista."
    assert D.sesgo_de_la_conclusion(texto) is None


def test_fuera_de_la_conclusion_no_se_busca():
    texto = "Ayer mi sesgo era alcista.\n\n**MI CONCLUSIÓN**\nEl mercado está débil."
    assert D.sesgo_de_la_conclusion(texto) is None


def test_main_recorta_y_rescata_el_sesgo_antes_de_guardar():
    fuente = inspect.getsource(D.main)
    i_recorte = fuente.index("briefing = recortar_a_frase_completa(briefing)")
    i_sesgo = fuente.index("bias = sesgo_de_la_conclusion(briefing)")
    i_guardar = fuente.index("save_to_gist(briefing, market_data, bias")
    assert i_recorte < i_sesgo < i_guardar, "el sesgo se busca en el texto ya recortado, y antes de guardar"
    assert 'if diag.get("truncado"):' in fuente[:i_recorte][-200:], "solo se recorta lo que salió cortado"
    assert "if not bias:" in fuente[:i_sesgo][-200:], "la etiqueta manda: el respaldo solo si falta"


# ── #76 Una condición no es un hecho ─────────────────────────────────────────

FED = [{"event": "Federal Funds Rate", "forecast": "4.00%", "previous": "3.75%", "actual": "", "impact": "high"}]


@pytest.mark.parametrize("frase", [
    "Si la Fed confirma la subida al 4,00% y el tono es hawkish, el yield a 10 años podría dispararse.",
    "El dólar se fortalecerá, y si la Fed sube al 4,00% lo hará más.",
    "Si la Fed mantiene el 4,00% y ofrece una guía neutral, los rendimientos se estabilizarán.",
    "En caso de que la Fed suba al 4,00%, el dólar se fortalecerá.",
])
def test_EL_CASO_una_condicion_no_da_la_decision_por_publicada(frase):
    assert D.previsiones_contadas_como_hechos(frase, FED) == []


def test_una_afirmacion_sigue_cayendo():
    assert D.previsiones_contadas_como_hechos("La Fed subió los tipos al 4,00% esta tarde.", FED)


def test_si_bien_no_es_una_condicion():
    assert D.previsiones_contadas_como_hechos("Si bien la Fed subió los tipos al 4,00%, el mercado aguanta.", FED)


# ── El sesgo también en Market ───────────────────────────────────────────────

def test_market_ensena_el_sesgo_del_briefing():
    with open(os.path.join(FRONT, 'pages', 'market.js'), encoding='utf-8') as f:
        market = f.read()
    cuerpo = market[market.index("async function loadBriefing"):market.index("function openBriefingModal")]
    assert "const bias = (data.bias || '').toUpperCase();" in cuerpo
    assert "BIAS_COLORS[bias]" in cuerpo and "esc(bias)" in cuerpo
    assert "+ biasBadge +" in cuerpo, "la insignia no llega a la cabecera"


def test_podria_en_la_consecuencia_no_esconde_la_afirmacion():
    """«El BCE sube su tipo al 2,65%…, lo que podría fortalecer el euro» afirma
    la decisión (test del 10/09); con «podría» como marca se escapaba."""
    bce = [{"event": "Main Refinancing Rate", "forecast": "2.65%", "previous": "2.40%", "actual": "", "impact": "high"}]
    assert D.previsiones_contadas_como_hechos(
        "Además, el BCE sube su tipo principal al 2,65% (desde el 2,40%), lo que podría fortalecer el euro.", bce)


def test_un_si_que_no_abre_la_condicion_no_esconde_la_afirmacion():
    """«veremos si…» no condiciona lo que se afirma antes."""
    assert D.previsiones_contadas_como_hechos("La Fed subió al 4,00% y veremos si el mercado aguanta.", FED)
