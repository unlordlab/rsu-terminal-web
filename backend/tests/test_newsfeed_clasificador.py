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
    # Bajó de HIGH a MED con el rediseño del clasificador (13/08/2026) y es
    # deliberado, no una regresión: "war" sale en price war, trade war, bidding
    # war, culture war... Es de las palabras ambiguas, así que sola vale MED;
    # para llegar a HIGH necesita una segunda señal. Sigue apareciendo en el
    # feed, solo pierde el distintivo de destacada.
    ("Ukraine war escalates near the border", "MED",  "palabra suelta"),
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


# ── #11: una caída general no puede convertirse en un martilleo ──────────

def test_si_se_caen_todas_las_fuentes_no_se_reintenta_en_cada_visita():
    """Sin nada que cachear, la siguiente visita repetía los 15 fetches en
    paralelo, y la siguiente, y la siguiente: con ~100 usuarios eso es
    martillear a quince servidores que ya están fallando, justo cuando peor
    les viene. Se guarda una marca corta (60s) para saltarse el ciclo.

    Se guarda una MARCA, no el resultado vacío: cachear la lista vacía la
    serviría como si fuera buena."""
    from services import newsfeed_service as NF
    cache.delete("newsfeed:raw")
    cache.delete("newsfeed:caida")
    intentos = []

    def caida(src):
        intentos.append(src["id"])
        return [], src["id"], False

    try:
        with patch.object(NF, "_fetch_source", side_effect=caida), \
             patch.object(NF, "_fetch_finnhub_news", return_value=([], False)):
            NF._fetch_all_items()
            primera = len(intentos)
            intentos.clear()
            NF._fetch_all_items()
            segunda = len(intentos)
        assert primera > 0, "la primera visita sí debe intentarlo"
        assert segunda == 0, f"la segunda repitió {segunda} peticiones a fuentes caídas"
        assert cache.get("newsfeed:raw") is None, "no se puede cachear un feed vacío como si fuera bueno"
    finally:
        cache.delete("newsfeed:caida")


def test_un_feed_sano_no_deja_marca_de_caida():
    """Si la marca se pusiera con datos buenos, el feed se quedaría en blanco
    un minuto sin motivo."""
    from services import newsfeed_service as NF
    cache.delete("newsfeed:raw")
    cache.delete("newsfeed:caida")
    sanos = [{"title": f"noticia {i}", "mins_ago": i, "impact": "LOW",
              "sector": "GENERAL", "sentiment": "neutral"} for i in range(20)]
    try:
        with patch.object(NF, "_fetch_source", side_effect=lambda s: (sanos, s["id"], True)), \
             patch.object(NF, "_fetch_finnhub_news", return_value=([], True)):
            NF._fetch_all_items()
        assert cache.get("newsfeed:caida") is None
        assert cache.get("newsfeed:raw") is not None
    finally:
        cache.delete("newsfeed:caida")
        cache.delete("newsfeed:raw")


# ── El defecto que motivó el rediseño: una keyword suelta no es un HIGH ──────

def test_una_sola_keyword_high_en_el_titular_no_llega_a_high():
    """'Federal Reserve' aparecía en los 7 titulares del feed de la propia Fed
    por construcción, y los marcaba todos. Una señal sola es MED, no HIGH."""
    t = "Federal Reserve Board announces termination of enforcement action"
    assert N._classify_impact(t, titulo=t) == "MED"


def test_dos_keywords_high_en_el_titular_si_llegan_a_high():
    t = "Fed officials debate rate cut as inflation cools"
    assert N._classify_impact(t, titulo=t) == "HIGH"


def test_el_comunicado_del_fomc_sigue_siendo_high():
    """El caso que NO se podía perder al subir el listón: de los 7 titulares de
    la Fed, este es el único que mueve el mercado."""
    t = "Federal Reserve issues FOMC statement"
    assert N._classify_impact(t, titulo=t) == "HIGH"


# ── Titular vs descripción: la misma palabra no vale lo mismo según dónde esté ──

def test_el_titular_pesa_mas_que_la_descripcion():
    """Mismas dos keywords, distinto sitio: en el titular llegan a HIGH, en el
    cuerpo no. Antes daba igual porque se concatenaba todo en un solo string."""
    titulo = "Fed weighs rate cut at next meeting"
    en_titular = N._classify_impact(titulo, titulo=titulo)

    titulo_flojo = "Analysts publish their quarterly outlook"
    texto = titulo_flojo + " " + "the Fed may consider a rate cut next month"
    en_cuerpo = N._classify_impact(texto, titulo=titulo_flojo)

    assert en_titular == "HIGH"
    assert en_cuerpo != "HIGH"


def test_sin_titulo_explicito_el_texto_entero_cuenta_como_titular():
    """Retrocompatibilidad: la llamada de Truth Social no pasa `titulo` porque
    el post ES el titular. Sin el parámetro, el texto no puede quedar
    silenciosamente degradado a peso de descripción.

    El texto lleva justo las señales necesarias para que la diferencia se note:
    con peso de titular llega a HIGH, con peso de descripción se queda en MED."""
    t = "Fed announces rate cut"
    assert N._classify_impact(t) == N._classify_impact(t, titulo=t) == "HIGH"


# ── N.CRITICO_KW: las palabras que no admiten segunda lectura llegan solas ─────

def test_una_critica_sola_en_el_titular_llega_a_high():
    """'tariff' o 'fomc' no son ambiguas como sí lo son 'war' o 'attack', que
    salen en cualquier crónica internacional. Sin este peso extra, un titular
    con UNA señal inequívoca se quedaba en MED."""
    t = "Trump announces 50% tariff on China"
    assert N._classify_impact(t, titulo=t) == "HIGH"


def test_una_high_no_critica_sola_en_el_titular_se_queda_en_med():
    """El contraste que da sentido al test anterior: 'sanction' está en N.HIGH_KW
    pero no en N.CRITICO_KW, así que sola no basta."""
    t = "Officials discuss a sanction against the shipping company"
    assert N._classify_impact(t, titulo=t) == "MED"


def test_las_criticas_no_se_cobran_dos_veces():
    """N.CRITICO_KW y N.HIGH_KW se solapan a propósito (tariff, cpi, fomc...), y el
    bucle de N.HIGH_KW descuenta las críticas para no sumarlas por partida doble.

    El caso donde la diferencia se ve: una crítica en el CUERPO (1,5) más una
    MED en el titular (1) suman 2,5 y se quedan en MED. Cobrando dos veces la
    crítica pasarían de 3 y colarían como HIGH."""
    solapadas = [k for k in N.CRITICO_KW if k in N.HIGH_KW]
    assert solapadas, "el test pierde sentido si dejan de solaparse"

    titulo = "Company raises its dividend"
    texto  = titulo + " after the tariff decision was postponed"
    assert N._classify_impact(texto, titulo=titulo) == "MED"


# ── Contexto de surge/plunge: el fallo que sobrevivió a la primera pasada ────

def test_plunge_sin_contexto_de_mercado_no_es_high():
    """'Lettuce prices see record-setting plunge' seguía en HIGH tras el
    rediseño porque N.CONTEXT_HIGH_PLUNGE incluía la palabra suelta 'price'.
    Cualquier caída de precio de cualquier cosa entraba."""
    t = "Lettuce prices see record-setting plunge"
    assert N._classify_impact(t, titulo=t) != "HIGH"


def test_plunge_con_contexto_de_mercado_si_es_high():
    t = "Nasdaq futures plunge after CPI surprise"
    assert N._classify_impact(t, titulo=t) == "HIGH"


def test_price_ya_no_es_contexto_de_mercado_por_si_solo():
    assert "price" not in N.CONTEXT_HIGH_SURGE
    assert "price" not in N.CONTEXT_HIGH_PLUNGE


# ── Vocabulario del informe de empleo ───────────────────────────────────────

def test_el_informe_de_empleo_se_caza_por_como_lo_titulan_los_medios():
    """Solo estaba "nonfarm", que los titulares casi nunca usan -- el informe
    macro que más mueve el mercado cada mes se colaba como MED."""
    t = "Here are three key takeaways from the disappointing July jobs report"
    assert N._classify_impact(t, titulo=t) == "HIGH"


def test_las_palabras_del_informe_de_empleo_estan_en_high():
    for kw in ("payrolls", "jobs report", "jobless claims"):
        assert kw in N.HIGH_KW


# ── Ruido: lo que NO debe subir ─────────────────────────────────────────────

def test_una_nota_corporativa_rutinaria_es_low():
    t = "Apple names new head of retail operations"
    assert N._classify_impact(t, titulo=t) == "LOW"


def test_una_recomendacion_de_analista_es_med_no_high():
    t = "Analyst upgrades Nike to buy"
    assert N._classify_impact(t, titulo=t) == "MED"


def test_las_med_valen_la_mitad_que_las_high():
    """Dos MED en el titular suman 2 (0,5 cada una, x2 por ir en titular) y se
    quedan cortas; una HIGH + una MED suman 3 y llegan. Es lo que fija el peso
    relativo entre las dos listas -- si alguien las iguala, este test cae."""
    dos_med = "Company announces dividend increase and buyback"
    assert N._classify_impact(dos_med, titulo=dos_med) == "MED"

    high_y_med = "Sanction pressure builds as the company cuts its dividend"
    assert N._classify_impact(high_y_med, titulo=high_y_med) == "HIGH"


# ── Los umbrales son coherentes entre sí ────────────────────────────────────

def test_umbrales_y_pesos_mantienen_la_relacion_que_asumen_los_tests():
    assert N.PESO_TITULO == 2 * N.PESO_DESC
    assert N.UMBRAL_HIGH > N.UMBRAL_MED > 0
    # Una HIGH sola en el titular (2) tiene que quedarse CORTA del umbral alto,
    # o volvemos al comportamiento de "la primera palabra gana".
    assert N.PESO_TITULO < N.UMBRAL_HIGH


def test_med_kw_y_high_kw_no_se_solapan():
    """Una palabra en las dos listas sumaría por los dos bucles. N.HIGH_KW y
    N.MED_KW se recorren enteras y sin descuento entre ellas (a diferencia de
    N.CRITICO_KW, que sí se descuenta de N.HIGH_KW)."""
    assert not (set(N.HIGH_KW) & set(N.MED_KW))
