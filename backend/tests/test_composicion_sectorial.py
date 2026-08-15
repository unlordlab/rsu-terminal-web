"""
Composición sectorial: cestas pequeñas, nombres muertos y unidades.

EL FALLO, medido el 15/08/2026 sobre el scan real. El ranking lo encabezaba
STORAGE con un 91,9 y **tres valores**, y PHOTONICS era tercera con cuatro:

     1  STORAGE     N=3   91,9
     2  CYBER       N=14  84,0
     3  PHOTONICS   N=4   82,7

No es que el almacenamiento fuera el sector más fuerte del mercado: promediar
tres percentiles tiene una varianza enorme, así que las cestas diminutas ocupan
los extremos del ranking —arriba y abajo— por aritmética, no por fuerza real.

Y tenían tres y cuatro porque **13 tickers habían dejado de cotizar** y se
caían en silencio: STORAGE definía 5 (PSTG fuera), PHOTONICS definía 6 (INFN y
NPTN, esta última comprada por Lumentum en 2022). La cesta encogía sin que
nada lo dijera.

LO QUE FIJA ESTE FICHERO:
1. Ninguna cesta baja del mínimo, salvo MAG7, que son siete por definición.
2. Los 13 muertos no vuelven.
3. La respuesta lleva cuántos valores se definieron y cuántos faltan.
4. El momentum viaja en porcentaje, y el puente con el Gist viejo funciona en
   los dos sentidos sin doblar el número.

Uso:
    cd backend
    python -m pytest tests/test_composicion_sectorial.py -v
"""
import sys, os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from thematic_scan import THEMATIC_SECTORS  # noqa: E402
from services.thematic_service import _normalizar  # noqa: E402


# Verificados uno a uno el 15/08/2026: ninguno devuelve un solo dato en dos
# años, ni siquiera histórico.
MUERTOS = {'BITF', 'BLUE', 'CYBR', 'FI', 'FOLD', 'INFN', 'IRBT', 'K',
           'NPTN', 'PSTG', 'TERN', 'VERV', 'X'}

MINIMO = 9
# MAG7 son los siete magníficos: no se puede engordar sin dejar de ser lo que es.
EXCEPCIONES = {"MAG7"}


def test_ninguna_cesta_es_demasiado_pequena_para_promediar():
    flacas = {n: len(v) for n, v in THEMATIC_SECTORS.items()
              if n not in EXCEPCIONES and len(v) < MINIMO}
    assert not flacas, f"cestas por debajo de {MINIMO}: {flacas}"


def test_los_tickers_muertos_no_vuelven():
    vivos = {t for v in THEMATIC_SECTORS.values() for t in v}
    assert not (vivos & MUERTOS), f"han vuelto: {sorted(vivos & MUERTOS)}"


def test_no_hay_tickers_repetidos_dentro_de_una_misma_cesta():
    """Un duplicado pesaría doble en la media de esa cesta sin que se vea."""
    repes = {n: [t for t in set(v) if v.count(t) > 1]
             for n, v in THEMATIC_SECTORS.items() if len(v) != len(set(v))}
    assert not repes, f"duplicados: {repes}"


# ── El puente con el Gist viejo ─────────────────────────────────────────────

def test_una_fraccion_del_gist_viejo_se_convierte_a_porcentaje():
    """El Gist solo se reescribe una vez al día: entre el despliegue y ese
    scan, el backend lee el formato viejo. Sin esto la pantalla mostraría
    «0%» en todas las cestas hasta la noche."""
    assert _normalizar({"avg_momentum": 0.43})["avg_momentum"] == 43


def test_un_porcentaje_del_gist_nuevo_no_se_vuelve_a_multiplicar():
    assert _normalizar({"avg_momentum": 43})["avg_momentum"] == 43


def test_el_cero_y_el_cien_no_se_confunden_entre_formatos():
    """0 es 0 en los dos formatos. Y 1 se lee como fracción -- es el único
    valor ambiguo, y equivocarse ahí da 100%, que en fracción SÍ significa
    «toda la cesta acelerando». Coincide, así que no hay caso perdido."""
    assert _normalizar({"avg_momentum": 0})["avg_momentum"] == 0
    assert _normalizar({"avg_momentum": 1})["avg_momentum"] == 100
    assert _normalizar({"avg_momentum": 100})["avg_momentum"] == 100


def test_sin_momentum_no_se_inventa_un_cero():
    assert _normalizar({"avg_momentum": None})["avg_momentum"] is None


def test_el_gist_viejo_recibe_los_campos_nuevos_sin_mentir():
    """Un Gist anterior al cambio no sabe cuántos valores se definieron. Se
    rellena con los que hay y `faltan: 0` -- así el frontend no pinta un aviso
    de nombres perdidos que no puede confirmar."""
    f = _normalizar({"sector": "SEMIS", "basket": 25, "avg_momentum": 0.3})
    assert f["definidos"] == 25 and f["faltan"] == 0


def test_el_gist_nuevo_conserva_lo_que_trae():
    f = _normalizar({"sector": "STORAGE", "basket": 8, "definidos": 10,
                     "faltan": 2, "avg_momentum": 50})
    assert (f["definidos"], f["faltan"], f["avg_momentum"]) == (10, 2, 50)


# ── La amplitud de liderazgo ────────────────────────────────────────────────

from thematic_scan import _amplitud_ponderada  # noqa: E402


def _serie(valores):
    import pandas as pd
    return pd.Series(valores, dtype=float)


def test_una_cesta_sin_ningun_lider_marca_cero():
    """Es la diferencia entera con la media. MAG7 medía 48,4 -- por encima de
    la mitad de la tabla -- con CERO nombres en el 20% superior. Preguntando
    «¿dónde está el liderazgo?», la respuesta correcta es cero."""
    assert _amplitud_ponderada(_serie([69, 60, 55, 40])) == 0.0


def test_todos_en_el_diez_por_ciento_superior_es_cien():
    assert _amplitud_ponderada(_serie([95, 92, 99, 90])) == 100.0


def test_los_escalones_pesan_distinto():
    """Un nombre en el 10% superior vale el triple que uno que solo llega al
    30%: si pesaran igual, la métrica no distinguiría liderar de acompañar."""
    arriba = _amplitud_ponderada(_serie([95, 95, 95, 95]))
    medio  = _amplitud_ponderada(_serie([85, 85, 85, 85]))
    abajo  = _amplitud_ponderada(_serie([75, 75, 75, 75]))
    assert arriba > medio > abajo > 0
    assert (arriba, medio, abajo) == (100.0, 66.7, 33.3)


def test_la_amplitud_es_una_proporcion_y_por_tanto_ciega_al_tamano():
    """LÍMITE CONOCIDO DE LA MÉTRICA, y está aquí escrito a propósito.

    Dos estrellas de tres nombres empatan exactamente con diez nombres todos
    en el 20% superior: los dos casos alcanzan dos tercios del liderazgo
    posible. La amplitud mide QUÉ PROPORCIÓN del liderazgo posible alcanza la
    cesta, no cuánta evidencia hay detrás.

    Se deja así a propósito -- es lo que la hace explicable ("de 0 a 100, cuánto
    del liderazgo posible alcanza") -- y quien protege del caso degenerado es el
    mínimo de nombres por cesta, que tiene su propio test arriba: con 9 valores
    como suelo, el caso «tres nombres, dos disparados» no puede darse.

    Lo destapó el sabotaje al escribir este fichero, comprobando que
    _amplitud_ponderada([99,98,20]) == _amplitud_ponderada([85]*10) == 66,7."""
    pequena = _serie([99, 98, 20])
    grande  = _serie([85] * 10)
    assert _amplitud_ponderada(pequena) == _amplitud_ponderada(grande) == 66.7


def test_lo_que_si_resuelve_la_amplitud_frente_a_la_media():
    """El caso real que la motivó. Una cesta con media alta pero sin ningún
    líder pierde contra una de media más baja y liderazgo repartido -- con la
    media pasaba justo al revés."""
    sin_lideres = _serie([69, 68, 67, 66, 65, 64, 63, 62, 61])   # media 65,0
    con_lideres = _serie([95, 92, 30, 25, 20, 88, 15, 10, 12])   # media 43,0
    assert _amplitud_ponderada(sin_lideres) == 0.0
    assert _amplitud_ponderada(con_lideres) > 0
    import statistics
    assert statistics.mean([69, 68, 67, 66, 65, 64, 63, 62, 61]) > \
           statistics.mean([95, 92, 30, 25, 20, 88, 15, 10, 12]), \
        "la media las ordenaba al revés: ese es el punto"


def test_un_solo_rezagado_no_borra_el_liderazgo_del_resto():
    """No es un todo-o-nada: la métrica es proporcional, no un umbral."""
    a = _amplitud_ponderada(_serie([95] * 9 + [10]))
    assert 80 < a < 100


def test_sin_datos_no_devuelve_cero(  ):
    """Un 0 significa «ninguno es líder», que es una afirmación. Sin datos no
    se puede afirmar eso."""
    assert _amplitud_ponderada(_serie([])) is None
    assert _amplitud_ponderada(None) is None


def test_la_tabla_se_ordena_por_amplitud_no_por_media():
    """Con la fórmula correcta pero ordenando por media, la tabla seguiría
    mintiendo igual -- y ningún test sobre _amplitud_ponderada lo detectaría.
    Lo echó en falta el sabotaje, y por eso la ordenación es una función
    aparte que se puede probar."""
    from thematic_scan import _ordenar_por_amplitud
    cestas = [
        {"sector": "MEDIA_ALTA_SIN_LIDERES", "avg_score": 67.0, "breadth": 2.4},
        {"sector": "MEDIA_BAJA_CON_LIDERES", "avg_score": 42.2, "breadth": 20.0},
        {"sector": "SIN_DATOS",              "avg_score": None, "breadth": None},
    ]
    scored, empty = _ordenar_por_amplitud(cestas)
    assert [c["sector"] for c in scored] == ["MEDIA_BAJA_CON_LIDERES", "MEDIA_ALTA_SIN_LIDERES"]
    assert scored[0]["rank"] == 1 and scored[1]["rank"] == 2
    assert [c["sector"] for c in empty] == ["SIN_DATOS"]
    assert empty[0]["rank"] is None, "sin datos no se le pone puesto"


def test_el_empate_en_amplitud_lo_rompe_la_media():
    """Dos cestas pueden alcanzar la misma proporción de liderazgo sin ser
    igual de fuertes por debajo."""
    from thematic_scan import _ordenar_por_amplitud
    scored, _ = _ordenar_por_amplitud([
        {"sector": "FLOJA", "avg_score": 40.0, "breadth": 30.0},
        {"sector": "SOLIDA", "avg_score": 65.0, "breadth": 30.0},
    ])
    assert [c["sector"] for c in scored] == ["SOLIDA", "FLOJA"]
