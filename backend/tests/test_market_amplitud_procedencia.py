"""
El panel decía «[S&P 500 REAL]» sobre 2.422 valores, y no decía de qué día eran.

EL CASO, 08/09/2026: el usuario pidió auditar el módulo Amplitud de Mercado.
**Todos los números eran reales** — recalculados aparte y cuadrando al decimal:
SPY 767,70 · SMA50 757,63 · SMA200 710,43 · RSI 50,3 (desvío 0,00–0,11% frente
a yfinance), McClellan −16,7, ABI 14,3% (= |1357−1018|/2375), % sobre SMA50 48%
en 498 tickers, NH−NL +53 (69−16), A/D 1.357/1.018/+339. Nada inventado.

Lo que fallaba eran las ETIQUETAS, y de dos formas.

1. LA PROCEDENCIA. McClellan, ABI y la línea A/D salen de `breadth_history`,
   que hoy tiene **2.422 valores (S&P 500 + Russell 2000)**, y se mostraban
   como «[S&P 500 REAL]». Lo delataba la propia pantalla: la fila de NH−NL lee
   **exactamente el mismo array** y sí ponía «[S&P 500 + RUSSELL 2000 REAL]»,
   así que una misma respuesta se contradecía a sí misma.

   Y ES LA SEGUNDA VUELTA DEL MISMO BUG. El comentario que había ahí explica
   que antes ponía «[NYSE REAL]» sobre datos del S&P 500, y que se corrigió
   cambiando la cadena a mano. Por eso volvió a quedarse vieja en cuanto el
   universo creció de 525 a 2.422. Ahora se DERIVA de `total_valores`, que
   viene en cada fila del propio dato: una etiqueta calculada no envejece.

2. LA FECHA. El precio del SPY, sus medias y el RSI son de HOY; McClellan, ABI,
   % sobre SMA50, NH−NL y A/D salen del scan NOCTURNO, o sea de la última
   sesión CERRADA — que un martes después de un lunes festivo son **dos**
   sesiones atrás. El payload no traía ninguna clave de fecha, así que la
   pantalla no podía decirlo aunque quisiera, y las variaciones «sem.» de cada
   fila daban a entender lo contrario.

   Es el mismo desfase que obligó a poner «AMPLITUD del X, NO de hoy» en el
   prompt del briefing (#35/#36) después de que escribiera «el 45,5% de las
   acciones avanzaron HOY» sobre números del viernes. Se había arreglado para
   el consumidor que habla y no para el que pinta.

Uso:
    cd backend
    python -m pytest tests/test_market_amplitud_procedencia.py -v
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.market_service as M  # noqa: E402

MARKET_JS = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "pages", "market.js")


def _js():
    return io.open(MARKET_JS, encoding="utf-8").read()


def _fuente_de(total_valores):
    """Llama a la función REAL del backend.

    LA PRIMERA VERSIÓN DE ESTE AYUDANTE COPIABA LA EXPRESIÓN aquí dentro, y con
    la copia **tres sabotajes se escaparon**: mover el umbral en el backend no
    rompía ningún test, porque los tests medían la copia. Por eso la decisión
    se extrajo a `_fuente_amplitud()` — no por elegancia, sino porque dentro de
    `get_market_breadth` no se podía ejecutar sin salir a la red."""
    return M._fuente_amplitud({"total_valores": total_valores})


# ── La etiqueta sale del dato, no de una cadena escrita a mano ───────────────

def test_la_etiqueta_se_DERIVA_de_total_valores():
    """EL test. Escrita a mano se ha quedado vieja DOS veces: primero decía
    NYSE sobre datos del S&P 500, luego S&P 500 sobre S&P 500 + Russell."""
    import ast
    import inspect
    fuente = inspect.getsource(M.get_market_breadth)
    asignaciones = [n for n in ast.walk(ast.parse(inspect.cleandoc(fuente)))
                    if isinstance(n, ast.Assign)
                    and any(getattr(t, "id", "") == "ad_source" for t in n.targets)]
    assert asignaciones, "no se asigna ad_source en ninguna parte"
    derivadas = [a for a in asignaciones
                 if isinstance(a.value, ast.Call)
                 and getattr(a.value.func, "id", "") == "_fuente_amplitud"]
    assert derivadas, (
        "ad_source sigue escrito a mano: se quedará viejo la próxima vez que "
        "cambie el universo del escáner, igual que ha pasado ya dos veces")


def test_el_universo_grande_se_etiqueta_como_SP500_mas_Russell():
    """Los 2.422 valores del 08/09."""
    assert _fuente_de(2422) == "sp500_r2k"


def test_y_el_universo_del_SP500_solo_sigue_diciendo_SP500():
    """Si el escáner volviera a las ~500, la etiqueta tiene que volver sola."""
    assert _fuente_de(498) == "sp500"
    assert _fuente_de(525) == "sp500"


def test_el_corte_no_depende_de_un_numero_exacto():
    """Entre 500 y 2.400 hay muchísimo margen: el umbral no puede estar pegado
    a ninguno de los dos, o volvería a fallar cuando el universo se mueva."""
    assert _fuente_de(999) == "sp500" and _fuente_de(1001) == "sp500_r2k"
    for n in (450, 500, 600):
        assert _fuente_de(n) == "sp500", n
    for n in (1800, 2422, 3000):
        assert _fuente_de(n) == "sp500_r2k", n


def test_sin_dato_no_se_inventa_el_universo_grande():
    assert _fuente_de(None) == "sp500" and _fuente_de(0) == "sp500"


def test_el_frontend_sabe_pintar_las_dos_etiquetas():
    """El frontend ya lo soportaba; era el backend el que no se lo mandaba."""
    js = _js()
    assert "sp500_r2k" in js
    assert "[S&amp;P 500 + RUSSELL 2000 REAL]" in js or "[S&P 500 + RUSSELL 2000 REAL]" in js


def test_McClellan_ABI_y_A_D_comparten_la_MISMA_etiqueta():
    """Los tres salen del mismo array. Si a uno se le pone otra, vuelve la
    contradicción dentro de la misma pantalla que delató el bug."""
    js = _js()
    assert "const abiBadge" in js and "mcBadge" in js
    i = js.index("const abiBadge")
    assert "mcBadge" in js[i:i + 200], "el ABI ha dejado de compartir etiqueta con McClellan"
    # La COMPARACIÓN, no que la cadena aparezca por ahí: con `false ?` el
    # sabotaje se escapaba porque `data.ad_source` seguía saliendo unas líneas
    # más abajo, en la rama del NYSE.
    mc = js[js.index("const mcBadge"):js.index("const abiAvailable")]
    assert "data.ad_source === 'sp500_r2k'" in mc, (
        "McClellan ya no mira si los datos son del universo ampliado: volvería "
        "a etiquetar 2.422 valores como «[S&P 500 REAL]»")


# ── De qué sesión es la amplitud ─────────────────────────────────────────────

def test_el_payload_lleva_la_fecha_de_la_amplitud():
    """Sin esto la pantalla no puede decirlo aunque quiera, que es la situación
    en la que se auditó el módulo."""
    import inspect
    fuente = inspect.getsource(M.get_market_breadth)
    assert '"breadth_fecha"' in fuente, (
        "el payload no dice de qué sesión es la amplitud: el precio de al lado "
        "es de hoy y esto puede ser de hace días")


def test_la_fecha_se_declara_TAMBIEN_en_el_camino_de_error():
    """Una clave que aparece y desaparece según la rama obliga al frontend a
    adivinar. Es el mismo criterio que ya se aplicó en el briefing."""
    import inspect
    fuente = inspect.getsource(M.get_market_breadth)
    assert fuente.count('"breadth_fecha"') >= 2


def test_la_fecha_sale_de_la_FILA_usada_no_de_hoy():
    """Poner `date.today()` ahí sería peor que no poner nada: afirmaría que la
    amplitud es de hoy justo cuando no lo es."""
    import inspect
    fuente = inspect.getsource(M.get_market_breadth)
    assert 'ad_fecha = last.get("date")' in fuente


# ── Lo que pinta el panel ────────────────────────────────────────────────────

def _bloque_fecha():
    js = _js()
    i = js.index("let fechaAmplitudHtml")
    return js[i:js.index("const nhNlAvailable", i)]


def test_el_panel_dice_de_que_dia_es_la_amplitud():
    b = _bloque_fecha()
    assert "data.breadth_fecha" in b
    assert "Amplitud del" in b


def test_y_la_linea_se_CONCATENA_de_verdad_en_el_panel():
    """Construir el HTML no sirve de nada si nadie lo mete en la pantalla. El
    sabotaje de quitar `+ fechaAmplitudHtml` del render se escapaba mirando
    solo el bloque que lo construye — el mismo fallo que ya me costó dos veces
    esta semana."""
    js = _js()
    definicion = js.index("let fechaAmplitudHtml")
    fin_bloque = js.index("const nhNlAvailable", definicion)
    usos_fuera = js.count("fechaAmplitudHtml") - js[definicion:fin_bloque].count("fechaAmplitudHtml")
    assert usos_fuera >= 1, (
        "fechaAmplitudHtml se construye pero no se usa en ninguna parte: la "
        "fecha no llegaría a la pantalla")
    assert "+ fechaAmplitudHtml" in js[fin_bloque:], (
        "no se concatena en el HTML del panel")


def test_avisa_cuando_lleva_DOS_sesiones_o_mas_de_retraso():
    """Una sesión de retraso es lo normal (el scan es nocturno). Dos ya no, y
    es justo el caso del 08/09 por el festivo del lunes. Sin el umbral, o se
    avisa todos los días —y se deja de mirar— o no se avisa nunca."""
    b = _bloque_fecha()
    assert "sesiones >= 2" in b, "no hay umbral: el aviso sería diario o inexistente"
    assert "⚠" in b


def test_dice_explicitamente_que_el_precio_de_arriba_SI_es_de_hoy():
    """Es la mitad que evita la confusión: el panel mezcla las dos cosas."""
    assert "sí son de hoy" in _bloque_fecha()


def test_sin_fecha_no_se_pinta_nada():
    """Un servidor viejo o el camino de error no pueden dejar un hueco ni un
    «undefined» en pantalla."""
    b = _bloque_fecha()
    assert re.search(r"if \(data\.breadth_fecha\)", b), (
        "se pinta el bloque sin comprobar que hay fecha")


def test_el_conteo_de_sesiones_NO_pretende_conocer_los_festivos():
    """`_ultima_sesion_esperada` ya enseñó lo que cuesta suponerlos (la Cartera
    se quedó sin «HOY %» el día después de Labor Day). Aquí solo se saltan
    fines de semana y el umbral de 2 absorbe el resto."""
    b = _bloque_fecha()
    assert "wd !== 0 && wd !== 6" in b
    assert "festivo" in b.lower(), "no se deja dicho que no conoce los festivos"
