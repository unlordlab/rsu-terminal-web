"""
Watchlist #19 (listas múltiples) y #16 (notas por ticker).

CÓMO ESTÁ MODELADO, que es lo que hay que proteger:

  - Una lista NO tiene tabla propia: es una etiqueta en la fila del ticker.
    Existe mientras algún ticker la lleve y desaparece sola al quedarse vacía.
    Sin tabla no hay dos cosas que mantener sincronizadas ni huérfanas que
    limpiar, y renombrar es actualizar la etiqueta de sus tickers.
  - Un ticker vive en UNA lista. El `UNIQUE(user_id, ticker)` es de la tabla
    original y cambiarlo obligaría a reconstruirla entera en SQLite; y mientras
    el ticker sea único, todo lo que ya lee la watchlist (Research, Scanner,
    RS/RW, CANSLIM, Options, Congress, Insider) sigue viendo el mismo conjunto
    y las alertas, que apuntan al ticker, no se enteran de que hay listas.
  - Las filas de antes del cambio tienen `lista` a NULL y se leen como la de
    por defecto: nadie tiene que migrar nada.

Uso:
    cd backend
    python -m pytest tests/test_watchlist_listas_y_notas.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.watchlist_service as W  # noqa: E402

ANA, LUIS = 1, 2
PRINCIPAL = W.LISTA_POR_DEFECTO


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(W, "DB_PATH", str(tmp_path / "users.db"))
    W.init_db()
    return W.DB_PATH


def _nombres(user_id=ANA):
    return [l["nombre"] for l in W.listas_de(user_id)]


def _fila(user_id, ticker):
    conn = W._conn()
    try:
        return dict(conn.execute(
            "SELECT ticker, lista, nota FROM watchlist WHERE user_id = ? AND ticker = ?",
            (user_id, ticker)).fetchone())
    finally:
        conn.close()


# ── Listas ──────────────────────────────────────────────────────────────────

def test_sin_decir_nada_todo_cae_en_la_lista_de_siempre(base):
    """Quien no quiera saber nada de listas no tiene que enterarse de que
    existen."""
    assert W.add_to_watchlist(ANA, "NVDA")["ok"] is True
    assert _fila(ANA, "NVDA")["lista"] == PRINCIPAL
    assert _nombres() == [PRINCIPAL]


def test_se_puede_añadir_directamente_a_una_lista(base):
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.add_to_watchlist(ANA, "AMD", "Semis")
    W.add_to_watchlist(ANA, "KO")
    assert _fila(ANA, "NVDA")["lista"] == "Semis"
    assert {l["nombre"]: l["n"] for l in W.listas_de(ANA)} == {PRINCIPAL: 1, "Semis": 2}


def test_la_lista_de_por_defecto_sale_aunque_este_vacia(base):
    """Es el sitio donde cae lo que se añade sin decir nada: si no apareciera,
    la pantalla no tendría dónde ponerlo."""
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    assert PRINCIPAL in _nombres()


def test_mover_un_ticker_de_lista(base):
    W.add_to_watchlist(ANA, "NVDA")
    assert W.mover_a_lista(ANA, "NVDA", "Semis")["ok"] is True
    assert _fila(ANA, "NVDA")["lista"] == "Semis"


def test_la_lista_vacia_desaparece_sola(base):
    """No hay nada que borrar: una lista es la etiqueta de sus tickers."""
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.mover_a_lista(ANA, "NVDA", PRINCIPAL)
    assert "Semis" not in _nombres()


def test_renombrar_mueve_a_todos_sus_tickers(base):
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.add_to_watchlist(ANA, "AMD", "Semis")
    r = W.renombrar_lista(ANA, "Semis", "Semiconductores")
    assert r["ok"] is True and r["movidos"] == 2
    assert _nombres() == [PRINCIPAL, "Semiconductores"]


def test_renombrar_a_una_que_ya_existe_las_funde(base):
    """Es lo que uno espera al renombrar «Semis» a «Semiconductores» cuando ya
    tenía esa: acabar con una sola lista y todo dentro."""
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.add_to_watchlist(ANA, "AMD", "Semiconductores")
    W.renombrar_lista(ANA, "Semis", "Semiconductores")
    assert {l["nombre"]: l["n"] for l in W.listas_de(ANA)} == {PRINCIPAL: 0, "Semiconductores": 2}


def test_renombrar_una_lista_que_no_existe_avisa(base):
    assert W.renombrar_lista(ANA, "NoExiste", "Otra")["ok"] is False


def test_las_listas_son_de_cada_usuario(base):
    """Con dos usuarios que llaman IGUAL a su lista: renombrar la de uno no
    puede tocar la del otro. Que no coincidan los nombres haría pasar el test
    sin comprobar nada."""
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.add_to_watchlist(LUIS, "AMD", "Semis")
    W.add_to_watchlist(LUIS, "KO", "Defensivas")
    assert _nombres(ANA) == [PRINCIPAL, "Semis"]
    assert _nombres(LUIS) == [PRINCIPAL, "Defensivas", "Semis"]
    r = W.renombrar_lista(ANA, "Semis", "Chips")
    assert r["movidos"] == 1, "ha renombrado filas que no eran suyas"
    assert _nombres(ANA) == [PRINCIPAL, "Chips"]
    assert _nombres(LUIS) == [PRINCIPAL, "Defensivas", "Semis"], "ha tocado las listas de otro"


def test_mover_a_una_lista_nueva_tambien_respeta_el_tope(base):
    """La puerta de atrás del límite: si solo se comprobara al añadir, se
    llegaba a 20 listas moviendo tickers de una a otra."""
    for i in range(W.MAX_LISTAS - 1):
        W.add_to_watchlist(ANA, f"TCK{i}", f"Lista {i}")
    W.add_to_watchlist(ANA, "OTRO")                     # cae en la de por defecto
    r = W.mover_a_lista(ANA, "OTRO", "La que sobra")
    assert r["ok"] is False and "listas" in r["error"]
    assert _fila(ANA, "OTRO")["lista"] == PRINCIPAL
    # Y moverlo a una que YA existe se puede, aunque se esté en el tope.
    assert W.mover_a_lista(ANA, "OTRO", "Lista 0")["ok"] is True


def test_una_lista_a_NULL_se_normaliza_al_arrancar(base, tmp_path, monkeypatch):
    """El invariante que permite que renombrar no tenga que acordarse de los
    huecos: después de `init_db()` ninguna fila se queda sin lista."""
    rara = str(tmp_path / "rara.db")
    monkeypatch.setattr(W, "DB_PATH", rara)
    conn = W._conn()
    conn.execute("""CREATE TABLE watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        ticker TEXT NOT NULL, added_at TEXT NOT NULL, lista TEXT, nota TEXT,
        UNIQUE(user_id, ticker))""")
    conn.executemany("INSERT INTO watchlist (user_id, ticker, added_at, lista) VALUES (?,?,?,?)",
                     [(ANA, "NULO", "2026-01-01T00:00:00+00:00", None),
                      (ANA, "VACIO", "2026-01-01T00:00:00+00:00", "   ")])
    conn.commit()
    conn.close()

    W.init_db()

    assert {f["ticker"]: f["lista"] for f in W.get_watchlist_tickers(ANA)} == {
        "NULO": PRINCIPAL, "VACIO": PRINCIPAL}
    assert W.renombrar_lista(ANA, PRINCIPAL, "Casa")["movidos"] == 2


def test_la_de_por_defecto_va_siempre_primera(base):
    """Es la pestaña de casa: si se colara por orden alfabético, cambiaría de
    sitio según cómo se llamen las demás."""
    W.add_to_watchlist(ANA, "AMD", "AAA primera")
    W.add_to_watchlist(ANA, "KO")
    W.add_to_watchlist(ANA, "XOM", "ZZZ ultima")
    assert _nombres() == [PRINCIPAL, "AAA primera", "ZZZ ultima"]


@pytest.mark.parametrize("nombre", [
    "<script>alert(1)</script>", "Semis'; DROP TABLE watchlist;--",
    "x" * 25, "lista\"rara", "<img src=x>",
])
def test_un_nombre_de_lista_raro_se_rechaza(base, nombre):
    """El nombre se pinta en la pantalla. Escapar es la segunda defensa; la
    primera es no guardarlo."""
    W.add_to_watchlist(ANA, "NVDA")
    assert W.mover_a_lista(ANA, "NVDA", nombre)["ok"] is False
    assert _fila(ANA, "NVDA")["lista"] == PRINCIPAL


def test_los_espacios_de_sobra_no_crean_listas_distintas(base):
    """«Semis» y « Semis » son la misma lista para cualquiera que las lea."""
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.add_to_watchlist(ANA, "AMD", "  Semis  ")
    assert {l["nombre"]: l["n"] for l in W.listas_de(ANA)}["Semis"] == 2


def test_hay_un_tope_de_listas(base):
    for i in range(W.MAX_LISTAS - 1):          # la de por defecto ya cuenta
        assert W.add_to_watchlist(ANA, f"TCK{i}", f"Lista {i}")["ok"] is True
    r = W.add_to_watchlist(ANA, "UNA MAS", "La que sobra")
    assert r["ok"] is False and "listas" in r["error"]


def test_la_base_de_produccion_se_migra_sola(base, tmp_path, monkeypatch):
    """LA prueba de que nadie tiene que migrar nada a mano: se monta la tabla
    VIEJA, sin las columnas nuevas, con un ticker dentro — que es exactamente
    lo que hay hoy en el VPS — y se arranca `init_db()` encima."""
    vieja = str(tmp_path / "vieja.db")
    monkeypatch.setattr(W, "DB_PATH", vieja)
    conn = W._conn()
    conn.execute("""CREATE TABLE watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
        ticker TEXT NOT NULL, added_at TEXT NOT NULL, UNIQUE(user_id, ticker))""")
    conn.execute("INSERT INTO watchlist (user_id, ticker, added_at) VALUES (?,?,?)",
                 (ANA, "VIEJO", "2026-01-01T00:00:00+00:00"))
    conn.commit()
    conn.close()

    W.init_db()                       # el arranque del backend

    assert _nombres() == [PRINCIPAL]
    fila = W.get_watchlist_tickers(ANA)[0]
    assert fila["ticker"] == "VIEJO" and fila["lista"] == PRINCIPAL and not fila["nota"]
    W.init_db()                       # y otra vez: tiene que ser idempotente
    assert len(W.get_watchlist_tickers(ANA)) == 1


# ── Notas ───────────────────────────────────────────────────────────────────

def test_guardar_y_leer_una_nota(base):
    W.add_to_watchlist(ANA, "NVDA")
    assert W.set_nota(ANA, "NVDA", "Espero el retroceso a la EMA50")["ok"] is True
    assert W.get_watchlist_tickers(ANA)[0]["nota"] == "Espero el retroceso a la EMA50"


def test_una_nota_vacia_borra_la_que_hubiera(base):
    W.add_to_watchlist(ANA, "NVDA")
    W.set_nota(ANA, "NVDA", "algo")
    W.set_nota(ANA, "NVDA", "   ")
    assert _fila(ANA, "NVDA")["nota"] is None


def test_la_nota_se_recorta_al_maximo(base):
    W.add_to_watchlist(ANA, "NVDA")
    W.set_nota(ANA, "NVDA", "x" * 900)
    assert len(_fila(ANA, "NVDA")["nota"]) == W.MAX_NOTA


def test_no_se_puede_anotar_un_ticker_que_no_sigues(base):
    """Ni el de otro: el UPDATE lleva el user_id."""
    W.add_to_watchlist(LUIS, "NVDA")
    r = W.set_nota(ANA, "NVDA", "mía")
    assert r["ok"] is False
    assert _fila(LUIS, "NVDA")["nota"] is None


def test_quitar_el_ticker_se_lleva_la_nota(base):
    W.add_to_watchlist(ANA, "NVDA")
    W.set_nota(ANA, "NVDA", "algo")
    W.remove_from_watchlist(ANA, "NVDA")
    W.add_to_watchlist(ANA, "NVDA")
    assert _fila(ANA, "NVDA")["nota"] is None, "la nota ha sobrevivido al borrado"


# ── Lo que ya funcionaba y no se puede romper ───────────────────────────────

def test_la_watchlist_enriquecida_trae_lista_nota_y_el_indice_de_listas(base, monkeypatch):
    monkeypatch.setattr("services.cartera_service.fetch_live_prices",
                        lambda t: {"NVDA": {"price": 100.0, "chg": 1.5}})
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.set_nota(ANA, "NVDA", "la nota")
    d = W.get_watchlist(ANA)
    assert d["data"][0]["lista"] == "Semis" and d["data"][0]["nota"] == "la nota"
    assert {l["nombre"] for l in d["listas"]} == {PRINCIPAL, "Semis"}


def test_el_tope_de_tickers_sigue_siendo_de_la_watchlist_entera(base):
    """Las listas no pueden ser una forma de saltarse el límite de 50."""
    for i in range(W.MAX_WATCHLIST_ITEMS):
        W.add_to_watchlist(ANA, f"T{i}", "Principal" if i % 2 else "Otra")
    r = W.add_to_watchlist(ANA, "UNAMAS", "Tercera")
    assert r["ok"] is False and "watchlist" in r["error"]


def test_lo_que_leen_los_demas_modulos_no_cambia(base):
    """Research, Scanner, RS/RW, CANSLIM, Options, Congress e Insider hacen
    `{w["ticker"] for w in get_watchlist_tickers(uid)}`: con listas tienen que
    seguir viendo el conjunto entero, no una lista sola."""
    W.add_to_watchlist(ANA, "NVDA", "Semis")
    W.add_to_watchlist(ANA, "KO")
    assert {w["ticker"] for w in W.get_watchlist_tickers(ANA)} == {"NVDA", "KO"}


# ── El router ───────────────────────────────────────────────────────────────

def test_la_ruta_de_renombrar_no_se_come_la_del_ticker():
    """`/listas/{nombre}` y `/{ticker}` compiten por el mismo hueco y FastAPI
    resuelve por ORDEN de declaración: si algún día alguien mueve el bloque,
    renombrar una lista pasaría a intentar editar un ticker llamado «listas»."""
    import ast
    ruta = os.path.join(os.path.dirname(__file__), '..', 'routers', 'watchlist.py')
    arbol = ast.parse(open(ruta, encoding="utf-8").read())
    puts = []
    for n in ast.walk(arbol):
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for d in n.decorator_list:
            if (isinstance(d, ast.Call) and getattr(d.func, "attr", "") == "put"
                    and d.args and isinstance(d.args[0], ast.Constant)):
                puts.append((d.args[0].value, d.lineno))
    rutas = [r for r, _ in puts]
    assert "/listas/{nombre}" in rutas and "/{ticker}" in rutas
    assert rutas.index("/listas/{nombre}") < rutas.index("/{ticker}"), (
        "renombrar una lista va a caer en el endpoint del ticker")
