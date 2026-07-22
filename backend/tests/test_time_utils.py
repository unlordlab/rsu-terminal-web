"""
Test de regresión para shared/time_utils.py::get_timestamp() -- centralizado
en la sesión 2 (commit bae8091) para eliminar 14 copias de
datetime.now().strftime(...) (hora naive del contenedor, UTC) o un offset
CET fijo que ignoraba el horario de verano. Sin freezegun (no está en
requirements-dev.txt) no se puede fijar un instante exacto de transición
CET/CEST, pero sí se puede detectar la regresión más probable: volver a
UTC naive o a un offset fijo, ambos con 1-2h de diferencia frente a Madrid.

Uso:
    cd backend
    python -m pytest tests/test_time_utils.py -v
"""
import sys
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))

from time_utils import get_timestamp  # noqa: E402


def test_get_timestamp_usa_zona_madrid_no_utc_naive():
    esperado = datetime.now(ZoneInfo("Europe/Madrid"))
    resultado = get_timestamp()

    assert re.match(r"^\d{2}:\d{2}:\d{2}$", resultado), f"Formato inesperado: {resultado}"

    h, m, s = map(int, resultado.split(":"))
    segundos_resultado = h * 3600 + m * 60 + s
    segundos_esperado  = esperado.hour * 3600 + esperado.minute * 60 + esperado.second
    delta = abs(segundos_resultado - segundos_esperado)

    # Tolera unos segundos por el tiempo de ejecución, y el borde de
    # medianoche (23:59:59 vs 00:00:01 son "iguales" en la práctica).
    assert delta <= 2 or delta >= 86398, (
        f"get_timestamp() ({resultado}) difiere de la hora de Madrid calculada "
        f"en el propio test ({esperado.strftime('%H:%M:%S')}) por más de lo "
        f"esperable -- sospecha de que volvió a ser UTC naive o un offset CET fijo."
    )
