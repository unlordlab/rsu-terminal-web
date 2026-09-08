"""Qué días NO abre la bolsa de Nueva York, calculados por regla.

POR QUÉ EXISTE, 08/09/2026. El usuario reportó que la Cartera no enseñaba
NINGÚN «HOY %», ni por posición ni el global. Reproducido con tickers reales:

    AAPL   chg=None  sin_datos_hoy=True  prev_fecha=2026-09-04
    MSFT   chg=None  sin_datos_hoy=True  prev_fecha=2026-09-04
    NVDA   chg=None  sin_datos_hoy=True  prev_fecha=2026-09-04

La causa: `_ultima_sesion_esperada()` retrocedía desde hoy saltando solo
sábados y domingos, así que el martes 08/09 esperaba que la última sesión
cerrada fuese el **lunes 07/09**... que era **Labor Day**, con la bolsa
cerrada. La última barra real era la del viernes 04/09, el guardia de «faltan
sesiones» lo tomó por un proveedor degradado y prefirió callarse: `chg` a None
y un guion en cada fila, durante una sesión en curso.

Su docstring ya avisaba —«No conoce los festivos [...] puede saltar de más y
mostrar "—" un día: es la dirección segura del error»— y esa decisión era
correcta mientras el error durase el propio festivo. Pero cae el día DESPUÉS,
con el mercado abierto, y entonces no es una precaución: es la cartera entera
sin su dato principal.

POR REGLA Y NO POR LISTA. Una lista de fechas caduca en silencio: el 1 de
enero de 2028 dejaría de funcionar sin que nadie lo note hasta que un usuario
lo reporte, que es exactamente cómo se ha llegado hasta aquí. Los festivos del
NYSE son todos calculables — nueve por calendario y Viernes Santo por la fecha
de Pascua — así que se calculan.

LO QUE ESTO NO ES. No es un calendario de mercado completo: no sabe de cierres
por duelo nacional, huracanes ni medias sesiones. Para eso haría falta una
fuente externa. Cubre lo previsible, que es el 100% de los casos que han roto
algo hasta hoy.
"""
from datetime import date, timedelta


def _pascua(anio: int) -> date:
    """Domingo de Pascua (algoritmo gregoriano anónimo).

    Hace falta solo para Viernes Santo, el único festivo del NYSE que no cae en
    una fecha fija ni en un «enésimo lunes de».
    """
    a = anio % 19
    b, c = divmod(anio, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes, dia = divmod(h + l - 7 * m + 114, 31)
    return date(anio, mes, dia + 1)


def _enesimo_lunes(anio: int, mes: int, n: int) -> date:
    """El n-ésimo lunes de ese mes (n=1 el primero)."""
    d = date(anio, mes, 1)
    d += timedelta(days=(0 - d.weekday()) % 7)     # 0 = lunes
    return d + timedelta(weeks=n - 1)


def _ultimo_lunes(anio: int, mes: int) -> date:
    """El último lunes del mes. Memorial Day."""
    d = date(anio, mes, 28) + timedelta(days=4)    # cae seguro en el mes siguiente
    d = d.replace(day=1) - timedelta(days=1)       # último día del mes
    return d - timedelta(days=(d.weekday() - 0) % 7)


def _cuarto_jueves(anio: int, mes: int) -> date:
    """Thanksgiving."""
    d = date(anio, mes, 1)
    d += timedelta(days=(3 - d.weekday()) % 7)     # 3 = jueves
    return d + timedelta(weeks=3)


def _observado(d: date) -> "date | None":
    """Dónde cae el festivo cuando la fecha fija es fin de semana.

    Sábado -> el viernes anterior. Domingo -> el lunes siguiente. Es la regla
    del NYSE, con la excepción de Año Nuevo que trata `festivos_nyse`.
    """
    if d.weekday() == 5:                            # sábado
        return d - timedelta(days=1)
    if d.weekday() == 6:                            # domingo
        return d + timedelta(days=1)
    return d


def festivos_nyse(anio: int) -> set:
    """Los días de cierre completo del NYSE ese año."""
    f = {
        _enesimo_lunes(anio, 1, 3),                 # Martin Luther King Jr.
        _enesimo_lunes(anio, 2, 3),                 # Washington / Presidents
        _pascua(anio) - timedelta(days=2),          # Viernes Santo
        _ultimo_lunes(anio, 5),                     # Memorial Day
        _enesimo_lunes(anio, 9, 1),                 # Labor Day
        _cuarto_jueves(anio, 11),                   # Thanksgiving
    }
    for fija in (date(anio, 6, 19),                 # Juneteenth
                 date(anio, 7, 4),                  # Independence Day
                 date(anio, 12, 25)):               # Navidad
        obs = _observado(fija)
        if obs:
            f.add(obs)

    # AÑO NUEVO, y su excepción. La regla general adelantaría al viernes 31 de
    # diciembre cuando el 1 de enero cae en sábado -- pero el NYSE NO cierra
    # ese 31: el festivo simplemente no se observa. En domingo sí se traslada
    # al lunes 2.
    uno = date(anio, 1, 1)
    if uno.weekday() != 5:
        f.add(_observado(uno))
    return f


def es_festivo(d: date) -> bool:
    return d in festivos_nyse(d.year)


def sesion_habil(d: date) -> bool:
    """¿Abre la bolsa ese día? Ni fin de semana ni festivo."""
    return d.weekday() < 5 and not es_festivo(d)


def sesion_anterior(d: date) -> date:
    """La última sesión hábil ESTRICTAMENTE anterior a `d`."""
    d -= timedelta(days=1)
    while not sesion_habil(d):
        d -= timedelta(days=1)
    return d
