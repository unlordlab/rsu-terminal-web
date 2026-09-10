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
    if not _hay_sesion_hoy(now_et):
        return None
    t = now_et.time()
    if t < _NYSE_OPEN or t >= _NYSE_CLOSE:
        return None
    open_dt  = datetime.combine(now_et.date(), _NYSE_OPEN, tzinfo=now_et.tzinfo)
    close_dt = datetime.combine(now_et.date(), _NYSE_CLOSE, tzinfo=now_et.tzinfo)
    frac = (now_et - open_dt).total_seconds() / (close_dt - open_dt).total_seconds()
    return max(0.02, min(1.0, frac))  # suelo pequeño: evita dividir por ~0 justo al abrir


def _hay_sesion_hoy(now_et) -> bool:
    """Ni fin de semana NI FESTIVO. Hasta el 10/09/2026 solo se miraba el fin
    de semana: en un festivo entre semana (Labor Day, Good Friday…) se
    calculaba una fracción de una sesión que no existía, y el RVOL de la
    alerta dividía el volumen ENTERO de la sesión anterior por esa fracción —
    a mediodía, 2,6 veces lo normal, en un día sin bolsa."""
    if now_et.weekday() >= 5:
        return False
    try:
        from festivos_mercado import sesion_habil
        return sesion_habil(now_et.date())
    except Exception:
        return True          # sin el calendario, como antes: mejor que no avisar nunca


# ── LA CURVA REAL DEL VOLUMEN DE UNA SESIÓN ──────────────────────────────────
#
# Qué fracción del volumen del día se ha negociado al final de cada minuto de
# sesión (1 = 9:31 ET, 390 = 16:00). MEDIDA el 10/09/2026 con datos de 1
# minuto de Yahoo: mediana de 216 sesiones completas de 36 valores líquidos.
#
# POR QUÉ NO UNA RECTA. `session_fraction_elapsed()` supone que el volumen se
# reparte igual a lo largo del día, y no: la subasta de apertura mete un 4% en
# el primer minuto y a las 10:00 va el 16%, no el 7,7%. Con la recta, la alerta
# de «RVOL ≥ 2» saltaba en el 61% de las mañanas NORMALES a las 9:35 (33 días
# con RVOL final entre 0,7 y 1,3, en 12 valores). Y por la tarde se quedaba
# corta: a las 15:00 un día normal leía 0,78.
#
# Se evaluó con valores DISTINTOS de los que la construyeron, para no medir
# el acierto sobre los mismos datos con los que se ajustó.
_CURVA_VOLUMEN = {
    1: 0.0408, 6: 0.0721, 11: 0.0929, 16: 0.1133, 21: 0.1293, 26: 0.1479,
    31: 0.1670, 36: 0.1871, 41: 0.2025, 46: 0.2160, 51: 0.2318, 56: 0.2464,
    61: 0.2611, 76: 0.2994, 91: 0.3418, 106: 0.3750, 121: 0.4080, 136: 0.4366,
    151: 0.4630, 166: 0.4913, 181: 0.5155, 196: 0.5407, 211: 0.5650, 226: 0.5899,
    241: 0.6140, 256: 0.6372, 271: 0.6608, 286: 0.6858, 301: 0.7104, 316: 0.7345,
    331: 0.7632, 346: 0.7974, 361: 0.8308, 376: 0.8730, 390: 1.0,
}


def fraccion_de_volumen_esperada(now_et=None):
    """Qué parte del volumen de un día normal se habrá negociado a esta hora.

    Para comparar el volumen PARCIAL de hoy con una media de días COMPLETOS:
    `rvol = vol_hoy / (media * fraccion)`. None con el mercado cerrado, fin de
    semana o festivo: ahí «hoy» ya es un día entero y no hay nada que ajustar.

    Interpola linealmente entre los puntos medidos. Antes del primer minuto
    cerrado se usa el del primero: la subasta de apertura se imprime a las
    9:30:00, así que ese 4% ya está desde el primer segundo.

    Las sesiones de media jornada (cierre a las 13:00) no se distinguen:
    `festivos_mercado` no las conoce, y esos días la fracción sale corta.
    """
    now_et = now_et or datetime.now(ZoneInfo("America/New_York"))
    if not _hay_sesion_hoy(now_et):
        return None
    t = now_et.time()
    if t < _NYSE_OPEN or t >= _NYSE_CLOSE:
        return None
    minutos = (now_et.hour * 60 + now_et.minute + now_et.second / 60) - (9 * 60 + 30)
    puntos = sorted(_CURVA_VOLUMEN)
    if minutos <= puntos[0]:
        return _CURVA_VOLUMEN[puntos[0]]
    for a, b in zip(puntos, puntos[1:]):
        if minutos <= b:
            fa, fb = _CURVA_VOLUMEN[a], _CURVA_VOLUMEN[b]
            return fa + (fb - fa) * (minutos - a) / (b - a)
    return 1.0
