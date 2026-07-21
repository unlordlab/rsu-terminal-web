"""
time_utils.py -- timestamp de "última actualización" compartido entre todos
los servicios del backend. Fase transversal del Roadmap, 21/07/2026.

Antes cada servicio hacía datetime.now().strftime('%H:%M:%S') (hora naive
del contenedor, UTC) o, en algunos casos, un offset CET fijo que ignora el
horario de verano -- ambos van desfasados respecto a la hora real de España
buena parte del año. ZoneInfo con el nombre de la zona gestiona el cambio
de horario automáticamente.
"""
from datetime import datetime
from zoneinfo import ZoneInfo


def get_timestamp() -> str:
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime('%H:%M:%S')
