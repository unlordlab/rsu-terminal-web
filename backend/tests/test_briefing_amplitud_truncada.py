"""
El escaneo del Scanner trajo 24 valores y el briefing los tomó por el mercado.

EL CASO, 03/09/2026. El escaneo nocturno escribió la sesión del 02/09 con
**24 valores** (20 avances / 4 descensos) en vez de los ~2.380 de las once
sesiones anteriores, y el desglose del S&P 500 con **1** en vez de ~495:

    2026-08-28   2372 valores   (928/1444)
    2026-08-31   2387 valores   (722/1665)
    2026-09-01   2388 valores   (681/1707)
    2026-09-02     24 valores   (20/4)      <-- truncado

El briefing lo consumió sin enterarse. Calculó un ABI de 66,7% -- que es
|20−4|/24, ruido puro-- lo llamó «señal de capitulación», metió ese punto en
las EMA del McClellan y construyó encima toda su sección «Rotación sectorial y
la trampa de la amplitud» y su conclusión BAJISTA.

Un escaneo truncado no es un día flojo de mercado: es un dato que no existe. Y
se nota mirando el TAMAÑO de la muestra, que ya venía en el propio Gist.

Y UN SEGUNDO FALLO, encima del primero: 20 contra 4 es un desequilibrio **AL
ALZA**, y el briefing escribió que «la inmensa mayoría de los componentes
cayeron o se estancaron». Tenía los avances y los descensos al lado y los leyó
al revés, porque el ABI mide CUÁNTO se impone un lado pero no CUÁL. Ahora la
banda lleva la dirección.

Uso:
    cd backend
    python -m pytest tests/test_briefing_amplitud_truncada.py -v
"""
import json
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402


# ── ¿Está rota la última sesión? ─────────────────────────────────────────────

NORMALES = [2372, 2387, 2388, 2389, 2395, 2385, 2369, 2382, 2383, 2381, 2386]


def test_las_24_acciones_del_02_09_se_detectan_como_escaneo_roto():
    """EL test, con los números reales del caso."""
    rota, tot, esperado = D.amplitud_incompleta(24, NORMALES)
    assert rota is True and tot == 24
    assert 2300 < esperado < 2400


def test_una_sesion_normal_no_se_descarta():
    rota, _, _ = D.amplitud_incompleta(2388, NORMALES)
    assert rota is False


def test_una_sesion_algo_corta_pero_creible_NO_se_descarta():
    """Un día con menos cobertura no es un escaneo roto. Si el umbral fuera
    demasiado estricto se tirarían sesiones buenas, que es peor: el briefing se
    quedaría sin amplitud propia justo lo que lo diferencia."""
    rota, _, _ = D.amplitud_incompleta(2000, NORMALES)
    assert rota is False


def test_el_umbral_se_mide_contra_la_MEDIANA_no_contra_un_numero_fijo():
    """El universo cambia de tamaño con el tiempo (entradas y salidas del
    índice); un umbral escrito a mano envejece en silencio. Con un universo
    diez veces menor, 24 valores serían normales."""
    pequenos = [230, 235, 228, 240, 233]
    rota, _, esperado = D.amplitud_incompleta(220, pequenos)
    assert rota is False and 225 < esperado < 240


def test_aguanta_que_alguna_sesion_previa_tambien_viniera_rota():
    """La mediana no se desplaza porque haya dos sesiones basura entre las
    anteriores; una media sí lo haría."""
    con_basura = NORMALES + [24, 31]
    rota, _, _ = D.amplitud_incompleta(24, con_basura)
    assert rota is True


def test_sin_historial_previo_no_se_descarta_nada():
    """El primer día no hay con qué comparar: descartar por defecto dejaría el
    briefing sin amplitud sin motivo."""
    assert D.amplitud_incompleta(24, [])[0] is False
    assert D.amplitud_incompleta(None, NORMALES)[0] is False


# ── Lo que hace la función de amplitud con una sesión rota ───────────────────

def _gist(sesiones, sp):
    contenido = {"stocks": {"AAPL": {"above_sma50": True}},
                 "breadth_history": sesiones,
                 "breadth_sp500": sp,
                 "breadth_russell": [{"date": "2026-09-02", "advances": 20, "declines": 4}],
                 "universe_size": 498}
    r = MagicMock(status_code=200)
    r.json.return_value = {"files": {D.SCANNER_GIST_FILE: {"content": json.dumps(contenido)}}}
    return r


def _sesion(fecha, adv, dec):
    return {"date": fecha, "advances": adv, "declines": dec,
            "new_highs": 24, "new_lows": 43, "pct_above_sma50": 46.6}


def _amplitud(sesiones, sp):
    with patch.object(D.requests, "get", return_value=_gist(sesiones, sp)):
        return D.get_rsu_breadth_signals()


BUENAS = [_sesion(f"2026-06-{d:02d}", 1200, 1180) for d in range(1, 29)] * 2


def test_con_la_ultima_sesion_rota_se_usa_la_ANTERIOR_no_el_ruido():
    """EL otro test. El ABI, el McClellan y el NH-NL salen todos de la última
    sesión: si viene rota hay que retroceder, no publicar |20-4|/24."""
    sesiones = BUENAS + [_sesion("2026-09-01", 681, 1707), _sesion("2026-09-02", 20, 4)]
    b = _amplitud(sesiones, [{"date": "2026-09-01", "advances": 159, "declines": 336}])
    assert b["fecha"] == "2026-09-01", "no ha retrocedido a la última sesión buena"
    assert b["advances"] == 681 and b["declines"] == 1707
    assert b["abi"] != 66.7, "sigue publicando el ABI calculado sobre 24 acciones"


def test_el_McClellan_no_se_calcula_con_el_punto_basura():
    """Un neto de +16 entre sesiones de ±1.000 se cuela en las EMA y arrastra
    varias sesiones, no solo la del día."""
    sesiones = BUENAS + [_sesion("2026-09-01", 681, 1707)]
    limpio = _amplitud(sesiones, [{"date": "2026-09-01", "advances": 159, "declines": 336}])
    con_rota = _amplitud(sesiones + [_sesion("2026-09-02", 20, 4)],
                         [{"date": "2026-09-01", "advances": 159, "declines": 336}])
    assert con_rota["mcclellan"] == limpio["mcclellan"], (
        "la sesión truncada está entrando en las EMA del McClellan")


def test_el_desglose_del_S_and_P_se_filtra_igual():
    """El 02/09 traía UN valor (0/1). Un 0% al alza sobre una acción no es una
    lectura de amplitud."""
    sesiones = BUENAS + [_sesion("2026-09-01", 681, 1707)]
    sp = [{"date": f"2026-08-{d:02d}", "advances": 200, "declines": 296} for d in range(20, 29)]
    sp += [{"date": "2026-09-01", "advances": 159, "declines": 336},
           {"date": "2026-09-02", "advances": 0, "declines": 1}]
    b = _amplitud(sesiones, sp)
    assert b["sp500_advances"] == 159 and b["sp500_declines"] == 336
    assert b["sp500_pct_al_alza"] != 0.0


def test_una_racha_normal_no_se_toca():
    """El arreglo no puede quitarle la amplitud a los días buenos."""
    sesiones = BUENAS + [_sesion("2026-09-02", 681, 1707)]
    b = _amplitud(sesiones, [{"date": "2026-09-02", "advances": 159, "declines": 336}])
    assert b["fecha"] == "2026-09-02" and b["advances"] == 681


# ── El ABI dice ahora hacia qué lado ─────────────────────────────────────────

def test_un_desequilibrio_al_alza_se_etiqueta_al_alza():
    """El fallo del 03/09: «CAPITULACION» a secas junto a 20 avances y 4
    descensos, y el briefing escribió que la mayoría de componentes cayeron."""
    sesiones = BUENAS + [_sesion("2026-09-02", 2000, 400)]
    b = _amplitud(sesiones, [{"date": "2026-09-02", "advances": 300, "declines": 196}])
    assert b["abi_estado"].startswith("CAPITULACION")
    assert "al alza" in b["abi_estado"], (
        "el ABI sigue sin decir hacia qué lado se ha impuesto el mercado")


def test_un_desequilibrio_a_la_baja_se_etiqueta_a_la_baja():
    sesiones = BUENAS + [_sesion("2026-09-02", 400, 2000)]
    b = _amplitud(sesiones, [{"date": "2026-09-02", "advances": 100, "declines": 396}])
    assert "a la baja" in b["abi_estado"]


def test_un_mercado_apagado_no_lleva_direccion():
    """Con un ABI bajo el «lado ganador» no significa nada: ponerle dirección
    sería inventar una lectura donde no la hay."""
    sesiones = BUENAS + [_sesion("2026-09-02", 1250, 1150)]
    b = _amplitud(sesiones, [{"date": "2026-09-02", "advances": 250, "declines": 246}])
    assert b["abi_estado"] == "APAGADO"


def test_la_direccion_llega_al_prompt():
    p = D.build_prompt(
        {"date": "03/09/2026", "time": "07:47", "sectors": {}, "calendar": [],
         "sesion": {"en_curso": False, "fecha": "2026-09-02", "hora_et": "07:47"}},
        [], [], [], {"abi": 66.7, "abi_estado": "CAPITULACION al alza",
                     "mcclellan": -125.8, "mcclellan_estado": "BAJISTA",
                     "pct_above_sma50": 46.6, "advances": 2000, "declines": 400,
                     "new_highs": 24, "new_lows": 43, "nh_nl": -19,
                     "sp500_advances": 300, "sp500_declines": 196,
                     "sp500_pct_al_alza": 60.5, "universo_amplitud": 2400,
                     "universe_size": 498, "fecha": "2026-09-02"}, [], [], [])
    assert "ABI: 66.7% (CAPITULACION al alza)" in p


# ── Lo que se le dice al modelo cuando el escaneo vino roto ──────────────────

def _prompt(breadth):
    return D.build_prompt(
        {"date": "03/09/2026", "time": "07:47", "sectors": {}, "calendar": [],
         "sesion": {"en_curso": False, "fecha": "2026-09-02", "hora_et": "07:47"}},
        [], [], [], breadth, [], [], [])


_B = {"abi": 41.2, "abi_estado": "CAPITULACION a la baja", "mcclellan": -125.8,
      "mcclellan_estado": "BAJISTA", "pct_above_sma50": 46.6, "advances": 681,
      "declines": 1707, "new_highs": 24, "new_lows": 43, "nh_nl": -19,
      "sp500_advances": 159, "sp500_declines": 336, "sp500_pct_al_alza": 32.1,
      "universo_amplitud": 2388, "universe_size": 498, "fecha": "2026-09-01"}


def test_si_el_escaneo_vino_roto_el_modelo_se_entera():
    """Retroceder en silencio dejaría al modelo narrando la amplitud de ayer
    como si fuera la de hoy -- que es el fallo del 03/09 con otra cara."""
    p = _prompt(dict(_B, escaneo_incompleto=True))
    assert "ESCANEO NOCTURNO DE HOY VINO INCOMPLETO" in p
    assert "SESIÓN ANTERIOR" in p


def test_el_aviso_NO_dice_que_los_datos_falten():
    """El código retrocede a la última sesión completa, no deja huecos. Decir
    «N/D» contradiría a los números que el modelo tiene justo debajo -- y
    callarlo tampoco vale: el 25/08, con la amplitud vacía, escribió que «la
    herramienta no tiene ese dato»."""
    p = _prompt(dict(_B, escaneo_incompleto=True))
    aviso = [l for l in p.splitlines() if "VINO INCOMPLETO" in l][0]
    assert "N/D" not in aviso
    assert "681" in p and "-125.8" in p, "los números de la sesión buena siguen ahí"


def test_un_dia_normal_no_lleva_aviso():
    """Un aviso permanente es ruido que se paga en fichas todos los días."""
    p = _prompt(dict(_B, escaneo_incompleto=False))
    assert "VINO INCOMPLETO" not in p


def test_el_flag_lo_pone_la_funcion_de_amplitud_no_el_prompt():
    """Si `escaneo_incompleto` no se calculara de verdad, el aviso no saldría
    nunca y el retroceso sería mudo."""
    sesiones = BUENAS + [_sesion("2026-09-01", 681, 1707), _sesion("2026-09-02", 20, 4)]
    b = _amplitud(sesiones, [{"date": "2026-09-01", "advances": 159, "declines": 336}])
    assert b["escaneo_incompleto"] is True
    limpio = _amplitud(BUENAS + [_sesion("2026-09-02", 681, 1707)],
                       [{"date": "2026-09-02", "advances": 159, "declines": 336}])
    assert limpio["escaneo_incompleto"] is False


# ── total_valores no es lo mismo que avances+descensos ───────────────────────

def test_una_sesion_MUY_PLANA_no_se_confunde_con_una_truncada():
    """`avances + descensos` NO cuenta los valores que cierran planos, así que
    en una sesión muy quieta se queda corto y parecería un escaneo roto. Por eso
    el escáner emite `total_valores` desde el 04/09 y el briefing lo prefiere.

    Sin esa preferencia, una sesión legítima de 2.400 valores con casi todos
    planos (24 con movimiento) se tiraría por la borda -- justo el mercado
    apagado que el ABI está para señalar."""
    plana = _sesion("2026-09-02", 20, 4)
    plana["total_valores"] = 2400
    sesiones = BUENAS + [_sesion("2026-09-01", 681, 1707), plana]
    for h in sesiones[:-1]:
        h["total_valores"] = h["advances"] + h["declines"]
    b = _amplitud(sesiones, [{"date": "2026-09-02", "advances": 159, "declines": 336}])
    assert b["fecha"] == "2026-09-02", (
        "se ha descartado una sesión completa por mirar avances+descensos en "
        "vez de `total_valores`: 2.376 valores planos no son un escaneo roto")
    assert b["escaneo_incompleto"] is False


def test_y_una_truncada_con_total_valores_bajo_SI_se_descarta():
    """El otro lado: si `total_valores` confirma que la muestra es una fracción,
    se descarta aunque los avances y descensos parezcan razonables."""
    rota = _sesion("2026-09-02", 20, 4)
    rota["total_valores"] = 24
    sesiones = BUENAS + [_sesion("2026-09-01", 681, 1707), rota]
    for h in sesiones[:-1]:
        h["total_valores"] = h["advances"] + h["declines"]
    b = _amplitud(sesiones, [{"date": "2026-09-01", "advances": 159, "declines": 336}])
    assert b["fecha"] == "2026-09-01" and b["escaneo_incompleto"] is True
