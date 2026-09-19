"""
interanual.py -- el valor de HACE UN AÑO de una serie, buscado por FECHA.

EL CASO, 19/09/2026. El briefing y Market calculaban el interanual de las
series mensuales con «la observación 12 (o 13) posiciones atrás». En octubre de
2025 el IPC no se publicó y FRED no tiene ese mes, así que doce posiciones
atrás era JULIO de 2025, no agosto: se comparaban trece meses. Medido contra
FRED ese día: IPC general 3,71% publicado frente a 3,35% real, IPC subyacente
2,76% frente a 2,45%, y los briefings llevaban semanas citando esas cifras.
Las series sin hueco (PCE, ventas minoristas, producción industrial) daban
igual por los dos caminos, que es por lo que no se veía.

Sin el dato del mismo mes del año anterior no hay interanual: se devuelve None,
nunca el vecino más cercano de una serie mensual.

NO depende de nada de backend/: lo usan el backend y los scripts del Action.
"""
from datetime import date, datetime, timedelta


def _a_fecha(valor):
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    return datetime.strptime(str(valor)[:10], "%Y-%m-%d").date()


def _un_ano_antes(f: date) -> date:
    try:
        return f.replace(year=f.year - 1)
    except ValueError:               # 29 de febrero
        return f.replace(year=f.year - 1, day=28)


def valor_hace_un_ano(pares, fecha=None, tolerancia_dias: int = 0):
    """Valor de la serie un año antes de `fecha` (por defecto, la última).

    `pares` es una lista de (fecha, valor) en cualquier orden. Con
    `tolerancia_dias=0` (series mensuales) la fecha tiene que existir tal cual;
    con tolerancia (series semanales) vale la observación más cercana ANTERIOR
    o igual dentro de ese margen. None si no hay."""
    datos = {}
    for f, v in pares or []:
        try:
            datos[_a_fecha(f)] = v
        except (TypeError, ValueError):
            continue
    if not datos:
        return None
    referencia = _a_fecha(fecha) if fecha is not None else max(datos)
    objetivo = _un_ano_antes(referencia)
    if objetivo in datos:
        return datos[objetivo]
    if tolerancia_dias <= 0:
        return None
    candidatas = [f for f in datos if objetivo - timedelta(days=tolerancia_dias) <= f <= objetivo]
    return datos[max(candidatas)] if candidatas else None


def variacion_interanual(pares, fecha=None, tolerancia_dias: int = 0):
    """% de variación frente a hace un año, o None."""
    datos = {}
    for f, v in pares or []:
        try:
            datos[_a_fecha(f)] = v
        except (TypeError, ValueError):
            continue
    if not datos:
        return None
    referencia = _a_fecha(fecha) if fecha is not None else max(datos)
    actual = datos.get(referencia)
    antes = valor_hace_un_ano(pares, referencia, tolerancia_dias)
    if actual is None or not antes:
        return None
    return (actual / antes - 1) * 100
