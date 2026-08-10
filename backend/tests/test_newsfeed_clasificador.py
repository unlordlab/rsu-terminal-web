"""
Test del clasificador de Newsfeed (hallazgo #2) y de la caché de precios (#4).

QUÉ ESTABA ROTO EN EL CLASIFICADOR. Buscaba las keywords con `kw in texto`,
y con palabras de tres o cuatro letras eso etiqueta por trozos. Medido el
08/08 sobre 118 titulares reales del feed: **26 de los 57 clasificados
HIGH/MED (el 46%) lo estaban por un fragmento**, no por la palabra. De ese
día, textualmente:

    "double dipping portfolio"           -> HIGH   por "ppi" en diPPIng
    "Europe space agency"                -> MED    por "spac" en SPACe
    "growth in second quarter"           -> MED    por "sec" en SECond
    "FedEx beats estimates"              -> HIGH   por "fed" en FEDex
    "software update"                    -> HIGH   por "war" en softWARe

El sector estaba peor: la keyword "ai" de TECH casa con said, again,
raised, chain, remain... así que casi todo acababa en TECH.

El filtro de impacto es lo que da valor al módulo. Con ese ruido, un HIGH
no significaba nada.

LO QUE FIJA ESTE FICHERO son las dos mitades, porque arreglar una rompe la
otra si no se mira: que los fragmentos ya NO cuenten, y que los plurales y
las formas verbales SÍ sigan contando. Lo segundo no es teórico -- la
primera versión del arreglo, con `\\b` a secas, dejó de clasificar
"Raymond James downgrades Arko" porque `\\bdowngrade\\b` no casa con
"downgrades". Se detectó mirando el antes/después titular a titular, no en
el total.

Uso:
    cd backend
    python -m pytest tests/test_newsfeed_clasificador.py -v
"""
import sys, os
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services import newsfeed_service as N  # noqa: E402
from services.cache import cache  # noqa: E402


# ── #2: fragmentos que NO deben clasificar ───────────────────────────────

@pytest.mark.parametrize("titular,fragmento", [
    ("Microsoft ships new software update",      "war dentro de softWARe"),
    ("Apple issues warning over supply delays",  "war dentro de WARning"),
    ("FedEx beats quarterly estimates",          "fed dentro de FEDex"),
    ("The company federated its login system",   "fed dentro de FEDerated"),
    ("Insecure API found in a trading app",      "sec dentro de inSECure"),
    ("Citi sees growth in second quarter",       "sec dentro de SECond"),
    ("Shortage of chips hits automakers",        "short dentro de SHORTage"),
    ("Thoughts on the double dipping portfolio", "ppi dentro de diPPIng"),
    ("Europe space agency plans a launch",       "spac dentro de SPACe"),
])
def test_un_trozo_de_palabra_no_clasifica(titular, fragmento):
    assert N._classify_impact(titular) == "LOW", f"clasificó por {fragmento}"


# ── #2: y las palabras de verdad SÍ deben clasificar ─────────────────────

@pytest.mark.parametrize("titular,esperado,forma", [
    ("Fed raises rates by 50 basis points",   "HIGH", "palabra suelta"),
    ("Ukraine war escalates near the border", "HIGH", "palabra suelta"),
    ("SEC charges the firm with fraud",       "MED",  "palabra suelta"),
    ("Raymond James downgrades Arko stock",   "MED",  "plural/verbo: downgradeS"),
    ("Trump announces new tariffs on steel",  "HIGH", "plural: tariffS"),
    ("Investors shorted the stock heavily",   "MED",  "verbo: shortED"),
    ("Company reports mass layoffs",          "MED",  "keyword ya en plural"),
])
def test_las_palabras_reales_si_clasifican(titular, esperado, forma):
    assert N._classify_impact(titular) == esperado, f"falló con {forma}"


def test_la_negacion_sigue_funcionando():
    """El arreglo cambió cómo se localiza la keyword, así que la ventana de
    negación se calcula sobre otra posición. Si se hubiera roto, un "no
    recession" volvería a contar como recesión."""
    assert N._classify_impact("Analysts see no recession this year") != "HIGH"
    assert N._classify_impact("Recession fears grip the market") == "HIGH"


# ── #2: el sector, que estaba peor por la keyword "ai" ───────────────────

@pytest.mark.parametrize("titular", [
    "He said the market would remain calm",       # ai en sAId / remAIn
    "Supply chain issues raised concerns",        # ai en chAIn / rAIsed
    "Ted Lasso turned a London neighborhood",     # ai en ...
])
def test_ai_dentro_de_otra_palabra_no_marca_TECH(titular):
    assert N._sector(titular) != "TECH"


def test_un_titular_de_tecnologia_de_verdad_sigue_siendo_TECH():
    assert N._sector("Nvidia unveils a new AI chip for data centers") == "TECH"


# ── #4: la caché de precios ──────────────────────────────────────────────

@pytest.fixture(autouse=True)
def limpiar_cache():
    cache.delete("newsfeed:prices")
    yield
    cache.delete("newsfeed:prices")


def test_los_precios_solo_se_bajan_una_vez():
    """Medido antes de la caché: 30 peticiones a Yahoo por cada carga de la
    página -- los 10 tickers del widget, cada uno con history() y
    fast_info. La cuota de Yahoo la comparte toda la terminal."""
    llamadas = []
    falsos = [{"name": "S&P 500", "price": 1.0, "chg": 0.5}]
    with patch.object(N, "_get_prices", side_effect=lambda: (llamadas.append(1), falsos)[1]):
        a = N.get_newsfeed_prices()
        b = N.get_newsfeed_prices()
        c = N.get_newsfeed_prices()
    assert a == b == c == falsos
    assert len(llamadas) == 1, f"se bajaron los precios {len(llamadas)} veces, debería ser 1"


def test_una_respuesta_vacia_no_se_cachea():
    """Una lista vacía es un fallo de red, no un resultado. Cachearla
    dejaría el widget en blanco durante los 5 minutos completos aunque
    Yahoo se recupere al segundo siguiente."""
    with patch.object(N, "_get_prices", return_value=[]):
        assert N.get_newsfeed_prices() == []
    assert cache.get("newsfeed:prices") is None
