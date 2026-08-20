import threading
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from auth import verify_token, verify_admin_key

# Un escaneo tarda varios minutos y escribe en options_flow.db. El candado
# impide que dos disparos solapados corran a la vez sobre la misma base.
_scan_lock = threading.Lock()

# Cómo fue el último escaneo. En memoria a propósito: es información de "qué
# está pasando ahora mismo", y lo que hay que conservar entre reinicios ya se
# guarda en `scan_log` dentro de la base de datos.
_ultimo_scan: dict = {"iniciado_en": None, "terminado_en": None,
                      "resultado": None, "error": None}
from services import users_service, watchlist_service
from services.insider_service import get_confluence_tickers
from services.options_service import (
    get_options_ticker,
    get_history_from_db,
    get_db_stats, get_repeat_signals,
    get_ticker_history_summary, init_db,
    get_options_flow_simple, get_ticker_flow_simple, get_oi_changes,
    get_gamma_exposure,
)

router = APIRouter(prefix="/api/v1/options", tags=["options"])
init_db()

# ── VERSIÓN SIMPLE — la que usa el frontend rediseñado (sin ruido) ─────────────


def _watchlist_tickers(user) -> set:
    """in_watchlist es por usuario -- mismo criterio que scanner.py/rsrw.py/
    insider.py. Ninguna función de options_service.py cachea su resultado
    (leen SQLite directo en cada llamada), así que aquí no hace falta
    copiar antes de mutar como sí hizo falta en insider.py/research.py."""
    user_id = users_service.get_user_id(user)
    return {w["ticker"] for w in watchlist_service.get_watchlist_tickers(user_id)} if user_id else set()

@router.get("/flow-simple")
async def flow_simple(user=Depends(verify_token)):
    result = get_options_flow_simple()
    watchlist_tickers  = _watchlist_tickers(user)
    confluence_tickers = get_confluence_tickers()
    for key in ("calls_bought", "puts_sold", "puts_bought", "calls_sold",
                "top_premium", "top_bullish", "top_bearish"):
        for row in result.get(key, []):
            row["in_watchlist"]  = row.get("ticker") in watchlist_tickers
            row["is_confluence"] = row.get("ticker") in confluence_tickers
    return result

@router.get("/ticker-flow/{ticker}")
async def ticker_flow(ticker: str, period: str = Query("1w"), user=Depends(verify_token)):
    result = get_ticker_flow_simple(ticker, period)
    if result.get("ok"):
        result["in_watchlist"]  = ticker.upper() in _watchlist_tickers(user)
        result["is_confluence"] = ticker.upper() in get_confluence_tickers()
    return result

@router.get("/oi-changes")
async def oi_changes(user=Depends(verify_token)):
    return get_oi_changes()

@router.get("/gex/{ticker}")
async def gex(
    ticker: str,
    max_dte: int = Query(50, ge=1, le=365),
    strike_range: float = Query(None, gt=0),
    fecha: str = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    user=Depends(verify_token),
):
    """GEX y DEX por strike, con calls y puts separadas. Los dos parámetros
    replican los controles de la herramienta de tradingedge.club: `max_dte`
    son días hasta vencimiento y `strike_range` es un ± en unidades de
    PRECIO (no en porcentaje ni en número de strikes). Sin `strike_range` se
    usa un rango automático del ±12% del spot.

    Con `fecha` (YYYY-MM-DD) se recalcula el de esa SESIÓN a partir de la
    foto de la cadena guardada, en vez de pedirle la cadena de ahora al
    proveedor. El resultado viene marcado `historico: true` y `parcial:
    true` -- la foto guarda los contratos con más open interest, no la
    cadena entera, así que su total no es comparable con el de en vivo. Ver
    get_gamma_exposure_historico()."""
    if fecha:
        from services.options_service import get_gamma_exposure_historico
        return get_gamma_exposure_historico(ticker, fecha, max_dte=max_dte,
                                            strike_range=strike_range)
    return get_gamma_exposure(ticker, max_dte=max_dte, strike_range=strike_range)


@router.get("/gex/{ticker}/fechas")
async def gex_fechas(ticker: str, user=Depends(verify_token)):
    """Sesiones de las que se puede recalcular el GEX de este ticker. Solo
    salen las que tienen guardadas la volatilidad implícita y el precio del
    subyacente -- las anteriores al 18/08/2026 tienen la foto pero no esos
    campos, y ofrecerlas daría un resultado vacío o inventado."""
    from services.options_service import fechas_gex_disponibles
    return {"ok": True, "ticker": ticker.upper(),
            "fechas": fechas_gex_disponibles(ticker)}

@router.post("/scan-now")
async def scan_now(_admin: None = Depends(verify_admin_key)):
    """Dispara el escaneo+guardado ahora mismo. Lo llama el cron de GitHub
    Actions (.github/workflows/options_scan.yml) a hora fija tras el cierre.

    DOS CAMBIOS DE SEGURIDAD EL 05/08/2026 (auditoría Options Flow #4):

    1. Pasa de `verify_token` a `verify_admin_key`. Antes, cualquier usuario
       registrado podía lanzar un escaneo de ~570 tickers contra yfinance
       tantas veces como quisiera — no roba datos, pero deja el backend
       ocupado varios minutos y agota el límite de Yahoo para todos. Un
       escaneo del sistema no es una acción de usuario.

    2. Candado de concurrencia NO BLOQUEANTE. Dos disparos solapados —el
       cron y un disparo manual, o dos reintentos del workflow— lanzaban dos
       escaneos completos a la vez contra la misma base y la misma API. Si
       ya hay uno en marcha se responde diciéndolo, en vez de encolar la
       petición detrás de varios minutos de descargas.

    El workflow tuvo que cambiar de cabecera: ahora manda X-Admin-Key en vez
    de Authorization. Requiere el secret ADMIN_KEY en GitHub."""
    from fastapi.responses import JSONResponse
    if not _scan_lock.acquire(blocking=False):
        # 409, no 200: hay un escaneo en curso, asi que ESTA peticion no ha
        # hecho nada. Devolverlo como 200 hacia que el disparador lo apuntase
        # como exito.
        return JSONResponse(status_code=409, content={
            "ok": False, "error": "Ya hay un escaneo en curso; no se lanza otro.",
            "en_curso": True})

    # ARRANCA Y RESPONDE. NO espera a que termine.
    #
    # POR QUE, medido el 19/08/2026: el escaneo tarda ~15 minutos, y Nginx
    # corta las peticiones a los 60 segundos (`proxy_read_timeout` por
    # defecto). El disparador recibia un 504 del PROXY y apuntaba el dia como
    # fallido -- aunque el backend seguia escaneando por detras y guardaba
    # bien: la sesion del 18/08 salio 575/579 pese al "fallo".
    #
    # Subir el tiempo de espera de Nginx seria tapar el sintoma. Una peticion
    # HTTP de quince minutos es fragil por naturaleza: cualquier proxy,
    # balanceador o cliente puede cortarla, y la configuracion de Nginx ni
    # siquiera vive en este repositorio. Asi que se rompe la dependencia: se
    # responde 202 en cuanto arranca y el estado se consulta aparte, en
    # /scan-estado.
    #
    # El candado se suelta en la TAREA, no aqui: si se soltara al responder,
    # un segundo disparo entraria mientras el primero sigue escaneando.
    import threading

    def _tarea():
        from services.options_service import run_and_save_scan
        try:
            r = run_and_save_scan()
            _ultimo_scan["resultado"] = r
            _ultimo_scan["error"] = None if r.get("ok") else r.get("error", "desconocido")
        except Exception as e:
            _ultimo_scan["resultado"] = None
            _ultimo_scan["error"] = f"{type(e).__name__}: {e}"
            print(f"[OptionsFlow] El escaneo ha reventado: {_ultimo_scan['error']}")
        finally:
            _ultimo_scan["terminado_en"] = datetime.now(timezone.utc).isoformat()
            _scan_lock.release()

    _ultimo_scan.update({"iniciado_en": datetime.now(timezone.utc).isoformat(),
                         "terminado_en": None, "resultado": None, "error": None})
    threading.Thread(target=_tarea, daemon=True, name="options-scan").start()
    return JSONResponse(status_code=202, content={
        "ok": True, "iniciado": True,
        "mensaje": ("Escaneo arrancado. Puede tardar unos 15 minutos; consulta "
                    "GET /api/v1/options/scan-estado para saber cómo va."),
        "iniciado_en": _ultimo_scan["iniciado_en"]})


@router.get("/aciertos")
async def aciertos(user=Depends(verify_token)):
    """¿Acierta este módulo? Aciertos de las señales de flujo contra el S&P 500
    en la misma ventana (ver options_tracking_service).

    Contra el índice y no contra cero: en un tramo alcista, «apostó al alza y
    subió» acierta casi siempre sin que la señal aporte nada. Y cada bloque
    viene con su `n` y con `suficiente`, para que un porcentaje sacado de
    cuatro casos no se lea como una conclusión."""
    from services.options_tracking_service import resumen
    return resumen()


@router.get("/aciertos-strike")
async def aciertos_strike(user=Depends(verify_token)):
    """¿Cuántas de las operaciones inusuales llegaron a su strike?

    El examen que la propia apuesta se puso, en vez de un horizonte inventado:
    una call a 340 que vence el 18/09 apostó a que el precio llegara a 340
    antes de esa fecha. Solo cuentan las que estaban FUERA del dinero al
    detectarse -- las que ya estaban dentro llegan el primer día sin que ocurra
    nada."""
    from services.options_tracking_service import resumen_strike
    return resumen_strike()


@router.get("/scan-estado")
async def scan_estado(_admin: None = Depends(verify_admin_key)):
    """Cómo va (o cómo fue) el último escaneo lanzado por /scan-now.

    Existe porque el disparo dejó de ser síncrono: el disparador arranca el
    escaneo y luego pregunta aquí hasta que termina. Devuelve el resultado
    REAL del escaneo, no el de una conexión HTTP -- que era justo lo que se
    estaba midiendo mal."""
    from services.options_service import get_scan_log
    en_curso = _scan_lock.locked()
    return {
        "ok": True,
        "en_curso": en_curso,
        "iniciado_en": _ultimo_scan.get("iniciado_en"),
        "terminado_en": _ultimo_scan.get("terminado_en"),
        "error": _ultimo_scan.get("error"),
        "resultado": _ultimo_scan.get("resultado"),
        # Del registro en disco, para poder responder también después de un
        # reinicio del contenedor, cuando la memoria de arriba está vacía.
        "ultimo_guardado": get_scan_log(),
    }

# ── DOS ENDPOINTS RETIRADOS EL 05/08/2026 (auditoría Options Flow #3 y #5) ────
#
# GET /flow — «versión anterior, se deja por compatibilidad». Ejecutaba el
# escaneo COMPLETO en vivo (~570 tickers contra yfinance) dentro de la
# petición HTTP, con solo `verify_token`: cualquier usuario registrado podía
# tumbar el backend y agotar el límite de Yahoo pidiendo una URL. Y no lo
# llamaba nadie — cero referencias en todo frontend/, comprobado antes de
# quitarlo.
#
# POST /save — aceptaba un cuerpo JSON arbitrario y lo escribía en el
# histórico de flujo, también con solo `verify_token`. Es decir: cualquier
# usuario podía inyectar señales falsas en los datos que ven todos los demás,
# y en el baseline por ticker que alimenta el scoring. Tampoco lo llamaba
# nadie.
#
# Las funciones de servicio NO se tocan: `get_options_flow()` y
# `save_current_scan()` las sigue usando `run_and_save_scan()`, que es el
# camino legítimo (cron nocturno). Lo que desaparece es la puerta HTTP.

@router.get("/history")
async def history(
    ticker: str = Query(None),
    period: str = Query("1w"),
    user=Depends(verify_token)
):
    rows = get_history_from_db(ticker=ticker, period=period)
    return {"ok": True, "records": rows, "total": len(rows), "period": period}

@router.get("/repeats")
async def repeats(
    days:        int = Query(7, ge=1, le=90),
    min_repeats: int = Query(2, ge=2),
    user=Depends(verify_token)
):
    return {"ok": True, "signals": get_repeat_signals(days, min_repeats)}

@router.get("/ticker-summary/{ticker}")
async def ticker_summary(ticker: str, user=Depends(verify_token)):
    return get_ticker_history_summary(ticker)

@router.get("/stats")
async def stats(user=Depends(verify_token)):
    return get_db_stats()

@router.get("/ticker/{ticker}")
async def options_ticker(ticker: str, user=Depends(verify_token)):
    return get_options_ticker(ticker)