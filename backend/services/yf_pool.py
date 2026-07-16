"""
Pool de threads COMPARTIDO para todas las llamadas a yfinance/proxy en toda
la terminal (Market, Cartera, Scanner, etc.) — ver conversación 16/07/2026
sobre el bloqueo por ráfagas de conexión contra el proxy residencial de
IPRoyal.

ANTES: cada función (get_indices, get_sectors, cartera...) creaba su PROPIO
ThreadPoolExecutor con su propio max_workers. Si varias funciones se
disparaban a la vez (los 9 bucles de fondo al arrancar el contenedor, por
ejemplo), la concurrencia REAL contra el proxy era la SUMA de todos esos
workers a la vez (hasta 30-40 conexiones simultáneas) — muy por encima de
lo que la pasarela de un proxy residencial tolera en ráfaga, lo que
provocaba errores 407 en cascada.

AHORA: un único pool con un límite global. No importa cuántas funciones
distintas llamen a la vez, nunca hay más de YF_MAX_WORKERS peticiones a
yfinance en vuelo en TODA la terminal a la vez.

Uso en cada función (sustituye al `with ThreadPoolExecutor(...) as ex:`):

    from services.yf_pool import yf_executor
    futures = {yf_executor.submit(fn, item): item for item in items}
    for future in futures:
        results.append(future.result())

No usar `with yf_executor as ex:` — el pool es compartido y NO debe
cerrarse al terminar una función, o rompería a todas las demás.
"""
from concurrent.futures import ThreadPoolExecutor

# Límite global de conexiones simultáneas a yfinance/proxy en toda la app.
# Si en el futuro se sube el plan del proxy (o se migra a EODHD, que no
# tiene este problema de ráfaga), este es el único número que hay que tocar.
YF_MAX_WORKERS = 4

yf_executor = ThreadPoolExecutor(
    max_workers=YF_MAX_WORKERS,
    thread_name_prefix="yf_pool",
)