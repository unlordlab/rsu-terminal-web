"""Genera el briefing de HOY con varios modelos y los deja lado a lado para elegir.

POR QUÉ NO SE DECIDE LEYENDO LA DOCUMENTACIÓN. Los tres candidatos tienen cada
uno una pega que solo se ve en el texto que producen:

  qwen/qwen3.6-27b   el actual. **Preview**: "for evaluation purposes only",
                     puede cambiar o retirarse con poco aviso — que es
                     exactamente lo que pasó el 07/09 con el techo de salida.
  openai/gpt-oss-120b  **Production** y más barato, pero NO admite
                     `reasoning_effort: "none"`: razona siempre, y ese
                     pensamiento cuenta dentro de `max_tokens`. Aquí ya hubo
                     un briefing de CERO palabras por eso. Hay que ver cuánto
                     presupuesto se come de verdad.
  groq/compound      **Production** y con 70.000 TPM (8,75× lo de ahora), que
                     haría innecesaria la escalera de recorte entera. Pero es
                     agéntico y su búsqueda web no se puede apagar, solo acotar
                     por dominio. Hay que ver SI busca, DÓNDE, y si lo que
                     escribe sigue siendo trazable.

QUÉ HACE. Construye el prompt real de hoy UNA vez -- los mismos datos para
todos, que si no la comparación no vale-- y lo manda a cada modelo. De cada uno
guarda el texto, el sesgo, las fichas que gastó, si salió cortado y, en los
`compound`, TODO lo que fueron a buscar.

QUÉ MIRAR AL LEER EL RESULTADO:
  1. ¿Hay algún número en el texto que no esté en los datos de entrada? Ese es
     el fallo que más veces se ha corregido en este briefing.
  2. En compound: `herramientas_usadas`. ¿Buscó? ¿En los medios de la lista?
  3. ¿Cuántas fichas de salida gastó cada uno? Los que razonan gastan de más.
  4. ¿Se corta a mitad de frase? ¿Sale la línea `SESGO:`?

NO PUBLICA NADA. No toca el Gist ni el briefing en producción: escribe ficheros
en el directorio actual y ya.

Uso (en el VPS, que es donde está la clave):

    cd ~/rsu-terminal-web
    set -a && . ./.env && set +a
    python3 scripts/comparar_modelos_briefing.py

    # o solo algunos:
    python3 scripts/comparar_modelos_briefing.py groq/compound qwen/qwen3.6-27b
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import daily_briefing as B  # noqa: E402

CANDIDATOS = [
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-120b",
    "groq/compound",
]


def construir_prompt_de_hoy():
    """El prompt real, con los datos reales. Se construye UNA vez y se reutiliza
    para todos: comparar textos hechos con datos distintos no dice nada."""
    print("Recogiendo los datos de hoy (mercado, noticias, amplitud, macro)...")
    market_data      = B.get_market_data()
    news             = B.get_market_news()
    major            = B.get_major_outlet_headlines()
    earnings         = B.get_notable_earnings()
    breadth          = B.get_rsu_breadth_signals()
    insiders         = B.get_insider_clusters()
    historial        = B.get_briefing_history()
    sesgos           = B.get_bias_history()
    macro            = B.get_macro_indicators()

    # QUE BLOQUES HAN LLEGADO Y CUALES NO. El briefing esta hecho para
    # degradarse sin morirse, asi que un bloque vacio no da error: se nota solo
    # en que el texto sale mas pobre. Para una comparacion da igual --los tres
    # modelos reciben lo mismo-- pero hay que SABERLO al leer el resultado.
    print("\nDatos recogidos:")
    for nombre, dato in [("precios", market_data), ("noticias", news),
                         ("medios internacionales", major), ("resultados", earnings),
                         ("amplitud", breadth), ("insiders", insiders),
                         ("historial", historial), ("macro", macro)]:
        cuantos = len(dato) if isinstance(dato, (list, dict)) else 0
        print(f"  {nombre:<24} {cuantos if cuantos else 'VACIO'}")

    # El nivel de recorte que main() acabaría usando: el primero que quepa.
    for nivel in B.NIVELES_RECORTE:
        prompt = B.build_prompt(market_data, news, major, earnings, breadth,
                                insiders, historial, sesgos, macro, recorte=nivel)
        if B.estimar_tokens(prompt) <= B.TECHO_PROMPT:
            print(f"Nivel de recorte '{nivel['nombre']}' "
                  f"(~{B.estimar_tokens(prompt)} fichas de prompt)")
            return prompt, market_data
    print(f"Ni el nivel mas agresivo cabe; se usa ese igualmente "
          f"(~{B.estimar_tokens(prompt)} fichas)")
    return prompt, market_data


def main():
    if not B.GROQ_KEY:
        print("Falta GROQ_API_KEY en el entorno. Ver el uso arriba.")
        return 2

    modelos = sys.argv[1:] or CANDIDATOS
    prompt, market_data = construir_prompt_de_hoy()

    # EL PROMPT SE GUARDA. Sin el no se puede hacer la unica comprobacion que
    # importa de verdad: si un numero del briefing NO esta en los datos de
    # entrada, el modelo se lo ha inventado o lo ha ido a buscar por su cuenta.
    with open("prompt_usado.txt", "w", encoding="utf-8") as f:
        f.write(prompt)
    print(f"\nPrompt exacto guardado en prompt_usado.txt "
          f"({len(prompt)} caracteres) — es contra esto contra lo que hay que "
          f"auditar cada cifra de los briefings")

    resultados = {}
    for i, modelo in enumerate(modelos):
        print(f"\n{'=' * 70}\n{modelo}\n{'=' * 70}")
        B.MODEL = modelo                     # lo que lee generate_briefing
        arranque = time.time()
        try:
            texto, diag = B.generate_briefing(prompt)
        except Exception as e:
            print(f"FALLO: {type(e).__name__}: {e}")
            resultados[modelo] = {"error": f"{type(e).__name__}: {e}"}
            continue
        tardanza = round(time.time() - arranque, 1)

        cuerpo, sesgo = B.extract_bias_tag(texto)
        resultados[modelo] = {
            "segundos":     tardanza,
            "palabras":     len(cuerpo.split()),
            "sesgo":        sesgo,
            "truncado":     diag.get("truncado"),
            "diagnostico":  diag,
            "briefing":     cuerpo,
        }
        print(f"{len(cuerpo.split())} palabras · sesgo {sesgo or 'N/D'} · "
              f"{tardanza}s · cortado: {diag.get('truncado')}")
        herramientas = diag.get("herramientas_usadas")
        if herramientas:
            print(f"BUSCO POR SU CUENTA: {len(herramientas)} llamada(s) a herramientas"
                  f"{', ' + str(diag['herramientas_fuera_de_lista']) + ' FUERA de la lista de medios'
                    if diag.get('herramientas_fuera_de_lista') else ' (todas dentro de la lista)'}")
        print()
        print(cuerpo[:900] + ("..." if len(cuerpo) > 900 else ""))

        # El limite de Groq es por minuto y acabamos de gastar la salida entera.
        if i < len(modelos) - 1:
            print("\n(esperando 65 s: el limite de Groq es por minuto)")
            time.sleep(65)

    destino = "comparacion_modelos.json"
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 70}\nRESUMEN")
    for m, r in resultados.items():
        if "error" in r:
            print(f"  {m:<22} FALLO: {r['error'][:80]}")
        else:
            busco = r["diagnostico"].get("herramientas_usadas")
            print(f"  {m:<22} {r['palabras']:>4} palabras · sesgo {str(r['sesgo']):<8} · "
                  f"{r['segundos']:>5}s · cortado {str(r['truncado']):<5} · "
                  f"busco {len(busco) if busco else 0}")
    print(f"\nTexto completo y diagnostico de cada uno en {destino}")
    print("Lo importante no es cual escribe mas bonito: es si algun numero del")
    print("texto NO esta en los datos de entrada. Eso es lo que hay que mirar.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
