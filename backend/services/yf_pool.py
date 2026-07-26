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

26/07/2026 — hasta esta fecha solo 2 de ~10 módulos usaban este pool
(market_service.py, cartera_service.py); el resto creaba su propio
ThreadPoolExecutor privado (CANSLIM 15, Options Flow 15, Research 10,
Earnings 8, RSU Algoritmo 5-6, Newsfeed 6, Watchlist 4, BTC Stratum 2),
sumando ~76-92 conexiones simultáneas TEÓRICAS si varios coincidían en el
tiempo -- muy por encima del techo que este fichero existe para imponer.
Migrados todos al pool compartido. De paso, el proxy residencial que
motivó el límite de 4 ya no está en uso (yfinance_proxy_url vacío por
defecto, dado de baja por coste) -- las peticiones salen directas desde la
IP del VPS, sin el colchón de IP residencial que tenía el proxy. Subido a
6 como punto de partida conservador (no hay límite publicado de Yahoo como
el de SEC EDGAR, así que es una estimación a monitorizar, no un número
verificado) -- ajustar si en producción nunca se satura, o bajarlo si
aparecen 429/403 de Yahoo.
"""
from concurrent.futures import ThreadPoolExecutor

YF_MAX_WORKERS = 6

yf_executor = ThreadPoolExecutor(
    max_workers=YF_MAX_WORKERS,
    thread_name_prefix="yf_pool",
)