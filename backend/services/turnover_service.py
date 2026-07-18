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
        "chart": {
            "dates":            [d.strftime("%Y-%m-%d") for d in df.index],
            "ticker_turnover":  [round(float(v), 4) for v in df["ticker_norm"]],
            "bench_turnover":   [round(float(v), 4) for v in df["bench_norm"]],
        },
    }