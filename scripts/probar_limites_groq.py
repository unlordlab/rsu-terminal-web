"""¿El techo de fichas de SALIDA es de la cuenta o del modelo? Una llamada por modelo.

POR QUÉ EXISTE ESTO. El 07/09/2026 el briefing murió con un 429 por un límite
de "output tokens per minute (OTPM): Limit 1000" que **la página de límites de
la consola no muestra**: ahí solo hay una columna «Tokens per Minute», que es
otra cosa (entrada+salida) y que ese día estaba entera libre. O sea que el
único tope que importa no se puede consultar, solo provocar.

QUÉ MIDE. Pide `max_tokens` en DOS niveles a cada modelo candidato -- 1445,
que es lo que Groq rechazó, y 2000, que es lo que necesita Elia-- con un
prompt de dos líneas y pidiendo una respuesta de UNA palabra. Así lo único que
se pone a prueba es si el techo SOLICITADO se acepta, sin gastar presupuesto
real de salida.

SON DOS CONSUMIDORES, no uno. El briefing sobrevive al techo escribiendo un
tercio menos. Elia no: una lección completa de la Academia son 1.586 fichas de
mediana y 1.935 en el p90 --medido sobre los 149 bloques reales--, así que con
950 solo cabría el 6% de ellas. Un modelo puede servir para el briefing y
dejar a Elia fuera igualmente.

CÓMO LEER EL RESULTADO:
  · Si TODOS dan 429 por OTPM -> el techo es de la organización. No hay
    alternativa gratuita: o briefing corto o plan de pago.
  · Si alguno acepta 1445 -> el techo es del modelo y el briefing se salva
    cambiando de modelo, gratis.
  · Si además acepta 2000 -> Elia también se salva. Si no, Elia hay que
    rehacerla para que escriba la lección por partes.

Uso (la clave no pasa por ningún sitio más que tu terminal):

    set GROQ_API_KEY=...        (cmd)   /   $env:GROQ_API_KEY="..."  (PowerShell)
    python scripts/probar_limites_groq.py
"""
import json
import os
import sys
import time

import requests

CLAVE = os.environ.get("GROQ_API_KEY", "")

# Dos niveles, porque hay DOS consumidores de Groq con necesidades distintas:
#
#   1445 — lo que pidió el briefing el 07/09 y Groq rechazó. Reproducirlo es
#          el objetivo, así que no se toca.
#   2000 — lo que necesita Elia. Medido el 07/09 sobre los 149 bloques reales
#          de `academy_lessons.js`: una lección completa son 1.586 fichas de
#          mediana y 1.935 en el p90. Elia pide 3000 desde siempre.
#
# Hace falta probar los dos: un modelo puede aceptar el del briefing y seguir
# dejando a Elia fuera, y entonces la decisión no es la misma.
NIVELES = [
    (1445, "briefing"),
    (2000, "Elia (p90 de una leccion real)"),
]

# Los de la tabla de la consola que pueden escribir prosa. Se dejan fuera los
# dos `llama-prompt-guard` (son clasificadores) y `allam-2-7b` (6K TPM, peor
# que el actual, y orientado al árabe).
CANDIDATOS = [
    ("qwen/qwen3.6-27b",   "el actual, Preview, 8K TPM"),
    ("openai/gpt-oss-120b", "Production, 8K TPM, 4-5x mas barato si algun dia se paga"),
    ("qwen/qwen3.8-27b",   "hermano mayor del actual, 8K TPM"),
    ("openai/gpt-oss-20b", "Production, 8K TPM, mas pequeno"),
    ("groq/compound",      "70K TPM y sin tope diario, pero es un sistema AGENTICO"),
    ("groq/compound-mini", "70K TPM y sin tope diario, version reducida"),
]

PROMPT = "Responde con una sola palabra: hola"


def probar(modelo: str, max_tokens: int) -> dict:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {CLAVE}", "Content-Type": "application/json"},
        json={
            "model":      modelo,
            "messages":   [{"role": "user", "content": PROMPT}],
            "max_tokens": max_tokens,
        },
        timeout=60,
    )
    cabeceras = {k.lower(): v for k, v in r.headers.items()
                 if k.lower().startswith("x-ratelimit")}
    return {"status": r.status_code, "texto": r.text[:300], "cabeceras": cabeceras}


def veredicto_de(res: dict) -> str:
    if res["status"] == 200:
        return "ACEPTA"
    if res["status"] == 429 and "OTPM" in res["texto"]:
        return "RECHAZA por OTPM"
    if res["status"] == 429:
        return "429 por otra cosa (mirar el texto)"
    if res["status"] == 404:
        return "modelo no habilitado en la cuenta"
    return f"HTTP {res['status']}"


def main():
    if not CLAVE:
        print("Falta GROQ_API_KEY en el entorno. Ver el uso arriba.")
        return 2

    print(f"Probando {len(CANDIDATOS)} modelos x {len(NIVELES)} niveles de salida.")
    print("Prompt minimo y respuesta de una palabra: lo unico que se mide es si")
    print("el techo SOLICITADO se acepta.\n")

    resultados = {}
    llamadas = [(m, n, tope, etiqueta)
                for m, n in CANDIDATOS for tope, etiqueta in NIVELES]

    for i, (modelo, nota, tope, etiqueta) in enumerate(llamadas):
        try:
            res = probar(modelo, tope)
        except Exception as e:
            print(f"  {modelo:<22} {tope:>5}  ERROR DE RED: {type(e).__name__}: {e}")
            continue

        resultados.setdefault(modelo, {})[str(tope)] = res
        print(f"  {modelo:<22} {tope:>5}  {veredicto_de(res)}   [{etiqueta}]")
        for k, v in sorted(res["cabeceras"].items()):
            print(f"  {'':<30}{k}: {v}")
        if res["status"] not in (200, 404):
            print(f"  {'':<30}{res['texto'][:180]}")

        # El tope es POR MINUTO: si una llamada cuela y consume salida, la
        # siguiente podria fallar por presupuesto agotado y no por el techo,
        # que es justo la confusion que se quiere evitar.
        if i < len(llamadas) - 1:
            time.sleep(20)

    def acepta(modelo, tope):
        r = resultados.get(modelo, {}).get(str(tope))
        return bool(r) and r["status"] == 200

    print("\n" + "=" * 70)
    sirven_briefing = [m for m, _ in CANDIDATOS if acepta(m, NIVELES[0][0])]
    sirven_elia     = [m for m, _ in CANDIDATOS if acepta(m, NIVELES[1][0])]

    print("Aceptan el briefing largo (1445):", ", ".join(sirven_briefing) or "NINGUNO")
    print("Aceptan lo que necesita Elia (2000):", ", ".join(sirven_elia) or "NINGUNO")
    print()
    if not sirven_briefing:
        print("EL TECHO ES DE LA ORGANIZACION: no lo salva ningun modelo.")
        print("No hay alternativa gratuita. Briefing corto o plan de pago, y Elia")
        print("no funciona en ninguno de los dos casos sin rediseno.")
    elif sirven_elia:
        print("EL TECHO ES POR MODELO, y hay al menos uno que sirve para los dos.")
        print("Cambiar de modelo recupera briefing largo Y Elia, sin pagar nada.")
    else:
        print("EL TECHO ES POR MODELO pero ninguno llega a lo que pide Elia.")
        print("El briefing se salva cambiando de modelo; Elia hay que rehacerla")
        print("para que escriba la leccion por partes.")

    destino = "limites_groq_medidos.json"
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    print(f"\nDetalle completo en {destino}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
