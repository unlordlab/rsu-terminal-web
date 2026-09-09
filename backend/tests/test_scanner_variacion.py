"""
El escáner no sabía cuánto se había movido nada: cero columnas de variación en 497 valores.

EL CASO, pedido por el usuario el 09/09/2026 con la captura del desplegable de
Finviz («Today Up», «Week −20%», «Month +30%»…). Comprobado contra el escaneo
publicado ANTES de tocar nada: 497 valores, y los campos por ticker eran
`above_sma50, dias_absorcion, l3_*, new_high, new_low, phase*, precio, rs_pct,
rs_score, rvol, score_tecnico, sector, trend`. **Ni uno de variación de
precio.** No es que estuviera mal calculado: no existía.

TRES DECISIONES QUE NO SON OBVIAS:

  1. **No es intradía, y la etiqueta lo dice.** Este módulo tiene escrita como
     regla de diseño que ninguna petición de usuario dispara descargas — el
     escaneo corre una vez de madrugada. Así que el dato es siempre el de la
     última sesión CERRADA. Por eso la ventana se llama «Sesión» y no «Hoy»:
     llamarlo «hoy» a media tarde sería afirmar algo falso sobre un dato de
     anoche, que es exactamente lo que costó dos auditorías en Amplitud de
     Mercado. (En Finviz el intradía de verdad es de pago; su propio
     desplegable lo marca «Elite only».)
  2. **Los umbrales crecen con la ventana**: ±5/10/15 en una sesión, ±10/20/30
     en una semana, hasta ±50 en un mes. Los mismos cortes en las cuatro darían
     listas vacías arriba y de trescientos valores abajo.
  3. **Sin dato es None, nunca 0.** Un 0 significaría «no se ha movido» y
     colaría el ticker en cualquier filtro de rango. Es el mismo fallo que ya
     está documentado en `l3_zona_baja`.

LO MEDIDO, sobre 125 valores reales del universo (1 de cada 4) en una sesión
normal: «Sesión −5%» dejó pasar 1, «Sesión ±15%» ninguno, «Mes −10%» 24. Las
opciones extremas salen vacías casi siempre **porque el universo son las ~500
mayores empresas de EE.UU.**, que rara vez se mueven un 15% en un día. No es un
fallo: es lo que las hace útiles como aviso el día que devuelven algo.

Uso:
    cd backend
    python -m pytest tests/test_scanner_variacion.py -v
"""
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.scanner_service as S  # noqa: E402

RAIZ = os.path.join(os.path.dirname(__file__), "..", "..")


def _fila(**chg):
    """Una fila del escaneo con solo las variaciones que interesen."""
    base = {f"chg_{v}": None for v in S.VARIACION_VENTANAS}
    base.update(chg)
    return base


# ── Qué significa cada opción ────────────────────────────────────────────────

def test_sube_y_baja_dejan_fuera_al_que_no_se_ha_movido():
    """EL test de los dos extremos. Un valor exactamente plano no «sube» ni
    «baja»; si entrara en los dos, las dos listas sumarían más que el universo."""
    plano = _fila(chg_1d=0.0)
    assert not S._cumple_variacion(plano, "1d_up")
    assert not S._cumple_variacion(plano, "1d_down")
    assert S._cumple_variacion(_fila(chg_1d=0.01), "1d_up")
    assert S._cumple_variacion(_fila(chg_1d=-0.01), "1d_down")


def test_los_umbrales_son_o_mas_no_exactamente():
    """«−15% o peor» tiene que incluir al que ha caído un 40%. Si fuera un rango
    cerrado, el desplome grande se escaparía justo del filtro hecho para él."""
    desplome = _fila(chg_1d=-40.0)
    for cod in ("1d_-5", "1d_-10", "1d_-15", "1d_down"):
        assert S._cumple_variacion(desplome, cod), cod
    assert not S._cumple_variacion(desplome, "1d_up")


def test_el_limite_exacto_SI_pasa():
    """Un −5,00% clavado cumple «−5% o peor». Es la diferencia entre `<=` y `<`,
    y es el sitio donde se cuela un fallo de uno."""
    assert S._cumple_variacion(_fila(chg_1d=-5.0), "1d_-5")
    assert not S._cumple_variacion(_fila(chg_1d=-4.99), "1d_-5")
    assert S._cumple_variacion(_fila(chg_1d=5.0), "1d_+5")
    assert not S._cumple_variacion(_fila(chg_1d=4.99), "1d_+5")


def test_sin_dato_NO_pasa_ningun_filtro():
    """La mitad que se olvida. Con `or 0`, un valor sin histórico entraría en
    todos los filtros de caída como si estuviera plano — y es justo el ticker
    del que no sabemos nada."""
    sin = _fila()
    for cod in S.VARIACION_PRESETS:
        assert not S._cumple_variacion(sin, cod), cod


def test_sin_dato_no_pasa_NI_SIQUIERA_un_umbral_de_cero(monkeypatch):
    """El test de arriba NO caza el `or 0`, y lo comprobé: con los umbrales de
    hoy (±5 y más), sustituir «sin dato» por 0 da exactamente el mismo
    resultado en las 32 opciones, porque ningún corte pasa por el cero.

    O sea que el sabotaje se escapaba por suerte, no por estar cubierto. Basta
    con que alguien añada mañana un «Sesión: sin cambios» o baje un umbral a 0
    para que «no sé cuánto se ha movido» empiece a colarse como «no se ha
    movido». Aquí se le pone delante ese umbral y se exige que siga fuera."""
    monkeypatch.setitem(S.VARIACION_PRESETS, "1d_cero",
                        {"campo": "chg_1d", "op": ">=", "valor": 0.0,
                         "etiqueta": "Sesión: 0% o más"})
    assert S._cumple_variacion(_fila(chg_1d=0.0), "1d_cero"), "el cero real sí cumple"
    assert not S._cumple_variacion(_fila(), "1d_cero"), (
        "un ticker SIN dato ha pasado un umbral de 0: se está sustituyendo el "
        "None por un número")


def test_cada_opcion_mira_SU_ventana():
    """Un valor que se desploma en el día pero sube en el mes solo puede salir
    en el filtro del día. Es el fallo que se cuela al copiar la tabla a mano:
    `chg_1w` pegado en la fila del mes."""
    fila = _fila(chg_1d=-20.0, chg_1w=-20.0, chg_1m=+40.0, chg_3m=+40.0)
    assert S._cumple_variacion(fila, "1d_-15")
    assert S._cumple_variacion(fila, "1w_-20")
    assert not S._cumple_variacion(fila, "1m_-20")
    assert S._cumple_variacion(fila, "1m_+30")


def test_un_codigo_inventado_no_deja_pasar_a_nadie():
    """Fallar cerrado. Si un código desconocido dejara pasar a todos, un enlace
    con un parámetro mal escrito enseñaría el universo entero como si lo
    cumpliera."""
    assert not S._cumple_variacion(_fila(chg_1d=99.0), "1d_+999")
    assert not S._cumple_variacion(_fila(chg_1d=99.0), "")


# ── La tabla de opciones ─────────────────────────────────────────────────────

def test_hay_las_CUATRO_ventanas_y_ninguna_se_queda_sin_opciones():
    assert set(S.VARIACION_VENTANAS) == {"1d", "1w", "1m", "3m"}
    for v in S.VARIACION_VENTANAS:
        codigos = [c for c in S.VARIACION_PRESETS if c.startswith(v + "_")]
        assert len(codigos) >= 4, f"{v} solo tiene {len(codigos)} opciones"


def test_cada_opcion_apunta_al_campo_de_SU_ventana():
    """El error de copiar y pegar, atado. Un `chg_1w` en una opción de mes
    filtraría por la semana sin fallar nunca."""
    for codigo, p in S.VARIACION_PRESETS.items():
        ventana = codigo.split("_")[0]
        assert p["campo"] == f"chg_{ventana}", f"{codigo} mira {p['campo']}"


def test_los_umbrales_CRECEN_con_la_ventana():
    """Decisión de diseño, atada: el corte más grande de cada ventana no puede
    ser menor que el de la ventana más corta. Si alguien iguala los cuatro, el
    filtro del trimestre devuelve media bolsa."""
    topes = {}
    for v in S.VARIACION_VENTANAS:
        subidas = [p["valor"] for c, p in S.VARIACION_PRESETS.items()
                   if c.startswith(v + "_") and p["op"] == ">="]
        topes[v] = max(subidas)
    assert topes["1d"] < topes["1w"] <= topes["1m"]
    assert topes["1w"] > 0


def test_las_etiquetas_dicen_la_ventana_y_el_signo():
    """Se pintan tal cual en el desplegable y en la línea de criterios activos:
    si no llevan la ventana, «+10% o más» aparece cuatro veces idéntico."""
    for codigo, p in S.VARIACION_PRESETS.items():
        nombre = S.VARIACION_VENTANAS[codigo.split("_")[0]][0]
        assert p["etiqueta"].startswith(nombre + ":"), p["etiqueta"]
    # El menos es un MENOS tipográfico (U+2212), no un guion: en la tabla
    # monoespaciada de resultados un guion normal se confunde con el «—» de
    # «sin dato».
    assert S.VARIACION_PRESETS["1w_-20"]["etiqueta"] == "Semana: −20% o peor"
    assert S.VARIACION_PRESETS["1w_+20"]["etiqueta"] == "Semana: +20% o más"


def test_ninguna_etiqueta_dice_HOY():
    """LA decisión de honestidad de este trabajo. El dato es del cierre
    anterior; una etiqueta «Hoy» afirmaría algo falso sobre él a partir de la
    apertura, y es el error exacto que ya se pagó dos veces en Amplitud."""
    for p in S.VARIACION_PRESETS.values():
        assert "hoy" not in p["etiqueta"].lower(), p["etiqueta"]
    for _, explicacion in S.VARIACION_VENTANAS.values():
        assert "hoy" not in explicacion.lower(), explicacion


def test_el_desplegable_llega_ORDENADO_de_caida_a_subida():
    """Se pinta en ese orden; ordenarlo en el frontend obligaría a saber allí
    que «1w_-30» va antes que «1w_-20», que es conocimiento de esta tabla."""
    ops = S.opciones_de_variacion()
    assert len(ops) == len(S.VARIACION_PRESETS)
    por_ventana = {}
    for o in ops:
        por_ventana.setdefault(o["codigo"].split("_")[0], []).append(o["codigo"])
    for ventana, codigos in por_ventana.items():
        valores = [S.VARIACION_PRESETS[c]["valor"] for c in codigos]
        assert valores == sorted(valores), f"{ventana} sale desordenado: {codigos}"


def test_el_desplegable_dice_cuantas_sesiones_mide_cada_ventana():
    """«Semana» es ambiguo —¿5 sesiones, 7 días, la semana natural?— y de eso
    depende que el número cuadre o no con el de otro sitio."""
    ops = S.opciones_de_variacion()
    mide = {o["grupo"]: o["mide"] for o in ops}
    assert "5 sesiones" in mide["Semana"]
    assert "21 sesiones" in mide["Mes"]
    assert "63 sesiones" in mide["Trimestre"]
    assert "cerrada" in mide["Sesión"], "no se dice que es la sesión ya cerrada"


# ── Que no se filtre contra un escaneo que no trae el dato ───────────────────

def test_se_detecta_el_escaneo_ANTIGUO():
    """Entre desplegar esto y el siguiente escaneo nocturno, el Gist vivo es el
    de antes y no trae las columnas."""
    viejo = {"AAPL": {"precio": 100.0}, "MSFT": {"precio": 200.0}}
    assert not S.hay_datos_de_variacion(viejo)
    nuevo = {"AAPL": {"precio": 100.0, "chg_1d": None},
             "MSFT": {"precio": 200.0, "chg_1d": -1.2}}
    assert S.hay_datos_de_variacion(nuevo)


def test_con_escaneo_antiguo_se_DICE_no_se_devuelve_lista_vacia(monkeypatch):
    """LA parte que evita el silencio ambiguo. Una lista vacía sería
    indistinguible de «hoy no se ha movido nada así», y el usuario esperaría
    resultados que no van a llegar nunca."""
    viejo = {"ok": True, "stocks": {"AAPL": {"precio": 100.0}},
             "universe_size": 1, "generated_at": ""}
    monkeypatch.setattr(S, "_load_gist", lambda: viejo)
    monkeypatch.setattr(S.cache, "get", lambda k: None)
    monkeypatch.setattr(S.cache, "set", lambda *a, **k: None)
    r = S.run_filter(variacion="1w_-20")
    assert r["ok"] is False
    assert "escaneo" in r["error"].lower()
    # Y sin el filtro, el mismo escaneo antiguo SIGUE funcionando: lo que falta
    # es una columna, no el módulo.
    assert S.run_filter(rvol_min=0)["ok"] is True


# ── El cálculo, en el escaneo nocturno ───────────────────────────────────────

def test_el_calculo_del_escaneo_es_el_porcentaje_de_verdad():
    """Verificado además contra precios reales de AAPL/NVDA/KO calculando el %
    por otro camino: los 12 cuadran al segundo decimal."""
    pd = pytest.importorskip("pandas")
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    from scanner_universe import _variacion

    s = pd.Series([100.0, 110.0])
    assert _variacion(s, 1) == 10.0
    assert _variacion(pd.Series([100.0, 90.0]), 1) == -10.0
    # Cinco sesiones atrás es cinco POSICIONES atrás, no la primera de la serie.
    serie = pd.Series([50.0, 100.0, 101.0, 102.0, 103.0, 104.0, 110.0])
    assert _variacion(serie, 5) == 10.0


def test_el_calculo_devuelve_None_y_no_cero_cuando_no_puede():
    pd = pytest.importorskip("pandas")
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    from scanner_universe import _variacion

    assert _variacion(pd.Series([1.0, 2.0, 3.0]), 21) is None, "serie corta"
    assert _variacion(pd.Series(dtype=float), 1) is None, "serie vacía"
    assert _variacion(None, 1) is None
    assert _variacion(pd.Series([0.0, 5.0]), 1) is None, "precio 0 detrás: división"
    assert _variacion(pd.Series([5.0, float("nan")]), 1) is None, "NaN al final"


def test_el_escaneo_guarda_las_MISMAS_ventanas_que_filtra_el_servicio():
    """Si el escaneo publicara `chg_2w` y el servicio buscara `chg_1w`, el
    filtro devolvería lista vacía siempre sin fallar. Las dos listas tienen que
    salir de la misma verdad."""
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    from scanner_universe import VENTANAS_VARIACION
    assert set(VENTANAS_VARIACION) == set(S.VARIACION_VENTANAS)


def test_las_ventanas_son_sesiones_de_bolsa_con_los_numeros_de_siempre():
    sys.path.insert(0, os.path.join(RAIZ, "scripts"))
    from scanner_universe import VENTANAS_VARIACION
    assert VENTANAS_VARIACION == {"1d": 1, "1w": 5, "1m": 21, "3m": 63}


# ── Que llegue a la pantalla ─────────────────────────────────────────────────

def test_las_variaciones_viajan_en_CADA_resultado(monkeypatch):
    """Se filtre o no por ellas: la tabla pinta la columna y se puede ordenar
    por «lo que más se ha movido» sin activar ningún filtro."""
    scan = {"ok": True, "universe_size": 1, "generated_at": "",
            "stocks": {"AAPL": {"precio": 1.0, "score_tecnico": 50,
                                "chg_1d": -2.0, "chg_1w": 3.0,
                                "chg_1m": None, "chg_3m": 9.0}}}
    monkeypatch.setattr(S, "_load_gist", lambda: scan)
    monkeypatch.setattr(S.cache, "get", lambda k: None)
    monkeypatch.setattr(S.cache, "set", lambda *a, **k: None)
    monkeypatch.setattr("services.cartera_service.get_cartera_tickers", lambda: set())
    fila = S.run_filter()["results"][0]
    assert fila["chg_1d"] == -2.0 and fila["chg_1w"] == 3.0
    assert fila["chg_3m"] == 9.0
    assert fila["chg_1m"] is None, "un None se ha convertido en número por el camino"


def test_el_filtro_DEJA_FUERA_de_verdad_a_quien_no_cumple(monkeypatch):
    """EL test de punta a punta, y el que faltaba: los de arriba llaman a
    `_cumple_variacion` directamente, así que **quitar el criterio de
    `_passes_filters` no lo notaba ninguno** — el filtro habría devuelto el
    universo entero con cara de haber filtrado. Lo destapó el sabotaje."""
    scan = {"ok": True, "universe_size": 3, "generated_at": "", "stocks": {
        "CAE":   {"precio": 1.0, "score_tecnico": 10, "chg_1d": -18.0, "chg_1m": 2.0},
        "SUBE":  {"precio": 1.0, "score_tecnico": 20, "chg_1d": +9.0,  "chg_1m": 2.0},
        "QUIETO": {"precio": 1.0, "score_tecnico": 30, "chg_1d": 0.0,  "chg_1m": 2.0},
    }}
    monkeypatch.setattr(S, "_load_gist", lambda: scan)
    monkeypatch.setattr(S.cache, "get", lambda k: None)
    monkeypatch.setattr(S.cache, "set", lambda *a, **k: None)
    monkeypatch.setattr("services.cartera_service.get_cartera_tickers", lambda: set())

    def tickers(**kw):
        return sorted(r["ticker"] for r in S.run_filter(**kw)["results"])

    assert tickers() == ["CAE", "QUIETO", "SUBE"], "sin filtro salen los tres"
    assert tickers(variacion="1d_-15") == ["CAE"]
    assert tickers(variacion="1d_up") == ["SUBE"]
    assert tickers(variacion="1d_down") == ["CAE"]
    assert tickers(variacion="1d_+5") == ["SUBE"]
    # Y el recuento que se pinta en pantalla tiene que cuadrar con la lista.
    r = S.run_filter(variacion="1d_-15")
    assert r["matched"] == 1 and r["active_criteria"]["variacion"] == "1d_-15"


def test_el_embudo_cuenta_la_variacion_como_un_criterio_mas(monkeypatch):
    """El embudo dice cuántos pasa cada criterio POR SEPARADO. Si la variación
    no entrara, una lista vacía por su culpa no tendría explicación en
    pantalla."""
    scan = {"ok": True, "universe_size": 2, "generated_at": "", "stocks": {
        "CAE":  {"precio": 1.0, "score_tecnico": 10, "chg_1d": -18.0},
        "SUBE": {"precio": 1.0, "score_tecnico": 20, "chg_1d": +9.0},
    }}
    monkeypatch.setattr(S, "_load_gist", lambda: scan)
    monkeypatch.setattr(S.cache, "get", lambda k: None)
    monkeypatch.setattr(S.cache, "set", lambda *a, **k: None)
    monkeypatch.setattr("services.cartera_service.get_cartera_tickers", lambda: set())
    embudo = S.run_filter(variacion="1d_-15")["embudo"]
    fila = next((f for f in embudo if f["criterio"] == "variacion"), None)
    assert fila is not None, "la variación no aparece en el embudo"
    assert fila["pasan"] == 1 and fila["de"] == 2


def test_el_endpoint_RECHAZA_un_codigo_inventado():
    """Ignorarlo devolvería el universo entero con cara de haber filtrado — la
    forma más silenciosa posible de mentir.

    Se LLAMA al endpoint, no se lee su código: mi primera versión buscaba las
    cadenas «VARIACION_PRESETS» y «422» en el fichero, y el sabotaje de anular
    la comprobación (`if False:`) las dejaba las dos vivas y se escapaba."""
    from fastapi.testclient import TestClient
    from auth import verify_token
    from main import app

    app.dependency_overrides[verify_token] = lambda: {"sub": "x@y.z", "tier": "tier1"}
    try:
        with TestClient(app) as c:
            malo = c.get("/api/v1/scanner/filter", params={"variacion": "1d_+999"})
            bueno = c.get("/api/v1/scanner/filter", params={"variacion": "1d_up"})
    finally:
        app.dependency_overrides.clear()
    assert malo.status_code == 422, malo.status_code
    assert "1d_+999" in malo.text
    # El código bueno NO puede rechazarse: si el endpoint rechazara todo, el
    # test de arriba pasaría con el filtro entero inservible.
    assert bueno.status_code != 422, bueno.text[:200]


def test_el_desplegable_de_la_pantalla_NO_es_una_segunda_lista():
    """Este fichero ya tuvo cuatro listas paralelas y dos filtros llegaron a
    producción sin funcionar. Las opciones tienen que venir del backend."""
    js = io.open(os.path.join(RAIZ, "frontend", "pages", "scanner.js"),
                 encoding="utf-8").read()
    assert "data.variaciones" in js, "el frontend no consume la lista del backend"
    # Y NO puede haber una tabla de códigos escrita a mano en el JS.
    #
    # Se miran las líneas de CÓDIGO, no el fichero entero: mi primera versión
    # buscaba en todo el texto y falló contra mi propio comentario, que cita
    # "1w_-20" como ejemplo. Van nueve veces esta semana el mismo patrón --
    # comprobar texto en vez de comportamiento.
    codigo_js = "\n".join(l for l in js.split("\n") if not l.strip().startswith("//"))
    for cod in ("1w_-20", "1m_+30", "3m_+50"):
        assert cod not in codigo_js, (
            f"{cod} está escrito a mano en el frontend: es una segunda lista")
