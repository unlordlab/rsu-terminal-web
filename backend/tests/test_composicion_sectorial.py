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
