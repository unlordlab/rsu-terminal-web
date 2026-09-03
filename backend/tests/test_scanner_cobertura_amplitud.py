"""
El escáner publicaba una sesión de amplitud calculada sobre 24 tickers.

EL CASO, 02/09/2026. El escaneo nocturno escribió la sesión del 02/09 con 24
valores (20 avances / 4 descensos) en vez de los ~2.380 de las once anteriores.
Lo consumieron CUATRO sitios sin que ninguno se enterara: Market (el McClellan
y la línea A-D), el RSU Algoritmo (el factor Breadth), `snapshots_service` --que
lo PERSISTE con `INSERT OR IGNORE`, así que una ejecución buena posterior no lo
corrige-- y el briefing diario, que publicó un ABI de 66,7% como «señal de
capitulación» y construyó encima su conclusión bajista.

EL MECANISMO. `pd.DataFrame(cols)` UNE los índices de todos los tickers. Si 24
ya tienen barra del día y los otros ~2.360 todavía no, pandas crea la fila del
día con NaN en casi todas las columnas, y entonces:

    advances  = (diff > 0).sum(axis=1)          <- recuento CRUDO
    pct_above = above.sum(axis=1) / valid_cnt   <- este SÍ divide por los válidos

`pct_above_sma50` es inmune porque divide por los que tienen dato — un arreglo
del 15/08/2026 cuyo comentario está TRES LÍNEAS por encima de `advances`. El
mismo arreglo aplicado a un indicador y no a sus vecinos, que es el tercer caso
igual en dos semanas (ver el McClellan y el ABI en el briefing).

NO ERA UN PROBLEMA DE HORARIO: ese escaneo arrancó a las 00:16 UTC del 03/09
(20:16 ET del 02/09), tres horas después del cierre. La descarga vino parcial.

Uso:
    cd backend
    python -m pytest tests/test_scanner_cobertura_amplitud.py -v
"""
import os
import sys

import numpy as np
import pandas as pd

RAIZ = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(RAIZ, 'shared'))
sys.path.insert(0, os.path.join(RAIZ, 'scripts'))

from cobertura_amplitud import (  # noqa: E402
    cobertura_insuficiente, sesiones_con_cobertura)


# ── La regla, sola ───────────────────────────────────────────────────────────

NORMALES = [2372, 2387, 2388, 2389, 2395, 2385, 2369, 2382, 2383, 2381, 2386]


def test_las_24_del_02_09_se_detectan():
    """EL test, con los números reales del caso."""
    rota, tot, esperado = cobertura_insuficiente(24, NORMALES)
    assert rota is True and tot == 24 and 2300 < esperado < 2400


def test_una_sesion_normal_pasa():
    assert cobertura_insuficiente(2388, NORMALES)[0] is False


def test_un_dia_con_algo_menos_de_cobertura_NO_se_tira():
    """Tirar sesiones buenas es peor que el fallo: el briefing y Market se
    quedarían sin amplitud propia, que es justo lo que los diferencia."""
    assert cobertura_insuficiente(2000, NORMALES)[0] is False


def test_el_umbral_va_contra_la_mediana_no_contra_un_numero_fijo():
    """El universo cambia de tamaño con las entradas y salidas del índice. Con
    un universo diez veces menor, 24 valores serían lo normal."""
    pequenos = [230, 235, 228, 240, 233]
    assert cobertura_insuficiente(220, pequenos)[0] is False
    assert cobertura_insuficiente(24, pequenos)[0] is True


def test_sin_historial_no_se_descarta_nada():
    assert cobertura_insuficiente(24, [])[0] is False
    assert cobertura_insuficiente(None, NORMALES)[0] is False


def test_el_filtro_de_historial_usa_total_valores_y_cae_a_avances_si_no_esta():
    """Los historiales escritos antes del 04/09 no llevan `total_valores`."""
    con = [{"total_valores": 2380, "advances": 1, "declines": 1} for _ in range(6)]
    con.append({"total_valores": 24, "advances": 20, "declines": 4})
    buenas, malas = sesiones_con_cobertura(con)
    assert len(malas) == 1 and malas[0]["total_valores"] == 24

    viejo = [{"advances": 1200, "declines": 1180} for _ in range(6)]
    viejo.append({"advances": 20, "declines": 4})
    buenas, malas = sesiones_con_cobertura(viejo)
    assert len(malas) == 1, "sin `total_valores` no cae al respaldo de avances+descensos"


# ── El escáner, que es donde se origina ──────────────────────────────────────

def _precios(n_tickers, dias, ultimo_dia_solo_para=None):
    """Cierres sintéticos. `ultimo_dia_solo_para` reproduce el caso real: unos
    pocos tickers ya tienen la barra del último día y el resto no."""
    idx = pd.bdate_range("2026-01-01", periods=dias)
    close_d = {}
    for i in range(n_tickers):
        serie = pd.Series(100 + np.arange(dias) * 0.1 + (i % 7) * 0.05, index=idx)
        if ultimo_dia_solo_para is not None and i >= ultimo_dia_solo_para:
            serie = serie.iloc[:-1]          # a este le falta el último día
        close_d[f"T{i:04d}"] = serie
    return close_d


def _historial(close_d):
    import scanner_universe as S
    return S._compute_breadth_history(close_d, list(close_d.keys()), lookback_days=60)


def test_una_sesion_completa_se_publica_con_su_cobertura():
    h = _historial(_precios(300, 200))
    assert h, "no ha salido historial"
    assert h[-1]["total_valores"] == 300, (
        "la cobertura no viaja en la fila: sin ella el problema solo se detecta "
        "auditando a mano, que es como se detectó el del 02/09")


def test_la_sesion_parcial_del_caso_real_NO_se_publica():
    """EL test. 300 tickers, y solo 24 tienen la barra del último día."""
    completo = _historial(_precios(300, 200))
    parcial = _historial(_precios(300, 200, ultimo_dia_solo_para=24))
    assert parcial[-1]["date"] != completo[-1]["date"], (
        "se sigue publicando la sesión truncada: es la que dio un ABI de 66,7% "
        "sobre 24 acciones y la conclusión bajista del briefing del 03/09")
    assert parcial[-1]["total_valores"] > 200


def test_la_serie_ANTERIOR_no_se_toca_al_descartar():
    """Descartar por la cola no puede llevarse por delante el histórico: el
    McClellan necesita la ventana entera para que sus EMA maduren."""
    completo = _historial(_precios(300, 200))
    parcial = _historial(_precios(300, 200, ultimo_dia_solo_para=24))
    assert len(parcial) == len(completo) - 1
    assert [x["date"] for x in parcial] == [x["date"] for x in completo[:-1]]


def test_dos_sesiones_parciales_seguidas_se_descartan_las_dos():
    """El 02/09 fue una, pero si la descarga falla dos noches seguidas no puede
    colarse la segunda solo porque la primera ya no esté."""
    close_d = _precios(300, 200)
    for i, t in enumerate(sorted(close_d)):
        if i >= 24:
            close_d[t] = close_d[t].iloc[:-2]
    h = _historial(close_d)
    assert all(x["total_valores"] > 200 for x in h)


def test_un_universo_pequeno_no_se_descarta_entero():
    """Si el universo real fuera de 60 tickers, 60 es su normalidad — no una
    sesión rota. Es el motivo de comparar con la mediana."""
    h = _historial(_precios(60, 200))
    assert h and h[-1]["total_valores"] == 60


def test_pct_above_sma50_sigue_dividiendo_por_los_validos():
    """El arreglo del 15/08 que sí estaba puesto. Este test existe para que no
    se caiga al tocar sus vecinos."""
    parcial = _historial(_precios(300, 200, ultimo_dia_solo_para=24))
    for fila in parcial:
        if fila["pct_above_sma50"] is not None:
            assert 0 <= fila["pct_above_sma50"] <= 100
