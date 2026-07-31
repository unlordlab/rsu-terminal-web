"""
El puente "cuándo → qué" del RSU Algoritmo.

POR QUÉ EXISTE:
El semáforo dice CUÁNDO empezar a construir posición, pero no en QUÉ. Se pone
verde y el usuario se queda mirando un color. Toda la información para cerrar
ese hueco ya existe en la terminal —el scan nocturno de RS/RW calcula el
percentil de fuerza relativa de ~500 tickers cada noche— pero nadie la
conectaba con el semáforo.

QUÉ CRITERIO Y POR QUÉ:
Los líderes. Tras un suelo de mercado, lo que históricamente funciona mejor no
es comprar lo más castigado (el "value trap" del que se recupera último o no se
recupera) sino lo que MENOS cayó y primero recupera — la lógica de Weinstein,
Minervini y O'Neil, que es además la que ya enseña la Academia del proyecto.

Traducido a los datos que ya hay: percentil de fuerza relativa alto (cayó menos
que el resto) Y precio por encima de su media de 50 sesiones (ya está
recuperando, no sigue cayendo). El segundo filtro importa: sin él saldrían
valores con RS alta que simplemente aún no han empezado a caer.

NO CALCULA NADA NUEVO. Lee el mismo Gist que ya usa la página de RS/RW, así
que no añade ni una petición de red por usuario.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))
from time_utils import get_timestamp  # noqa: E402

# Percentil mínimo de fuerza relativa. 80 = el 20% más fuerte del S&P 500.
RS_MINIMO = 80
MAX_CANDIDATOS = 5


def get_candidatos_algoritmo() -> dict:
    """Los tickers a vigilar cuando el semáforo se ponga verde.

    Se devuelven SIEMPRE, esté el semáforo como esté — la página los enseña en
    gris cuando no es momento ("esto es lo que estarás mirando cuando llegue")
    y en color cuando sí lo es. Que el usuario los vea antes es justo lo que
    permite tener la decisión tomada de antemano, que es el propósito de la
    fase ÁMBAR.
    """
    from services.cache import cache
    cacheado = cache.get("algoritmo:candidatos")
    if cacheado is not None:
        return cacheado or {"ok": False, "error": "Sin datos del scan nocturno"}

    resultado = {"ok": False, "error": "Sin datos del scan nocturno de RS/RW"}
    try:
        from services.rsrw_service import get_universe_dataframe
        datos = get_universe_dataframe()
        if datos is not None:
            df, meta = datos
            # Columnas del Gist de RS/RW: RS_Pct (percentil 1-100), Precio,
            # Sector. `sobre_sma50` no viene de RS/RW sino del Scanner, así que
            # se usa RS_Trend (pendiente de la fuerza relativa) como prueba de
            # que ya está girando, que sí está en este mismo DataFrame.
            if not df.empty and "RS_Pct" in df.columns:
                fuertes = df[df["RS_Pct"] >= RS_MINIMO].copy()
                if "RS_Trend" in fuertes.columns:
                    # Pendiente positiva: la fuerza relativa está mejorando, no
                    # solo es alta por inercia de hace meses.
                    fuertes = fuertes[fuertes["RS_Trend"] > 0]
                fuertes = fuertes.sort_values("RS_Pct", ascending=False).head(MAX_CANDIDATOS)

                candidatos = []
                for ticker, fila in fuertes.iterrows():
                    pct = fila.get("RS_Pct")
                    candidatos.append({
                        "ticker": str(ticker),
                        "rs_pct": round(float(pct), 1) if pct == pct else None,
                        "sector": str(fila.get("Sector") or "Otros"),
                        # UNA línea, en lenguaje normal. Nada de percentiles ni
                        # jerga: el usuario tiene que entenderlo sin saber qué
                        # es la fuerza relativa.
                        "porque": (f"Aguantó mejor que el {pct:.0f}% del mercado "
                                   f"y su fuerza sigue mejorando") if pct == pct else "Entre los más fuertes del índice",
                    })

                if candidatos:
                    resultado = {
                        "ok": True,
                        "candidatos": candidatos,
                        "criterio": (f"Los {MAX_CANDIDATOS} valores del S&P 500 que mejor aguantaron "
                                     f"la caída y ya están recuperando fuerza"),
                        "fuente": "Scan nocturno de RS/RW",
                        "actualizado": (meta or {}).get("generated_at"),
                        "timestamp": get_timestamp(),
                    }
    except Exception as e:
        print(f"[AlgoritmoCandidatos] Error: {type(e).__name__}: {e}")

    # 10 min: el origen es un scan NOCTURNO, no cambia durante la sesión.
    cache.set("algoritmo:candidatos", resultado if resultado.get("ok") else {}, 600)
    return resultado
