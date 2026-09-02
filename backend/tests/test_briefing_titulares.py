"""
El bloque de «medios internacionales» traía prensa local de Kelowna.

EL CASO, 02/09/2026, al preguntar el usuario si el prompt lee las noticias más
relevantes. `get_major_outlet_headlines()` existe para traer geopolítica de
alto impacto de Reuters, Bloomberg, WSJ, AP y FT. Comprobado en vivo ese día:

    query=domain:reuters.com        -> {}   (HTTP 200, 2 bytes, sin artículos)
    query=(los 5 dominios con OR)   -> 10 artículos, TODOS de kelownacapnews.com

`kelownacapnews` es un periódico local de Kelowna, Columbia Británica. Los
titulares que llegaban al prompt eran un choque en la autopista 97, un perro
salvado con naloxona, un incendio en una iglesia y un aviso de hervir el agua
en Peachland.

DOS FALLOS ENCADENADOS:

1. GDELT ignora las cláusulas `domain:` y el script SE FIABA DE LA CONSULTA --
   no comprobaba de dónde venía lo que recibía. El log incluso afirmaba
   «artículos recibidos de {domains}», que es la frase que impide ver el fallo.

2. El respaldo RSS (BBC, CNBC, Al Jazeera, verificados vivos) solo se dispara
   `if not major_headlines`. Diez titulares de Kelowna no son una lista vacía,
   así que el respaldo bueno NO ENTRABA NUNCA. Filtrar por dominio deja la
   lista vacía cuando no hay nada válido, y con eso el respaldo vuelve a vivir.

Y NO SE PUDO SABER DESDE CUÁNDO, porque los titulares no se guardaban en
ningún sitio -- el mismo agujero que costó no poder explicar cuatro
porcentajes el 01/09. Ahora se archivan, junto a los precios, en un fichero
rodante podado a los últimos días.

Uso:
    cd backend
    python -m pytest tests/test_briefing_titulares.py -v
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

MEDIOS = ["reuters.com", "bloomberg.com", "wsj.com", "apnews.com", "ft.com"]


# ── De dónde viene de verdad cada titular ────────────────────────────────────

def test_el_periodico_local_de_Kelowna_no_es_Reuters():
    """EL test. Es el dominio exacto que llenó el bloque de medios
    internacionales el 02/09."""
    assert D.es_dominio_pedido("kelownacapnews.com", MEDIOS) is False


def test_los_medios_pedidos_si_entran():
    for d in MEDIOS:
        assert D.es_dominio_pedido(d, MEDIOS) is True


def test_un_subdominio_del_mismo_medio_entra():
    """`uk.reuters.com` es Reuters; descartarlo sería tirar titulares buenos."""
    assert D.es_dominio_pedido("uk.reuters.com", MEDIOS) is True
    assert D.es_dominio_pedido("www.bloomberg.com", MEDIOS) is True


def test_un_dominio_que_solo_TERMINA_parecido_no_cuela():
    """`notreuters.com` o `fake-ft.com` no son el medio. El `endswith` va con
    punto delante justamente por esto."""
    assert D.es_dominio_pedido("notreuters.com", MEDIOS) is False
    assert D.es_dominio_pedido("reuters.com.co", MEDIOS) is False


def test_sin_dominio_no_se_da_por_bueno():
    assert D.es_dominio_pedido("", MEDIOS) is False
    assert D.es_dominio_pedido(None, MEDIOS) is False


def test_no_distingue_mayusculas():
    assert D.es_dominio_pedido("Reuters.COM", MEDIOS) is True


def _gdelt(articulos):
    from unittest.mock import MagicMock, patch
    r = MagicMock(status_code=200)
    r.json.return_value = {"articles": articulos}
    return patch.object(D.requests, "get", return_value=r)


def _art(domain, title, seendate="20260902T091500Z"):
    return {"domain": domain, "title": title, "seendate": seendate}


def test_los_titulares_de_Kelowna_NO_llegan_al_briefing():
    """EL test, con la respuesta real que dio GDELT el 02/09.

    La primera versión de este test miraba si la cadena `es_dominio_pedido(`
    aparecía en el fuente de la función -- y el sabotaje de sustituir la
    llamada por `if False:` SE LE ESCAPÓ, porque el comentario que hay encima
    menciona el nombre de la función. Cuarta vez esta semana que comprobar una
    regla contra su propia silueta en el código deja pasar el sabotaje."""
    kelowna = [
        _art("kelownacapnews.com", "2-vehicle crash on Highway 97 southbound"),
        _art("kelownacapnews.com", "Naloxone saves Vancouver Island dog Birdie"),
        _art("kelownacapnews.com", "Boil Water Notice in place for Peachland"),
    ]
    with _gdelt(kelowna):
        out = D.get_major_outlet_headlines()
    assert out == [], (
        "la prensa local de Kelowna sigue entrando en el bloque de «medios "
        "internacionales»: es lo que leyó el briefing del 02/09")


def test_lo_que_SI_es_de_los_medios_pedidos_pasa():
    buenos = [
        _art("reuters.com", "Global bond selloff gains pace"),
        _art("kelownapcapnews.com", "Church fire under investigation"),
        _art("www.bloomberg.com", "Fed officials split on next move"),
    ]
    with _gdelt(buenos):
        out = D.get_major_outlet_headlines()
    assert [x["source"] for x in out] == ["reuters.com", "www.bloomberg.com"]
    assert out[0]["headline"] == "Global bond selloff gains pace"


def test_devolver_vacio_es_lo_que_hace_entrar_al_respaldo_RSS():
    """El respaldo (BBC/CNBC/Al Jazeera, verificados vivos) solo se dispara con
    `if not major_headlines`. Mientras GDELT devolvía diez titulares de Kelowna
    -- que no son una lista vacía-- el respaldo bueno NO ENTRABA NUNCA."""
    import inspect
    main = inspect.getsource(D.main)
    assert "if not major_headlines:" in main and "get_rss_fallback_headlines()" in main
    with _gdelt([_art("kelownacapnews.com", "Vernon church fire")]):
        assert D.get_major_outlet_headlines() == []


def test_el_log_ya_no_afirma_lo_que_no_ha_comprobado():
    """«artículos recibidos de {domains}» es la frase que impedía ver el fallo
    al leer los registros del Action."""
    import inspect
    fuente = inspect.getsource(D.get_major_outlet_headlines)
    assert "recibidos de {domains}" not in fuente


# ── El archivo de auditoría, podado ──────────────────────────────────────────

def _entrada(fecha, relleno=""):
    return {"fecha": fecha, "sesion": {"fecha": fecha}, "barras": {},
            "indices": {}, "sectores": {}, "titulares_medios": [],
            "titulares_mercado": [{"titular": relleno}] if relleno else []}


def test_se_guardan_los_titulares_con_los_que_se_escribio():
    """No se guardaban, y por eso no se pudo saber desde cuándo llegaba prensa
    local al bloque de medios internacionales."""
    md = {"date": "02/09/2026", "sesion": {"fecha": "2026-09-01"}, "barras": {},
          "sectors": {}}
    news = [{"source": "Reuters", "time": "07:10 UTC", "headline": "Bond selloff gains pace"}]
    medios = [{"source": "kelownacapnews.com", "time": "09:15 UTC", "headline": "Church fire"}]
    d = D.construir_datos(md, news, medios)
    assert d["titulares_mercado"][0]["titular"] == "Bond selloff gains pace"
    assert d["titulares_medios"][0]["fuente"] == "kelownacapnews.com", (
        "sin guardar la FUENTE de cada titular no se puede detectar que el "
        "bloque de medios internacionales trae otra cosa")


def test_el_archivo_se_poda_a_los_ultimos_dias():
    """EL otro test, y lo que pidió el usuario: un fichero que solo crece acaba
    siendo ilegible y pesado de subir en cada ejecución."""
    hist = [_entrada(f"2026-08-{d:02d}") for d in range(1, 29)]
    out = D.podar_datos(hist, _entrada("2026-09-01"), max_dias=7)
    assert len(out) == 7
    assert out[-1]["fecha"] == "2026-09-01", "el de hoy tiene que estar"
    # 6 días de agosto (23 al 28) más el de hoy: los 7 más recientes.
    assert out[0]["fecha"] == "2026-08-23", "se conservan los más recientes"
    assert "2026-08-01" not in [e["fecha"] for e in out], "no se ha podado nada"


def test_una_segunda_ejecucion_del_MISMO_dia_no_duplica():
    """El Action se relanza a mano con frecuencia por el retraso del
    planificador de GitHub: dos ejecuciones el mismo día no pueden dejar dos
    entradas para esa fecha."""
    hist = [_entrada("2026-08-31"), _entrada("2026-09-01", relleno="viejo")]
    out = D.podar_datos(hist, _entrada("2026-09-01", relleno="nuevo"))
    fechas = [e["fecha"] for e in out]
    assert fechas.count("2026-09-01") == 1
    assert out[-1]["titulares_mercado"][0]["titular"] == "nuevo", (
        "la segunda ejecución del día tiene que REEMPLAZAR a la primera")


def test_un_tope_duro_de_tamano_por_si_un_dia_entra_algo_enorme():
    """Más vale perder archivo antiguo que dejar de publicar el briefing por un
    Gist demasiado pesado."""
    gordas = [_entrada(f"2026-08-{d:02d}", relleno="x" * 20_000) for d in range(20, 28)]
    out = D.podar_datos(gordas, _entrada("2026-09-01"), max_dias=7, max_chars=30_000)
    assert len(json.dumps(out, ensure_ascii=False)) <= 30_000
    assert out[-1]["fecha"] == "2026-09-01", "el de hoy nunca se poda"


def test_el_de_hoy_sobrevive_aunque_el_solo_pase_del_tope():
    """Si la entrada de hoy es enorme, podar hasta dejarla fuera perdería justo
    lo que se acaba de escribir."""
    out = D.podar_datos([], _entrada("2026-09-01", relleno="x" * 50_000), max_chars=1000)
    assert len(out) == 1 and out[0]["fecha"] == "2026-09-01"


def test_un_archivo_corrupto_no_tumba_la_publicacion():
    """`leer_datos_archivados()` puede devolver cualquier cosa si el Gist viene
    raro. Perder archivo es malo; no publicar el briefing, peor."""
    out = D.podar_datos(["basura", None, 42, _entrada("2026-08-31")], _entrada("2026-09-01"))
    assert [e["fecha"] for e in out] == ["2026-08-31", "2026-09-01"]


def test_el_archivo_se_publica_como_fichero_propio_del_Gist():
    import inspect
    fuente = inspect.getsource(D.save_to_gist)
    assert "DATOS_FILE" in fuente and "podar_datos(" in fuente, (
        "el archivo de auditoría no se está publicando ni podando")


def test_los_titulares_no_se_cuelan_en_el_prompt_por_esta_via():
    """El archivo es para auditar después, no para el modelo: este prompt lleva
    semanas sin caber en el límite de Groq."""
    md = {"date": "02/09/2026", "time": "08:00", "sectors": {}, "calendar": [],
          "sesion": {"en_curso": False, "fecha": "2026-09-01", "hora_et": "08:00"}}
    p = D.build_prompt(md, [], [], [], {}, [], [], [])
    assert "titulares_medios" not in p and "briefing_datos" not in p
