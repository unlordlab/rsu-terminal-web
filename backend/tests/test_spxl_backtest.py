"""
Test de regresión para run_backtest() (SPXL) -- ver conversación
18-19/07/2026. Los escenarios de este test reutilizan los mismos casos
sintéticos que ya sirvieron para encontrar y confirmar el arreglo de 3
bugs reales el 18/07/2026:

1. El "runner" quedaba huérfano en cuanto shares llegaba a 0 -- nadie
   volvía a comprobar si debía cerrarse (bloqueaba toda reentrada futura).
2. Podía arrancar una fase nueva mientras el runner del ciclo anterior
   seguía abierto (dos posiciones simultáneas pisándose entre sí).
3. Las ventas parciales C-trim1/C-trim2 del Escenario C no sumaban el
   dinero de la venta al efectivo (el bug más grave: el dinero
   desaparecía en las peores crisis, justo las que la estrategia está
   pensada para aprovechar).

Este test formaliza esas mismas pruebas para que, si algún cambio futuro
reintroduce cualquiera de los tres, falle de inmediato en vez de
descubrirse meses después con datos reales.

Uso:
    cd backend
    python -m pytest tests/test_spxl_backtest.py -v
"""
import sys
import os

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.spxl_service import run_backtest  # noqa: E402


def _df_desde_precios(precios: list, inicio="2020-01-01") -> pd.DataFrame:
    return pd.DataFrame({"price": precios}, index=pd.date_range(inicio, periods=len(precios)))


def _df_con_low(precios: list, lows: list, inicio="2020-01-01") -> pd.DataFrame:
    return pd.DataFrame(
        {"price": precios, "low": lows},
        index=pd.date_range(inicio, periods=len(precios)),
    )


def test_backtest_fase1_dispara_con_caida_del_15_porciento():
    """Caso más simple: una caída del 15% desde el máximo debe disparar
    la Fase 1 y comprar, sin más complicaciones."""
    precios = [100] * 3 + [95, 90, 86, 84]  # -16% desde el maximo de 100
    df = _df_desde_precios(precios)

    r = run_backtest(df, initial_capital=100_000)
    fs = r["final_state"]

    assert fs["phase_idx"] == 0, "Debería estar en Fase 1 (índice 0)"
    assert fs["shares"] > 0, "Debería haber comprado acciones"
    assert fs["cash"] < 100_000, "El efectivo debería haber bajado tras la compra"


def test_backtest_reentra_tras_cerrar_un_ciclo_completo():
    """Bug 1 y 2 (huérfano + solapamiento): tras cerrar un ciclo del
    todo, una caída NUEVA y separada debe poder disparar otro ciclo
    -- no debe quedarse la estrategia congelada para siempre."""
    precios = (
        [100] * 3 +
        [90, 80, 70, 60, 50, 45, 40] +      # primera crisis: -60%, ciclo completo
        [50, 65, 80, 100, 120, 150] +        # recuperación a nuevo máximo real
        [140, 130, 120, 110, 100]            # segunda crisis: -33% desde 150
    )
    df = _df_desde_precios(precios)

    r = run_backtest(df, initial_capital=100_000)
    fs = r["final_state"]

    # Debe haber operado en AMBAS crisis, no solo en la primera
    assert len(r["trades"]) >= 3, f"Se esperaban al menos 3 operaciones (1ª crisis + inicio de la 2ª), salieron {len(r['trades'])}"
    assert fs["phase_idx"] >= 0, "Debería haber vuelto a entrar en la segunda crisis, no quedarse en STAND BY para siempre"
    # La referencia de la 2ª crisis debe partir del nuevo máximo real (150), no de un valor viejo congelado
    assert fs["phase_high"] < 150, "phase_high debería haberse actualizado tras alguna compra en la 2ª crisis"


def test_backtest_runner_se_cierra_por_stop_no_queda_huerfano():
    """Bug 1 específicamente: tras activarse un runner (Escenario A) y
    caer más del stop desde su pico, debe cerrarse solo -- no debe
    quedar in_runner=True para siempre bloqueando el resto de la
    estrategia.

    Nota (sesión 18): el pico se mantiene deliberadamente por debajo de
    124.02 (= 106*1.17, el target de first_sell_px arreglado en la sesión
    17) para que este runner cierre SOLO por stop, no por objetivo --
    antes del fix de la sesión 17 el target era inalcanzable siempre, así
    que cualquier pico servía; ahora hay que mantenerse por debajo a
    propósito para seguir aislando el bug 1 (huérfano) del fix de
    first_sell_px, que tiene su propio test dedicado."""
    precios = (
        [100] * 3 +
        [90, 85] +                # -15%, dispara Fase 1 (Escenario A)
        [95, 106, 115] +          # +25% desde 85 -> dispara A-main, entra en runner
        [118, 120, 121] +         # el runner sigue subiendo, nuevo pico 121 (< target 124.02)
        [115, 108, 100]           # cae más del 11% desde 121 -> debe cerrar el runner por stop
    )
    df = _df_desde_precios(precios)

    r = run_backtest(df, initial_capital=100_000)
    fs = r["final_state"]

    escenarios = [t["scenario"] for t in r["trades"]]
    assert "A-runner" in escenarios, "El runner debería haberse cerrado y aparecer como operación A-runner"
    assert fs["in_runner"] is False, "in_runner debería quedar en False tras cerrarse -- si sale True, ha reaparecido el bug del runner huérfano"
    assert fs["phase_idx"] == -1, "Tras cerrar el runner, debería volver a STAND BY (-1), listo para el siguiente ciclo"


def test_backtest_escenario_c_el_efectivo_cuadra():
    """Bug 3, el más grave: en el Escenario C (las 6 fases), la suma de
    todos los P&L reportados debe coincidir con el efectivo final. Si
    C-trim1/C-trim2 dejan de sumar el dinero al efectivo (la regresión
    exacta que causaba el bug real), este test debe fallar."""
    precios = (
        [100] * 3 +
        [84, 75, 69, 62, 55, 48] +   # 6 caídas seguidas, sin pausas intermedias
        [55, 65, 75, 90, 105, 120]    # recuperación fuerte: trim1 -> trim2 -> final
    )
    df = _df_desde_precios(precios)

    r = run_backtest(df, initial_capital=100_000)
    fs = r["final_state"]

    escenarios = [t["scenario"] for t in r["trades"]]
    assert escenarios == ["C-trim1", "C-trim2", "C-final"], f"Se esperaba el ciclo completo del Escenario C, salió: {escenarios}"
    assert fs["shares"] == 0 and fs["runner_shares"] == 0.0, "Al cerrar del todo con C-final no debería quedar ninguna posición abierta"

    suma_pnl = sum(t["pnl"] for t in r["trades"])
    esperado = 100_000 + suma_pnl

    assert abs(fs["cash"] - esperado) < 1.0, (
        f"El efectivo final ({fs['cash']:.2f}) no cuadra con capital inicial + suma de P&L reportados "
        f"({esperado:.2f}). Si esto falla, sospecha primero de que alguna venta parcial (trim) haya "
        f"dejado de sumar sus ganancias al efectivo -- exactamente el bug real del 18/07/2026."
    )


def test_backtest_sin_datos_suficientes_no_revienta():
    """Caso límite: muy pocos datos, no debería lanzar una excepción."""
    df = _df_desde_precios([100, 99, 101])
    r = run_backtest(df, initial_capital=100_000)
    assert r["final_state"]["phase_idx"] == -1
    assert r["trades"] == []


# ── Sesión 17 (commit 48422ff): first_sell_px, stops vs Low, B&H al 100% ──

def test_backtest_escenario_a_runner_cierra_por_target_gracias_a_first_sell_px():
    """Antes del fix, Escenario A nunca asignaba first_sell_px al abrir el
    runner -- el target caía siempre al fallback `price * 1.17`, que se
    recalcula cada día con el precio DE HOY, así que `price >= price*1.17`
    era matemáticamente imposible. Esta subida monótona (que nunca toca el
    trailing stop) solo puede cerrar el runner si el target es alcanzable."""
    precios = [100] * 3 + [90, 85] + [95, 106, 115, 120, 124.5]
    df = _df_desde_precios(precios)

    r = run_backtest(df, initial_capital=100_000)
    fs = r["final_state"]

    a_runner = [t for t in r["trades"] if t["scenario"] == "A-runner"]
    assert len(a_runner) == 1, "El runner debería haber cerrado exactamente una vez, por objetivo alcanzado"
    assert a_runner[0]["exit_price"] == 124.5, (
        f"Se esperaba exit_price=124.5 (target 106*1.17=124.02 alcanzado), salió {a_runner[0]['exit_price']}"
    )
    assert fs["in_runner"] is False


def test_backtest_stop_se_dispara_por_low_intradiario_aunque_el_cierre_recupere():
    """El Low del día del stop es 100 pero el cierre ese mismo día es 118
    -- sin el fix (Low descartado en la descarga, fallback low=price), el
    stop ni se habría disparado ese día (118 > runner_peak*0.89). Con el
    fix, dispara por el Low intradía y el fill es realista (el nivel de
    stop, no el cierre que sobreestimaría la salida)."""
    precios = [100, 100, 100, 90, 85, 95, 106, 112, 118]
    lows    = [100, 100, 100, 90, 85, 95, 106, 112, 100]
    df = _df_con_low(precios, lows)

    r = run_backtest(df, initial_capital=100_000)

    a_runner = [t for t in r["trades"] if t["scenario"] == "A-runner"]
    assert len(a_runner) == 1
    assert a_runner[0]["exit_price"] == 105.02, (
        f"Se esperaba exit_price=105.02 (118*0.89, el nivel de stop, no el cierre 118), "
        f"salió {a_runner[0]['exit_price']}"
    )


def test_backtest_buy_and_hold_invierte_el_100_por_ciento_del_capital():
    """Con el reserve_pct=0.10 viejo (huérfano, eliminado en la sesión 17),
    un doblaje exacto del precio habría dado solo +90% de retorno en vez
    de +100% -- el B&H solo invertía el 90% del capital."""
    df = _df_desde_precios([100, 100, 200])
    r = run_backtest(df, initial_capital=100_000)

    assert r["bnh_curve"][-1]["equity"] == 200_000.0, (
        f"Doblaje exacto del precio debe doblar el equity de B&H exactamente "
        f"(100% invertido), salió {r['bnh_curve'][-1]['equity']}"
    )


def test_backtest_equity_curve_consistente_con_estado_final_y_sin_drift_en_reposo():
    """Invariante de contabilidad: sin ninguna posición abierta, el equity
    no debe derivar ni un céntimo; y al cierre, equity == cash + valor de
    mercado de lo que quede abierto (verificado en los dos puntos donde el
    estado independiente está disponible sin instrumentar más código)."""
    precios = (
        [100] * 3 +
        [84, 75, 69, 62, 55, 48] +
        [55, 65, 75, 90, 105, 120]
    )
    df = _df_desde_precios(precios)
    r = run_backtest(df, initial_capital=100_000)
    fs = r["final_state"]

    assert len(r["equity_curve"]) == len(df)

    for e in r["equity_curve"][:3]:
        assert e["equity"] == 100_000.0, "Sin trades ni cambio de precio, el equity no debe derivar"

    ultimo_precio = df["price"].iloc[-1]
    equity_esperado = round(fs["cash"] + fs["shares"] * ultimo_precio + fs["runner_shares"] * ultimo_precio, 2)
    assert r["equity_curve"][-1]["equity"] == equity_esperado