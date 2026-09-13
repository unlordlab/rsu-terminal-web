"""
Infraestructura #32: el apagado no espera sin límite a los hilos de fondo.

EL CASO. `Exited (137)` el 12/09/2026 aunque uvicorn había escrito
«Application shutdown complete». Reproducido el 13/09 arrancando la app de
verdad con una tarea de la misma forma que las de routers/ws.py
(`await loop.run_in_executor(None, trabajo)`): con un trabajo de 30 s a medias,
el proceso tardó 22 s en salir tras pedir el apagado. Cancelar la tarea suelta
el `await`, pero el hilo sigue, y Python lo espera al salir. Docker da 10 s.

Después del arreglo, mismo experimento: sale a los 6 s escribiendo qué seguía
en curso; si el trabajo acaba dentro del margen, sale limpio (2,1 s).

Uso:
    cd backend
    python -m pytest tests/test_apagado_sin_esperar_hilos.py -v
"""
import asyncio
import functools
import os
import re
import sys
import threading
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ejecutor_fondo import ESPERA_HILOS_S, EjecutorVigilado, esperar_hilos_o_salir  # noqa: E402

MAIN = os.path.join(os.path.dirname(__file__), '..', 'main.py')


def trabajo_lento(evento):
    evento.wait(5)


def test_el_ejecutor_sabe_que_corre_cada_hilo():
    ej = EjecutorVigilado(max_workers=2)
    fin = threading.Event()
    try:
        ej.submit(trabajo_lento, fin)
        ej.submit(functools.partial(trabajo_lento, fin))
        time.sleep(0.1)
        nombres = sorted(n for n, _ in ej.en_curso())
        assert nombres == ["trabajo_lento", "trabajo_lento"], nombres
    finally:
        fin.set()
        ej.shutdown(wait=True)
    assert ej.en_curso() == []


def test_lo_terminado_no_se_acumula():
    # La app corre semanas enviando trabajos cada minuto: si lo terminado no se
    # olvida, el registro crece sin techo.
    ej = EjecutorVigilado(max_workers=4)
    for f in [ej.submit(time.sleep, 0) for _ in range(200)]:
        f.result()
    ej.shutdown(wait=True)
    assert len(ej._en_curso) == 0


def test_si_un_hilo_no_acaba_se_dice_cual_y_se_sale():
    ej = EjecutorVigilado(max_workers=1)
    fin = threading.Event()
    salidas, logs = [], []

    async def escenario():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ej)
        async def bucle():                   # la forma de los bucles de ws.py
            await loop.run_in_executor(None, trabajo_lento, fin)
        tarea = asyncio.create_task(bucle())
        await asyncio.sleep(0.05)
        tarea.cancel()                       # lo que hace main.py con sus tareas
        await asyncio.gather(tarea, return_exceptions=True)
        ini = time.monotonic()
        seguian = await esperar_hilos_o_salir(ej, espera_s=0.3, salir=salidas.append, log=logs.append)
        tardo = time.monotonic() - ini
        fin.set()   # en producción aquí ya se habría salido; en el test se suelta el hilo
        return seguian, tardo

    try:
        seguian, tardo = asyncio.run(escenario())
    finally:
        fin.set()
        ej.shutdown(wait=True)
    assert [n for n, _ in seguian] == ["trabajo_lento"]
    assert salidas == [0], "con un hilo colgado hay que salir, no esperarlo"
    assert 0.25 <= tardo < 1.5, tardo
    assert logs and "trabajo_lento" in logs[0]


def test_si_todo_acaba_a_tiempo_no_se_fuerza_la_salida():
    ej = EjecutorVigilado(max_workers=1)
    salidas = []

    async def escenario():
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ej)
        await loop.run_in_executor(None, time.sleep, 0.05)
        loop.run_in_executor(None, time.sleep, 0.2)   # en curso al apagar
        await asyncio.sleep(0.02)
        return await esperar_hilos_o_salir(ej, espera_s=2, salir=salidas.append, log=lambda *_: None)

    assert asyncio.run(escenario()) == []
    assert salidas == []


def test_lo_que_no_habia_empezado_no_retiene_el_apagado():
    ej = EjecutorVigilado(max_workers=1)
    fin = threading.Event()
    salidas = []
    try:
        ej.submit(trabajo_lento, fin)
        colas = [ej.submit(time.sleep, 30) for _ in range(3)]
        time.sleep(0.05)
        # El primero acaba DESPUÉS de pedir el apagado: si la cola no se
        # cancelara, empezarían los sleep(30) y retendrían la salida.
        threading.Timer(0.2, fin.set).start()
        asyncio.run(esperar_hilos_o_salir(ej, espera_s=2, salir=salidas.append, log=lambda *_: None))
        assert all(f.cancelled() for f in colas)
        assert salidas == []
    finally:
        fin.set()
        ej.shutdown(wait=True)


def test_el_margen_cabe_en_los_10s_de_docker():
    assert 2 <= ESPERA_HILOS_S <= 8


def test_main_usa_el_ejecutor_y_espera_con_limite_tras_cancelar():
    with open(MAIN, encoding='utf-8') as f:
        src = f.read()
    ini = src.index("async def lifespan")
    cuerpo = src[ini:src.index("\napp = FastAPI(", ini)]
    antes, despues = cuerpo.split("yield", 1)
    assert re.search(r"set_default_executor\(\s*ejecutor\s*\)", antes)
    assert "EjecutorVigilado(" in antes
    i_gather = despues.index("asyncio.gather(*tareas")
    i_espera = despues.index("await esperar_hilos_o_salir(ejecutor)")
    assert i_gather < i_espera, "primero cancelar las tareas, luego esperar a los hilos"

