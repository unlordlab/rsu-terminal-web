"""
El modelo recibió los tickers desnudos y les inventó un sector.

EL CASO, 31/08/2026. El briefing del día montaba su tesis sobre una escalada
entre Estados Unidos e Irán, y la remataba así:

    «la compra de insiders en energía (DKS, AMR) y defensa/industrial (AMRC)
     confirma que el capital inteligente está posicionándose para la duración
     del conflicto»

Ninguna de las tres etiquetas es cierta:

    DKS   Dick's Sporting Goods  -> Consumer Cyclical / Specialty Retail
    AMR   Alpha Metallurgical    -> Basic Materials / Coking Coal
    AMRC  Ameresco               -> Industrials / Engineering & Construction

DKS es una tienda de artículos deportivos presentada como una petrolera. Y no
es un número mal copiado: sobre esas etiquetas inventadas se construye una
frase causal («el capital inteligente se posiciona para la duración del
conflicto») que el lector no tiene forma de contrastar.

LA CAUSA, otra vez la misma. `insider_lines` mandaba al prompt el ticker, el
número de insiders, el importe y la señal. Nada más. Pero el endpoint YA
devuelve `company` -- se tiraba antes de llegar al prompt, igual que el
`actual` del calendario (#36) y el desglose del S&P (#35). Tercer caso del
mismo patrón: el dato estaba, no viajaba, y el modelo rellenó el hueco.

LA LECCIÓN: un ticker desnudo es una invitación a inventar. Cuatro letras no
dicen a qué se dedica una empresa, y un modelo que está construyendo una
narrativa las interpretará a favor de esa narrativa.

Uso:
    cd backend
    python -m pytest tests/test_briefing_insiders.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

# Los tres del caso real, con el nombre tal y como lo devuelve el endpoint.
CLUSTERS = [
    {"ticker": "DKS",  "company": "Dick's Sporting Goods Inc",
     "n_insiders": 3, "total_value": 1_200_000, "signal": "FUERTE"},
    {"ticker": "AMR",  "company": "Alpha Metallurgical Resources, Inc.",
     "n_insiders": 2, "total_value": 800_000, "signal": "MODERADA"},
    {"ticker": "AMRC", "company": "Ameresco, Inc.",
     "n_insiders": 2, "total_value": 400_000, "signal": "MODERADA"},
]


def _prompt(clusters):
    d = {"date": "31/08/2026", "time": "10:30", "sectors": {}, "calendar": [],
         "sesion": {"en_curso": True, "fecha": "2026-08-31", "hora_et": "10:30"}}
    return D.build_prompt(d, [], [], [], {}, clusters, [], [])


# ── El caso real ─────────────────────────────────────────────────────────────

def test_el_nombre_de_la_empresa_llega_al_prompt():
    """EL test. Con «Dick's Sporting Goods» delante, llamarlo energía cuesta
    mucho más que con un «DKS» a secas."""
    p = _prompt(CLUSTERS)
    assert "Dick's Sporting Goods" in p, (
        "el ticker sigue viajando desnudo: es lo que dejó al modelo inventarse "
        "que DKS era una empresa de energía")
    assert "Alpha Metallurgical" in p
    assert "Ameresco" in p


def test_el_ticker_NO_desaparece():
    """El nombre se añade, no sustituye: el ticker es lo que el lector puede
    buscar."""
    p = _prompt(CLUSTERS)
    for t in ("DKS", "AMR", "AMRC"):
        assert t in p


def test_siguen_viajando_los_datos_de_siempre():
    p = _prompt(CLUSTERS)
    assert "3 insiders" in p and "FUERTE" in p and "1,200,000" in p


def test_un_cluster_sin_nombre_no_rompe_ni_inventa():
    """El endpoint devuelve `company` vacío en algunos casos. Sin nombre se
    manda el ticker solo, que es lo que había -- pero sin paréntesis vacíos."""
    p = _prompt([{"ticker": "XYZ", "company": "", "n_insiders": 2,
                  "total_value": 100, "signal": "MODERADA"}])
    assert "- XYZ:" in p
    assert "XYZ ()" not in p


# ── El recorte del nombre ────────────────────────────────────────────────────
#
# Se recorta porque este prompt NO CABE en el límite de Groq desde hace
# semanas: cada ficha que se gasta aquí sale de otro sitio.

def test_no_parte_palabras_por_la_mitad():
    """Cortar a pelo por caracteres dejaba «Dick's Sporting Goods In», que
    parece un fallo de programa dentro de un texto que lee gente."""
    assert D.nombre_corto("Dick's Sporting Goods Inc") == "Dick's Sporting Goods"
    assert not D.nombre_corto("Alpha Metallurgical Resources, Inc.").endswith(" Reso")


def test_quita_el_ruido_societario():
    """«Inc.», «Corporation» o «Ltd» no dicen a qué se dedica nadie, y en un
    prompt que no cabe son fichas tiradas."""
    assert D.nombre_corto("NVIDIA Corporation") == "NVIDIA"
    assert D.nombre_corto("Ameresco, Inc.") == "Ameresco"
    assert D.nombre_corto("Exxon Mobil Corp") == "Exxon Mobil"


def test_conserva_lo_que_identifica_a_la_empresa():
    """El recorte no puede dejar el nombre irreconocible: «Alpha» solo no
    distingue nada, «Alpha Metallurgical» ya dice que no es una petrolera."""
    assert D.nombre_corto("Alpha Metallurgical Resources, Inc.") == "Alpha Metallurgical"


def test_un_nombre_vacio_o_ausente_devuelve_cadena_vacia():
    assert D.nombre_corto("") == "" and D.nombre_corto(None) == ""
    assert D.nombre_corto("   ") == ""


def test_una_sola_palabra_larguisima_no_desaparece():
    """Si no hay espacio por donde cortar, es mejor un nombre truncado que
    ninguno -- el `or` del final existe por esto."""
    assert D.nombre_corto("Supercalifragilisticoexpialidoso") != ""


def test_el_prompt_usa_la_funcion_y_no_recorta_a_pelo():
    """Que la función esté bien no sirve si build_prompt corta por su cuenta."""
    import inspect
    fuente = inspect.getsource(D.build_prompt)
    assert "nombre_corto(" in fuente, (
        "build_prompt no usa el recortador: el nombre volvería a partirse por "
        "la mitad o a viajar entero")
