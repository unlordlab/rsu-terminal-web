"""
Una sesión de amplitud calculada sobre 24 valores no es un día flojo: es un
dato que no existe.

EL CASO, 02/09/2026. El escaneo nocturno publicó la sesión del 02/09 con **24
valores** (20 avances / 4 descensos) en vez de los ~2.380 de las once
sesiones anteriores, y el desglose del S&P 500 con **1** en vez de ~495.

EL MECANISMO, encontrado el 04/09 leyendo `_compute_breadth_history`:
`pd.DataFrame(cols)` UNE los índices de todos los tickers. Si 24 ya tienen
barra del día y los otros ~2.360 todavía no, pandas crea una fila para ese día
con NaN en casi todas las columnas. Y entonces:

    advances = (diff > 0).sum(axis=1)      <- recuento CRUDO de todas las columnas
    pct_above = above.sum(axis=1) / valid_cnt   <- este SÍ divide por los válidos

`pct_above_sma50` es inmune porque divide por los que tienen dato — un arreglo
del 15/08/2026. `advances`, `declines`, `new_highs` y `new_lows`, tres líneas
más abajo, se quedaron como recuentos crudos. El mismo arreglo aplicado a un
indicador y no a sus vecinos.

NO ES UN PROBLEMA DE HORARIO: ese escaneo arrancó a las 00:16 UTC del 03/09,
o sea 20:16 ET del 02/09, tres horas después del cierre. La descarga volvió
parcial y el código la publicó como una sesión normal.

POR QUÉ VIVE AQUÍ Y NO EN UN SOLO SITIO. La amplitud la consumen cuatro
sitios: el escáner que la produce, `market_service` (el McClellan y la línea
A-D de Market), `rsu_algoritmo_service` (el factor Breadth) y el briefing
diario. La regla se escribió primero en `daily_briefing.py` y protegía solo al
briefing; en cuanto se vio el alcance, el sitio correcto era el origen y una
casa común, no una copia por consumidor -- que es como se acaba con dos
definiciones del mismo umbral contradiciéndose (ver Scanner #6).
"""

FRACCION_MINIMA = 0.5


def _mediana(valores):
    v = sorted(x for x in valores if x)
    if not v:
        return None
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2


def cobertura_insuficiente(total_ultima, totales_previos, fraccion=FRACCION_MINIMA):
    """¿La última sesión cubre bastantes valores para creerla?

    Se compara con la MEDIANA de las sesiones anteriores en vez de con un
    número fijo: el universo cambia de tamaño (entradas y salidas del índice) y
    un umbral escrito a mano se queda obsoleto en silencio. La mediana aguanta
    además que alguna sesión previa también viniera rota, cosa que una media no.

    Sin historial previo NO se descarta nada: el primer día no hay con qué
    comparar, y descartar por defecto dejaría sin amplitud a quien la pide.

    Devuelve (esta_rota, total, esperado)."""
    mediana = _mediana(totales_previos or [])
    if mediana is None or not total_ultima:
        return (False, total_ultima, None)
    return (total_ultima < mediana * fraccion, total_ultima, mediana)


def sesiones_con_cobertura(historial, clave="total_valores", fraccion=FRACCION_MINIMA):
    """Filtra un historial de amplitud dejando fuera las sesiones truncadas.

    `clave` es el campo con el número de valores que entraron en esa sesión. Si
    no está (historiales escritos antes de que se guardara), se cae a
    advances+declines, que es lo que se podía deducir del caso del 02/09.

    Devuelve (buenas, descartadas)."""
    filas = [h for h in (historial or []) if isinstance(h, dict)]

    def _total(h):
        v = h.get(clave)
        if v is not None:
            return v
        return (h.get("advances") or 0) + (h.get("declines") or 0)

    totales = [_total(h) for h in filas]
    mediana = _mediana(totales)
    if mediana is None:
        return filas, []
    minimo = mediana * fraccion
    buenas = [h for h, t in zip(filas, totales) if t >= minimo]
    malas = [h for h, t in zip(filas, totales) if t < minimo]
    return buenas, malas
