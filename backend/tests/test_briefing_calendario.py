"""
El briefing abrió con el IPC de Australia presentado como el de Estados Unidos.

EL CASO, 25/08/2026. El briefing de la mañana titulaba «El IPC de junio define
la sesión» y escribía: «Hoy a las 08:30 ET se publica el IPC de junio, con un
consenso que apunta a un repunte mensual del 0,9% frente al -0,1% de mayo. El
IPC interanual se espera en el 3,3%, bajando del 3,8%». Esas cuatro cifras son,
literalmente, las del calendario:

    2026-08-25T21:30 | AUD | CPI m/m | forecast 0.9%  previous -0.1%
    2026-08-25T21:30 | AUD | CPI y/y | forecast 3.3%  previous 3.8%

Australia, a las 21:30 ET. Ese día NO había ningún dato macro de alto impacto
de Estados Unidos. El titular, toda la primera sección y la conclusión giraban
sobre un dato que no era de Wall Street.

DOS FALLOS DEL SCRIPT, ninguno del modelo:

1. EL CALENDARIO NO DECÍA EL PAÍS. Entraba cualquier evento High/Medium del
   feed, de cualquier país, y la tabla del prompt solo llevaba hora, título,
   consenso, previo e impacto. El modelo no podía saber que era australiano.

2. LA HORA ERA BASURA. `item["date"][-8:-3]` sobre
   "2026-08-25T21:30:00-04:00" devuelve "0-04:", y se rotulaba «ET». Viendo
   una hora sin sentido para un IPC, el modelo escribió de memoria la canónica
   de Estados Unidos: 08:30 ET.

Uso:
    cd backend
    python -m pytest tests/test_briefing_calendario.py -v
"""
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

HOY = datetime.now().strftime("%Y-%m-%d")


def _filtrar(eventos):
    """Llama al CODIGO REAL, no a una copia de la regla. La primera version de
    este fichero reescribia el filtro aqui dentro: los tests pasaban y dos
    sabotajes -- quitar la lista de paises y devolver el parseo de hora viejo--
    seguian en verde. Una regla comprobada contra su propia copia no comprueba
    nada."""
    return [{"time": D.hora_et(it), "pais": (it.get("country") or "").upper(),
             "event": it.get("title")}
            for it in eventos if D.evento_relevante(it, HOY)]


def _ev(pais, titulo, impacto="High", hora="21:30"):
    return {"country": pais, "title": titulo, "impact": impacto,
            "date": f"{HOY}T{hora}:00-04:00", "forecast": "0.9%", "previous": "-0.1%"}


# ── El caso real ─────────────────────────────────────────────────────────────

def test_el_IPC_australiano_NO_entra_en_el_briefing_de_wall_street():
    """EL test. Es el evento exacto que abrió el briefing del 25/08."""
    assert _filtrar([_ev("AUD", "CPI m/m")]) == [], (
        "el IPC de Australia sigue entrando: es el dato que el briefing "
        "presentó como el IPC de Estados Unidos")


def test_un_dato_de_estados_unidos_entra_aunque_sea_de_impacto_medio():
    r = _filtrar([_ev("USD", "CB Consumer Confidence", impacto="Medium", hora="10:00")])
    assert len(r) == 1 and r[0]["pais"] == "USD"


def test_una_decision_del_BCE_si_entra():
    """Un banco central de la lista mueve los futuros de Wall Street antes de
    la apertura; un IPC australiano a las 21:30 ET no."""
    r = _filtrar([_ev("EUR", "Main Refinancing Rate", hora="08:15")])
    assert len(r) == 1 and r[0]["pais"] == "EUR"


def test_un_dato_de_fuera_de_impacto_MEDIO_no_entra():
    assert _filtrar([_ev("EUR", "Italian Retail Sales", impacto="Medium")]) == []


# ── La hora ──────────────────────────────────────────────────────────────────

def test_la_hora_se_parsea_bien_y_en_horario_de_nueva_york():
    """`date[-8:-3]` devolvía "0-04:" sobre "2026-08-25T21:30:00-04:00". El
    modelo, viendo eso rotulado como ET, escribió 08:30 ET de memoria."""
    r = _filtrar([_ev("USD", "CPI m/m", hora="08:30")])
    assert r[0]["time"] == "08:30"
    viejo = f"{HOY}T08:30:00-04:00"[-8:-3]
    assert viejo != "08:30", "el parseo antiguo daba otra cosa; este test lo documenta"


def test_una_fecha_ilegible_da_N_D_en_vez_de_basura():
    ev = _ev("USD", "CPI m/m")
    ev["date"] = HOY + "T-invalido"
    assert _filtrar([ev])[0]["time"] == "N/D"


def test_la_hora_se_convierte_a_nueva_york_no_se_copia_tal_cual():
    """Si el feed cambiara de huso, copiar los caracteres daría una hora falsa
    rotulada «ET»."""
    ev = _ev("USD", "FOMC Statement")
    ev["date"] = f"{HOY}T18:00:00+00:00"      # 18:00 UTC = 14:00 en Nueva York
    assert _filtrar([ev])[0]["time"] == "14:00"


# ── Lo que ve el modelo ──────────────────────────────────────────────────────

def test_el_calendario_del_script_usa_estas_reglas_y_no_otras():
    """Que las funciones esten bien no sirve de nada si get_market_data() no
    las llama: la logica vivia inline y por eso los sabotajes no caian."""
    import inspect
    lineas = inspect.getsource(D.get_market_data).splitlines()
    fuente = chr(10).join(l.split("#")[0] for l in lineas)
    assert "evento_relevante(" in fuente, "el calendario no usa el filtro de relevancia"
    assert "hora_et(" in fuente, "el calendario no usa el parseo de hora correcto"
    assert "[-8:-3]" not in fuente, "sigue troceando la fecha por posicion de caracteres"


def test_la_tabla_del_prompt_lleva_columna_de_pais():
    """Que el filtro sea correcto no basta: lo que entra tiene que llegar
    etiquetado, o el modelo vuelve a suponer que todo es de EE.UU."""
    import inspect
    fuente = inspect.getsource(D.build_prompt)
    assert "País" in fuente, "la tabla del calendario no dice de qué país es cada dato"
    assert "ev.get('pais'" in fuente or 'ev.get("pais"' in fuente


# ── La amplitud propia ───────────────────────────────────────────────────────

def test_la_amplitud_se_pide_CON_token_y_el_fallo_se_dice():
    """El briefing del 25/08 escribio «la falta de datos de amplitud propia nos
    obliga a confiar en la rotacion sectorial»: le estaba diciendo al lector
    que la herramienta no tiene un dato que calcula cada noche.

    No lo invento el modelo -- le llego vacio. La lectura del Gist del Scanner
    iba SIN autenticar, y desde un runner de GitHub Actions la API publica esta
    limitada a 60 peticiones/hora por IP COMPARTIDA: un 403 es facil. Y el
    `return {}` era mudo, asi que nadie se enteraba."""
    import inspect
    fuente = inspect.getsource(D.get_rsu_breadth_signals)
    assert "GIST_TOKEN" in fuente and "Authorization" in fuente, (
        "la amplitud se sigue pidiendo sin token: un 403 por limite de la API "
        "deja el briefing sin amplitud y el modelo lo cuenta como una carencia "
        "de la herramienta")
    lineas = fuente.splitlines()
    for i, l in enumerate(lineas):
        if "return {}" in l and "status_code" in " ".join(lineas[max(0, i - 3):i]):
            contexto = " ".join(lineas[max(0, i - 3):i + 1])
            assert "print" in contexto, "el fallo de la amplitud se sigue tragando en silencio"
            break


# ── Los numeros de amplitud, con su escala ───────────────────────────────────
#
# EL CASO, 26/08/2026. El briefing escribio: «El Oscilador McClellan RSU esta
# en -26,7, lo que indica que la subida del indice no esta respaldada por una
# participacion amplia», y lo uso como pilar de su sesgo bajista.
#
# Los tres numeros eran EXACTOS (verificados recalculandolos desde precios:
# 59,1% frente al 59,2% del Gist, McClellan -26,69 frente a -26,70). El
# problema era otro:
#
# 1. -26,7 es NEUTRO segun la propia terminal (market_service: alcista >70,
#    bajista <-70). Al modelo le llegaba el numero DESNUDO, sin escala, asi que
#    se invento la lectura -- y le salio la contraria a la que enseña la pagina
#    de Market. Dos partes del mismo producto diciendo lo opuesto del mismo
#    numero el mismo dia.
#
# 2. Su conclusion era CORRECTA pero la prueba no: esa sesion la amplitud del
#    universo combinado fue POSITIVA (+141 neto). La prueba de verdad la tenia
#    al lado y no la recibia -- del S&P 500 solo subieron 206 de 496 (41,5%)
#    mientras el indice ganaba un 0,32%. El Gist ya separa `breadth_sp500` y
#    `breadth_russell`; simplemente no viajaban al prompt.

def _gist_falso(mcclellan_neto):
    """Un Gist del Scanner minimo: 40+ sesiones para que salga McClellan."""
    import json
    from unittest.mock import MagicMock
    hist = [{"date": f"2026-06-{d:02d}", "advances": 1000 + mcclellan_neto,
             "declines": 1000, "pct_above_sma50": 59.2, "new_highs": 89,
             "new_lows": 15} for d in range(1, 29)] * 2
    contenido = {
        "stocks": {"AAPL": {"above_sma50": True}},
        "breadth_history": hist,
        "breadth_sp500": [{"date": "2026-08-25", "advances": 206, "declines": 290,
                           "pct_above_sma50": 59.4}],
        "breadth_russell": [{"date": "2026-08-25", "advances": 1059, "declines": 834}],
        "universe_size": 498,
    }
    r = MagicMock(status_code=200)
    r.json.return_value = {"files": {D.SCANNER_GIST_FILE: {"content": json.dumps(contenido)}}}
    return r


def _amplitud(neto):
    from unittest.mock import patch
    with patch.object(D.requests, "get", return_value=_gist_falso(neto)):
        return D.get_rsu_breadth_signals()


def test_el_mcclellan_viaja_con_su_banda_no_desnudo():
    """EL test. -26,7 es NEUTRO para la terminal, y el modelo lo leyo como
    bajista porque nadie le dijo la escala."""
    b = _amplitud(0)          # neto 0 -> McClellan ~0, zona neutra
    assert b["mcclellan_estado"] == "NEUTRO", b.get("mcclellan")


def test_las_bandas_son_las_MISMAS_que_usa_la_terminal():
    """Si aqui se usara otro umbral, la pagina de Market y el briefing volverian
    a decir cosas distintas del mismo numero."""
    import re
    ruta = os.path.join(os.path.dirname(__file__), "..", "services", "market_service.py")
    with open(ruta, encoding="utf-8") as fh:
        fuente = fh.read()
    assert 'mcclellan > 70' in fuente and 'mcclellan < -70' in fuente
    import inspect
    mio = inspect.getsource(D.get_rsu_breadth_signals)
    assert "> 70" in mio and "< -70" in mio, (
        "el briefing usa unos umbrales de McClellan distintos a los de la terminal")


def test_los_avances_del_S_and_P_llegan_por_separado():
    """La prueba que el briefing necesitaba y no recibia."""
    b = _amplitud(0)
    assert b["sp500_advances"] == 206 and b["sp500_declines"] == 290
    assert b["sp500_pct_al_alza"] == 41.5, (
        "sin esto el modelo solo ve el agregado de 2.389 valores y no puede "
        "decir que el S&P subio con el 41% de sus componentes en rojo")


def test_tambien_llegan_los_avances_del_universo_completo():
    b = _amplitud(0)
    assert b["advances"] is not None and b["declines"] is not None


def test_el_prompt_pinta_la_banda_y_los_avances():
    """Que la funcion los devuelva no sirve si no llegan al texto."""
    import inspect
    fuente = inspect.getsource(D.build_prompt)
    assert "mcclellan_estado" in fuente, "la banda no se pinta en el prompt"
    assert "sp500_advances" in fuente, "los avances del S&P no se pintan en el prompt"
