"""
Tests del track record (services/track_record_service.py, 28/07/2026).

Fase 4.1 del roadmap. Lo que protegen estos tests es, sobre todo, la
HONESTIDAD de los agregados — que es la única razón de que la página exista:

  1. `n` se devuelve siempre. Una media sin su tamaño de muestra no es
     interpretable, y es justo lo que hace creíble un track record inflado.
  2. Muestra vacía -> None, no 0. Un "0.00%" en la interfaz se lee como
     "salió plano", no como "no hay datos" — mismo criterio anti-fabricación
     que se aplicó al resto de la terminal (fallbacks eliminados, sesión 12).
  3. `fiable` marca las muestras pequeñas en vez de esconderlas.
  4. Los None (horizontes aún no cumplidos) no cuentan como observaciones ni
     arrastran la media.

Uso:
    cd backend
    python -m pytest tests/test_track_record.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.track_record_service import _stats, MIN_MUESTRA_FIABLE  # noqa: E402


def test_muestra_vacia_no_devuelve_ceros():
    s = _stats([])
    assert s["n"] == 0
    assert s["media"] is None, "Sin datos debe ser None, nunca 0 (se leería como 'salió plano')"
    assert s["mediana"] is None and s["pct_positivas"] is None
    assert s["fiable"] is False


def test_solo_none_es_lo_mismo_que_vacia():
    # Horizontes aún no cumplidos: llegan como None y no son observaciones.
    assert _stats([None, None, None])["n"] == 0


def test_los_none_no_arrastran_la_media():
    con_none = _stats([10.0, None, 20.0, None])
    sin_none = _stats([10.0, 20.0])
    assert con_none["n"] == 2
    assert con_none["media"] == sin_none["media"] == 15.0


def test_agregados_calculados_a_mano():
    s = _stats([5.0, -2.0, 3.0, 10.0, -1.0])
    assert s["n"] == 5
    assert s["media"] == 3.0            # 15 / 5
    assert s["mediana"] == 3.0          # [-2,-1,3,5,10]
    assert s["pct_positivas"] == 60.0   # 3 de 5
    assert s["mejor"] == 10.0 and s["peor"] == -2.0


def test_mediana_con_muestra_par():
    assert _stats([1.0, 2.0, 3.0, 4.0])["mediana"] == 2.5


def test_marca_las_muestras_pequenas_como_no_fiables():
    pequena = _stats([1.0] * (MIN_MUESTRA_FIABLE - 1))
    grande  = _stats([1.0] * MIN_MUESTRA_FIABLE)
    assert pequena["fiable"] is False, "Una media de pocas observaciones debe ir marcada"
    assert grande["fiable"] is True
    assert pequena["media"] is not None, "Marcada, pero NO oculta: esconderla sería peor"


def test_un_periodo_entero_en_perdidas_no_se_maquilla():
    s = _stats([-4.0, -8.0, -1.5])
    assert s["media"] < 0 and s["pct_positivas"] == 0.0
    assert s["mejor"] == -1.5, "El 'mejor' de una racha mala sigue siendo negativo"
