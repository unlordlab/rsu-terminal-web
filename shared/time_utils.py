"""
time_utils.py -- timestamp de "última actualización" compartido entre todos
los servicios del backend. Fase transversal del Roadmap, 21/07/2026.

Antes cada servicio hacía datetime.now().strftime('%H:%M:%S') (hora naive
del contenedor, UTC) o, en algunos casos, un offset CET fijo que ignora el
horario de verano -- ambos van desfasados respecto a la hora real de España
buena parte del año. ZoneInfo con el nombre de la zona gestiona el cambio
de horario automáticamente.
"""
from datetime import datetime, time as dt_time
from zoneinfo import ZoneInfo


def get_timestamp() -> str:
    return datetime.now(ZoneInfo("Europe/Madrid")).strftime('%H:%M:%S')


_NYSE_OPEN  = dt_time(9, 30)
_NYSE_CLOSE = dt_time(16, 0)


def session_fraction_elapsed():
    """Fracción (0-1) de la sesión NYSE transcurrida ahora mismo. None si
    el mercado está cerrado (fuera de horario o fin de semana) -- ahí "hoy"
    ya es un día completo, no hace falta ajustar nada. Simplificación:
    asume acumulación lineal de volumen a lo largo de la sesión (en la
    práctica es más alto cerca de apertura/cierre, forma de "U") -- corrige
    la distorsión principal (comparar un día parcial contra un promedio de
    días completos) sin modelar la curva intradía real, que sería una
    mejora aparte. Ver hallazgo #3, auditoría Watchlist 21/07/2026.

    Vivía dentro de watchlist_service.py; se sube aquí al aparecer el
    segundo consumidor (el volumen relativo de Reddit Pulse, hallazgo #27
    de la auditoría de Market) -- mismo criterio que rsrw_engine.py o
    mcclellan.py: en cuanto un cálculo lo necesitan dos sitios, una sola
    copia, para que no puedan divergir sin que nadie se entere."""
    now_et = datetime.now(ZoneInfo("America/New_York"))
    if now_et.weekday() >= 5:
        return None
    t = now_et.time()
    if t < _NYSE_OPEN or t >= _NYSE_CLOSE:
        return None
    open_dt  = datetime.combine(now_et.date(), _NYSE_OPEN, tzinfo=now_et.tzinfo)
    close_dt = datetime.combine(now_et.date(), _NYSE_CLOSE, tzinfo=now_et.tzinfo)
    frac = (now_et - open_dt).total_seconds() / (close_dt - open_dt).total_seconds()
    return max(0.02, min(1.0, frac))  # suelo pequeño: evita dividir por ~0 justo al abrir
