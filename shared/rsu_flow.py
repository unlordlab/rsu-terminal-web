"""
rsu_flow.py -- Indicador RSU de flujo de dinero.

Mide si en las últimas semanas ha entrado o salido dinero de un valor, y lo
expresa como percentil (0-100) frente a lo normal en ESE mismo valor durante el
último año. 80 no significa "mucho dinero" en abstracto: significa que hay más
entrada que en el 80% de los días recientes de ese valor.

CÓMO SE CONSTRUYE
1. Presión de cada sesión: dónde cierra el precio dentro de su propio rango del
   día, de -1 (cierra en mínimos) a +1 (cierra en máximos). Es el multiplicador
   de Chaikin, el mismo ladrillo que ya usa el rating de acumulación/
   distribución de CANSLIM (shared/canslim_engine.py).
2. Ponderada por volumen, para que una sesión de mucho movimiento pese más que
   una tranquila. Aquí es donde el indicador se gana el nombre de "flujo": sin
   el volumen sería otra medida de precio.
3. Acumulada en 21 sesiones (~un mes de mercado) y dividida por el volumen de
   esas mismas sesiones, de forma que el resultado no dependa del tamaño del
   valor.
4. Suavizada dos veces para quitar el ruido diario.
5. Convertida a percentil de su propio año, que es lo que la hace comparable
   entre valores y entre épocas.

QUÉ MIDE Y QUÉ NO
No observa órdenes reales ni sabe quién compra: infiere presión a partir de
dónde cierra el precio dentro de su rango, ponderado por volumen. Es una
inferencia razonable y muy usada, no una lectura del libro de órdenes.

POR QUÉ NO LLEVA SEÑALES DE COMPRA/VENTA
Se probó la mecánica de cruces del indicador en el que se inspira (el "L3
Banker Fund Flow", que pese al nombre no usa volumen en ningún momento) sobre
62 valores y 3 años: sus señales de salida rendían MEJOR que las de entrada,
así que no ordenaban nada. El nivel del flujo, en cambio, sí ordena los
retornos a 3 meses de forma monótona (del quintil más bajo al más alto:
+4,98%, +5,42%, +6,11%, +6,50%, +7,54%), aunque con una diferencia modesta de
2,56 puntos y sin capacidad predictiva a 3 semanas. Por eso esto es un
indicador de CONTEXTO y no un generador de señales.

NO depende de nada de backend/ (fastapi, pydantic).
"""
import numpy as np
import pandas as pd

VENTANA_FLUJO = 21     # ~1 mes de mercado
VENTANA_PCT   = 250    # ~1 año, para el percentil
MIN_PCT       = 120    # sin al menos medio año no hay con qué comparar


def calcular_flujo(df: pd.DataFrame) -> pd.Series:
    """df necesita High, Low, Close y Volume. Devuelve la serie 0-100 (NaN
    mientras no haya historia suficiente para situar el dato)."""
    rango = (df["High"] - df["Low"]).replace(0, np.nan)
    presion = ((df["Close"] - df["Low"]) - (df["High"] - df["Close"])) / rango
    dinero  = presion * df["Volume"]

    vol_ventana = df["Volume"].rolling(VENTANA_FLUJO).sum().replace(0, np.nan)
    flujo = dinero.rolling(VENTANA_FLUJO).sum() / vol_ventana

    # Doble suavizado: el mismo esquema del indicador original, sin su
    # constante 1,032, que no está justificada en ninguna parte.
    s1 = flujo.ewm(alpha=1 / 5, adjust=False).mean()
    s2 = s1.ewm(alpha=1 / 3, adjust=False).mean()
    suavizado = 3 * s1 - 2 * s2

    return suavizado.rolling(VENTANA_PCT, min_periods=MIN_PCT).rank(pct=True) * 100


def zona(valor):
    """Tres tramos, en los mismos quintiles con los que se midió el indicador:
    el 20% más bajo, el 20% más alto y el medio."""
    if valor is None:
        return None
    if valor >= 80:
        return "entrando"
    if valor <= 20:
        return "saliendo"
    return "neutro"
