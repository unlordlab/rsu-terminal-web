"""
La auditoría del briefing del 11/09: la amplitud de otro día, el petróleo con el
signo cambiado y el reintento que nunca podía salir.

EL CASO. El briefing del viernes 11/09 —escrito a las 07:53 ET— narraba la
sesión del JUEVES 10 con la amplitud del MIÉRCOLES 9, porque el escaneo nocturno
va una sesión por detrás (Scanner #25). Lo publicado y lo real:

    «solo el 19,9% de los componentes avanzaron, 99 contra 399»  el jueves fue
                                                      165/329, el 33,4%
    «el ABI marca un 59,0%… capitulación… el pánico es estructural»  el jueves,
                                                      32,4% (alto, no capitulación)
    «el WTI cerró ayer en 99,40 $ (-3,01%)»           cerró en 102,48, un +6,69%
    «+162.000, una mejora respecto al mes anterior (+141.000)»  el mes anterior
                                                      fueron +21k; 141 era la diferencia

Y el verificador SÍ vio uno de los fallos (la previsión del IPC contada como
hecho) y pidió el reintento, que murió con un 429 de límite de ENTRADA por
minuto: con el prompt a ~6,2k fichas y un techo de 7.000 ITPM, dos llamadas en
el mismo minuto no caben nunca.

LO QUE ATA ESTE FICHERO, por hallazgo:

  #61  El verificador caza las cifras de amplitud citadas sin decir de qué día
       son — con los párrafos REALES de las dos lecturas de ese día.
  #62  El reintento espera a que pase la ventana del minuto antes de llamar.
  #63  En las filas con otro reloj (VIX, dólar, oro, WTI) el CIERRE va primero
       y con su nombre; el dato de ahora, detrás.
  #64  (en tests/test_briefing_direccion_macro.py) la fila de empleo ya no trae
       la diferencia entre meses como número suelto.

Uso:
    cd backend
    python -m pytest tests/test_briefing_auditoria_1109.py -v
"""
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


# ── La amplitud REAL de aquel día, tal como llegó al prompt ──────────────────
#
# Son las cifras del miércoles 9 (las que el Gist del Scanner tenía esa mañana),
# con la sesión que el briefing narraba: el jueves 10.
AMPLITUD = {"fecha": "2026-09-09", "sesion": "2026-09-10",
            "advances": 490, "declines": 1904,
            "sp500_advances": 99, "sp500_declines": 399, "sp500_pct_al_alza": 19.9,
            "pct_above_sma50": 38.2, "mcclellan": -123.1, "abi": 59.0,
            "nh_nl": -67, "new_highs": 31, "new_lows": 98}

# Los párrafos publicados, copiados del Gist del briefing de ese día.
PRIMERA_REAL = (
    "En la sesión del jueves 10 de septiembre, el S&P 500 cerró en 7.591,70, cayendo un "
    "0,58%, pero lo grave está en la amplitud. Solo el 19,9% de los componentes del índice "
    "avanzaron, con 99 avances frente a 399 descensos. El Oscilador McClellan RSU se sitúa "
    "en -123,1, una señal claramente bajista.")
SEGUNDA_REAL = (
    "La amplitud del mercado sigue en zona de debilidad: el oscilador McClellan RSU marcó "
    "–123,1 (por debajo del umbral bajista de –70), el ABI se ubicó en 59,0 % (capitulación "
    "a la baja) y el diferencial New Highs-New Lows quedó en –67 (31 máximos frente a 98 "
    "mínimos).")


# ── #61: la amplitud, citada por el día que es ───────────────────────────────

@pytest.mark.parametrize("texto", [PRIMERA_REAL, SEGUNDA_REAL],
                         ids=["primera lectura", "segunda lectura"])
def test_las_cifras_de_otro_dia_sin_su_dia_se_cazan(texto):
    """EL test del caso: los dos textos reales, tal como se publicaron."""
    fallos = D.amplitud_de_otro_dia(texto, AMPLITUD)
    assert len(fallos) == 1, f"no lo ve: {fallos}"
    assert "2026-09-09 (miercoles)" in fallos[0] and "2026-09-10 (jueves)" in fallos[0], (
        f"el aviso no dice de qué día son ni de cuál deberían: «{fallos[0]}»")


@pytest.mark.parametrize("texto", [
    "El miercoles solo avanzaron 99 valores frente a 399, con el McClellan en -123,1.",
    "La amplitud del 2026-09-09 fue de 99 avances contra 399 descensos.",
    "El 9 de septiembre solo avanzó el 19,9% del índice: 99 contra 399.",
    "En la sesion anterior avanzaron 99 valores frente a 399.",
    "Miro la amplitud del miercoles. Solo avanzó el 19,9% del S&P, 99 contra 399.",
])
def test_si_dice_de_que_dia_son_NO_salta(texto):
    """La regla no prohíbe usar la amplitud de ayer: prohíbe callarse el día.
    Vale nombrarlo de cualquiera de las formas en que lo escribe una persona,
    y vale decirlo en la frase anterior."""
    assert D.amplitud_de_otro_dia(texto, AMPLITUD) == []


def test_si_la_amplitud_es_de_la_misma_sesion_no_mira_nada():
    """Cuando el escaneo va al día —que es como debería ir siempre— exigir la
    fecha sería ruido: las cifras SON las de la sesión que se cuenta."""
    al_dia = {**AMPLITUD, "fecha": "2026-09-10"}
    assert D.amplitud_de_otro_dia(PRIMERA_REAL, al_dia) == []


def test_con_dos_sesiones_por_medio_NO_vale_decir_la_sesion_anterior():
    """«La sesión anterior» es exacto si va un día por detrás; con el martes
    contra el jueves es tan falso como no decir nada."""
    atrasada = {**AMPLITUD, "fecha": "2026-09-08"}
    assert D.amplitud_de_otro_dia("En la sesion anterior avanzaron 99 frente a 399.",
                                  atrasada) != []
    # Y nombrando el día sí vale, también dos sesiones atrás.
    assert D.amplitud_de_otro_dia("El martes avanzaron 99 valores frente a 399.",
                                  atrasada) == []


def test_el_viernes_contra_el_lunes_si_es_la_sesion_anterior():
    """El puente del fin de semana no son dos sesiones, es una."""
    finde = {"fecha": "2026-09-04", "sesion": "2026-09-07", "sp500_advances": 399,
             "mcclellan": -123.1}
    assert D.amplitud_de_otro_dia("En la sesion anterior el McClellan marcó -123,1.",
                                  finde) == []


def test_sin_amplitud_o_sin_fechas_no_inventa_fallos():
    """Si el Scanner no ha dado datos, no hay nada que comprobar."""
    assert D.amplitud_de_otro_dia(PRIMERA_REAL, {}) == []
    assert D.amplitud_de_otro_dia(PRIMERA_REAL, {"fecha": "2026-09-09"}) == []
    assert D.amplitud_de_otro_dia(PRIMERA_REAL, {"fecha": None, "sesion": "2026-09-10"}) == []


def test_una_cifra_pequeña_suelta_no_basta_para_acusar():
    """31 máximos y 98 mínimos son números que salen en cualquier frase. Solo
    acusan las cifras de tres dígitos o con decimales; si no, la regla daría
    avisos falsos a diario y acabaría ignorándose."""
    assert D.amplitud_de_otro_dia("Los 31 valores del sector suman un 98 por ciento.",
                                  AMPLITUD) == []


def test_el_verificador_lo_devuelve_en_su_propia_casilla():
    """Va aparte de «otros» porque pesa distinto: como los datos inventados,
    descarta la segunda lectura en vez de publicarse con una nota."""
    r = D.revisar_briefing(PRIMERA_REAL, "", "", [], AMPLITUD)
    assert len(r["amplitud"]) == 1 and r["otros"] == []
    assert any("AMPLITUD DE OTRO DIA" in x for x in D.fallos_de(r))


def test_sin_amplitud_el_verificador_se_comporta_como_antes():
    """Las llamadas viejas (cuatro argumentos) no pueden empezar a fallar."""
    r = D.revisar_briefing(PRIMERA_REAL, "", "", [])
    assert r["amplitud"] == []


# ── #61 en la segunda lectura: si insiste, no se publica ─────────────────────

LARGO = " Relleno de contexto para que el texto supere las cincuenta palabras." * 8


def _segunda(monkeypatch, textos):
    llamadas = []

    def falso(prompt, modelo=None, **_):
        llamadas.append(prompt)
        return textos[min(len(llamadas), len(textos)) - 1] + "\n\nSESGO: BAJISTA", {}
    monkeypatch.setattr(D, "generate_briefing", falso)
    r = D.generar_segunda_lectura("PROMPT", modelo="groq/compound", titulares="",
                                  eventos=[], amplitud=AMPLITUD)
    return r, llamadas


def test_la_segunda_lectura_que_insiste_en_la_amplitud_de_otro_dia_no_se_publica(monkeypatch):
    r, llamadas = _segunda(monkeypatch, [SEGUNDA_REAL + LARGO, SEGUNDA_REAL + LARGO])
    assert r is None
    assert len(llamadas) == 2, "tiene que haber UN reintento antes de descartarla"
    assert "AMPLITUD DE OTRO DIA" in llamadas[1], "el reintento no le dice qué ha roto"


def test_si_el_reintento_nombra_el_dia_se_publica(monkeypatch):
    bueno = ("El miercoles el McClellan marcó -123,1 y el ABI el 59,0%, con 99 avances "
             "frente a 399 descensos." + LARGO)
    r, _ = _segunda(monkeypatch, [SEGUNDA_REAL + LARGO, bueno])
    assert r is not None and "El miercoles" in r["text"]


# ── #62: el reintento espera a que pase la ventana del minuto ────────────────

def test_el_reintento_espera_antes_de_volver_a_llamar():
    """Sin la espera, la segunda llamada se come un 429 de ITPM y el briefing
    se publica con el fallo que la revisión ya había visto — que es justo lo
    que pasó el 11/09."""
    fuente = inspect.getsource(D.main)
    assert "esperar_a_groq(" in fuente, "el reintento vuelve a llamar sin esperar"
    assert fuente.index("esperar_a_groq(") < fuente.index("reintento, diag_rev"), (
        "la espera tiene que ir ANTES de la llamada, no después")


def test_la_espera_cubre_la_ventana_entera():
    """El límite es por minuto: esperar 30 s no sirve de nada."""
    assert D.ESPERA_REINTENTO_S >= 60 or os.environ.get("BRIEFING_ESPERA_REINTENTO")


def test_la_espera_se_puede_apagar_para_los_tests(monkeypatch, capsys):
    monkeypatch.setattr(D, "ESPERA_REINTENTO_S", 0)
    D.esperar_a_groq("el reintento")          # no debe dormir ni imprimir
    assert capsys.readouterr().out == ""


# ── #63: el cierre, delante y con su nombre ──────────────────────────────────

def _md_del_1109():
    """Lo esencial del 11/09: los índices cerraron el jueves; el WTI ya cotiza
    el viernes, con su cierre del jueves guardado en `en_sesion`."""
    return {"date": "2026-09-11", "time": "07:53 ET",
            "sesion": {"fecha": "2026-09-10", "en_curso": False, "hora_et": "07:53"},
            "barras": {"SPX": ("2026-09-09", "2026-09-10"),
                       "WTI": ("2026-09-10", "2026-09-11")},
            "SPX": {"price": 7591.70, "chg_pct": -0.58, "prev": 7636.36},
            "WTI": {"price": 99.40, "chg_pct": -3.01, "prev": 102.48,
                    "en_sesion": {"desde": "2026-09-09", "prev": 96.05,
                                  "cierre": 102.48, "chg_pct": 6.69}}}


def test_el_cierre_va_primero_y_se_llama_cierre():
    """EL test del #63: con la fila vieja («99.40 (▼3.01%) [sesion ▲6.69%]») la
    segunda lectura escribió «el WTI cerró ayer en 99,40 $ (-3,01%)» el día en
    que el petróleo era LA noticia. Lo que se va a citar como cierre tiene que
    ir delante."""
    p = D.build_prompt(_md_del_1109(), [], [], [], {}, [], [])
    fila = next(l for l in p.splitlines() if l.startswith("- Petróleo WTI:"))
    assert "CIERRE 102.48 (▲6.69%)" in fila, f"el cierre no va con su nombre: {fila}"
    assert fila.index("CIERRE 102.48") < fila.index("99.40"), (
        f"el precio de ahora sigue yendo delante del cierre: {fila}")
    assert "ahora 99.40" in fila, f"el dato de ahora no dice que es de ahora: {fila}"


def test_la_cabecera_dice_de_que_dia_es_el_cierre():
    p = D.build_prompt(_md_del_1109(), [], [], [], {}, [], [])
    cab = next(l for l in p.splitlines() if l.startswith("EN CURSO HOY"))
    assert "CIERRE = el del 2026-09-10 (jueves)" in cab
    assert "NO un cierre" in cab, "no se dice que el dato de ahora no lo es"


def test_la_fila_del_cierre_no_se_toca():
    """Lo que cerró CON la sesión (el S&P) no lleva la etiqueta: su variación ya
    es la de la sesión, y duplicarla son fichas tiradas en un prompt que no
    cabe ningún día."""
    p = D.build_prompt(_md_del_1109(), [], [], [], {}, [], [])
    fila = next(l for l in p.splitlines() if l.startswith("- S&P 500:"))
    assert "CIERRE" not in fila and "ahora" not in fila, fila
