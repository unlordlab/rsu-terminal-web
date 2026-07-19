"""
turnover_service.py — rotación bursátil (turnover = volumen negociado /
acciones en circulación), basado en Lo & Wang (2000, "Trading Volume:
Definitions, Data Analysis, and Implications of Portfolio Theory", Review
of Financial Studies 13(2):257-300).

El paper muestra que la rotación NO es uniforme entre valores (rechaza la
hipótesis de separación en dos fondos) y que su variación sigue una
estructura de factores -- es decir, las desviaciones de rotación respecto
al mercado no son ruido, son información real sobre qué fuerzas mueven
cada activo.

Pensado para compartirse entre Research (comparativa individual vs.
mercado) y, más adelante, Scanner (detección de anomalías / filtro de
calidad sobre el universo completo).
"""
import yfinance as yf
import pandas as pd


def _get_shares_outstanding(tk_obj) -> float | None:
    try:
        shares = tk_obj.fast_info.shares_outstanding
        if shares:
            return float(shares)
    except Exception:
        pass
    try:
        info = tk_obj.info
        shares = info.get("sharesOutstanding")
        if shares:
            return float(shares)
    except Exception:
        pass
    return None


def _get_daily_turnover(ticker: str, days: int = 180) -> pd.Series | None:
    """Serie diaria de rotación: volumen / acciones en circulación."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=f"{days}d")
        if hist.empty:
            return None
        shares = _get_shares_outstanding(tk)
        if not shares:
            return None
        turnover = hist["Volume"] / shares
        turnover.index = turnover.index.tz_localize(None)
        return turnover
    except Exception:
        return None


def _get_price_volume_data(ticker: str, days: int = 180) -> pd.DataFrame | None:
    """DataFrame con precio, volumen, retorno diario, rotación e impacto de
    precio (Amihud) -- una sola descarga reutilizada tanto para el
    indicador de Rotación como para el de Absorción."""
    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period=f"{days}d")
        if hist.empty or len(hist) < 30:
            return None
        shares = _get_shares_outstanding(tk)
        if not shares:
            return None
        df = pd.DataFrame(index=hist.index.tz_localize(None))
        df["close"]         = hist["Close"].values
        df["volume"]        = hist["Volume"].values
        df["turnover"]      = df["volume"] / shares
        df["return"]        = df["close"].pct_change()
        df["dollar_volume"] = df["close"] * df["volume"]
        # Amihud (2002): |retorno| / volumen en dólares (en millones, para
        # que el número resultante sea legible) -- proxy estándar de la
        # Lambda de Kyle (1985), impacto de precio por unidad de volumen.
        df["amihud"] = df["return"].abs() / (df["dollar_volume"] / 1_000_000)
        df["amihud"] = df["amihud"].replace([float("inf"), float("-inf")], None)
        return df.dropna(subset=["turnover"])
    except Exception:
        return None


def get_absorption_signal(ticker: str, days: int = 180) -> dict:
    """Detecta indicios de absorción silenciosa: rotación por encima de lo
    normal PARA ESTE ACTIVO, combinada con impacto de precio (Amihud) por
    DEBAJO de lo normal -- la firma característica de una orden grande
    ejecutándose poco a poco sin delatar su propia posición (Kyle, 1985;
    Bouchaud, Farmer & Lillo, 2008). Un pico de volumen que SÍ mueve el
    precio con fuerza es más compatible con actividad especulativa/ruido
    que con absorción institucional cuidadosa."""
    df = _get_price_volume_data(ticker, days)
    if df is None or len(df) < 30:
        return {"ok": False, "error": "Datos insuficientes para calcular absorción"}

    df["turnover_z"] = (df["turnover"] - df["turnover"].rolling(20).mean()) / df["turnover"].rolling(20).std()
    df["amihud_z"]   = (df["amihud"]   - df["amihud"].rolling(20).mean())   / df["amihud"].rolling(20).std()

    # Día de "posible absorción": rotación por encima de su media reciente
    # Y, a la vez, impacto de precio por debajo de la suya -- ambas cosas
    # a la vez, no una sola. Umbral de 0.75 desviaciones en cada dirección
    # -- punto intermedio provisional; la ventana móvil de 20 días se ve
    # "contaminada" por los propios días anómalos que intenta detectar
    # (efecto normal de medias móviles cortas), así que este umbral
    # conviene recalibrarlo con casos reales una vez en producción, no
    # solo con datos sintéticos. Ver conversación 18/07/2026.
    df["absorcion_dia"] = (df["turnover_z"] > 0.75) & (df["amihud_z"] < -0.75)

    dias_absorcion = int(df["absorcion_dia"].tail(10).sum())

    tz_series = df["turnover_z"].dropna()
    az_series = df["amihud_z"].dropna()
    turnover_z_actual = float(tz_series.iloc[-1]) if len(tz_series) else 0.0
    amihud_z_actual   = float(az_series.iloc[-1]) if len(az_series) else 0.0

    if dias_absorcion >= 5:
        signal = {
            "level": "fuerte", "icon": "🟢", "color": "#00ffad",
            "label": "Posible absorción sostenida",
            "detail": f"{dias_absorcion} de los últimos 10 días muestran rotación alta con impacto de precio bajo — "
                      f"la combinación característica de una orden grande ejecutándose con cuidado, sin delatar la posición.",
        }
    elif dias_absorcion >= 2:
        signal = {
            "level": "moderada", "icon": "🟡", "color": "#ff9800",
            "label": "Indicios leves de absorción",
            "detail": f"{dias_absorcion} de los últimos 10 días con esa combinación — todavía pronto para hablar de una tendencia sostenida.",
        }
    else:
        signal = {
            "level": "ninguna", "icon": "⚪", "color": "var(--color-muted)",
            "label": "Sin señales de absorción",
            "detail": "El comportamiento reciente de volumen e impacto en precio no muestra ese patrón sostenido.",
        }

    return {
        "ok": True,
        "ticker": ticker,
        "dias_absorcion_10d": dias_absorcion,
        "turnover_z": round(turnover_z_actual, 2),
        "amihud_z": round(amihud_z_actual, 2),
        "signal": signal,
        "chart": {
            "dates":         [d.strftime("%Y-%m-%d") for d in df.index],
            "turnover_z":    [round(float(v), 2) if pd.notna(v) else None for v in df["turnover_z"]],
            "amihud_z":      [round(float(v), 2) if pd.notna(v) else None for v in df["amihud_z"]],
            "absorcion_dia": [bool(v) for v in df["absorcion_dia"]],
        },
    }


def _compute_signal(df) -> dict:
    """Combina dos señales en un único indicador sencillo:
    1) ¿Hay actividad de volumen anómala AHORA MISMO? (Z-score del último
       día de rotación frente a su propia media móvil de 20 días)
    2) ¿Se ha desconectado del mercado RECIENTEMENTE? (correlación de los
       últimos 20 días frente a la correlación de todo el periodo)

    Un activo con volumen anómalo Y desconectado del mercado es la señal
    más interesante -- sugiere algo propio del activo, no un movimiento
    de mercado general que arrastra a todos por igual."""
    turnover = df["ticker"]
    mean20 = turnover.rolling(20).mean()
    std20  = turnover.rolling(20).std()

    z_series = (turnover - mean20) / std20
    z_score = z_series.dropna()
    z_score = float(z_score.iloc[-1]) if len(z_score) else 0.0

    corr_total = df["ticker_norm"].corr(df["bench_norm"])
    if len(df) >= 20:
        corr_recent = df["ticker_norm"].tail(20).corr(df["bench_norm"].tail(20))
    else:
        corr_recent = corr_total

    volumen_anomalo = z_score >= 2.0
    desconectado    = (corr_total - corr_recent) >= 0.3  # ha caido bastante respecto a su propia base

    if volumen_anomalo and desconectado:
        return {"level": "fuerte", "icon": "🔴", "color": "#f23645",
                "label": "Actividad inusual y desconectada del mercado",
                "detail": f"El volumen de hoy está {z_score:.1f} desviaciones por encima de lo normal para este activo, "
                          f"y su correlación con el mercado ha caído de {corr_total:.2f} a {corr_recent:.2f} recientemente. "
                          f"Sugiere algo propio de este activo, no un movimiento de mercado general."}
    elif volumen_anomalo:
        return {"level": "moderada", "icon": "🟡", "color": "#ff9800",
                "label": "Actividad alta, pero en línea con el mercado",
                "detail": f"El volumen de hoy está {z_score:.1f} desviaciones por encima de lo normal, "
                          f"pero la correlación con el mercado se mantiene ({corr_recent:.2f}) — "
                          f"probablemente forma parte de un movimiento general, no algo específico de este activo."}
    elif desconectado:
        return {"level": "moderada", "icon": "🟡", "color": "#ff9800",
                "label": "Moviéndose por su cuenta, sin volumen extremo",
                "detail": f"Sin actividad de volumen destacable, pero la correlación con el mercado ha caído "
                          f"de {corr_total:.2f} a {corr_recent:.2f} en las últimas semanas — señal más suave, a vigilar."}
    else:
        return {"level": "ninguna", "icon": "⚪", "color": "var(--color-muted)",
                "label": "Sin señales relevantes",
                "detail": "Ni el volumen ni la relación con el mercado muestran nada fuera de lo normal ahora mismo."}


def get_turnover_comparison(ticker: str, benchmark: str = "SPY", days: int = 180) -> dict:
    """Compara la rotación del ticker frente a la del mercado (SPY por
    defecto). Si la rotación de un activo se desvía sistemáticamente de
    la del mercado general, es un aviso de que está bajo fuerzas propias
    distintas a las del mercado amplio (Lo & Wang, 2000)."""
    turnover_ticker = _get_daily_turnover(ticker, days)
    turnover_bench  = _get_daily_turnover(benchmark, days)

    if turnover_ticker is None or turnover_bench is None:
        return {"ok": False, "error": "Sin datos suficientes de rotación (falta volumen o acciones en circulación)"}

    df = pd.DataFrame({"ticker": turnover_ticker, "bench": turnover_bench}).dropna()
    if len(df) < 20:
        return {"ok": False, "error": "Histórico insuficiente para comparar (menos de 20 días con datos)"}

    # Se normaliza cada serie a su propia media -- el turnover de SPY (miles
    # de millones de acciones en circulación) no es comparable en magnitud
    # bruta con el de una acción individual. Lo que importa es la FORMA de
    # cada serie, no la escala absoluta.
    df["ticker_norm"] = df["ticker"] / df["ticker"].mean()
    df["bench_norm"]  = df["bench"] / df["bench"].mean()
    df["ratio"] = df["ticker_norm"] / df["bench_norm"]
    df["ratio_ma20"] = df["ratio"].rolling(20).mean()

    correlation = df["ticker_norm"].corr(df["bench_norm"])
    ultimo_ratio = df["ratio_ma20"].dropna()
    ultimo_ratio = float(ultimo_ratio.iloc[-1]) if len(ultimo_ratio) else None
    signal = _compute_signal(df)

    if correlation > 0.5:
        interpretacion = (
            "La rotación de este activo se mueve en línea con la del mercado general — "
            "no hay indicios claros de que esté bajo fuerzas propias distintas al mercado amplio."
        )
    elif correlation > 0.2:
        interpretacion = (
            "La rotación de este activo tiene una relación moderada con la del mercado — "
            "parte de su actividad se explica por el mercado general, pero también hay un componente propio."
        )
    else:
        interpretacion = (
            "La rotación de este activo apenas se explica por la del mercado general — "
            "sugiere que está bajo la influencia de fuerzas propias (noticias específicas, "
            "flujo institucional dirigido, u otro factor no ligado al mercado amplio)."
        )

    return {
        "ok":              True,
        "ticker":          ticker,
        "benchmark":       benchmark,
        "correlation":     round(float(correlation), 2),
        "current_ratio":   round(ultimo_ratio, 2) if ultimo_ratio is not None else None,
        "interpretation":  interpretacion,
        "signal":          signal,
        "chart": {
            "dates":            [d.strftime("%Y-%m-%d") for d in df.index],
            "ticker_turnover":  [round(float(v), 4) for v in df["ticker_norm"]],
            "bench_turnover":   [round(float(v), 4) for v in df["bench_norm"]],
        },
    }