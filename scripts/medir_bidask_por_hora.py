"""
Dos mediciones que solo se pueden hacer CON EL MERCADO ABIERTO, y de las que
dependen dos decisiones pendientes de Options Flow.

Se juntan en un solo script a propósito: las dos exigen una sesión real, y una
sola pasada por la tarde responde a las dos en vez de tener que repetir el
viaje.

────────────────────────────────────────────────────────────────────────────
MEDICIÓN 1 — ¿a qué hora hay precios de compra y venta? (hallazgo #29)
────────────────────────────────────────────────────────────────────────────
Desde el 18/08/2026, una operación de la que no se puede saber si fue compra o
venta ya no se publica (hallazgo #1: el antiguo `vol/OI >= 0.3` no medía
dirección, medía actividad nueva frente a posiciones existentes). Eso convierte
la HORA del escaneo en una decisión con consecuencias: si Yahoo no da bid/ask a
esa hora, no es que se publiquen señales dudosas -- es que no se publica casi
nada.

Y la hora actual no se eligió por ese motivo. El cron corre a las 23:00 UTC =
19:00 ET, tres horas después del cierre, y se puso ahí por ser el siguiente
hueco libre tras Thematic (22:00), Scanner (22:15), RS/RW (22:30) y CANSLIM
(22:45).

Ya medido: en premarket (05:20 ET) la cadena viene prácticamente vacía, incluida
AAPL. Y del escaneo real del 17/08, solo el 47,4% de las entradas tenían
bid/ask. Falta el resto de la curva.

────────────────────────────────────────────────────────────────────────────
MEDICIÓN 2 — ¿merece la pena escanear más allá del S&P 500? (Russell 2000)
────────────────────────────────────────────────────────────────────────────
El repo ya tiene 1.958 tickers del Russell 2000 (scanner_universe.py), hoy
usados solo para amplitud de mercado. La pregunta es si añadirlos al escaneo de
opciones aporta algo, y si cabe en el tiempo disponible.

Lo que se sabe apunta a que la mayoría NO aportaría nada: de los 46 tickers de
la cartera, solo 13 tienen algún contrato con OI >= 100 (hallazgo #31). Si esa
proporción se repite, escanear 1.958 valores costaría casi una hora para que la
inmensa mayoría no genere ni una entrada, porque MIN_VOLUME/MIN_OI los cortan.

Sobre el coste: medido el 18/08, en SERIE con pausa corta se leyeron 348
tickers seguidos sin que Yahoo cortara la IP, a ~1,2 s cada uno. El límite es
de ritmo, no de volumen total -- pero eso se midió con 348, no con miles, así
que este script mide también el ritmo real sobre la muestra.

Los tres números que hacen falta para decidir:
  · cuántos del Russell tienen cadena de opciones,
  · cuántos tienen algún contrato que pase los filtros REALES del escaneo
    (MIN_VOLUME=200 y MIN_OI=100) -- ese es el que decide si aportan o no,
  · cuánto tarda cada uno en serie, para extrapolar a 1.958.

────────────────────────────────────────────────────────────────────────────
CÓMO USARLO
────────────────────────────────────────────────────────────────────────────
Ejecutarlo varias veces a lo largo de UNA sesión real. Las horas que interesan:

    16:15 ET  (justo tras el cierre)
    17:00 ET
    19:00 ET  (la hora actual del escaneo -- el punto de comparación)
    22:00 ET

    python scripts/medir_bidask_por_hora.py            # las dos mediciones
    python scripts/medir_bidask_por_hora.py --solo-horario   # solo la 1 (rápida)

Cada ejecución añade una línea a cada CSV, con la hora de Nueva York, para
poder comparar las cuatro de un vistazo al final. Los CSV no se versionan (van
en .gitignore): el script sí, sus resultados dependen del día.

La muestra del Russell es FIJA (semilla 42) para que las cuatro horas sean
comparables entre sí: si cambiara de valores en cada pasada, las diferencias
podrían ser de la muestra y no de la hora.

NO decidir sin estos números. El 18/08 un diagnóstico plausible sobre este
mismo módulo costó un arreglo entero que recuperó 0 de 234.
"""
import csv
import os
import random
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.path.insert(0, os.path.join(AQUI, "..", "shared"))

# Muestra deliberadamente variada: mega caps muy líquidas, un par de ETF, y
# valores medianos/pequeños. Si solo se miraran las mega caps, el resultado
# saldría mejor de lo que es para el universo real de ~579 tickers.
TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META",      # mega caps
    "SPY", "QQQ", "IWM",                          # ETF
    "AMD", "INTC", "BAC", "F",                    # grandes menos calientes
    "SOFI", "PLTR", "AMAT",                       # medianas
]

# Los MISMOS cortes que usa el escaneo real (backend/services/options_service).
# Si allí cambian, aquí también, o la medición deja de responder a la pregunta.
MIN_OI = 100
MIN_VOLUME = 200
N_VENCIMIENTOS = 2      # con dos basta para la foto; el escaneo real usa 5

N_MUESTRA_RUSSELL = 60
SEMILLA = 42            # muestra fija: las 4 horas tienen que ser comparables
PAUSA_SERIE = 0.6       # la misma pausa que usa la segunda pasada del escaneo

CSV_HORARIO = os.path.join(AQUI, "medir_bidask_por_hora.csv")
CSV_RUSSELL = os.path.join(AQUI, "medir_russell_opciones.csv")


def _num(v) -> float:
    """None/NaN -> 0.0. Yahoo devuelve NaN en volumen fuera de sesión."""
    try:
        f = float(v)
        return 0.0 if f != f else f
    except (TypeError, ValueError):
        return 0.0


# ── Medición 1: disponibilidad de bid/ask por hora ───────────────────────────

def medir_horario() -> dict:
    total = con_bidask = con_volumen = 0
    fallos = []
    por_ticker = []

    for t in TICKERS:
        tk = yf.Ticker(t)
        try:
            vencimientos = tk.options[:N_VENCIMIENTOS]
        except Exception as e:
            fallos.append(f"{t}:{type(e).__name__}")
            continue
        if not vencimientos:
            fallos.append(f"{t}:sin-vencimientos")
            continue

        n = c = v = 0
        for exp in vencimientos:
            try:
                cadena = tk.option_chain(exp)
            except Exception as e:
                fallos.append(f"{t}/{exp}:{type(e).__name__}")
                continue
            for df in (cadena.calls, cadena.puts):
                for _, fila in df.iterrows():
                    # El denominador es todo contrato con open interest real:
                    # es el universo del que el escaneo saca sus entradas.
                    if _num(fila.get("openInterest")) < MIN_OI:
                        continue
                    n += 1
                    if _num(fila.get("volume")) > 0:
                        v += 1
                    bid, ask = _num(fila.get("bid")), _num(fila.get("ask"))
                    if bid > 0 and ask > bid:
                        c += 1

        por_ticker.append((t, n, c, v))
        total += n; con_bidask += c; con_volumen += v

    return {"total": total, "con_bidask": con_bidask, "con_volumen": con_volumen,
            "fallos": fallos, "por_ticker": por_ticker}


# ── Medición 2: ¿aporta algo el Russell 2000? ────────────────────────────────

def hay_datos_de_sesion(r_horario: dict) -> bool:
    """¿Se puede medir siquiera lo que pasa a esta hora?

    El juez NO es la muestra del Russell, sino las mega caps de la medición 1:
    SPY, AAPL y compañía son los instrumentos más líquidos que existen, así que
    si ELLAS vienen sin contratos o sin volumen, no es que hoy no se opere --
    es que Yahoo no está sirviendo datos de sesión a esta hora.

    Sin esto, un "aportan: 0" fuera de sesión se guardaría en el CSV como si
    fuera un resultado, y meses después alguien leería «el Russell no aporta
    nada» cuando lo que pasó es que no se pudo mirar. Es el mismo tipo de
    número fabricado que este proyecto lleva meses quitando -- y la primera
    versión de este chequeo caía en ello: se conformaba con que UN contrato de
    toda la muestra tuviera volumen, y en premarket eso lo cumplía BAC él solo.
    """
    total = r_horario.get("total", 0)
    if total < 50:
        return False
    return r_horario.get("con_volumen", 0) / total >= 0.20


def medir_russell() -> dict:
    from scanner_universe import RUSSELL2000_TICKERS

    rng = random.Random(SEMILLA)
    muestra = rng.sample(list(RUSSELL2000_TICKERS), N_MUESTRA_RUSSELL)

    con_cadena = con_oi = aportan = 0
    sin_cadena = []
    ejemplos = []
    t0 = time.time()

    for t in muestra:
        tk = yf.Ticker(t)
        try:
            vencimientos = tk.options[:N_VENCIMIENTOS]
        except Exception:
            sin_cadena.append(t)
            time.sleep(PAUSA_SERIE)
            continue
        if not vencimientos:
            sin_cadena.append(t)
            time.sleep(PAUSA_SERIE)
            continue
        con_cadena += 1

        tiene_oi = False
        # "Aporta" = tiene al menos un contrato que pasaría los filtros REALES
        # del escaneo. Es la única definición que responde a la pregunta: un
        # ticker con cadena pero sin ningún contrato que pase no genera ni una
        # entrada, solo cuesta tiempo.
        aporta = False
        for exp in vencimientos:
            try:
                cadena = tk.option_chain(exp)
            except Exception:
                continue
            for df in (cadena.calls, cadena.puts):
                for _, fila in df.iterrows():
                    vol = _num(fila.get("volume"))
                    oi = _num(fila.get("openInterest"))
                    if oi >= MIN_OI:
                        tiene_oi = True
                        if vol >= MIN_VOLUME:
                            aporta = True
        if tiene_oi:
            con_oi += 1
        if aporta:
            aportan += 1
            if len(ejemplos) < 12:
                ejemplos.append(t)
        time.sleep(PAUSA_SERIE)

    transcurrido = time.time() - t0
    return {"muestra": len(muestra), "con_cadena": con_cadena, "con_oi": con_oi,
            "aportan": aportan, "sin_cadena": sin_cadena, "ejemplos": ejemplos,
            "segundos": transcurrido,
            "seg_por_ticker": transcurrido / len(muestra) if muestra else 0}


# ── Salida ───────────────────────────────────────────────────────────────────

def _anotar(ruta, cabecera, fila):
    nuevo = not os.path.exists(ruta)
    with open(ruta, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if nuevo:
            w.writerow(cabecera)
        w.writerow(fila)
    print(f"\nAnotado en {ruta}")
    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            print("  " + linea.rstrip())


def main():
    solo_horario = "--solo-horario" in sys.argv
    ahora = datetime.now(ZoneInfo("America/New_York"))
    print(f"Hora de Nueva York: {ahora:%Y-%m-%d %H:%M %Z}\n")

    # ── 1 ──
    print(f"[1/2] Bid/ask por hora: {len(TICKERS)} valores, "
          f"{N_VENCIMIENTOS} vencimientos, OI >= {MIN_OI}...\n")
    r = medir_horario()
    for t, n, c, v in r["por_ticker"]:
        pct = c / n * 100 if n else 0
        print(f"  {t:6} contratos {n:4} | con bid/ask {c:4} ({pct:5.1f}%) | con volumen {v:4}")

    total, con = r["total"], r["con_bidask"]
    pct = con / total * 100 if total else 0
    print(f"\n  === {ahora:%H:%M} ET: {con}/{total} con bid/ask ({pct:.1f}%) "
          f"| con volumen: {r['con_volumen']} ===")
    if r["fallos"]:
        print(f"  Fallos: {len(r['fallos'])} -> {r['fallos'][:8]}")
    if total == 0:
        print("\n  ATENCION: cero contratos con open interest. Yahoo esta devolviendo\n"
              "  la cadena vacia a esta hora -- que en si mismo ES el resultado, y hay\n"
              "  que anotarlo igual (no es un fallo del script).")

    _anotar(CSV_HORARIO,
            ["fecha_et", "hora_et", "contratos_con_oi", "con_bidask", "pct_bidask",
             "con_volumen", "n_fallos"],
            [f"{ahora:%Y-%m-%d}", f"{ahora:%H:%M}", total, con, round(pct, 1),
             r["con_volumen"], len(r["fallos"])])

    if solo_horario:
        print("\n(--solo-horario: no se mide el Russell)")
        return

    # ── 2 ──
    print(f"\n[2/2] Russell 2000: muestra fija de {N_MUESTRA_RUSSELL}, "
          f"en serie con {PAUSA_SERIE}s de pausa. Tarda unos "
          f"{N_MUESTRA_RUSSELL * 2:.0f}-{N_MUESTRA_RUSSELL * 4:.0f}s...\n")
    q = medir_russell()
    m = q["muestra"]
    q["algun_volumen"] = hay_datos_de_sesion(r)
    print(f"  con cadena de opciones : {q['con_cadena']:3}/{m} ({q['con_cadena']/m*100:.0f}%)")
    print(f"  con algun OI >= {MIN_OI}    : {q['con_oi']:3}/{m} ({q['con_oi']/m*100:.0f}%)")
    if q["algun_volumen"]:
        print(f"  APORTAN (pasan filtros): {q['aportan']:3}/{m} ({q['aportan']/m*100:.0f}%)  <- el que decide")
    else:
        print("  APORTAN (pasan filtros): NO MEDIBLE a esta hora -- Yahoo devuelve el")
        print("                           volumen vacio en toda la cadena. El cero que")
        print("                           saldria aqui NO significa 'no aportan'.")
    if q["ejemplos"]:
        print(f"  ejemplos que aportan   : {q['ejemplos']}")
    print(f"  ritmo                  : {q['seg_por_ticker']:.2f}s por ticker en serie")

    # Extrapolación al universo entero, que es lo que hay que decidir.
    n_r2k = 1958
    utiles = q["aportan"] / m * n_r2k if (m and q["algun_volumen"]) else None
    coste_todos = n_r2k * q["seg_por_ticker"] / 60
    print(f"\n  === Extrapolado a los {n_r2k} del Russell 2000 ===")
    print(f"  escanearlos TODOS : ~{coste_todos:.0f} min  (presupuesto actual: 20 min)")
    if coste_todos > 20:
        print("  -> escanear el Russell entero NO cabe en el presupuesto.")
    if utiles is None:
        print("  aportarian algo   : SIN MEDIR -- hace falta el mercado abierto.")
        print("                      Volver a correr esto en sesion antes de decidir nada.")
    else:
        coste_utiles = utiles * q["seg_por_ticker"] / 60
        print(f"  aportarian algo   : ~{utiles:.0f} valores")
        print(f"  escanear solo los que aportan: ~{coste_utiles:.0f} min")
        if utiles and coste_utiles <= 20:
            print("  -> filtrar primero y escanear solo los utiles SI cabria.")

    _anotar(CSV_RUSSELL,
            ["fecha_et", "hora_et", "muestra", "con_cadena", "con_oi", "aportan",
             "pct_aportan", "volumen_disponible", "seg_por_ticker",
             "utiles_extrapolados", "min_todos"],
            [f"{ahora:%Y-%m-%d}", f"{ahora:%H:%M}", m, q["con_cadena"], q["con_oi"],
             q["aportan"] if q["algun_volumen"] else "SIN-MEDIR",
             round(q["aportan"] / m * 100, 1) if (m and q["algun_volumen"]) else "SIN-MEDIR",
             "si" if q["algun_volumen"] else "NO",
             round(q["seg_por_ticker"], 2),
             round(utiles) if utiles is not None else "SIN-MEDIR",
             round(coste_todos)])


if __name__ == "__main__":
    sys.exit(main())
