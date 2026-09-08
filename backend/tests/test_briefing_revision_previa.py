"""
Prohibir una frase en el prompt no impide que el modelo la escriba. Hay que mirar la salida.

EL CASO, 08/09/2026. El briefing publicado rompió TRES reglas, y una llevaba
CUATRO DÍAS escrita con todas las letras en el prompt que se le envió:

  1. «**No entro en largo** hasta que el VIX baje de 15» — el prompt dice, literal,
     `nada de "venderé", "no entro en largo", "mi cartera" ni "he cerrado"` (#44,
     04/09). Comprobado: la regla estaba en el prompt de ese día.
  2. «un cierre por encima de **7.750**» como nivel de invalidación, cuando el
     prompt da SMA20 7.708,70 · SMA50 7.591,71 · SMA200 7.141,76 · rango 20d
     7.611,20–7.816,70, y añade «nunca uno inventado».
  3. «cerca de **máximos históricos**», que la regla 12 prohíbe salvo que lo diga
     un titular — y ninguno lo decía. El propio rango de 20 días lo desmentía:
     con el techo en 7.816,70, ni siquiera estaba en máximos de 20 sesiones.

Más «+162k fueron **mejores de lo esperado**», sin una sola previsión en el
prompt y con la regla del consenso añadida el día anterior (#47).

LA LECCIÓN NO ES AFINAR LA REGLA. Las cuatro estaban ahí. Pedirle a un modelo
que no haga algo no garantiza que no lo haga; comprobar la SALIDA sí. Y cuesta
CERO fichas de prompt, que en un briefing que lleva semanas en modo «mínimo»
tampoco es menor.

QUÉ SE HACE AL ENCONTRAR ALGO. Se reintenta UNA vez diciéndole exactamente qué
rompió. Si en el reintento sigue habiendo una ORDEN DE OPERAR, se falla el
Action: publicar «no entro en largo» a ~100 personas que pagan es el único
fallo de esta lista que vale perder el briefing del día. Lo demás se publica y
queda anotado — medio briefing es mejor que ninguno (decisión de julio), y un
dato mal atribuido se corrige leyendo mientras que una orden no.

LO QUE NO PUEDE MARCAR, y es la mitad del trabajo: «mi lectura», «mi postura es
bajista», «esto me preocupa». El #44 fue explícito en que lo valioso del
briefing es que SE MOJA — si al quitar las órdenes se convierte en un informe
neutro, se cambia un problema por otro peor.

Uso:
    cd backend
    python -m pytest tests/test_briefing_revision_previa.py -v
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import daily_briefing as D  # noqa: E402

# Los niveles reales que tenía el prompt del 08/09.
PROMPT = ("S&P 500: Ultimo: 7,718.60 (+8.08% vs SMA200) | SMA20: 7,708.70 | SMA50: 7,591.71 | "
          "SMA200: 7,141.76 | Rango 20d: 7,611.20 - 7,816.70 | VIX: 15.74 | WTI: 93.91 | "
          "Nominas no agricolas +162k empleos | mes anterior +21k")
TITULARES = ('[{"titular": "Oil hits multi-week highs after Houthi attacks on Saudi energy facilities"}, '
             '{"titular": "Brent crude nears $100 after strikes on Saudi energy sites"}]')


def _rev(texto, prompt=PROMPT, titulares=TITULARES):
    return D.revisar_briefing(texto, prompt, titulares)


def _todo(r):
    return r["ordenes"] + r["otros"]


# ── Las cuatro del 08/09 ─────────────────────────────────────────────────────

def test_caza_la_orden_de_operar_que_se_publico():
    """EL test. La frase estaba prohibida en el prompt desde hacía cuatro días
    y se publicó igual."""
    r = _rev("El mercado está débil. No entro en largo hasta que el VIX baje de 15.")
    assert r["ordenes"], "se publicaría otra orden de operar a ~100 suscriptores"
    assert "no entro en largo" in r["ordenes"][0].lower()


def test_caza_el_nivel_de_invalidacion_inventado():
    """7.750 no es ninguno de los niveles que se le dieron, y es la línea más
    accionable del briefing."""
    r = _rev("La invalidación de mi tesis sería un cierre del S&P por encima de 7.750.")
    assert any("NIVEL INVENTADO" in x for x in r["otros"]), _todo(r)
    assert "7750" in " ".join(r["otros"]).replace(".", "")


def test_NO_marca_un_nivel_que_SI_sale_de_los_datos():
    """Si marcara los buenos, el aviso sería ruido diario y se dejaría de
    mirar — que es como muere cualquier alerta."""
    for nivel in ("7.708,70", "7.591,71", "7.816,70", "7708.70"):
        r = _rev(f"La invalidación sería un cierre por debajo de {nivel}.")
        assert not _todo(r), f"{nivel} está en los datos y se ha marcado: {_todo(r)}"


def test_caza_los_maximos_historicos_sin_titular():
    r = _rev("El índice se mantiene cerca de máximos históricos mientras sangra por dentro.")
    assert any("MAXIMOS" in x for x in r["otros"]), _todo(r)


def test_pero_los_ACEPTA_cuando_un_titular_lo_dice():
    """La regla 12 no prohíbe el superlativo: prohíbe inventárselo."""
    r = _rev("El oro marca máximos históricos según Reuters.",
             titulares='[{"titular": "Gold hits record high as investors flee to safety"}]')
    assert not any("MAXIMOS" in x for x in r["otros"]), _todo(r)


def test_caza_el_consenso_que_no_existe():
    """«mejores de lo esperado» sobre unas nóminas de las que solo se tiene el
    dato y el mes anterior."""
    r = _rev("Las nóminas de agosto (+162k) fueron mejores de lo esperado.")
    assert any("CONSENSO" in x for x in r["otros"]), _todo(r)


# ── Lo que NO puede marcar ───────────────────────────────────────────────────

def test_la_LECTURA_en_primera_persona_se_queda():
    """El #44 quitó la ORDEN y dejó la lectura a propósito: «si al quitar las
    operaciones se hubiera convertido en un informe neutro que no se compromete
    con nada, habríamos cambiado un problema por otro peor»."""
    for frase in ("Mi lectura es que el mercado pierde la batalla de la narrativa.",
                  "Mi postura es bajista hasta ver una consolidación real.",
                  "Esto me preocupa y no lo tengo claro.",
                  "Ayer me equivoqué y los datos de hoy lo demuestran."):
        assert not _todo(_rev(frase)), f"marcada una lectura legítima: {frase}"


def test_no_confunde_palabras_que_CONTIENEN_las_prohibidas():
    """`compro` dentro de «compromiso», `vender` dentro de «presión vendedora»:
    un patrón sin límites de palabra los cazaría a los dos."""
    for frase in ("El compromiso de la Fed con el 2% sigue intacto.",
                  "La presión vendedora domina la sesión.",
                  "Las expectativas de inflación implícitas suben 5 pb.",
                  "Los inversores venderán si pierde la SMA20."):
        assert not _todo(_rev(frase)), f"falso positivo: {frase}"


def test_un_briefing_limpio_no_dispara_nada():
    limpio = ("El S&P 500 cerró en 7.718,60, cayendo un 0,38%. El VIX subió a 15,74. "
              "Mi lectura es de cautela. La invalidación sería un cierre por encima "
              "de 7.816,70, el techo del rango de 20 días.")
    assert not _todo(_rev(limpio))


# ── Cómo separa lo grave de lo demás ─────────────────────────────────────────

def test_las_ordenes_van_APARTE_de_los_demas_avisos():
    """No cuestan lo mismo: una orden vale perder el briefing del día, un dato
    mal atribuido no. Si fueran la misma lista, o se pierde el briefing por una
    tontería o se publica una orden."""
    r = _rev("No entro en largo. Y el índice está en máximos históricos.")
    assert len(r["ordenes"]) == 1 and len(r["otros"]) == 1


def test_una_sola_frase_no_produce_el_aviso_dos_veces():
    """«no entro en largo» encaja en el patrón negado y en el llano; sin cuidado
    salía el mismo aviso duplicado y el mensaje de error se hacía ilegible."""
    r = _rev("No entro en largo hasta que el VIX baje.")
    assert len(r["ordenes"]) == 1, r["ordenes"]


# ── Los números, que vienen en dos formatos ──────────────────────────────────

def test_compara_el_formato_europeo_con_el_americano():
    """El briefing escribe 7.718,60 y el prompt 7,718.60. Compararlos como
    cadenas no vale para nada."""
    assert D._numeros("7.718,60")[0] == 7718.60
    assert D._numeros("7,718.60")[0] == 7718.60
    assert D._numeros("7.750")[0] == 7750.0
    assert D._numeros("15,74")[0] == 15.74


def test_tolera_el_redondeo_pero_no_un_nivel_distinto():
    """El modelo redondea: 7.708,70 puede salir como 7.708. Eso no es inventar.
    7.750 sí."""
    assert D._esta_en(7708.0, [7708.70])
    assert not D._esta_en(7750.0, [7708.70, 7591.71, 7141.76, 7816.70])


def test_los_porcentajes_no_se_toman_por_niveles():
    """«se invalida si el VIX cae un 15%» no lleva ningún nivel de índice."""
    r = _rev("La tesis se invalida si el VIX cae por debajo de 15 o el oro sube un 2,5%.")
    assert not any("NIVEL INVENTADO" in x for x in r["otros"]), _todo(r)


def test_solo_se_miran_las_frases_de_INVALIDACION():
    """Perseguir cada cifra del texto daría avisos a diario: el briefing cita
    legítimamente precios que no son niveles técnicos."""
    r = _rev("El Brent se acerca a los 100 dólares y el rupia cae con fuerza.")
    assert not any("NIVEL INVENTADO" in x for x in r["otros"]), _todo(r)


# ── Que esté conectado de verdad ─────────────────────────────────────────────

def test_main_revisa_ANTES_de_publicar_y_falla_si_hay_orden():
    """Que la función exista no sirve de nada si nadie la llama. Se comprueba
    que main() la usa y que una orden es fatal."""
    import ast
    import inspect
    import textwrap

    # TODO ESTO POR AST Y NO POR TEXTO, y las dos veces por el mismo motivo.
    # Contando apariciones del nombre salían tres, porque mi propio comentario
    # menciona la función. Y buscando las cadenas `revision["ordenes"]` y
    # `raise ValueError` por separado, el sabotaje de cambiar la guarda por
    # `if False:` se escapaba: las dos cadenas seguían estando, solo que ya no
    # conectadas. Es la quinta vez esta semana que comprobar una regla contra
    # su silueta en el código deja pasar el sabotaje.
    arbol = ast.parse(textwrap.dedent(inspect.getsource(D.main)))

    llamadas = [n for n in ast.walk(arbol)
                if isinstance(n, ast.Call) and getattr(n.func, "id", "") == "revisar_briefing"]
    assert len(llamadas) == 2, (
        f"main() llama {len(llamadas)} veces a revisar_briefing: debe revisar la "
        f"versión original y la del reintento, y solo esas")

    def _mira_las_ordenes(nodo):
        return any(isinstance(n, ast.Subscript)
                   and getattr(n.value, "id", "") == "revision"
                   and getattr(getattr(n, "slice", None), "value", None) == "ordenes"
                   for n in ast.walk(nodo))

    guardas = [n for n in ast.walk(arbol)
               if isinstance(n, ast.If) and _mira_las_ordenes(n.test)
               and any(isinstance(x, ast.Raise) for x in ast.walk(ast.Module(body=n.body,
                                                                            type_ignores=[])))]
    assert guardas, (
        "no hay ningún `if` sobre revision['ordenes'] que levante una excepción: "
        "una orden de operar se publicaría a ~100 suscriptores")


def test_lo_que_se_deja_pasar_queda_ANOTADO_en_el_fichero():
    """Un briefing con un dato mal atribuido no puede parecer limpio."""
    payload = D.construir_payload("texto", {"date": "2026-09-08", "time": "11:49"},
                                  "BAJISTA", None, {},
                                  revision={"ordenes": [], "otros": ["MAXIMOS sin titular"]})
    assert payload["diagnostico"]["revision"]["otros"] == ["MAXIMOS sin titular"]


def test_sin_hallazgos_no_se_ensucia_el_fichero():
    payload = D.construir_payload("texto", {"date": "2026-09-08", "time": "11:49"},
                                  "BAJISTA", None, {})
    assert "revision" not in payload["diagnostico"]
