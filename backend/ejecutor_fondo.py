"""
El ejecutor de hilos de la app, y un apagado que no espera sin límite a sus
hilos (Infraestructura #32).

EL CASO, 12/09/2026. El contenedor salió con `Exited (137)` —Docker lo mató—
aunque uvicorn ya había escrito «Application shutdown complete». Reproducido
el 13/09: los bucles de fondo de `routers/ws.py` y varias rutas mandan trabajo
a hilos con `run_in_executor`/`to_thread` (33 sitios, casi todos descargas de
red: yfinance, SEC, FRED...). Al apagar, `task.cancel()` suelta el `await`,
pero EL HILO SIGUE con su descarga, y Python no sale hasta que termina:
`asyncio.run` espera al ejecutor (hasta 5 minutos en 3.12) y después el
intérprete vuelve a esperar a sus hilos, sin límite. Con un trabajo de 30 s a
medias, el apagado tardó 22 s en vez de menos de uno. Docker da 10 s y luego
mata: cada despliegue se alargaba, y lo que estuviera escribiendo se cortaba
sin dejar rastro de qué era.

LO QUE HACE ESTO. La app usa un ejecutor que sabe qué función corre en cada
hilo. Al apagar se les da `ESPERA_HILOS_S` para acabar —casi siempre les
basta— y si alguno sigue, se escribe en el log QUÉ era y el proceso sale solo,
antes de que llegue el SIGKILL de Docker.

Salir con hilos a medias es exactamente lo que ya hacía el SIGKILL, así que no
se pierde nada que antes se salvara: SQLite es atómico por transacción y una
escritura cortada no deja la base a medias. Lo que sí puede pasar, igual que
antes, es un trabajo lógico incompleto (un aviso enviado y no marcado); la
diferencia es que ahora queda escrito cuál.
"""
import asyncio
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

# Docker da 10 s entre SIGTERM y SIGKILL, y en ese tiempo uvicorn también
# tiene que cerrar conexiones y la app cancelar sus trece tareas: 6 s deja
# margen para salir por nuestro pie.
ESPERA_HILOS_S = 6.0


class EjecutorVigilado(ThreadPoolExecutor):
    """ThreadPoolExecutor que recuerda qué función corre en cada trabajo
    enviado, para poder decir qué retenía el apagado."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._en_curso = {}
        self._cerrojo = threading.Lock()

    def submit(self, fn, /, *args, **kwargs):
        nombre = getattr(fn, "__qualname__", None) or getattr(fn, "__name__", None) or repr(fn)
        # functools.partial y similares: el nombre útil está en .func
        if hasattr(fn, "func"):
            nombre = getattr(fn.func, "__qualname__", nombre)
        futuro = super().submit(fn, *args, **kwargs)
        with self._cerrojo:
            self._en_curso[futuro] = (nombre, time.monotonic())
        futuro.add_done_callback(self._terminado)
        return futuro

    def _terminado(self, futuro):
        with self._cerrojo:
            self._en_curso.pop(futuro, None)

    def en_curso(self):
        """[(nombre, segundos que lleva)] de lo que aún no ha terminado."""
        ahora = time.monotonic()
        with self._cerrojo:
            return [(n, ahora - t) for f, (n, t) in self._en_curso.items() if not f.done()]


async def esperar_hilos_o_salir(ejecutor, espera_s=ESPERA_HILOS_S, salir=os._exit, log=print):
    """Espera hasta `espera_s` a que acaben los trabajos del ejecutor. Si
    alguno sigue, lo escribe y llama a `salir(0)`. Devuelve lo que seguía en
    curso (vacío si todo acabó a tiempo)."""
    # Lo que aún no había empezado ya no va a hacer falta.
    ejecutor.shutdown(wait=False, cancel_futures=True)
    limite = time.monotonic() + espera_s
    while ejecutor.en_curso() and time.monotonic() < limite:
        await asyncio.sleep(0.1)
    seguian = ejecutor.en_curso()
    if seguian:
        detalle = ", ".join(f"{n} ({s:.0f}s)" for n, s in seguian)
        log(f"[Apagado] {len(seguian)} trabajo(s) en hilos no acabaron en {espera_s:.0f}s: "
            f"{detalle} -- se sale sin esperarlos (Docker los mataría igual a los 10s)")
        sys.stdout.flush()
        sys.stderr.flush()
        salir(0)
    return seguian
