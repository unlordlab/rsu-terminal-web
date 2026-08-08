"""
l3_banker.py -- oscilador de flujo al estilo del "L3 Banker Fund Flow Trend
Oscillator" de blackcat, reproducido fielmente para que las velas de colores
caigan exactamente donde caen en TradingView.

Se reproduce TAL CUAL, incluida la constante 1,032 que el original no
justifica, porque el valor de este indicador para quien lo usa está en
reconocer visualmente los mismos patrones de siempre. Cambiarle la fórmula
movería las velas de sitio y lo empeoraría para ese uso, por bien que midiera
en un test.

FÓRMULA (verificada contra dos ports independientes del código publicado):

    wmCal      = (cierre - mín(bajo,27)) / (máx(alto,27) - mín(bajo,27)) * 100
    fundtrend  = (3·xsa(wmCal,5) - 2·xsa(xsa(wmCal,5),3) - 50) · 1,032 + 50
    typ        = (2·cierre + alto + bajo + apertura) / 5
    bullbear   = (typ - mín(bajo,34)) / (máx(alto,34) - mín(bajo,34)) * 100
    línea      = EMA(bullbear, 13)

donde xsa(x, n) es la media suavizada china: y = (x + (n-1)·y_anterior) / n,
equivalente a una EMA de alfa 1/n.

LOS CINCO ESTADOS, en el mismo orden de precedencia que el original:

    entrada  fundtrend cruza al alza la línea   Y línea < 25   (vela amarilla)
    salida   fundtrend cruza a la baja la línea Y línea > 75   (vela violeta)
    debil_baja  fundtrend < línea y no ha caído más de un 5% respecto a ayer
    baja        fundtrend < línea
    debil_alta  fundtrend ha caído más de un 5% respecto a ayer
    alta        fundtrend > línea

NOTA IMPORTANTE SOBRE QUÉ MIDE: pese al nombre, este indicador no usa el
volumen en ningún momento -- es momento de precio suavizado. El flujo de
dinero ponderado por volumen se calcula aparte, en shared/rsu_flow.py.

NO depende de nada de backend/ (fastapi, pydantic).
"""
import numpy as np
import pandas as pd

CAIDA_DEBIL = 0.95   # el original compara contra el 95% del valor de ayer
UMBRAL_ENTRADA = 25
UMBRAL_SALIDA  = 75


def _xsa(x, n):
    """Media suavizada del original: y = (x + (n-1)·y_anterior) / n."""
    return x.ewm(alpha=1 / n, adjust=False).mean()


def calcular_l3(df: pd.DataFrame) -> pd.DataFrame:
    """df necesita Open, High, Low y Close. Devuelve un DataFrame con
    `fundtrend`, `linea` y `estado` por sesión."""
    bajo27, alto27 = df["Low"].rolling(27).min(), df["High"].rolling(27).max()
    wm = (df["Close"] - bajo27) / (alto27 - bajo27).replace(0, np.nan) * 100
    s1 = _xsa(wm, 5)
    s2 = _xsa(s1, 3)
    fundtrend = (3 * s1 - 2 * s2 - 50) * 1.032 + 50

    typ = (2 * df["Close"] + df["High"] + df["Low"] + df["Open"]) / 5
    bajo34, alto34 = df["Low"].rolling(34).min(), df["High"].rolling(34).max()
    bullbear = (typ - bajo34) / (alto34 - bajo34).replace(0, np.nan) * 100
    linea = bullbear.ewm(span=13, adjust=False).mean()

    encima = fundtrend > linea
    cruce_alza = encima & ~encima.shift(1).fillna(False)
    cruce_baja = ~encima & encima.shift(1).fillna(False)
    cae_fuerte = fundtrend < fundtrend.shift(1) * CAIDA_DEBIL

    estado = pd.Series("alta", index=df.index, dtype=object)
    estado[encima & cae_fuerte] = "debil_alta"
    estado[~encima] = "baja"
    estado[~encima & ~cae_fuerte] = "debil_baja"
    estado[cruce_baja & (linea > UMBRAL_SALIDA)] = "salida"
    estado[cruce_alza & (linea < UMBRAL_ENTRADA)] = "entrada"
    estado[fundtrend.isna() | linea.isna()] = None

    return pd.DataFrame({"fundtrend": fundtrend, "linea": linea, "estado": estado})
