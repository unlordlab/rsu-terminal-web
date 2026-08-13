"""market_calendar.py -- qué sesión de mercado toca, según el reloj y nada más.

Vive en shared/ y no dentro de un servicio concreto por el mismo criterio que
ya aplican rsrw_engine.py, mcclellan.py o time_utils.py: en cuanto un cálculo
lo necesitan dos sitios, una sola copia, para que no puedan divergir sin que
nadie se entere. Nació en `cartera_service` para el «HOY %» de la cartera, y
la barra superior de Market (`backend/routers/ws.py`) necesita exactamente el
mismo criterio. Duplicarlo era garantizar que un día se arreglara en un sitio
y no en el otro -- que es literalmente la historia de este bug: el mismo
patrón se corrigió tres veces en Cartera (11, 12 y 13/08/2026) mientras seguía
intacto en la barra superior.

Es hermano de time_utils.py y la frontera entre los dos es: allí, QUÉ HORA es
dentro de la sesión (timestamp de "última actualización", fracción de sesión
transcurrida); aquí, QUÉ DÍA de sesión es -- que es lo que hace falta para
comprobar si una barra diaria es la que dice ser.

POR QUÉ EL RELOJ Y NO LOS DATOS. Se podría deducir el calendario a partir de
las propias barras (si diez símbolos traen barra del martes, el martes fue
sesión). Es tentador y resuelve los festivos gratis, pero se rompe justo en
el caso contra el que existe esta comprobación: cuando el proveedor está
degradado y le faltan sesiones a TODOS los símbolos a la vez, el «calendario»
deducido pierde esa sesión también, la comprobación se da por satisfecha y se
desactiva sola en silencio. El reloj no lo puede corromper el proveedor, así
que es el único árbitro que sigue siendo válido cuando los datos fallan.
"""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def ultima_sesion_esperada() -> "object":
    """Qué sesión de mercado debería ser la última con datos, ahora mismo.

    Retrocede desde hoy (Nueva York) saltando sábados y domingos, y si el
    mercado aún no ha cerrado hoy, retrocede un día más: durante la sesión
    en curso la última barra COMPLETA sigue siendo la de ayer. No conoce
    los festivos, y por eso el llamador da un día de margen antes de gritar
    -- vale más callarse el 4 de julio que avisar en falso cada festivo."""
    d = datetime.now(ZoneInfo("America/New_York"))
    dia = d.date()
    if not (d.hour > 16 or (d.hour == 16 and d.minute >= 5)):
        dia -= timedelta(days=1)
    while dia.weekday() >= 5:          # 5 sábado, 6 domingo
        dia -= timedelta(days=1)
    return dia


def sesion_anterior_a(dia):
    """La sesión inmediatamente anterior a `dia`, saltando el fin de semana.

    Es la pieza que permite preguntar lo que de verdad importa al calcular una
    variación diaria: «este cierre de referencia, ¿es el de la sesión anterior
    o el de hace tres?». Sin ella solo se puede comprobar que existan dos
    barras, que es exactamente la suposición que falla.

    Tampoco conoce los festivos: el martes siguiente a un lunes festivo dirá
    «lunes» cuando la sesión anterior real fue el viernes. El llamador se come
    ahí un falso positivo -- enseñar «—» en vez de un porcentaje, un día al
    año y pico -- y esa es la dirección segura del error."""
    d = dia - timedelta(days=1)
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def dia_anterior_a(dia):
    """La misma idea para lo que cotiza los siete días (cripto): ahí no hay
    fin de semana que saltar, y aplicarle el calendario bursátil haría que
    cada lunes se descartara un dato perfectamente bueno."""
    return dia - timedelta(days=1)


def cotiza_todos_los_dias(ticker: str) -> bool:
    """Cripto cotiza sábados y domingos; el resto de lo que hay en la barra
    superior (índices, forex, materias primas, acciones) no."""
    return str(ticker).upper().endswith("-USD")
