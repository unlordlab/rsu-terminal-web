"""
Test de las estadísticas del backtest de SPXL (12/08/2026, hallazgos #6, #7,
#8 y #10 de su auditoría).

Dos de los cuatro tenían la premisa equivocada, y comprobarlo con datos fue
lo que lo destapó:

  #8  decía «max_dd se calcula dos veces con BASES DISTINTAS». Se calculaba
      dos veces, sí, pero las dos partían de `initial_capital` y recorrían la
      misma curva: daban 47,77 las dos sobre el histórico completo. No era un
      número mal, era la misma cuenta escrita dos veces esperando a divergir.
  #10 decía que `cycle_equity` tras `C-final` incluye un runner inexistente.
      Cierto, pero el término valía 0 en los 3 C-final del histórico: código
      muerto, no una cifra contaminada.

Los otros dos sí eran defectos:

  #7  `compute_stats` devolvía `{}` en cuanto no había operaciones, y con él
      se iban el Buy & Hold, el drawdown y los años, que NO dependen de que
      se haya operado.
  #6  el backtest no descuenta costes... pero el cálculo del rango con costes
      YA existía en el backend con su endpoint, y la página nunca lo pedía.

Uso:
    cd backend
    python -m pytest tests/test_spxl_stats.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.spxl_service as S  # noqa: E402


def _curva(valores, desde="2020-01-01"):
    from datetime import datetime, timedelta
    d0 = datetime.strptime(desde, "%Y-%m-%d")
    return [{"date": (d0 + timedelta(days=i)).strftime("%Y-%m-%d"), "equity": v}
            for i, v in enumerate(valores)]


def _trade(pnl, pnl_pct):
    return {"pnl": pnl, "pnl_pct": pnl_pct, "scenario": "A-main"}


# ── #7: sin operaciones no se pierde todo lo demás ───────────────────────────

def test_sin_operaciones_ya_no_devuelve_un_diccionario_vacio():
    eq  = _curva([100_000, 110_000, 105_000])
    bnh = _curva([100_000, 120_000, 130_000])
    r = S.compute_stats([], eq, bnh, 100_000)
    assert r != {}, "la página se quedaba sin nada solo porque la estrategia no operó"


def test_el_buy_and_hold_no_depende_de_que_haya_operaciones():
    """Es la comparación que más falta hace justo cuando la estrategia no hizo
    nada: ¿cuánto habrías ganado sin tocar nada?"""
    eq  = _curva([100_000, 100_000, 100_000])
    bnh = _curva([100_000, 150_000, 200_000])
    r = S.compute_stats([], eq, bnh, 100_000)
    assert r["final_bnh"] == 200_000
    assert r["bnh_return"] == 100.0
    assert r["bnh_cagr"] is not None


def test_el_drawdown_tampoco_depende_de_las_operaciones():
    eq = _curva([100_000, 120_000, 60_000])   # cae a la mitad desde el pico
    r = S.compute_stats([], eq, _curva([100_000] * 3), 100_000)
    assert r["max_dd"] == 50.0


def test_las_metricas_por_operacion_quedan_a_none_no_a_cero():
    """Un win rate de 0% se lee como «pierde siempre». Sin muestra, la
    respuesta honesta es que no hay dato."""
    r = S.compute_stats([], _curva([100_000, 110_000]), _curva([100_000, 110_000]), 100_000)
    assert r["total_trades"] == 0
    assert r["win_rate"] is None
    assert r["avg_win"] is None and r["avg_loss"] is None


def test_con_operaciones_las_metricas_siguen_saliendo():
    trades = [_trade(100, 10.0), _trade(-50, -5.0), _trade(200, 20.0)]
    r = S.compute_stats(trades, _curva([100_000, 110_000]), _curva([100_000, 105_000]), 100_000)
    assert r["total_trades"] == 3
    assert r["win_rate"] == pytest.approx(66.7, abs=0.1)
    assert r["avg_win"] == pytest.approx(15.0)
    assert r["avg_loss"] == pytest.approx(-5.0)


def test_sin_curva_no_hay_nada_que_calcular():
    """Aquí sí procede el diccionario vacío: sin serie de equity no hay ni
    drawdown ni periodo ni benchmark."""
    assert S.compute_stats([], [], [], 100_000) == {}
    assert S.compute_stats([_trade(1, 1.0)], [], [], 100_000) == {}


# ── #8: el drawdown se calcula en un solo sitio ──────────────────────────────

def test_run_backtest_ya_no_devuelve_su_propia_copia_del_drawdown():
    """El contrato: `max_dd` sale de compute_stats y de ningún otro sitio. Si
    vuelve a aparecer en run_backtest, hay dos cuentas que pueden divergir."""
    import inspect
    src = inspect.getsource(S.run_backtest)
    assert '"max_dd"' not in src, "run_backtest volvió a calcular el drawdown por su cuenta"


def test_el_drawdown_se_mide_desde_el_capital_inicial():
    """La base importa: partiendo del capital inicial, una curva que solo sube
    no tiene drawdown, aunque su primer punto sea menor que el segundo."""
    r = S.compute_stats([], _curva([100_000, 150_000, 200_000]), _curva([100_000] * 3), 100_000)
    assert r["max_dd"] == 0.0


# ── #10: el término muerto del Escenario C ───────────────────────────────────

def test_el_escenario_c_no_arrastra_un_runner_en_su_cierre():
    """El Escenario C no abre runner (solo A y B), así que sumarlo al capital
    del ciclo sugería una posición que ahí no existe."""
    import inspect
    src = inspect.getsource(S.run_backtest)
    # Desde el `C-final` hasta el `elif` del Escenario B, que es donde acaba
    # el bloque de C. Recortar por un número fijo de caracteres no vale: el
    # comentario que explica esto ya desplazó la línea fuera de la ventana y
    # el sabotaje se coló.
    bloque = src.split('"C-final"')[1].split("elif n_phases")[0]
    assert "cycle_equity = cash + runner_shares" not in bloque, \
        "el cierre del Escenario C volvió a sumar un runner que ahí no existe"
    assert "cycle_equity = cash" in bloque, \
        "el capital del ciclo tiene que seguir actualizándose al cerrar C"


# ── #6: el rango con costes existe y tiene que llegar a la página ────────────

def test_hay_escenarios_de_coste_definidos():
    assert S.SLIPPAGE_ESCENARIOS, "sin escenarios no hay rango que enseñar"
    for coste, etiqueta in S.SLIPPAGE_ESCENARIOS:
        assert 0 <= coste < 0.1, f"coste por operación fuera de rango: {coste}"
        assert etiqueta


def test_el_rango_de_costes_descarga_los_mismos_datos_que_el_backtest():
    """Descargaba solo `Close`, así que `run_backtest` caía a su respaldo
    `lows = prices` y los stops no podían dispararse intradía: salía otro
    backtest. El resultado era que la tabla de costes anunciaba un «equity
    limpio» de $611.775 mientras el titular de la misma página decía
    $634.606. Dos cifras para lo mismo, en la misma pantalla."""
    import inspect
    src = inspect.getsource(S.get_backtest_con_slippage)
    assert '[["Close", "Low"]]' in src, "sin Low, este backtest no es el mismo que el de arriba"
    assert '["price", "low"]' in src


def test_los_anios_del_rango_de_costes_no_estan_clavados():
    """Estaban fijos en 17,7 desde el día que se escribió la función, y el
    histórico crece solo: hoy ya son 17,8, así que el CAGR ajustado se
    calculaba sobre un periodo que ya no era el del backtest."""
    import inspect
    src = inspect.getsource(S.get_backtest_con_slippage)
    assert "años = 17.7" not in src
    assert "curva[-1][\"date\"]" in src, "el periodo debe salir de la propia curva"
