"""
senales_service.py -- qué le ha pasado HOY a cada valor, según la propia
terminal.

POR QUÉ EXISTE. Hasta ahora una alerta solo podía vigilar precio, RVOL o el
toque de una EMA: cosas que cualquier bróker ya avisa. Lo que la terminal
calcula cada noche y NO avisaba a nadie es justo lo suyo — el cambio de fase de
Weinstein, la entrada en el grupo de líderes por fuerza relativa, la pérdida de
la media de 50, el máximo de 52 semanas. Esto pone esos hechos en un sitio
común, y de ahí beben las alertas de señal (Watchlist #18) y el digest diario
(#20): son la misma pieza vista de dos formas, una al momento y otra resumida.

DE DÓNDE SALEN. De `snapshot_ticker`, la foto que la terminal ya guarda de ~500
valores cada sesión. Una señal es la DIFERENCIA entre las dos últimas fotos, así
que no se calcula nada nuevo ni se pide nada a la red: se restan dos filas.

SON SEÑALES DIARIAS, y eso hay que decirlo donde se enseñen: salen del escaneo
nocturno, así que llegan con la sesión cerrada, no en el momento en que ocurren.
"""
from services.snapshots_service import fechas_snapshot_ticker, _conn

# El corte de líder es el MISMO que usa RS/RW en su tabla y en sus movimientos.
# Si aquí se pusiera otro número, la terminal estaría avisando de que un valor
# "entra en el grupo de líderes" mientras la pantalla de al lado no lo pinta
# como líder. Ver la lección de CANSLIM #6: dos varas de medir lo mismo.
from services.rsrw_service import UMBRAL_LIDER

# Qué se le dice al usuario por cada señal. El texto es el del aviso: en
# lenguaje normal, sin jerga y sin referencias a hallazgos ni a sesiones.
SENALES = {
    "fase2":        "entra en Fase 2 — la de tendencia alcista",
    "fase4":        "entra en Fase 4 — la de tendencia bajista",
    "lider_rs":     f"entra en el grupo de líderes por fuerza relativa (percentil {UMBRAL_LIDER} o más)",
    "sale_lider":   "sale del grupo de líderes por fuerza relativa",
    "sma50_arriba": "recupera su media de 50 sesiones",
    "sma50_abajo":  "pierde su media de 50 sesiones",
    "maximo_52":    "hace un máximo de 52 semanas",
    "minimo_52":    "hace un mínimo de 52 semanas",
}


def _filas(fecha):
    conn = _conn()
    try:
        return {r["ticker"]: dict(r) for r in conn.execute(
            "SELECT ticker, phase, phase_confirmed, rs_pct, above_sma50, new_high, new_low "
            "FROM snapshot_ticker WHERE fecha = ?", (fecha,)).fetchall()}
    finally:
        conn.close()


def _de_una_fila(hoy, antes) -> list:
    """Las señales de un valor comparando su foto de hoy con la anterior."""
    fuera = []

    # LA FASE, SOLO CONFIRMADA. El escáner trae `phase_confirmed` justamente
    # para esto: sin el debounce de tres sesiones, un valor que baila entre la
    # 1 y la 2 mandaría un aviso cada dos días y el usuario apagaría la alerta.
    if hoy.get("phase_confirmed") and hoy.get("phase") != antes.get("phase"):
        if hoy.get("phase") == 2:
            fuera.append("fase2")
        elif hoy.get("phase") == 4:
            fuera.append("fase4")

    rs_hoy, rs_antes = hoy.get("rs_pct"), antes.get("rs_pct")
    if rs_hoy is not None and rs_antes is not None:
        if rs_antes < UMBRAL_LIDER <= rs_hoy:
            fuera.append("lider_rs")
        elif rs_hoy < UMBRAL_LIDER <= rs_antes:
            fuera.append("sale_lider")

    sma_hoy, sma_antes = hoy.get("above_sma50"), antes.get("above_sma50")
    if sma_hoy is not None and sma_antes is not None and sma_hoy != sma_antes:
        fuera.append("sma50_arriba" if sma_hoy else "sma50_abajo")

    # EL PRIMERO DE LA RACHA, no cada día de la racha. Un valor en subida libre
    # marca máximo diez sesiones seguidas; avisar las diez es ruido, y a la
    # tercera nadie lee el aviso.
    if hoy.get("new_high") and not antes.get("new_high"):
        fuera.append("maximo_52")
    if hoy.get("new_low") and not antes.get("new_low"):
        fuera.append("minimo_52")

    return fuera


def senales_de_la_sesion(fecha: str = None) -> dict:
    """{ticker: [claves de señal]} de una sesión, comparándola con la anterior.

    Sin `fecha`, la última guardada. Devuelve {} si no hay dos sesiones con las
    que comparar: una señal es un CAMBIO, y con una sola foto no hay cambio que
    ver — inventarlo llenaría el primer día de avisos falsos.
    """
    fechas = fechas_snapshot_ticker(limite=60)
    if fecha is None:
        fecha = fechas[0] if fechas else None
    if fecha not in fechas:
        return {}
    # La sesión anterior A ESA, no «la penúltima guardada»: si se piden las
    # señales de una sesión de hace una semana, hay que compararla con la suya.
    siguiente = fechas.index(fecha) + 1
    if siguiente >= len(fechas):
        return {}          # es la primera foto que hay: no hay cambio que ver
    anterior = fechas[siguiente]

    hoy, antes = _filas(fecha), _filas(anterior)
    fuera = {}
    for ticker, fila in hoy.items():
        previa = antes.get(ticker)
        if not previa:
            continue          # no estaba en el universo: no hay cambio que contar
        senales = _de_una_fila(fila, previa)
        if senales:
            fuera[ticker] = senales
    return fuera


def texto_de(clave: str) -> str:
    return SENALES.get(clave, clave)
