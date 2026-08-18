"""
¿A qué hora del día hay precios de compra y venta en las cadenas de opciones?

PARA QUÉ ES ESTO. Desde el 18/08/2026, una operación de la que no se puede
saber si fue compra o venta ya no se publica en Options Flow (hallazgo #1: el
antiguo `vol/OI >= 0.3` no medía dirección, medía actividad nueva frente a
posiciones existentes). Eso convierte la HORA del escaneo en una decisión con
consecuencias: si Yahoo no da bid/ask a esa hora, no es que se publiquen
señales dudosas -- es que no se publica casi nada.

Y la hora actual no se eligió por ese motivo. El cron corre a las 23:00 UTC =
19:00 ET, tres horas después del cierre, y se puso ahí por ser el siguiente
hueco libre tras Thematic (22:00), Scanner (22:15), RS/RW (22:30) y CANSLIM
(22:45). Ver hallazgo #29 en ESTADO_REAL.md.

Lo que ya se sabe, medido: en premarket (4:45 ET) Yahoo devuelve bid=0, ask=0 Y
openInterest=0 en la cadena ENTERA, incluida AAPL. Y del escaneo real del
17/08, solo el 47,4% de las entradas tenían bid/ask. Falta el resto de la
curva.

CÓMO USARLO. Hay que ejecutarlo VARIAS VECES A LO LARGO DE UNA SESIÓN REAL de
mercado, y anotar los resultados. Las horas que interesan:

    16:15 ET  (justo tras el cierre)
    17:00 ET
    19:00 ET  (la hora actual del escaneo -- el punto de comparación)
    22:00 ET

    python scripts/medir_bidask_por_hora.py

Cada ejecución añade una línea a scripts/medir_bidask_por_hora.csv, con la hora
de Nueva York, para poder comparar las cuatro de un vistazo al final.

QUÉ HACER CON EL RESULTADO. Si alguna hora da bastante más bid/ask que las
19:00, se puede mover el cron de .github/workflows/options_scan.yml -- pero
mirando también el otro lado: acercarse al cierre lo pega a los otros cuatro
escaneos nocturnos y al límite de peticiones de Yahoo, que ya nos cortó la IP
entera una vez (hallazgo #28). No es solo elegir el máximo de esta tabla.

NO decidir sin estos números. El 18/08 un diagnóstico plausible sobre este
mismo módulo costó un arreglo entero que recuperó 0 de 234.
"""
import csv
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

import yfinance as yf

# Muestra deliberadamente variada: mega caps muy líquidas, un par de ETF, y
# valores medianos/pequeños. Si solo se miraran las mega caps, el resultado
# saldría mejor de lo que es para el universo real de ~579 tickers.
TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META",      # mega caps
    "SPY", "QQQ", "IWM",                          # ETF
    "AMD", "INTC", "BAC", "F",                    # grandes menos calientes
    "SOFI", "PLTR", "AMAT",                       # medianas
]

MIN_OI = 100          # mismo corte que usa el escaneo real (options_service)
N_VENCIMIENTOS = 2    # con dos basta para la foto; el escaneo real usa hasta 5

CSV = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "medir_bidask_por_hora.csv")


def medir() -> dict:
    total = con_bidask = con_volumen = con_oi = 0
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

        n = c = v = o = 0
        for exp in vencimientos:
            try:
                cadena = tk.option_chain(exp)
            except Exception as e:
                fallos.append(f"{t}/{exp}:{type(e).__name__}")
                continue
            for df in (cadena.calls, cadena.puts):
                for _, fila in df.iterrows():
                    oi = _num(fila.get("openInterest"))
                    if oi >= MIN_OI:
                        o += 1
                    # El denominador es TODO contrato con open interest real:
                    # es el universo del que el escaneo saca sus entradas.
                    if oi < MIN_OI:
                        continue
                    n += 1
                    if _num(fila.get("volume")) > 0:
                        v += 1
                    bid, ask = _num(fila.get("bid")), _num(fila.get("ask"))
                    if bid > 0 and ask > bid:
                        c += 1

        por_ticker.append((t, n, c, v))
        total += n; con_bidask += c; con_volumen += v; con_oi += o

    return {"total": total, "con_bidask": con_bidask, "con_volumen": con_volumen,
            "fallos": fallos, "por_ticker": por_ticker}


def _num(v) -> float:
    """None/NaN -> 0.0. Yahoo devuelve NaN en volumen fuera de sesión."""
    try:
        f = float(v)
        return 0.0 if f != f else f
    except (TypeError, ValueError):
        return 0.0


def main():
    ahora_et = datetime.now(ZoneInfo("America/New_York"))
    print(f"Hora de Nueva York: {ahora_et:%Y-%m-%d %H:%M %Z}")
    print(f"Midiendo {len(TICKERS)} valores, {N_VENCIMIENTOS} vencimientos, OI >= {MIN_OI}...\n")

    r = medir()
    for t, n, c, v in r["por_ticker"]:
        pct = c / n * 100 if n else 0
        print(f"  {t:6} contratos {n:4} | con bid/ask {c:4} ({pct:5.1f}%) | con volumen {v:4}")

    total, con = r["total"], r["con_bidask"]
    pct = con / total * 100 if total else 0
    print(f"\n=== {ahora_et:%H:%M} ET: {con}/{total} con bid/ask ({pct:.1f}%) "
          f"| con volumen: {r['con_volumen']} ===")
    if r["fallos"]:
        print(f"Fallos: {len(r['fallos'])} -> {r['fallos'][:8]}")
    if total == 0:
        print("\nATENCION: cero contratos con open interest. Yahoo esta devolviendo\n"
              "la cadena vacia a esta hora -- que en si mismo ES el resultado, y hay\n"
              "que anotarlo igual (no es un fallo del script).")

    nuevo = not os.path.exists(CSV)
    with open(CSV, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if nuevo:
            w.writerow(["fecha_et", "hora_et", "contratos_con_oi", "con_bidask",
                        "pct_bidask", "con_volumen", "n_fallos"])
        w.writerow([f"{ahora_et:%Y-%m-%d}", f"{ahora_et:%H:%M}", total, con,
                    round(pct, 1), r["con_volumen"], len(r["fallos"])])
    print(f"\nAnotado en {CSV}")

    if os.path.exists(CSV):
        print("\nMediciones acumuladas:")
        with open(CSV, encoding="utf-8") as fh:
            for fila in fh:
                print("  " + fila.rstrip())


if __name__ == "__main__":
    sys.exit(main())
