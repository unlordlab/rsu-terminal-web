"""
digest_service.py -- el resumen nocturno de la watchlist de cada usuario.

QUÉ LLENA (Watchlist #20). La terminal tenía dos extremos y nada en medio: el
briefing, que es del mercado entero y el mismo para todos, y las alertas, que
son instantáneas y de una condición que tú pusiste a mano. Lo que faltaba es lo
que uno quiere saber al cerrar el día: «de los valores que sigo, ¿en cuáles ha
pasado algo?». Eso, hasta ahora, solo se conseguía entrando y mirando pantalla
por pantalla.

NO CALCULA NADA NUEVO. Las novedades son las señales de
`services/senales_service.py` —la diferencia entre las dos últimas fotos de
`snapshot_ticker`— filtradas por los tickers de cada uno. El digest es ese dato
agrupado por usuario, ni más ni menos, así que nunca puede contradecir a lo que
enseñan Scanner, RS/RW o Research.

TRES DECISIONES:

  - **Se manda de noche**, cuando entra la foto de la sesión: es cuando el dato
    está completo y cuando da tiempo a decidir sin prisa. Va enganchado al mismo
    punto que las alertas de señal, así que no hace falta otro reloj.
  - **Los días sin novedades no se manda.** Un mensaje vacío cada día enseña a
    no abrirlo, y entonces tampoco se abre el día que trae algo.
  - **Es opt-in.** Un mensaje diario a quien no lo ha pedido es correo basura
    aunque sea útil.

Y la línea de «los otros N, sin novedades» no es relleno: un resumen que solo
habla cuando hay ruido deja al lector sin saber si el silencio es que no pasó
nada o que el sistema no miró.
"""
from datetime import datetime

MAX_LINEAS = 8

_DIAS  = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")


def fecha_larga(fecha: str) -> str:
    """«2026-09-11» -> «viernes 11 de septiembre»."""
    try:
        d = datetime.strptime(str(fecha)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return str(fecha or "")
    return f"{_DIAS[d.weekday()]} {d.day} de {_MESES[d.month - 1]}"


def digest_de(user_id: int, fecha: str = None) -> dict:
    """El resumen de un usuario para una sesión.

    Devuelve siempre la misma forma, con `novedades` vacío si no hubo nada: la
    pantalla lo enseña igual («sin novedades»), y quien decide si se manda o no
    es `enviar_digests()`, no esto.
    """
    from services.watchlist_service import get_watchlist_tickers
    from services.senales_service import senales_de_la_sesion, texto_de

    items = get_watchlist_tickers(user_id)
    tickers = {i["ticker"] for i in items}
    senales = senales_de_la_sesion(fecha)
    if not fecha:
        from services.snapshots_service import fechas_snapshot_ticker
        fechas = fechas_snapshot_ticker(limite=1)
        fecha = fechas[0] if fechas else None

    novedades = []
    for ticker in sorted(tickers):
        claves = senales.get(ticker) or []
        if claves:
            novedades.append({"ticker": ticker, "senales": claves,
                              "textos": [texto_de(c) for c in claves]})
    # Primero quien más se ha movido: si hay que recortar, que se quede fuera
    # el valor con una sola novedad, no el que tiene tres.
    novedades.sort(key=lambda n: (-len(n["senales"]), n["ticker"]))

    return {
        "ok": True,
        "fecha": fecha,
        "fecha_larga": fecha_larga(fecha),
        "seguidos": len(tickers),
        "novedades": novedades,
        "sin_novedades": len(tickers) - len(novedades),
    }


def texto_del_digest(d: dict) -> str:
    """El mensaje de Telegram. Markdown del que acepta la API de Telegram."""
    lineas = [f"📋 *RSU · {d['fecha_larga']}*",
              f"De tus {d['seguidos']} valores seguidos:", ""]
    for n in d["novedades"][:MAX_LINEAS]:
        lineas.append(f"▸ *{n['ticker']}* {' · '.join(n['textos'])}")
    de_mas = len(d["novedades"]) - MAX_LINEAS
    if de_mas > 0:
        lineas.append(f"…y {de_mas} valor{'es' if de_mas > 1 else ''} más con novedades.")
    if d["sin_novedades"]:
        lineas.append("")
        lineas.append(f"Los otros {d['sin_novedades']}, sin novedades.")
    return "\n".join(lineas)


def enviar_digests(fecha: str = None) -> int:
    """Manda el resumen a quien lo tenga activado. Devuelve cuántos salieron.

    Se llama desde `routers/ws.py` en cuanto el snapshot diario escribe una
    sesión nueva — el mismo punto que las alertas de señal, porque es el mismo
    dato. Nunca levanta: un resumen que falla no puede tumbar el bucle que
    mantiene caliente la caché de Market.
    """
    from services.users_service import destinatarios_del_digest
    from services.telegram_service import enviar_telegram

    destinatarios = destinatarios_del_digest()
    if not destinatarios:
        return 0
    enviados = 0
    for user_id, chat_id in destinatarios.items():
        try:
            d = digest_de(user_id, fecha)
            if not d["novedades"]:
                continue          # día sin nada: no se manda (ver cabecera)
            enviar_telegram(texto_del_digest(d), chat_id=chat_id)
            enviados += 1
        except Exception as e:
            print(f"[Digest] No se pudo mandar el de {user_id}: {type(e).__name__}: {e}")
    if enviados:
        print(f"[Digest] {enviados} resúmenes enviados para la sesión {fecha}")
    return enviados
