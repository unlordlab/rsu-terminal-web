"""
Watchlist #20: el resumen nocturno de lo que ha pasado en tus valores.

QUÉ LLENA. La terminal tenía el briefing (del mercado entero, igual para todos)
y las alertas (instantáneas, de una condición puesta a mano), y nada en medio.
Lo que faltaba es lo que uno quiere saber al cerrar el día: «de los valores que
sigo, ¿en cuáles ha pasado algo?».

LO QUE PROTEGEN ESTOS TESTS:

  - No calcula nada nuevo: son las señales de `senales_service` filtradas por
    los tickers de cada uno. Así nunca contradice a Scanner, RS/RW o Research.
  - Los días sin novedades NO se manda: un mensaje vacío cada día enseña a no
    abrirlo, y entonces tampoco se abre el día que trae algo.
  - Es opt-in, y solo sale hacia quien además tiene Telegram vinculado.
  - «Los otros N, sin novedades» va siempre: sin esa línea no se distingue
    «no pasó nada» de «no se ha mirado».
  - Se manda en el mismo punto que las alertas de señal: cuando entra la foto
    de la sesión.

Uso:
    cd backend
    python -m pytest tests/test_watchlist_digest.py -v
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.digest_service as D  # noqa: E402
import services.snapshots_service as S  # noqa: E402
import services.users_service as U  # noqa: E402
import services.watchlist_service as W  # noqa: E402

AYER, HOY = "2026-09-10", "2026-09-11"


@pytest.fixture
def bases(tmp_path, monkeypatch):
    monkeypatch.setattr(S, "DB_PATH", str(tmp_path / "snapshots.db"))
    monkeypatch.setattr(W, "DB_PATH", str(tmp_path / "users.db"))
    monkeypatch.setattr(U, "DB_PATH", str(tmp_path / "users.db"))
    conn = S._conn()
    conn.execute("""CREATE TABLE snapshot_ticker (
        fecha TEXT NOT NULL, ticker TEXT NOT NULL, sector TEXT, precio REAL, rvol REAL,
        rs_pct REAL, rs_score REAL, phase INTEGER, phase_confirmed INTEGER,
        phase_weekly INTEGER, above_sma50 INTEGER, new_high INTEGER, new_low INTEGER,
        dias_absorcion INTEGER, regla_fase TEXT, PRIMARY KEY (fecha, ticker))""")
    conn.commit()
    conn.close()
    U.init_db()
    W.init_db()
    return tmp_path


def _usuario(email, telegram=None, digest=False):
    conn = U._conn()
    cur = conn.execute("INSERT INTO users (email, password_hash, created_at, telegram_chat_id, "
                       "digest_diario) VALUES (?, 'x', '2026-01-01', ?, ?)",
                       (email, telegram, 1 if digest else 0))
    conn.commit()
    conn.close()
    return cur.lastrowid


def _foto(fecha, ticker, **campos):
    base = {"phase": 1, "phase_confirmed": 1, "rs_pct": 50.0, "above_sma50": 0,
            "new_high": 0, "new_low": 0}
    base.update(campos)
    conn = S._conn()
    conn.execute(
        "INSERT OR REPLACE INTO snapshot_ticker (fecha, ticker, phase, phase_confirmed, rs_pct, "
        "above_sma50, new_high, new_low) VALUES (?,?,?,?,?,?,?,?)",
        (fecha, ticker, base["phase"], base["phase_confirmed"], base["rs_pct"],
         base["above_sma50"], base["new_high"], base["new_low"]))
    conn.commit()
    conn.close()


def _sesion(movimientos):
    """{ticker: (antes, hoy)} -> las dos fotos."""
    for t, (antes, hoy) in movimientos.items():
        _foto(AYER, t, **antes)
        _foto(HOY, t, **hoy)


@pytest.fixture
def telegram(monkeypatch):
    enviados = []
    monkeypatch.setattr("services.telegram_service.enviar_telegram",
                        lambda texto, chat_id=None: enviados.append((chat_id, texto)))
    return enviados


# ── El contenido ────────────────────────────────────────────────────────────

def test_el_resumen_trae_solo_los_valores_que_sigues(bases):
    ana = _usuario("ana@x.com")
    W.add_to_watchlist(ana, "NVDA")
    W.add_to_watchlist(ana, "KO")
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2}),
             "AMD":  ({"phase": 1}, {"phase": 2}),        # no lo sigue
             "KO":   ({"phase": 2}, {"phase": 2})})
    d = D.digest_de(ana, HOY)
    assert [n["ticker"] for n in d["novedades"]] == ["NVDA"]
    assert d["seguidos"] == 2 and d["sin_novedades"] == 1


def test_los_textos_son_los_de_las_senales(bases):
    """El mismo texto que el aviso de la alerta: dos formas de decir lo mismo
    acaban diciendo cosas distintas."""
    from services.senales_service import texto_de
    ana = _usuario("ana@x.com")
    W.add_to_watchlist(ana, "NVDA")
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2})})
    assert D.digest_de(ana, HOY)["novedades"][0]["textos"] == [texto_de("fase2")]


def test_el_que_mas_se_ha_movido_va_primero(bases):
    """Si hay que recortar, que se quede fuera el de una novedad, no el de tres."""
    ana = _usuario("ana@x.com")
    for t in ("AAA", "ZZZ"):
        W.add_to_watchlist(ana, t)
    _sesion({"AAA": ({"above_sma50": 0}, {"above_sma50": 1}),
             "ZZZ": ({"phase": 1, "rs_pct": 70.0, "above_sma50": 0},
                     {"phase": 2, "rs_pct": 90.0, "above_sma50": 1})})
    assert [n["ticker"] for n in D.digest_de(ana, HOY)["novedades"]] == ["ZZZ", "AAA"]


def test_las_listas_no_dejan_fuera_a_nadie(bases):
    """El resumen es de la watchlist ENTERA, no de la lista que se esté mirando."""
    ana = _usuario("ana@x.com")
    W.add_to_watchlist(ana, "NVDA", "Semis")
    W.add_to_watchlist(ana, "KO")
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2}), "KO": ({"phase": 1}, {"phase": 2})})
    assert {n["ticker"] for n in D.digest_de(ana, HOY)["novedades"]} == {"NVDA", "KO"}


def test_la_fecha_va_en_castellano_y_con_el_dia(bases):
    assert D.fecha_larga("2026-09-11") == "viernes 11 de septiembre"
    assert D.fecha_larga("2026-09-07") == "lunes 7 de septiembre"


# ── El mensaje ──────────────────────────────────────────────────────────────

def test_el_mensaje_dice_cuantos_quedaron_sin_novedades(bases):
    """Sin esta línea no se distingue «no pasó nada» de «no se ha mirado»."""
    ana = _usuario("ana@x.com")
    for t in ("NVDA", "KO", "XOM"):
        W.add_to_watchlist(ana, t)
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2}),
             "KO": ({"phase": 1}, {"phase": 1}), "XOM": ({"phase": 1}, {"phase": 1})})
    texto = D.texto_del_digest(D.digest_de(ana, HOY))
    assert "viernes 11 de septiembre" in texto
    assert "*NVDA*" in texto and "Fase 2" in texto
    assert "Los otros 2, sin novedades." in texto


def test_con_muchas_novedades_se_recorta_y_se_dice(bases):
    ana = _usuario("ana@x.com")
    movs = {}
    for i in range(D.MAX_LINEAS + 3):
        t = f"T{i:02d}"
        W.add_to_watchlist(ana, t)
        movs[t] = ({"phase": 1}, {"phase": 2})
    _sesion(movs)
    texto = D.texto_del_digest(D.digest_de(ana, HOY))
    assert texto.count("▸") == D.MAX_LINEAS
    assert "y 3 valores más con novedades" in texto


# ── El envío ────────────────────────────────────────────────────────────────

def test_se_manda_a_quien_lo_ha_activado_y_tiene_telegram(bases, telegram):
    ana  = _usuario("ana@x.com",  telegram="111", digest=True)
    luis = _usuario("luis@x.com", telegram="222", digest=False)      # no lo quiere
    eva  = _usuario("eva@x.com",  telegram=None,  digest=True)       # sin Telegram
    for u in (ana, luis, eva):
        W.add_to_watchlist(u, "NVDA")
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2})})

    assert D.enviar_digests(HOY) == 1
    assert [chat for chat, _ in telegram] == ["111"]


def test_un_dia_sin_novedades_NO_se_manda(bases, telegram):
    """Un mensaje vacío cada día enseña a no abrirlo."""
    ana = _usuario("ana@x.com", telegram="111", digest=True)
    W.add_to_watchlist(ana, "KO")
    _sesion({"KO": ({"phase": 2}, {"phase": 2})})
    assert D.enviar_digests(HOY) == 0 and telegram == []


def test_una_watchlist_vacia_no_manda_nada(bases, telegram):
    _usuario("ana@x.com", telegram="111", digest=True)
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2})})
    assert D.enviar_digests(HOY) == 0


def test_si_falla_uno_los_demas_salen(bases, monkeypatch):
    """Un resumen roto no puede dejar sin el suyo a todos los que van detrás."""
    ana = _usuario("ana@x.com", telegram="111", digest=True)
    luis = _usuario("luis@x.com", telegram="222", digest=True)
    for u in (ana, luis):
        W.add_to_watchlist(u, "NVDA")
    _sesion({"NVDA": ({"phase": 1}, {"phase": 2})})
    enviados = []

    def telegram_caprichoso(texto, chat_id=None):
        if chat_id == "111":
            raise RuntimeError("Telegram caído para este chat")
        enviados.append(chat_id)
    monkeypatch.setattr("services.telegram_service.enviar_telegram", telegram_caprichoso)
    assert D.enviar_digests(HOY) == 1 and enviados == ["222"]


# ── La preferencia ──────────────────────────────────────────────────────────

def test_es_opt_in(bases):
    """Por defecto no llega nada: nadie lo ha pedido todavía."""
    ana = _usuario("ana@x.com", telegram="111")
    assert U.quiere_digest(ana) is False
    assert U.destinatarios_del_digest() == {}


def test_activar_y_desactivar(bases):
    ana = _usuario("ana@x.com", telegram="111")
    assert U.set_digest_diario(ana, True)["ok"] is True
    assert U.destinatarios_del_digest() == {ana: "111"}
    U.set_digest_diario(ana, False)
    assert U.destinatarios_del_digest() == {}


def test_la_columna_se_crea_sola_en_la_base_de_produccion(tmp_path, monkeypatch):
    """La tabla de usuarios del VPS no tiene la columna: arrancar tiene que
    añadirla sin tocar a nadie, y dejarles a todos con el resumen APAGADO."""
    monkeypatch.setattr(U, "DB_PATH", str(tmp_path / "vieja.db"))
    conn = U._conn()
    conn.execute("""CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
        tier TEXT NOT NULL DEFAULT 'free', created_at TEXT NOT NULL)""")
    conn.execute("INSERT INTO users (email, password_hash, created_at) VALUES ('vieja@x.com','x','2026-01-01')")
    conn.commit()
    conn.close()
    U.init_db()
    assert U.quiere_digest(1) is False


# ── El enganche ─────────────────────────────────────────────────────────────

def test_se_manda_cuando_entra_la_sesion_junto_a_las_senales():
    """Mismo punto que las alertas de señal: mismo dato, mismo momento. Se mira
    el árbol del código, no el texto."""
    import ast
    import inspect
    import textwrap
    import routers.ws as ws
    arbol = ast.parse(textwrap.dedent(inspect.getsource(ws.market_cache_warm_loop)))

    def _menciona(nodo, nombre):
        return any(isinstance(n, ast.Name) and n.id == nombre for n in ast.walk(nodo))

    guardas = [n for n in ast.walk(arbol)
               if isinstance(n, ast.If) and _menciona(n.test, "sesion_nueva")]
    assert any(_menciona(g, "enviar_digests") for g in guardas), (
        "el resumen no se manda cuando entra la foto de la sesión")
