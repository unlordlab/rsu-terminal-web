"""
canslim_engine.py -- núcleo técnico puro del scan CAN SLIM, compartido
entre backend/services/canslim_service.py (análisis individual on-demand,
y el scan on-demand que se mantiene vivo aunque ya no sea el camino
principal del frontend) y scripts/canslim_scan.py (scan nocturno vía
GitHub Actions, sesión 32). Extraído sin cambiar la fórmula -- mismo
criterio que shared/rsrw_engine.py (sesión 14).

Contiene: retorno a 12 meses, rating de Acumulación/Distribución A-E,
Trend Template de Minervini y score técnico 0-100.

POR QUÉ ESTÁN AQUÍ trend_template() Y technical_score() (01/08/2026)
Hasta esta fecha vivían solo en canslim_service.py y el scan usaba sus
propias versiones simplificadas, así que la terminal se contradecía a sí
misma. Medido sobre los 500 tickers reales del universo:

  · TENDENCIA -- el scan usaba 3 condiciones (precio>MA50, precio>MA150,
    MA50>MA150) y el análisis las 7 de Minervini. Discrepaban en el
    23,8% del universo (119/500). En 15 casos la tabla decía «tendencia
    OK» y el análisis suspendía la letra L del mismo ticker el mismo día
    -- AXON con 3/7 y un -39,4% desde máximos, ARE con 3/7 y -37,6%: el
    chequeo ligero no mira las 52 semanas, así que no puede distinguir un
    rebote dentro de una caída de una tendencia real.

  · SCORE -- dos escalas «técnico 0-100» que coincidían solo el 16% de
    las veces, con 13 puntos de diferencia media y hasta 38 de máxima
    (MSFT: 5 en la tabla, 43 en el análisis, mismo día).

  · Y el score del scan CONTABA perf_12m DOS VECES: el RS ya es el
    percentil de perf_12m dentro del universo, y encima sumaba +10 por
    «perf_12m >= 20%». Los 211 tickers que cobraban ese bonus tenían un
    RS medio de 78,5 frente a 29,0 los que no -- premiaba exactamente lo
    que el RS ya había premiado. La versión de aquí no lo hace.

La justificación que se había escrito para la divergencia («el template
completo ralentizaría el scan de 503 acciones») resultó ser falsa al
medirla: 157 ms extra para 500 tickers, frente a los 34,9 s que tarda la
descarga de yfinance -- el 0,45% del tiempo del scan. Ver auditoría
CANSLIM, hallazgo #6.

NO depende de nada de backend/ (fastapi, pydantic) -- scripts/ corre en el
runner de GitHub Actions sin ese entorno instalado.
"""
import math
import pandas as pd

# Un valor está "cerca de máximos" si no ha caído más de un 15% desde el
# máximo de 52 semanas. Mismo umbral en el scan y en el análisis (letra N).
NEAR_HIGH_PCT = -15


def _safe(val, default=0.0):
    try:
        v = float(val)
        return v if not math.isnan(v) and not math.isinf(v) else default
    except Exception:
        return default


def perf_12m(hist: pd.DataFrame) -> float:
    """Retorno a ~12 meses (252 sesiones) -- misma fórmula en
    analyze_ticker(), el scan on-demand y el scan nocturno, para que el
    percentil de RS Rating compare peras con peras. Ver sesión 23."""
    price = _safe(hist['Close'].iloc[-1])
    return _safe(((price / hist['Close'].iloc[-252]) - 1) * 100) if len(hist) >= 252 else 0.0


def acc_dis_rating(hist: pd.DataFrame) -> str:
    """Rating de Acumulación/Distribución (A-E) sobre los últimos 20 días.

    Usa el multiplicador de flujo de dinero de Chaikin -- ((Close-Low) -
    (High-Close)) / (High-Low) -- que pondera CADA día según dónde cierra
    el precio DENTRO de su propio rango de la sesión (High-Low), no solo
    si cierra por encima o por debajo de la apertura.

    Antes se clasificaba cada día como "volumen alcista" o "volumen
    bajista" solo mirando Close vs Open -- eso clasifica mal los días de
    reversión: un día que abre bajo, cae más durante la sesión, pero
    CIERRA cerca del máximo del día (alguien compró fuerte en la caída,
    acumulación real) se contaba como "bajista" solo por cerrar por
    debajo de la apertura, aunque la acción del precio dentro del día
    dijera lo contrario -- justo los días más informativos para detectar
    acumulación/distribución real. Ver Plan Maestro 3.5, auditoría
    CANSLIM 19-20/07/2026.
    """
    if len(hist) < 20:
        return 'C'
    recent = hist.tail(20)
    rango = recent['High'] - recent['Low']
    # Multiplicador -1 (cierre en el mínimo del día) a +1 (cierre en el
    # máximo). Días sin rango (High==Low, rarísimo con datos reales) se
    # tratan como neutros en vez de dividir por cero.
    multiplicador = ((recent['Close'] - recent['Low']) - (recent['High'] - recent['Close'])) / rango
    multiplicador = multiplicador.replace([float('inf'), float('-inf')], 0).fillna(0)
    flujo_ponderado = (multiplicador * recent['Volume']).sum()
    volumen_total   = recent['Volume'].sum()
    if volumen_total == 0:
        return 'C'
    # flujo_ponderado/volumen_total va de -1 (distribución pura) a +1
    # (acumulación pura) -- reescalado a 0-1 para reutilizar los mismos
    # umbrales de siempre (antes "ratio" era up_vol/total, con el mismo
    # rango 0-1).
    ratio = (flujo_ponderado / volumen_total + 1) / 2
    if ratio >= 0.70: return 'A'
    if ratio >= 0.58: return 'B'
    if ratio >= 0.45: return 'C'
    if ratio >= 0.35: return 'D'
    return 'E'


def trend_template(hist: pd.DataFrame, price: float) -> dict:
    """Trend Template de Minervini — 7 condiciones, se aprueba con 5.

    Movido aquí tal cual desde canslim_service.py (01/08/2026) para que el
    scan nocturno y el análisis individual dejen de usar definiciones
    distintas de «tendencia» — ver la cabecera del módulo. La fórmula no
    cambia ni un carácter respecto a la que ya usaba el análisis, que es
    la que alimenta la letra L de CAN SLIM.
    """
    n = len(hist)
    closes = hist['Close']

    ma50  = float(closes.tail(50).mean())  if n >= 50  else price
    ma150 = float(closes.tail(150).mean()) if n >= 150 else ma50
    ma200 = float(closes.tail(200).mean()) if n >= 200 else ma150

    # 200 MA trend (slope over last 20 days)
    if n >= 220:
        ma200_20ago = float(closes.iloc[-220:-20].tail(200).mean())
        ma200_rising = ma200 > ma200_20ago
    else:
        # Antes: True por defecto -- sesgo optimista, daba por buena una
        # condición que en realidad no se puede verificar por falta de
        # histórico (típico en salidas a bolsa recientes). El resto de
        # condiciones del Trend Template exigen datos reales para pasar;
        # esta debe tratarse igual: si no se puede comprobar, no se
        # concede. Ver conversación 19/07/2026.
        ma200_rising = False

    high_52w = float(closes.tail(252).max()) if n >= 252 else float(closes.max())
    low_52w  = float(closes.tail(252).min()) if n >= 252 else float(closes.min())

    pct_from_high = ((price - high_52w) / high_52w * 100) if high_52w > 0 else -100

    conditions = {
        "Precio > MA150 y MA200":    bool(price > ma150 and price > ma200),
        "MA150 > MA200":             bool(ma150 > ma200),
        "MA200 subiendo (20d)":      bool(ma200_rising),
        "MA50 > MA150 y MA200":      bool(ma50 > ma150 and ma50 > ma200),
        "Precio > MA50":             bool(price > ma50),
        ">30% sobre mínimo 52s":     bool(price >= low_52w * 1.30),
        "< 25% del máximo 52s":      bool(pct_from_high >= -25),
    }

    score  = sum(conditions.values())
    passed = score >= 5

    return {
        "passed":      passed,
        "score":       score,
        "conditions":  conditions,
        "ma50":        round(ma50, 2),
        "ma150":       round(ma150, 2),
        "ma200":       round(ma200, 2),
        "high_52w":    round(high_52w, 2),
        "low_52w":     round(low_52w, 2),
        "pct_from_high": round(pct_from_high, 1),
    }


def technical_score(rs, trend_passed: bool, trend_score: int, acc_dis: str,
                    near_new_high: bool, vol_ratio: float) -> int:
    """Score técnico 0-100 — la parte de CAN SLIM que se puede evaluar sin
    fundamentales. Movido aquí tal cual desde canslim_service.py
    (01/08/2026); el scan usaba antes su propia versión con otros pesos,
    sin crédito parcial y con perf_12m contado dos veces (ver cabecera).

    `rs` puede ser None: sin percentil real no hay componente RS, y el
    resto se reescala proporcionalmente a /100 en vez de tratar el hueco
    como un cero — mismo criterio que el score fundamental, y el mismo
    que evita en todo el proyecto rellenar un dato ausente con un número
    que parece real.

    perf_12m NO entra aquí a propósito: el RS ya es su percentil dentro
    del universo, así que sumarlo aparte sería contar el mismo dato dos
    veces.
    """
    sub, maximo = [], 0
    if rs is not None:
        sub.append(25 if rs >= 80 else (15 if rs >= 70 else 0));                   maximo += 25
    sub.append(25 if trend_passed else (10 if trend_score >= 4 else 0));           maximo += 25
    sub.append(20 if acc_dis in ('A', 'B') else (10 if acc_dis == 'C' else 0));    maximo += 20
    sub.append(15 if near_new_high else 0);                                        maximo += 15
    sub.append(15 if vol_ratio >= 1.5 else (8 if vol_ratio >= 1.0 else 0));        maximo += 15
    return min(100, int(sum(sub) / maximo * 100)) if maximo > 0 else 0
