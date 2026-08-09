"""
Test del scoring de prima de Options Flow (hallazgo #9).

QUÉ ESTABA ROTO. La mitad de prima de _score_entry comparaba la prima
contra la MEDIA de las entradas guardadas del ticker y pedía 5x esa media
para la puntuación máxima. Pero esa media se calcula sobre entradas que YA
pasaron el filtro, o sea que ya son de las grandes -- así que pedir 5x
ponía el techo por encima de lo que el ticker había registrado nunca.
Medido sobre los datos reales el 08/08: **15 de 16 tickers con historial
no podían sacar los 4 puntos ni con su mejor operación jamás vista**, y el
60,4% de las filas se quedaba en 0 puntos por prima.

QUÉ FIJA ESTE FICHERO. Que la escala sea ALCANZABLE: la mejor entrada de
un ticker tiene que poder llegar al tope, y una entrada mediana tiene que
caer en medio. Es la propiedad que el criterio viejo no cumplía y la que
se rompería si alguien volviera a un ratio contra la media.

LO QUE NO SE CORRIGE, A PROPÓSITO: un ticker con historial sigue puntuando
por debajo de lo que sacaría el mismo importe sin historial. Eso es la
función, no el defecto -- que $3M en un valor donde $3M es rutina no se lea
igual que $3M en uno donde no pasa nunca. Lo que se arregló es que el techo
fuera inalcanzable, no que el ajuste exista.

Uso:
    cd backend
    python -m pytest tests/test_options_scoring.py -v
"""
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.options_service import _score_entry, _percentil  # noqa: E402


# Histórico sintético de un ticker: 10 primas de 1M a 10M. Sirve para saber
# exactamente en qué percentil cae cada valor sin depender de datos reales.
HISTORICO = [float(n) * 1_000_000 for n in range(1, 11)]


def _baseline(valores):
    return {
        "avg_premium": sum(valores) / len(valores) if valores else None,
        "premium_values": sorted(valores),
        "iv_values": [],
    }


# Argumentos neutros para todo lo que no es la prima, para que las
# diferencias de score vengan solo de la mitad que se está probando.
def _score(premium, baseline):
    score, _, _ = _score_entry(
        vol=0, oi=0, premium=premium, iv=0.0, exp_days=1,
        strike_pct_val=100.0, baseline=baseline,
    )
    return score


def test_el_percentil_ordena_y_llega_a_los_extremos():
    assert _percentil(500_000, HISTORICO) == 0.0
    assert _percentil(10_000_000, HISTORICO) == 100.0
    assert _percentil(5_000_000, HISTORICO) == 50.0
    assert _percentil(1_000_000, HISTORICO) is not None


def test_sin_historico_no_hay_percentil_que_calcular():
    """Ni se inventa un 50 ni se asume nada: el llamador cae al umbral
    absoluto, que es el comportamiento correcto para un ticker nuevo."""
    assert _percentil(1_000_000, []) is None
    assert _percentil(None, HISTORICO) is None


def test_la_mejor_entrada_de_un_ticker_alcanza_el_tope():
    """LA PROPIEDAD QUE ESTABA ROTA. Con el criterio viejo (5x la media) el
    máximo de este histórico -- 10M contra una media de 5,5M, ratio 1,8 --
    solo sacaba 2 de los 4 puntos. Su mejor operación no podía llegar al
    tope ni siendo la mejor."""
    b = _baseline(HISTORICO)
    tope    = _score(10_000_000, b)
    mediana = _score(5_000_000, b)
    minimo  = _score(1_000_000, b)
    assert tope > mediana > minimo, f"tope={tope} mediana={mediana} minimo={minimo}"
    # 4 puntos de prima es el máximo del componente; el resto de argumentos
    # son neutros, así que el score total tiene que reflejarlo.
    assert tope - minimo == 4


def test_una_entrada_mediana_cae_en_medio_de_la_escala():
    b = _baseline(HISTORICO)
    assert _score(5_000_000, b) - _score(1_000_000, b) == 2


def test_el_techo_no_depende_de_la_escala_del_ticker():
    """Un ticker que mueve millones y otro que mueve miles llegan igual a su
    propio tope. Con el ratio contra la media, en cambio, alcanzarlo dependía
    de cómo de dispersa fuera la distribución de cada uno."""
    grande  = _baseline([float(n) * 1_000_000 for n in range(1, 11)])
    pequeno = _baseline([float(n) * 10_000 for n in range(1, 11)])
    assert _score(10_000_000, grande) == _score(100_000, pequeno)


def test_sin_baseline_se_usa_el_umbral_absoluto():
    """El camino de los tickers sin historial no se toca: sigue puntuando
    por importe absoluto, que es lo único que se puede hacer sin referencia
    propia."""
    vacio = {"avg_premium": None, "premium_values": [], "iv_values": []}
    assert _score(2_000_000, vacio) - _score(50_000, vacio) == 4
    assert _score(500_000, vacio) - _score(50_000, vacio) == 2


def test_un_baseline_antiguo_sin_premium_values_no_rompe():
    """Retrocompatibilidad: si algún camino construye el dict a la vieja
    usanza (solo avg_premium e iv_values), se cae al umbral absoluto en vez
    de lanzar KeyError."""
    viejo = {"avg_premium": 5_000_000, "iv_values": []}
    assert _score(2_000_000, viejo) == _score(2_000_000,
                                              {"avg_premium": None, "premium_values": [], "iv_values": []})
