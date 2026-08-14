"""
Rastreo desde Scanner de los activos en la zona baja del oscilador L3 (el
"indicador RSU" que se ve bajo el gráfico en Research).

QUÉ ZONA ES, porque hay dos números que se confunden con facilidad: la FÓRMULA
exige `línea < 25` para dar una señal de entrada, pero lo que el indicador
DIBUJA como zona de sobreventa es la franja del 10 al 20. Es esa franja la que
se rastrea aquí, y por eso el corte no es 25.

LO QUE FIJA ESTE FICHERO:

1. Un ticker SIN lectura del oscilador no entra en la zona, y la exclusión
   viene de que no hay dato -- no de que el 0 caiga fuera de la franja por
   casualidad. La distinción no es teórica: el patrón `(row.get(x) or 0)` que
   usan los otros seis filtros de este módulo convierte `None` en 0, y con la
   franja actual (10-20) eso da el MISMO resultado, así que el primer test que
   se escribió no distinguía las dos implementaciones. Lo destapó el sabotaje,
   y por eso hay un segundo test que mueve la franja para incluir el 0.

2. Los límites son cerrados por los dos lados (10 y 20 entran).

3. El lote de descarga trae `Open`. El oscilador necesita OHLC completo para su
   precio típico, y hasta el 14/08/2026 `download_batch` solo daba High/Low --
   sin esa columna el escáner no puede calcular nada.

4. Una entrada de caché escrita ANTES de que el lote trajera `Open` se trata
   como fallo de caché. Pasaría todos los filtros de validez (es de hoy, tiene
   filas de sobra, tiene HL) y serviría un OHLC incompleto.

Uso:
    cd backend
    python -m pytest tests/test_scanner_zona_l3.py -v
"""
import sys, os

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from services.scanner_service import _passes_filters, L3_ZONA_BAJA  # noqa: E402
import price_cache  # noqa: E402


ZONA = {"l3_zona_baja": True}


def _fila(fundtrend):
    return {"ticker": "X", "l3_fundtrend": fundtrend}


# ── 1. Sin lectura NO es sobreventa ─────────────────────────────────────────

def test_un_ticker_sin_lectura_no_cuenta_como_zona_baja():
    assert _passes_filters(_fila(None), ZONA) is False


def test_la_exclusion_viene_de_no_haber_dato_no_de_que_el_cero_caiga_fuera():
    """Con la franja actual (10-20) este test parecería redundante, y ahí
    estaba la trampa: el patrón habitual del módulo, `(row.get(x) or 0)`,
    convierte `None` en 0... y 0 queda fuera de 10-20 por casualidad, así que
    da el mismo resultado y ningún test lo distinguía. Lo destapó el sabotaje.

    Aquí se mueve la franja para que incluya el 0. Si la exclusión viniera de
    que 0 está fuera y no de que NO HAY DATO, un ticker sin lectura pasaría a
    contarse como sobreventa extrema."""
    import services.scanner_service as S
    original = S.L3_ZONA_BAJA
    S.L3_ZONA_BAJA = (0.0, 20.0)
    try:
        assert _passes_filters(_fila(None), ZONA) is False, (
            "sin lectura NO puede contar como zona baja, caiga donde caiga el 0")
        assert _passes_filters(_fila(0.0), ZONA) is True, (
            "con la franja movida, un 0 real sí entra -- el test compara contra esto")
    finally:
        S.L3_ZONA_BAJA = original


def test_un_campo_ausente_tampoco_cuenta():
    """Un ticker escaneado antes de que existiera esta columna no trae la
    clave siquiera."""
    assert _passes_filters({"ticker": "X"}, ZONA) is False


# ── 2. Los límites de la franja ─────────────────────────────────────────────

@pytest.mark.parametrize("valor,dentro", [
    (9.9,  False),
    (10.0, True),    # el borde inferior entra
    (14.4, True),
    (20.0, True),    # el borde superior entra
    (20.1, False),
    (0.0,  False),   # muy sobrevendido, pero POR DEBAJO de la franja dibujada
    (24.0, False),   # por debajo del umbral de señal (25) y aun así fuera
    (87.0, False),
])
def test_los_bordes_de_la_franja(valor, dentro):
    assert _passes_filters(_fila(valor), ZONA) is (dentro)


def test_la_franja_es_la_dibujada_no_el_umbral_de_la_senal():
    """25 es lo que la fórmula exige para dar entrada; 10-20 es lo que el
    indicador pinta. Si alguien iguala los dos, este test cae."""
    assert L3_ZONA_BAJA == (10.0, 20.0)


def test_sin_el_criterio_activo_no_se_filtra_por_el_oscilador():
    """El filtro es opcional, como los otros seis: sin activarlo, un ticker sin
    lectura sigue apareciendo en el escáner con el resto de sus columnas."""
    assert _passes_filters(_fila(None), {}) is True
    assert _passes_filters(_fila(87.0), {}) is True


# ── 3. El lote de descarga trae el Open que el oscilador necesita ───────────

def test_el_lote_declara_open_entre_sus_columnas():
    """Contrato entre shared/yf_batch.py y shared/price_cache.py. Si allí se
    deja de traer `Open`, el escáner se queda sin oscilador."""
    assert "Open" in price_cache._COLUMNAS_HL
    assert {"High", "Low"}.issubset(price_cache._COLUMNAS_HL)


# ── 4. Una caché vieja no puede servir un OHLC incompleto ──────────────────

def _escribir_cache(tmp_path, hl):
    import pickle
    ticker = "ZZZ"
    entrada = {"fecha": price_cache._fecha_hoy(),
               "close": pd.Series(range(300), dtype=float),
               "vol":   pd.Series(range(300), dtype=float),
               "hl":    hl}
    with open(price_cache._ruta(str(tmp_path), ticker), "wb") as f:
        pickle.dump(entrada, f)
    return ticker


def test_una_entrada_cacheada_sin_open_se_trata_como_fallo_de_cache(tmp_path):
    """Es de hoy, tiene filas de sobra y tiene HL: pasa todos los filtros de
    validez que había. Pero sin `Open` el oscilador no se puede calcular."""
    vieja = pd.DataFrame({"High": pd.Series(range(300), dtype=float),
                          "Low":  pd.Series(range(300), dtype=float)})
    tk = _escribir_cache(tmp_path, vieja)
    assert price_cache.leer(str(tmp_path), tk, 200, True, True) is None


def test_una_entrada_cacheada_con_open_si_sirve(tmp_path):
    """El contraste que da sentido al test anterior: con las tres columnas, la
    caché cumple su función y evita volver a descargar."""
    nueva = pd.DataFrame({"Open": pd.Series(range(300), dtype=float),
                          "High": pd.Series(range(300), dtype=float),
                          "Low":  pd.Series(range(300), dtype=float)})
    tk = _escribir_cache(tmp_path, nueva)
    leido = price_cache.leer(str(tmp_path), tk, 200, True, True)
    assert leido is not None
    assert "Open" in leido[2].columns
