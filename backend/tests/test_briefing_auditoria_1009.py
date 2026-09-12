"""
La auditoría del briefing del 10/09: cifras de otro día y datos que no habían salido.

EL CASO. Contrastado con Yahoo y con el registro de las ejecuciones, el
briefing del jueves 10/09 —escrito a las 07:54 ET— mezclaba tres días:

    «el VIX sube un 1,03%»                      el miércoles subió +4,71%
    «el dólar sube un 0,14%… refugio en el dólar» el miércoles BAJÓ un 0,07%
    «el WTI gana un 1,46%» (motor de Energía)    el miércoles subió +3,25%
    «solo el 29,2% de los componentes avanzaron» era el MARTES; el miércoles, 19,7%

Y contaba como publicados datos que salían después: el BCE a las 08:15, el PPI
y los subsidios a las 08:30. La segunda lectura, que no pasaba por ningún
verificador, escribió «el Core PPI subió 0,3%… señal de inflación subyacente
persistente» con la cifra exacta del consenso.

LO QUE ATA ESTE FICHERO, por hallazgo:

  #55  Cada fila del bloque de mercado va bajo la fecha de SU barra, y lo que
       ya cotiza hoy trae también lo que hizo EN la sesión. Se ejecuta
       `get_market_data()` entero contra un Yahoo simulado con las dos fechas
       reales de ese día.
  #56  La columna «5D» son cinco sesiones, no cuatro.
  #57  El calendario dice encima de la tabla que nada ha salido, y el
       verificador caza la previsión contada como hecho — con las frases
       REALES publicadas ese día.
  #58  La segunda lectura pasa por el verificador y, si insiste, no se publica.
  #59  «Supera el consenso» ya no salta cuando el consenso sí está en la tabla.

EL PRESUPUESTO. El prompt de ese día estimó 6.415 fichas contra un techo de
6.450: 35 de margen. La primera versión de estas etiquetas sumaba +53 y no
habría cabido; recortadas, el cambio ahorra 60 (medido con las mismas entradas
reales, versión anterior contra la nueva). Los dos últimos tests impiden que
las etiquetas vuelvan a crecer sin que nadie lo decida.

Uso:
    cd backend
    python -m pytest tests/test_briefing_auditoria_1009.py -v
"""
import ast
import inspect
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


# ── Un Yahoo simulado con las fechas reales del 10/09 ────────────────────────
#
# Lo que solo cotiza en sesion llega hasta el miercoles 09/09; lo que cotiza de
# noche ya trae el jueves 10/09. El 07/09 fue festivo (Labor Day).
SESIONES = ["2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01", "2026-09-02",
            "2026-09-03", "2026-09-04", "2026-09-08", "2026-09-09"]
DE_NOCHE = {"^VIX", "DX-Y.NYB", "GC=F", "CL=F", "BTC-USD", "ES=F", "NQ=F",
            "EURUSD=X", "USDJPY=X"}
# Cierres reales del martes, miercoles y jueves (en curso) medidos en Yahoo.
REALES = {"^VIX": (15.72, 16.46, 16.63), "DX-Y.NYB": (98.84, 98.77, 98.91),
          "CL=F": (93.03, 96.05, 97.45), "GC=F": (4393.9, 4416.0, 4427.2),
          "^GSPC": (7673.52, 7636.36, None)}


class _TickerFalso:
    def __init__(self, simbolo):
        self.s = simbolo

    def history(self, period="5d", interval="1d", **_):
        fechas = list(SESIONES) + (["2026-09-10"] if self.s in DE_NOCHE else [])
        n = int(period[:-1]) if period.endswith("d") else len(fechas)
        # yfinance con period="Nd" devuelve las N ULTIMAS barras: honrarlo es
        # lo que permite ver que "5d" daba cinco barras y un 5D de cuatro sesiones.
        fechas = fechas[-n:]
        # Serie creciente y distinta por posicion: cualquier ventana mal
        # contada da un porcentaje distinto del correcto.
        # `sum(map(ord))` y no `hash()`: el hash de un str cambia en cada
        # proceso, y un test con datos distintos cada vez es un test flojo.
        paso = 1 + sum(map(ord, self.s)) % 7
        cierres = [100.0 + i * paso for i in range(len(fechas))]
        if self.s in REALES:
            martes, miercoles, jueves = REALES[self.s]
            i = fechas.index("2026-09-08") if "2026-09-08" in fechas else None
            if i is not None:
                cierres[i] = martes
                cierres[i + 1] = miercoles
                if jueves is not None and i + 2 < len(fechas):
                    cierres[i + 2] = jueves
        idx = pd.DatetimeIndex(pd.to_datetime(fechas)).tz_localize("America/New_York")
        return pd.DataFrame({"Open": cierres, "High": cierres, "Low": cierres,
                             "Close": cierres, "Volume": [1e6] * len(fechas)}, index=idx)


@pytest.fixture
def datos(monkeypatch):
    monkeypatch.setattr(D.yf, "Ticker", _TickerFalso)

    def _sin_red(*a, **k):
        raise ConnectionError("sin red en los tests")
    monkeypatch.setattr(D.requests, "get", _sin_red)
    return D.get_market_data()


# ── #55: cada fila, bajo la fecha de su barra ────────────────────────────────

def test_la_sesion_es_la_del_miercoles_y_el_VIX_va_por_delante(datos):
    """EL test del caso. Es lo que `barras` registró aquel día."""
    assert datos["sesion"]["fecha"] == "2026-09-09"
    assert datos["barras"]["SPX"] == ("2026-09-08", "2026-09-09")
    assert datos["barras"]["VIX"] == ("2026-09-09", "2026-09-10")


def test_lo_que_va_por_delante_trae_lo_que_hizo_EN_la_sesion(datos):
    """Sin esto el modelo no tiene forma de contar que el VIX subió un 4,71% el
    miércoles: solo ve el +1,03% de la noche del jueves."""
    vix, dxy, wti = datos["VIX"]["en_sesion"], datos["DXY"]["en_sesion"], datos["WTI"]["en_sesion"]
    assert vix["chg_pct"] == pytest.approx(4.71, abs=0.01)
    assert dxy["chg_pct"] == pytest.approx(-0.07, abs=0.01), "el dólar BAJÓ el miércoles"
    assert wti["chg_pct"] == pytest.approx(3.25, abs=0.01)
    # Y su variación "de hoy" sigue siendo la de la noche: no se ha pisado.
    assert datos["VIX"]["chg_pct"] == pytest.approx(1.03, abs=0.01)


def test_lo_que_cierra_con_la_sesion_NO_lleva_cifra_de_sesion(datos):
    """Para el S&P la variación de la sesión YA es su `chg_pct`. Duplicarla
    serían fichas tiradas en un prompt que no cabe."""
    assert "en_sesion" not in datos["SPX"]


def test_el_prompt_pone_cada_fila_bajo_su_dia(datos):
    p = D.build_prompt(datos, [], [], [], {}, [], [])
    cierre, hoy = p.index("CIERRE DE ESA SESION"), p.index("EN CURSO HOY 2026-09-10 (jueves)")
    assert cierre < p.index("- S&P 500:") < hoy
    for fila in ("- VIX:", "- Dólar Index (DXY):", "- Oro:", "- Petróleo WTI:"):
        assert p.index(fila) > hoy, f"{fila} sigue bajo el cierre"
    # El formato cambió el 12/09 (Newsfeed #63): el cierre va primero.
    assert "- VIX: CIERRE 16.46 (▲4.71%) · ahora 16.63" in p
    assert "- Dólar Index (DXY): CIERRE 98.77 (▼0.07%) · ahora 98.91" in p


def test_la_variacion_de_la_sesion_no_se_inventa_si_falta_la_barra():
    """Sin la barra de esa sesión, None. Nunca la de otro día en su lugar."""
    assert D.variacion_en_la_sesion({"2026-09-08": 1.0, "2026-09-10": 2.0}, "2026-09-09") is None
    assert D.variacion_en_la_sesion({"2026-09-09": 1.0}, "2026-09-09") is None
    r = D.variacion_en_la_sesion({"2026-09-08": 100.0, "2026-09-09": 110.0}, "2026-09-09")
    assert r["chg_pct"] == 10.0 and r["desde"] == "2026-09-08"


def test_un_ticker_ATRASADO_va_aparte_y_con_su_fecha():
    """Si Yahoo no trae la barra del miércoles del Russell, el Russell no puede
    salir bajo «CIERRE DE ESA SESION» con la variación del martes."""
    barras = {"SPX": ("2026-09-08", "2026-09-09"), "RUT": ("2026-09-04", "2026-09-08"),
              "VIX": ("2026-09-09", "2026-09-10")}
    g = D.agrupar_por_sesion(barras, "2026-09-09", ["SPX", "RUT", "VIX"])
    assert [t for _, t, _ in g] == ["cierre", "hoy", "atrasado"], "orden: sesión, hoy, atrás"
    assert dict((t, k) for _, t, k in g)["atrasado"] == ["RUT"]
    md = {"date": "2026-09-10", "time": "07:54", "barras": barras,
          "sesion": {"fecha": "2026-09-09", "en_curso": False, "hora_et": "07:54"},
          "SPX": {"price": 1, "chg_pct": 0}, "RUT": {"price": 1, "chg_pct": 0},
          "VIX": {"price": 1, "chg_pct": 0}}
    p = D.build_prompt(md, [], [], [], {}, [], [])
    assert p.index("SIN DATO DE ESA SESION, ultimo del 2026-09-08 (martes)") < p.index("- Russell 2000:")


def test_una_variacion_que_ABARCA_dos_sesiones_se_marca():
    """El mecanismo que mejor explica Newsfeed #39: sin la barra del 28/08, la
    penúltima es la del 27 y la «variación del día» son dos sesiones."""
    assert D.salta_mas_de_una_sesion({"SPX": ("2026-08-27", "2026-08-31")}, "SPX")
    assert not D.salta_mas_de_una_sesion({"SPX": ("2026-08-28", "2026-08-31")}, "SPX")
    # El festivo no cuenta como hueco: del viernes 04 al martes 08 es UNA sesión.
    assert not D.salta_mas_de_una_sesion({"SPX": ("2026-09-04", "2026-09-08")}, "SPX")


def test_el_bitcoin_NO_se_marca_por_el_fin_de_semana():
    """Cotiza el sábado: su día anterior no es el de la bolsa, y marcarlo cada
    lunes sería ruido en el prompt."""
    md = {"date": "2026-08-31", "time": "07:54",
          "barras": {"BTC": ("2026-08-27", "2026-08-31")},
          "sesion": {"fecha": "2026-08-31", "en_curso": False, "hora_et": "07:54"},
          "BTC": {"price": 1, "chg_pct": 0}}
    assert "abarca MAS de una sesion" not in D.build_prompt(md, [], [], [], {}, [], [])


def test_sin_barras_no_se_inventa_ninguna_fecha():
    """Una descarga sin `barras` no puede producir un bloque que afirme de qué
    día es cada fila."""
    md = {"date": "2026-09-10", "time": "07:54",
          "sesion": {"fecha": "2026-09-09", "en_curso": False, "hora_et": "07:54"},
          "SPX": {"price": 1, "chg_pct": 0}}
    p = D.build_prompt(md, [], [], [], {}, [], [])
    assert "EN CURSO HOY" not in p and "SIN DATO DE ESA SESION" not in p


# ── #56: el 5D son cinco sesiones ────────────────────────────────────────────

def test_el_5D_de_sectores_son_CINCO_sesiones(datos):
    """Con `period="5d"` llegaban cinco barras y `iloc[0]` quedaba a cuatro
    sesiones: 11 de 11 sectores cuadraban con 4 el 10/09, 0 con 5."""
    serie = _TickerFalso("XLK").history(period="30d")["Close"]
    esperado = round((serie.iloc[-1] / serie.iloc[-6] - 1) * 100, 2)
    assert datos["sectors"]["XLK"]["chg_5d"] == esperado


def test_sin_cinco_sesiones_se_dice_nd_y_no_cero():
    """`or 0` pintaba «+0,00%»: un «no sé» convertido en «no se ha movido»."""
    md = {"date": "2026-09-10", "time": "07:54", "calendar": [],
          "sesion": {"fecha": "2026-09-09", "en_curso": False, "hora_et": "07:54"},
          "sectors": {"XLK": {"name": "Tecnología", "chg_1d": 0.5, "chg_5d": None}}}
    p = D.build_prompt(md, [], [], [], {}, [], [])
    assert "| XLK | Tecnología | +0.50% | n/d |" in p


# ── #57: lo que no ha salido ─────────────────────────────────────────────────

EVENTOS = [
    {"time": "08:15", "pais": "EUR", "event": "Main Refinancing Rate", "forecast": "2.65%",
     "previous": "2.40%", "impact": "High", "actual": ""},
    {"time": "08:30", "pais": "USD", "event": "Core PPI m/m", "forecast": "0.3%",
     "previous": "0.2%", "impact": "High", "actual": ""},
    {"time": "08:30", "pais": "USD", "event": "PPI m/m", "forecast": "0.4%",
     "previous": "0.0%", "impact": "High", "actual": ""},
    {"time": "08:30", "pais": "USD", "event": "Unemployment Claims", "forecast": "205K",
     "previous": "206K", "impact": "Medium", "actual": ""},
]

# Las frases PUBLICADAS el 10/09, tal cual.
SEGUNDA_REAL = ("Hoy el Banco Central Europeo elevó su tasa de referencia a 2,65 % (previa "
                "2,40 %), lo que refuerza el dólar, ya en 98,91 (+0,14 %). En EE. UU., el Core "
                "PPI subió 0,3 % frente al 0,2 % previo y el PPI general 0,4 % frente a 0,0 %, "
                "señal de inflación subyacente persistente. Las solicitudes de subsidio por "
                "desempleo cayeron a 205 000 frente a 206 000, una ligera mejora.")
PRIMERA_REAL = ("A las 08:30 ET, el IPC de productores (PPI) core tiene un consenso del 0,3% "
                "frente al 0,2% previo. Si sale por encima, reforzará la tesis inflacionista. "
                "Además, el BCE sube su tipo principal al 2,65% (desde el 2,40%), lo que "
                "podría fortalecer el euro temporalmente. Mi lectura es que la presión bajista "
                "se intensificará si el PPI de hoy supera el consenso.")


def _md_calendario(eventos):
    return {"date": "2026-09-10", "time": "07:54", "calendar": eventos,
            "sesion": {"fecha": "2026-09-09", "en_curso": False, "hora_et": "07:54"}}


def test_el_prompt_avisa_de_que_NADA_ha_salido():
    p = D.build_prompt(_md_calendario(EVENTOS), [], [], [], {}, [], [])
    assert "A las 07:54 ET NADA de esta tabla ha salido" in p
    assert "nunca «subió/cayó/elevó»" in p


def test_con_algo_ya_publicado_el_aviso_habla_solo_de_lo_que_falta():
    ya = [dict(EVENTOS[0], actual="2.65%")] + EVENTOS[1:]
    p = D.build_prompt(_md_calendario(ya), [], [], [], {}, [], [])
    assert "lo marcado «aún no» no ha salido" in p
    assert "NADA de esta tabla" not in p


def test_sin_eventos_pendientes_no_hay_aviso():
    publicados = [dict(e, actual=e["forecast"]) for e in EVENTOS]
    p = D.build_prompt(_md_calendario(publicados), [], [], [], {}, [], [])
    assert "ha salido" not in p


def test_el_verificador_caza_las_CUATRO_frases_reales_de_la_segunda_lectura():
    """EL test del verificador, con el texto publicado. Antes: nada."""
    r = D.revisar_briefing(SEGUNDA_REAL, "", "", EVENTOS)
    eventos_cazados = {x.split("«")[1].split("»")[0] for x in r["hechos"]}
    assert eventos_cazados == {"Main Refinancing Rate", "Core PPI m/m", "PPI m/m",
                               "Unemployment Claims"}, r["hechos"]


def test_y_el_BCE_dado_por_hecho_en_la_primera():
    r = D.revisar_briefing(PRIMERA_REAL, "", "", EVENTOS)
    assert len(r["hechos"]) == 1 and "Main Refinancing Rate" in r["hechos"][0]


def test_NO_marca_el_consenso_dicho_como_consenso():
    """«tiene un consenso del 0,3%… si sale por encima» es exactamente como hay
    que escribirlo. Si esto saltara, la regla castigaría lo correcto."""
    r = D.revisar_briefing(PRIMERA_REAL.split("Además")[0], "", "", EVENTOS)
    assert r["hechos"] == []


def test_NO_marca_un_dato_que_YA_ha_salido():
    """Después de las 08:30, «el PPI subió un 0,3%» es un hecho y hay que poder
    decirlo."""
    publicados = [dict(e, actual=e["forecast"]) for e in EVENTOS]
    assert D.revisar_briefing(SEGUNDA_REAL, "", "", publicados)["hechos"] == []


def test_NO_marca_la_misma_cifra_hablando_de_OTRA_cosa():
    """El día que el PPI esperado es 0,3, «el Nasdaq cayó un 0,3%» es otra cosa.
    Sin el tema del evento, la regla solo se fiaría del número."""
    r = D.revisar_briefing("El Nasdaq cayó un 0,3% y el Russell un 0,4%.", "", "", EVENTOS)
    assert r["hechos"] == []


def test_lee_las_cifras_en_miles_escritas_de_cualquier_forma():
    """«205K» en el calendario; «205.000», «205 000» o «205K» en el texto."""
    for escrito in ("205.000", "205 000", "205K"):
        r = D.revisar_briefing(f"Las solicitudes de subsidio cayeron a {escrito}.", "", "", EVENTOS)
        assert r["hechos"], escrito


# ── #59: el consenso que sí estaba ───────────────────────────────────────────

def test_SUPERA_EL_CONSENSO_ya_no_salta_si_el_evento_esta_en_el_calendario():
    """Lo que saltó de verdad el 10/09: una frase sin cifra que nombra el PPI,
    cuyo consenso SÍ estaba en la tabla. Costó un reintento contra Groq."""
    r = D.revisar_briefing("Se intensificará si el PPI de hoy supera el consenso.", "", "", EVENTOS)
    assert not any("CONSENSO INVENTADO" in x for x in r["otros"])


def test_el_consenso_sin_respaldo_SIGUE_saltando():
    """Lo que la regla vino a cazar el 08/09 no se puede perder: unas nóminas de
    FRED, sin consenso en ninguna parte, «mejores de lo esperado»."""
    r = D.revisar_briefing("Las nóminas salieron mejores de lo esperado.", "", "", EVENTOS)
    assert any("CONSENSO INVENTADO" in x for x in r["otros"])
    # Y sin calendario, como hasta ahora.
    r = D.revisar_briefing("El PPI supera el consenso.", "", "")
    assert any("CONSENSO INVENTADO" in x for x in r["otros"])


# ── #58: la segunda lectura pasa por el verificador ──────────────────────────

LARGO = " Relleno de contexto para que el texto supere las cincuenta palabras." * 8


def _segunda(monkeypatch, textos):
    """Ejecuta generar_segunda_lectura con un modelo falso que devuelve `textos`
    en orden, y cuenta cuántas veces se le llamó."""
    llamadas = []

    def falso(prompt, modelo=None, **_):
        llamadas.append(prompt)
        return textos[min(len(llamadas), len(textos)) - 1] + "\n\nSESGO: BAJISTA", {}
    monkeypatch.setattr(D, "generate_briefing", falso)
    r = D.generar_segunda_lectura("PROMPT", modelo="groq/compound", titulares="", eventos=EVENTOS)
    return r, llamadas


def test_si_insiste_en_el_dato_inventado_NO_se_publica(monkeypatch):
    """EL test del #58. Opcional: mejor ausente que equivocada."""
    r, llamadas = _segunda(monkeypatch, [SEGUNDA_REAL + LARGO, SEGUNDA_REAL + LARGO])
    assert r is None
    assert len(llamadas) == 2, "tiene que haber UN reintento antes de descartarla"
    assert "AVISO" in llamadas[1] and "Core PPI" in llamadas[1], (
        "el reintento no le dice al modelo qué ha roto")


def test_si_el_reintento_lo_corrige_se_publica_el_reintento(monkeypatch):
    bueno = ("El consenso espera que el PPI subyacente suba un 0,3%; si sale por encima, "
             "reforzará la presión sobre los bonos." + LARGO)
    r, _ = _segunda(monkeypatch, [SEGUNDA_REAL + LARGO, bueno])
    assert r is not None and "El consenso espera" in r["text"]


def test_una_segunda_lectura_limpia_no_gasta_reintento(monkeypatch):
    bueno = "El consenso espera que el PPI suba un 0,3%." + LARGO
    r, llamadas = _segunda(monkeypatch, [bueno])
    assert r is not None and len(llamadas) == 1
    assert "revision" not in r


def test_main_le_pasa_el_calendario_a_TODAS_las_revisiones():
    """Sin `eventos`, las reglas #57 y #59 no pueden funcionar y el verificador
    vuelve a ser el del 09/09 sin que nada falle. Se miran las LLAMADAS en el
    árbol del código de main(), no el texto: un comentario que las mencionara
    no cuenta."""
    arbol = ast.parse(inspect.getsource(D.main))
    llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call)
                and getattr(n.func, "id", None) in ("revisar_briefing", "generar_segunda_lectura")]
    assert len(llamadas) >= 3, "han desaparecido llamadas al verificador"
    for c in llamadas:
        nombres = [k.arg for k in c.keywords]
        tiene = "eventos" in nombres or (c.func.id == "revisar_briefing" and len(c.args) >= 4)
        assert tiene, f"{c.func.id} se llama sin el calendario (línea {c.lineno} de main)"


# ── El presupuesto de fichas ─────────────────────────────────────────────────

def test_el_aviso_del_calendario_no_vuelve_a_crecer():
    """Su primera versión costaba 82 fichas; con el prompt a 35 del techo, no
    cabía. Si alguien lo alarga, que sea una decisión, no un descuido."""
    p = D.build_prompt(_md_calendario(EVENTOS), [], [], [], {}, [], [])
    linea = next(l for l in p.splitlines() if "ha salido" in l)
    assert D.estimar_tokens(linea) <= 40, D.estimar_tokens(linea)


def test_el_encabezado_de_HOY_no_vuelve_a_crecer(datos):
    p = D.build_prompt(datos, [], [], [], {}, [], [])
    linea = next(l for l in p.splitlines() if l.startswith("EN CURSO HOY"))
    assert D.estimar_tokens(linea) <= 45, D.estimar_tokens(linea)
