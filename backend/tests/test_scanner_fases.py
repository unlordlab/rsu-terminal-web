"""
Scanner: la fase semanal, y quién ACABA de entrar en avance.

DOS HALLAZGOS DE LA AUDITORÍA DE SCANNER (#17 y #18), los dos del mismo tipo:
el dato ya existía y nadie lo leía.

#17 — `phase_weekly` la calcula el scan nocturno desde siempre
(scanner_universe.py:516) y viaja en el Gist, pero el servicio no la pasaba y
la tabla no la pintaba. La fase diaria se voltea con ruido; la semanal es la
escala en la que Weinstein trabajaba.

#18 — `snapshot_ticker` lleva desde el 27/07/2026 guardando la fase confirmada
de los ~500 valores cada sesión, y nadie la consultaba. La tabla del Scanner es
una foto: un valor en fase 2 se ve igual lleve seis meses ahí o haya entrado
ayer, y en este método el recorrido grande está al PRINCIPIO del avance.

LO QUE FIJA ESTE FICHERO:
1. Solo cuentan las fases CONFIRMADAS -- sin eso, un valor que baila entre dos
   fases aparecería entrando y saliendo cada semana.
2. Un valor que ya estaba en avance NO es una entrada.
3. Se reporta la ventana REAL, no la pedida.
4. Sin histórico se devuelve un error explicado, no una lista vacía -- una
   lista vacía se lee como "no ha cambiado nada".

Uso:
    cd backend
    python -m pytest tests/test_scanner_fases.py -v
"""
import sys, os
from datetime import date, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.snapshots_service as S  # noqa: E402


@pytest.fixture
def db(tmp_path, monkeypatch):
    ruta = str(tmp_path / "snapshots.db")
    monkeypatch.setattr(S, "DB_PATH", ruta)
    S.init_db()
    return ruta


def _sembrar(filas):
    """filas: [(dias_atras, ticker, fase, confirmada)]"""
    base = date(2026, 8, 14)
    conn = S._conn()
    for atras, ticker, fase, conf in filas:
        conn.execute(
            "INSERT OR REPLACE INTO snapshot_ticker "
            "(fecha, ticker, sector, precio, rvol, rs_pct, phase, phase_confirmed) "
            "VALUES (?,?,?,?,?,?,?,?)",
            ((base - timedelta(days=atras)).strftime("%Y-%m-%d"), ticker,
             "Technology", 100.0, 1.0, 75.0, fase, conf))
    conn.commit(); conn.close()


# ── Entradas y salidas ──────────────────────────────────────────────────────


def test_detecta_la_entrada_en_avance(db):
    _sembrar([(5, "AAA", 1, 1), (0, "AAA", 2, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["ok"] is True
    assert [x["ticker"] for x in r["entradas"]] == ["AAA"]
    assert r["entradas"][0]["desde"] == 1 and r["entradas"][0]["hasta"] == 2
    assert r["entradas"][0]["desde_label"] == "Acumulación"


def test_detecta_la_salida_de_avance(db):
    _sembrar([(5, "BBB", 2, 1), (0, "BBB", 4, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert [x["ticker"] for x in r["salidas"]] == ["BBB"]
    assert r["entradas"] == []


def test_seguir_en_avance_no_es_una_entrada(db):
    """Es la diferencia entera con la tabla de arriba: un valor que lleva
    meses en fase 2 no ha cambiado de fase."""
    _sembrar([(5, "CCC", 2, 1), (0, "CCC", 2, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["entradas"] == [] and r["salidas"] == []


def test_un_cambio_entre_fases_que_no_tocan_el_avance_no_sale(db):
    """De distribución a declive es un cambio, pero no es lo que esta sección
    vigila -- meterlo diluiría la lista con movimientos que no accionan nada."""
    _sembrar([(5, "DDD", 3, 1), (0, "DDD", 4, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["entradas"] == [] and r["salidas"] == []


def test_solo_cuentan_las_fases_confirmadas(db):
    """Sin este filtro, un valor que baila entre dos fases en días
    consecutivos aparecería entrando y saliendo cada semana."""
    _sembrar([(5, "EEE", 1, 1), (0, "EEE", 2, 0)])   # hoy sin confirmar
    r = S.transiciones_de_fase(sesiones=5)
    assert r["entradas"] == []


def test_un_valor_nuevo_sin_fase_previa_no_cuenta_como_entrada(db):
    """No se puede afirmar que ha cambiado de fase algo que no estaba antes."""
    _sembrar([(5, "VIEJO", 1, 1), (0, "VIEJO", 1, 1), (0, "NUEVO", 2, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert [x["ticker"] for x in r["entradas"]] == []


def test_las_entradas_se_ordenan_por_fuerza_relativa(db):
    """Entre varias entradas a la vez, la que ya lidera es la que más dice."""
    base = date(2026, 8, 14)
    conn = S._conn()
    for atras, t, fase, rs in [(5, "FLOJA", 1, 20.0), (0, "FLOJA", 2, 20.0),
                               (5, "FUERTE", 1, 94.0), (0, "FUERTE", 2, 94.0)]:
        conn.execute("INSERT OR REPLACE INTO snapshot_ticker "
                     "(fecha,ticker,sector,precio,rvol,rs_pct,phase,phase_confirmed) "
                     "VALUES (?,?,?,?,?,?,?,1)",
                     ((base - timedelta(days=atras)).strftime("%Y-%m-%d"), t,
                      "Technology", 100.0, 1.0, rs, fase))
    conn.commit(); conn.close()
    r = S.transiciones_de_fase(sesiones=5)
    assert [x["ticker"] for x in r["entradas"]] == ["FUERTE", "FLOJA"]


# ── Honestidad sobre la ventana ─────────────────────────────────────────────

def test_se_reporta_la_ventana_real_no_la_pedida(db):
    """Con el histórico a medio llenar, anunciar «5 sesiones» cuando solo hay 2
    sería mentir sobre el periodo mirado."""
    _sembrar([(2, "AAA", 1, 1), (1, "AAA", 1, 1), (0, "AAA", 2, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["sesiones"] == 2
    assert r["sesiones_pedidas"] == 5


def test_sin_historico_se_explica_en_vez_de_devolver_una_lista_vacia(db):
    """Una lista vacía se leería como «no ha cambiado nada», que es una
    afirmación distinta de «todavía no lo sé»."""
    _sembrar([(0, "AAA", 2, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["ok"] is False
    assert "error" in r


def test_se_dice_cuantos_valores_eran_comparables(db):
    """Para saber de qué tamaño es la foto: si solo 30 valores tenían fase
    confirmada en las dos fechas, la lista dice mucho menos."""
    _sembrar([(5, "AAA", 1, 1), (0, "AAA", 2, 1),
              (5, "BBB", 2, 1), (0, "BBB", 2, 1),
              (0, "SOLO_HOY", 2, 1)])
    r = S.transiciones_de_fase(sesiones=5)
    assert r["comparables"] == 2


# ── Hallazgo #9: los puntos por volumen ─────────────────────────────────────
#
# La auditoría decía: "rvol_pts satura a RVOL=3x, pero los RVOL extremos siguen
# siendo informativos". Al medirlo aparecieron DOS defectos más en las mismas
# dos líneas, y uno de ellos pesa más que el denunciado.
#
# Calibrado sobre las 6.012 observaciones reales de snapshots.db (12 sesiones x
# ~500 valores): mediana 0,78 · p90 1,35 · p95 1,65 · p99 2,42 · máximo 9,67.

import pandas as pd  # noqa: E402
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
from scanner_universe import _rvol, _rvol_pts, RVOL_WINDOW, RVOL_TECHO  # noqa: E402


def test_el_volumen_normal_no_puntua():
    """EL DEFECTO QUE MÁS PESABA, y no es el que denunciaba la auditoría. La
    fórmula anterior era lineal desde 0, así que un valor con volumen NORMAL se
    llevaba 6,7 de los 20 puntos y uno con la mitad de lo habitual, 3,3. Con la
    mediana del universo en 0,78, eso era un sumando casi constante que añadía
    ruido al score sin distinguir nada."""
    assert _rvol_pts(1.0) == 0.0
    assert _rvol_pts(0.5) == 0.0
    assert _rvol_pts(0.26) == 0.0


def test_por_encima_de_lo_normal_si_puntua_y_crece():
    a, b, c = _rvol_pts(1.5), _rvol_pts(2.0), _rvol_pts(3.0)
    assert 0 < a < b < c <= 20


def test_el_crecimiento_es_logaritmico_no_lineal():
    """Con crecimiento lineal, el tramo 1-2 y el 2-3 valdrían lo mismo. El
    logaritmo da más peso al primer salto, que es donde está la información:
    pasar de normal a el doble dice más que de el doble al triple."""
    primero = _rvol_pts(2.0) - _rvol_pts(1.0)
    segundo = _rvol_pts(3.0) - _rvol_pts(2.0)
    assert primero > segundo


def test_un_volumen_extremo_ya_no_empata_con_uno_de_tres():
    """El hallazgo #9 tal cual lo escribía la auditoría. Antes, `min(rvol/3,1)`
    daba 20 puntos tanto a un RVOL de 3 como a uno de 9,67 -- y en el histórico
    real hay 21 observaciones por encima de 3."""
    assert _rvol_pts(3.0) < _rvol_pts(4.0)


def test_queda_un_techo_y_esta_puesto_a_conciencia():
    """No se resuelve del todo, y está escrito así en el código: solo hay 20
    puntos, y una curva que llegue al máximo en 10x aplastaría el tramo 1-2,5
    donde vive el 99% de los datos. Por encima de 4 (el 0,13% de las
    observaciones) se sigue empatando."""
    assert _rvol_pts(RVOL_TECHO) == 20.0
    assert _rvol_pts(9.67) == _rvol_pts(RVOL_TECHO)


# ── El promedio que se incluía a sí mismo ───────────────────────────────────

def test_el_dia_evaluado_no_entra_en_su_propia_media():
    """Tercer defecto, encontrado al medir. Con 20 días a 100 y hoy a 300, el
    RVOL real es 3,0; incluyendo hoy en la media el denominador sube a 110 y
    sale 2,73 -- el día anómalo disimula su propia anomalía. Mismo fallo ya
    corregido dos veces: alertas de Watchlist y _vol_ratio_desde_serie."""
    vols = pd.Series([100.0] * RVOL_WINDOW + [300.0])
    assert _rvol(vols) == 3.0


def test_sin_serie_suficiente_se_devuelve_normal():
    """1.0 significa «normal», y con la curva nueva vale cero puntos: no se
    regala nada por no tener datos."""
    assert _rvol(pd.Series([100.0] * 5)) == 1.0
    assert _rvol(pd.Series(dtype=float)) == 1.0
    assert _rvol_pts(_rvol(pd.Series(dtype=float))) == 0.0


def test_una_media_de_cero_no_revienta():
    vols = pd.Series([0.0] * RVOL_WINDOW + [500.0])
    assert _rvol(vols) == 1.0


# ── Hallazgo #20: grandes contra pequeñas ───────────────────────────────────
#
# Y el fallo GRANDE que salió al construirlo, que no estaba en la auditoría:
# el denominador de `pct_above_sma50` contaba los valores con PRECIO, no los
# que tienen SMA50 calculable. `rolling(50, min_periods=50)` exige 50 sesiones
# sin huecos, así que un solo día en el que la descarga no traiga a parte del
# universo deja a esos valores sin SMA50 durante las 50 sesiones siguientes:
# siguen contando abajo y nunca arriba, porque `NaN > NaN` es False.
#
# Medido el 15/08/2026 sobre el universo combinado: la amplitud marcaba
# 51,2 / 53,3 / 54,7 cuando lo real era 64,0 / 66,6 / 68,4 -- casi catorce
# puntos de menos, con el índice SUBIENDO los tres días. Ese número alimenta el
# widget de amplitud de Market, snapshot_mercado y el factor Breadth del RSU
# Algoritmo, así que no era un detalle de esta sección.

from scanner_universe import _compute_breadth_history  # noqa: E402


def _serie(dias=80, huecos_en=None, huecos_tickers=0, n=100):
    """dias de precios crecientes para n tickers; opcionalmente se borra el
    precio de `huecos_tickers` de ellos en la sesión `huecos_en` (contada
    desde el final)."""
    fechas = pd.bdate_range("2026-01-01", periods=dias)
    datos = {f"T{i:03d}": pd.Series(range(100, 100 + dias), index=fechas, dtype=float)
             for i in range(n)}
    if huecos_en is not None:
        for i in range(huecos_tickers):
            datos[f"T{i:03d}"].iloc[-huecos_en] = float("nan")
    return {t: s for t, s in datos.items()}


def test_un_hueco_de_un_dia_no_hunde_la_amplitud_50_sesiones():
    """EL FALLO. Con precios estrictamente crecientes, todos los valores están
    siempre por encima de su SMA50: la amplitud tiene que ser 100% todos los
    días, con hueco o sin él."""
    close = _serie(dias=80, huecos_en=3, huecos_tickers=40, n=100)
    hist = _compute_breadth_history(close, list(close), lookback_days=5)
    pcts = [d["pct_above_sma50"] for d in hist if d["pct_above_sma50"] is not None]
    assert pcts, "debería haber sesiones con dato"
    assert all(p == 100.0 for p in pcts), f"un hueco de datos ha hundido la amplitud: {pcts}"


def test_sin_huecos_el_resultado_no_cambia():
    """El arreglo no puede mover el caso normal, que es la inmensa mayoría."""
    close = _serie(dias=80, n=100)
    hist = _compute_breadth_history(close, list(close), lookback_days=5)
    assert all(d["pct_above_sma50"] == 100.0 for d in hist)


def test_la_amplitud_distingue_de_verdad_arriba_y_abajo():
    """Comprobación de que la métrica sigue midiendo algo: la mitad subiendo y
    la mitad bajando tiene que dar ~50%."""
    fechas = pd.bdate_range("2026-01-01", periods=80)
    close = {}
    for i in range(50):
        close[f"UP{i:02d}"]   = pd.Series(range(100, 180), index=fechas, dtype=float)
        close[f"DOWN{i:02d}"] = pd.Series(range(180, 100, -1), index=fechas, dtype=float)
    hist = _compute_breadth_history(close, list(close), lookback_days=3)
    assert all(d["pct_above_sma50"] == 50.0 for d in hist)


def test_los_dos_universos_se_calculan_por_separado():
    """Es el hallazgo #20: mezclados, una mitad tapa a la otra. La misma
    función con dos listas distintas tiene que dar dos lecturas distintas."""
    fechas = pd.bdate_range("2026-01-01", periods=80)
    grandes  = {f"G{i:02d}": pd.Series(range(100, 180), index=fechas, dtype=float) for i in range(60)}
    pequenas = {f"P{i:02d}": pd.Series(range(180, 100, -1), index=fechas, dtype=float) for i in range(60)}
    close = {**grandes, **pequenas}
    hg = _compute_breadth_history(close, list(grandes),  lookback_days=3)
    hp = _compute_breadth_history(close, list(pequenas), lookback_days=3)
    hc = _compute_breadth_history(close, list(close),    lookback_days=3)
    assert hg[-1]["pct_above_sma50"] == 100.0
    assert hp[-1]["pct_above_sma50"] == 0.0
    assert hc[-1]["pct_above_sma50"] == 50.0, "el combinado promedia y esconde las dos lecturas"


def test_lo_que_se_publica_son_dos_universos_distintos():
    """No basta con que el cálculo sepa separar: hay que comprobar QUÉ SE
    PUBLICA. Con la función correcta pero llamada dos veces con el universo
    combinado, las dos series saldrían idénticas y la brecha sería cero para
    siempre. Lo echó en falta el sabotaje."""
    from scanner_universe import _amplitudes_separadas, RUSSELL2000_TICKERS
    fechas = pd.bdate_range("2026-01-01", periods=80)
    grandes = [f"G{i:02d}" for i in range(60)]
    close = {t: pd.Series(range(100, 180), index=fechas, dtype=float) for t in grandes}
    # Los pequeños, cayendo: si se mezclaran, la brecha se diluiría
    for t in RUSSELL2000_TICKERS[:60]:
        close[t] = pd.Series(range(180, 100, -1), index=fechas, dtype=float)

    g, p = _amplitudes_separadas(close, grandes)
    assert g[-1]["pct_above_sma50"] == 100.0, "las grandes van todas arriba"
    assert p[-1]["pct_above_sma50"] == 0.0,   "las pequeñas, todas abajo"
    assert g[-1]["pct_above_sma50"] != p[-1]["pct_above_sma50"]
