"""
Respuesta JSON que nunca revienta por un NaN.

Starlette serializa con `allow_nan=False`, así que un solo `float('nan')` en
cualquier punto de la respuesta lanza un ValueError, FastAPI lo convierte en un
500 y el cliente recibe la cadena "Internal Server Error" en TEXTO PLANO. En la
pantalla eso se ve como:

    ✗ Unexpected token 'I', "Internal S"... is not valid JSON

que no dice nada de lo que ha pasado. El módulo entero desaparece por un único
punto malo de una serie de cientos.

Ha ocurrido tres veces en este proyecto, siempre por la misma vía: yfinance
devuelve NaN en la barra en curso o en una semana de festivo, y ese NaN viaja
hasta la respuesta.
  · /api/v1/watchlist, 25/07/2026 -- barras diarias de AAPL/NVDA.
  · /api/v1/market/liquidity, 17/08/2026 -- barra semanal del S&P 500, punto
    104 de la serie. Reportado por el usuario.

Los dos primeros se arreglaron en su origen, y está bien que así sea: el sitio
correcto para descartar un dato que no existe es donde se lee. Pero arreglar
orígenes de uno en uno no cierra la clase de fallo -- solo tapa el caso que se
ha visto. Esto sí la cierra: un NaN que se escape de cualquier sitio sale como
`null`, que es lo que de verdad significa (no hay dato), y el frontend ya sabe
tratarlo. El módulo pierde un punto de la serie en vez de desaparecer entero.

NO sustituye a limpiar el origen. Un `null` inesperado sigue siendo una señal de
que algo hay que mirar; lo que cambia es que deja de ser una pantalla en blanco.
"""
import math

from fastapi.responses import JSONResponse


def sanear(valor):
    """Reemplaza NaN e infinitos por None, recorriendo dicts y listas."""
    if isinstance(valor, float):
        return valor if math.isfinite(valor) else None
    if isinstance(valor, dict):
        return {k: sanear(v) for k, v in valor.items()}
    if isinstance(valor, (list, tuple)):
        return [sanear(v) for v in valor]
    return valor


class JSONSeguro(JSONResponse):
    def render(self, content) -> bytes:
        return super().render(sanear(content))
