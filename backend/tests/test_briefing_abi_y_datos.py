"""
El ABI de 39,8% se leyó como «falta de convicción» siendo casi capitulación.

EL CASO, 01/09/2026. El briefing escribió:

    «el índice de Breadth (ABI) está en el 39,8%, un nivel que denota
     dispersión y falta de convicción. No hay un líder claro que arrastre
     al resto.»

Es exactamente al revés. El ABI es |avances − descensos| sobre el total: mide
CUÁNTO SE IMPONE UN LADO. Un 39,8% está a dos décimas del umbral de
capitulación de la propia escala — una venta abrumadoramente unidireccional,
que es lo contrario de «falta de convicción».

POR QUÉ. Al McClellan se le puso su banda el 26/08 (#35) y desde entonces se
lee bien todos los días: −39,0 «zona neutra», −70,6 «bajista», −109,5
«claramente bajista». Al ABI se le mandaba el número con la escala al lado
pero SIN banda, y encima la escala empezaba con la palabra «dispersión», que
invita justo a la lectura contraria. El mismo hallazgo, en el indicador de al
lado, sin aplicar.

Y LA SEGUNDA MITAD DE ESTE FICHERO: ese mismo día el briefing publicó un S&P
−0,58%, un Russell −1,92%, un XLU −2,20% y un XLI −2,05% que no son la
variación de ninguna sesión real — los cuatro coinciden EXACTAMENTE con el
tramo 27/08 → 31/08, dos sesiones presentadas como una. **No se pudo
averiguar la causa**: `briefing.json` guardaba el texto y el nivel de recorte,
pero no los datos de entrada, y al día siguiente los precios de yfinance ya
han cambiado y la ventana de `period="5d"` se ha desplazado. Auditar era
adivinar. Ahora se guarda con qué números se escribió, y sobre todo QUÉ DOS
FECHAS se compararon para sacar cada porcentaje. No cuesta ni una ficha del
prompt: va al Gist, no al modelo.

Uso:
    cd backend
    python -m pytest tests/test_briefing_abi_y_datos.py -v
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


def _gist(adv, dec):
    """Gist del Scanner con 56 sesiones (hacen falta 40+ para el McClellan).
    El ABI sale del ÚLTIMO día, así que solo ese lleva los avances de prueba."""
    hist = [{"date": f"2026-06-{d:02d}", "advances": 1200, "declines": 1200,
             "new_highs": 24, "new_lows": 43, "pct_above_sma50": 50.8}
            for d in range(1, 29)] * 2
    hist[-1] = {"date": "2026-08-31", "advances": adv, "declines": dec,
                "new_highs": 24, "new_lows": 43, "pct_above_sma50": 50.8}
    contenido = {"stocks": {"AAPL": {"above_sma50": True}},
                 "breadth_history": hist,
                 "breadth_sp500": [{"date": "2026-08-31", "advances": 135, "declines": 358}],
                 "breadth_russell": [{"date": "2026-08-31", "advances": 465, "declines": 1242}],
                 "universe_size": 497}
    r = MagicMock(status_code=200)
    r.json.return_value = {"files": {D.SCANNER_GIST_FILE: {"content": json.dumps(contenido)}}}
    return r


def _amplitud(adv, dec):
    with patch.object(D.requests, "get", return_value=_gist(adv, dec)):
        return D.get_rsu_breadth_signals()


# ── La banda del ABI ─────────────────────────────────────────────────────────

def test_el_ABI_del_caso_real_no_se_clasifica_como_mercado_flojo():
    """EL test. 135+358 en el S&P y el resto del universo igual de sesgado dan
    el 39,8% que el briefing llamó «falta de convicción»."""
    b = _amplitud(717, 1666)          # |717-1666| / 2383 = 39,8%
    assert b["abi"] == 39.8
    assert b["abi_estado"].startswith("ALTO"), (
        "un ABI de 39,8 está a dos décimas de capitulación; sin banda el modelo "
        "lo leyó como dispersión y falta de convicción")
    # La dirección se le añadió el 03/09, después de que el briefing leyera un
    # desequilibrio AL ALZA como «la inmensa mayoría de los componentes
    # cayeron». Ver test_briefing_amplitud_truncada.py.
    assert b["abi_estado"] == "ALTO a la baja", "717 avances contra 1.666 es a la baja"


def test_un_mercado_de_verdad_apagado_se_llama_apagado():
    """El 27/08 el ABI fue 11,4% y el briefing lo leyó bien: «mercado
    apagado». Esa lectura no se puede romper al añadir la banda."""
    b = _amplitud(1056, 1328)         # 11,4%
    assert b["abi"] == 11.4 and b["abi_estado"] == "APAGADO"


def test_una_capitulacion_se_llama_capitulacion():
    b = _amplitud(300, 2100)          # 75%
    assert b["abi_estado"] == "CAPITULACION a la baja"


def test_el_tramo_de_en_medio_existe():
    b = _amplitud(900, 1500)          # 25%
    assert b["abi_estado"] == "MODERADO a la baja"


def test_sin_ABI_no_se_inventa_una_banda():
    b = _amplitud(0, 0)
    assert b.get("abi") is None and b.get("abi_estado") is None


def test_la_banda_viaja_al_prompt_y_la_escala_ya_no_dice_dispersion():
    """Que la banda exista no sirve si no llega, y la palabra «dispersión»
    invitaba justo a la lectura contraria."""
    p = D.build_prompt(
        {"date": "01/09/2026", "time": "08:09", "sectors": {}, "calendar": [],
         "sesion": {"en_curso": False, "fecha": "2026-08-31", "hora_et": "08:09"}},
        [], [], [], {"abi": 39.8, "abi_estado": "ALTO", "mcclellan": -109.5,
                     "mcclellan_estado": "BAJISTA", "pct_above_sma50": 50.8,
                     "advances": 717, "declines": 1666, "new_highs": 24,
                     "new_lows": 43, "nh_nl": -19, "sp500_advances": 135,
                     "sp500_declines": 358, "sp500_pct_al_alza": 27.4,
                     "universo_amplitud": 2383, "universe_size": 497,
                     "fecha": "2026-08-31"}, [], [], [])
    assert "ABI: 39.8% (ALTO)" in p, "el ABI sigue viajando sin su banda"
    assert "dispersión" not in p, (
        "la escala sigue empezando por «dispersión», que es la palabra que "
        "llevó al modelo a leer un ABI alto como falta de convicción")
    assert "CUÁNTO se impone un lado" in p


# ── Con qué números se escribió ──────────────────────────────────────────────

def test_el_briefing_guarda_las_DOS_fechas_que_compara_cada_variacion():
    """EL otro test. Sin esto, auditar un porcentaje raro al día siguiente es
    adivinar: los precios ya han cambiado y la ventana de `period="5d"` se ha
    desplazado. El 01/09 costó no poder explicar cuatro cifras."""
    import inspect
    fuente = inspect.getsource(D.get_market_data)
    assert "barras[name]" in fuente and "barras[etf]" in fuente, (
        "no se registra contra qué barra se calcula cada variación, ni para "
        "los índices ni para los sectores")
    assert 'data["barras"]' in fuente


MD = {
    "date": "01/09/2026", "time": "08:09",
    "sesion": {"en_curso": False, "fecha": "2026-08-31", "hora_et": "08:09"},
    "barras": {"SPX": ("2026-08-28", "2026-08-31"), "XLE": ("2026-08-28", "2026-08-31")},
    "SPX": {"price": 7686.14, "chg_pct": -0.33, "prev": 7711.76},
    "RUT": {"price": 2956.45, "chg_pct": -0.54, "prev": 2972.37},
    "sectors": {"XLE": {"name": "Energía", "chg_1d": 2.04, "chg_5d": 2.45}},
}


def test_esas_fechas_acaban_en_el_fichero_que_se_publica():
    """Registrarlas y no publicarlas dejaría el dato en una variable local.

    LA PRIMERA VERSIÓN DE ESTE TEST MIRABA EL TEXTO DEL FUENTE -- que apareciera
    la cadena `"barras":`-- y el sabotaje de poner `"barras": None` se le
    escapó, porque la cadena seguía estando. Por eso el diccionario se extrajo
    a `construir_payload()`: una función que se puede EJECUTAR no se puede
    comprobar contra su propia silueta."""
    pl = D.construir_payload("texto", MD, "BAJISTA", {"nombre": "mínimo"}, {})
    assert pl["datos"]["barras"] == MD["barras"], (
        "briefing.json no guarda contra qué barras se calculó cada variación: "
        "seguiría sin poderse auditar un porcentaje al día siguiente")
    assert pl["datos"]["sesion"]["fecha"] == "2026-08-31"


def test_se_guardan_los_precios_y_los_sectores_con_los_que_se_escribio():
    pl = D.construir_payload("texto", MD, "BAJISTA", {"nombre": "mínimo"}, {})
    assert pl["datos"]["indices"]["SPX"]["chg_pct"] == -0.33
    assert pl["datos"]["indices"]["RUT"]["prev"] == 2972.37
    assert pl["datos"]["sectores"]["XLE"]["chg_1d"] == 2.04


def test_el_diagnostico_de_recorte_sigue_estando():
    """El bloque nuevo no puede haberse llevado por delante el que ya había."""
    pl = D.construir_payload("t", MD, "BAJISTA", {"nombre": "mínimo", "titulares": 2},
                             {"tokens_reales": 5957})
    assert pl["diagnostico"]["nivel_recorte"] == "mínimo"
    assert pl["diagnostico"]["titulares_por_fuente"] == 2
    assert pl["diagnostico"]["tokens_reales"] == 5957
    assert pl["text"] == "t" and pl["bias"] == "BAJISTA"


def test_lo_que_se_guarda_es_JSON_de_verdad():
    """Se publica en un Gist: si una tupla o una fecha no fuera serializable,
    el briefing entero dejaría de publicarse por el bloque de diagnóstico."""
    import json as _json
    pl = D.construir_payload("t", MD, "BAJISTA", {"nombre": "mínimo"}, {})
    _json.dumps(pl, ensure_ascii=False)


def test_guardarlo_no_cuesta_fichas_del_prompt():
    """Va al Gist, no al modelo. Si `barras` se colara en el prompt sería un
    coste diario en un presupuesto que lleva semanas sin caber."""
    p = D.build_prompt(
        {"date": "01/09/2026", "time": "08:09", "sectors": {}, "calendar": [],
         "barras": {"SPX": ("2026-08-28", "2026-08-31")},
         "sesion": {"en_curso": False, "fecha": "2026-08-31", "hora_et": "08:09"}},
        [], [], [], {}, [], [], [])
    assert "2026-08-28" not in p, (
        "las fechas de las barras se están colando en el prompt: son para "
        "auditar después, no para el modelo")
