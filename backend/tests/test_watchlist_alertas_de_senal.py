"""
Watchlist #18: alertas sobre las señales de la propia terminal.

EL CASO. Una alerta solo podía vigilar precio, RVOL o el toque de una EMA —
cosas que cualquier bróker ya avisa. Lo que la terminal calcula cada noche y no
avisaba a nadie era justo lo suyo: el cambio de fase de Weinstein, la entrada en
el grupo de líderes por fuerza relativa, la pérdida de la media de 50, el máximo
de 52 semanas.

CÓMO ESTÁ HECHO, que es lo que protegen estos tests:

  - Una señal es la DIFERENCIA entre las dos últimas fotos de `snapshot_ticker`,
    que la terminal ya guardaba. No se calcula nada nuevo ni se pide nada a la
    red: se restan dos filas.
  - Por eso NO se miran cada 90 s como las otras alertas: entre dos pasadas de
    90 s no pueden haber cambiado. Se comprueban una vez, cuando entra la foto
    de la sesión, enganchadas al snapshot diario que ya existía.
  - Son recurrentes por naturaleza («avísame CADA VEZ que entre en Fase 2») y
    por eso guardan con qué sesión se dispararon: al pasar el cooldown vuelven a
    'active', y la señal de esa misma foto sigue ahí hasta que entre la
    siguiente sesión. Sin esa memoria, la misma foto avisaría dos veces.
  - El corte de líder es el MISMO que usa RS/RW en sus pantallas. Dos varas de
    medir lo mismo es la lección de CANSLIM #6.

Uso:
    cd backend
    python -m pytest tests/test_watchlist_alertas_de_senal.py -v
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.snapshots_service as S  # noqa: E402
import services.senales_service as SE  # noqa: E402
import services.watchlist_service as W  # noqa: E402

ANA = 1
AYER, HOY = "2026-09-10", "2026-09-11"


@pytest.fixture
def bases(tmp_path, monkeypatch):
    """Las dos bases: la de snapshots (de donde salen las señales) y la de
    usuarios (donde viven las alertas)."""
    monkeypatch.setattr(S, "DB_PATH", str(tmp_path / "snapshots.db"))
    monkeypatch.setattr(W, "DB_PATH", str(tmp_path / "users.db"))
    conn = S._conn()
    conn.execute("""CREATE TABLE snapshot_ticker (
        fecha TEXT NOT NULL, ticker TEXT NOT NULL, sector TEXT, precio REAL, rvol REAL,
        rs_pct REAL, rs_score REAL, phase INTEGER, phase_confirmed INTEGER,
        phase_weekly INTEGER, above_sma50 INTEGER, new_high INTEGER, new_low INTEGER,
        dias_absorcion INTEGER, regla_fase TEXT, PRIMARY KEY (fecha, ticker))""")
    conn.commit()
    conn.close()
    W.init_db()
    return tmp_path


def _foto(fecha, ticker, **campos):
    base = {"phase": 1, "phase_confirmed": 1, "rs_pct": 50.0,
            "above_sma50": 0, "new_high": 0, "new_low": 0}
    base.update(campos)
    conn = S._conn()
    conn.execute(
        "INSERT OR REPLACE INTO snapshot_ticker (fecha, ticker, phase, phase_confirmed, "
        "rs_pct, above_sma50, new_high, new_low) VALUES (?,?,?,?,?,?,?,?)",
        (fecha, ticker, base["phase"], base["phase_confirmed"], base["rs_pct"],
         base["above_sma50"], base["new_high"], base["new_low"]))
    conn.commit()
    conn.close()


def _dos_fotos(ticker, antes, hoy):
    _foto(AYER, ticker, **antes)
    _foto(HOY, ticker, **hoy)


# ── Las señales ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("antes,hoy,esperada", [
    ({"phase": 1}, {"phase": 2}, "fase2"),
    ({"phase": 3}, {"phase": 4}, "fase4"),
    ({"rs_pct": 78.0}, {"rs_pct": 84.0}, "lider_rs"),
    ({"rs_pct": 86.0}, {"rs_pct": 72.0}, "sale_lider"),
    ({"above_sma50": 0}, {"above_sma50": 1}, "sma50_arriba"),
    ({"above_sma50": 1}, {"above_sma50": 0}, "sma50_abajo"),
    ({"new_high": 0}, {"new_high": 1}, "maximo_52"),
    ({"new_low": 0}, {"new_low": 1}, "minimo_52"),
])
def test_cada_senal_sale_de_comparar_las_dos_ultimas_fotos(bases, antes, hoy, esperada):
    _dos_fotos("NVDA", antes, hoy)
    assert SE.senales_de_la_sesion(HOY) == {"NVDA": [esperada]}


def test_sin_cambio_no_hay_senal(bases):
    _dos_fotos("NVDA", {"phase": 2, "rs_pct": 85.0, "above_sma50": 1},
                       {"phase": 2, "rs_pct": 86.0, "above_sma50": 1})
    assert SE.senales_de_la_sesion(HOY) == {}


def test_una_fase_sin_confirmar_no_avisa(bases):
    """El escáner trae `phase_confirmed` justo para esto: sin el debounce de
    tres sesiones, un valor que baila entre la 1 y la 2 mandaría un aviso cada
    dos días y el usuario apagaría la alerta."""
    _dos_fotos("NVDA", {"phase": 1}, {"phase": 2, "phase_confirmed": 0})
    assert SE.senales_de_la_sesion(HOY) == {}


def test_el_maximo_avisa_el_PRIMER_dia_de_la_racha(bases):
    """Un valor en subida libre marca máximo diez sesiones seguidas. Avisar las
    diez es ruido, y a la tercera nadie lee el aviso."""
    _dos_fotos("NVDA", {"new_high": 1}, {"new_high": 1})
    assert SE.senales_de_la_sesion(HOY) == {}


def test_el_corte_de_lider_es_el_MISMO_que_usa_RS_RW(bases):
    """Si aquí hubiera otro número, la terminal avisaría de que un valor entra
    en el grupo de líderes mientras la pantalla de al lado no lo pinta como
    líder."""
    from services.rsrw_service import UMBRAL_LIDER
    assert SE.UMBRAL_LIDER == UMBRAL_LIDER
    _dos_fotos("NVDA", {"rs_pct": UMBRAL_LIDER - 0.1}, {"rs_pct": UMBRAL_LIDER})
    assert SE.senales_de_la_sesion(HOY) == {"NVDA": ["lider_rs"]}


def test_con_una_sola_sesion_no_se_inventa_nada(bases):
    """Una señal es un CAMBIO: con una sola foto no hay cambio que ver, y
    llenar el primer día de avisos falsos sería la peor presentación posible."""
    _foto(HOY, "NVDA", phase=2)
    assert SE.senales_de_la_sesion() == {}


def test_un_valor_que_no_estaba_ayer_no_genera_senales(bases):
    """Entró al universo hoy: no hay con qué comparar."""
    _foto(AYER, "OTRO", phase=1)
    _foto(HOY, "OTRO", phase=1)
    _foto(HOY, "NUEVO", phase=2, rs_pct=95.0, above_sma50=1, new_high=1)
    assert "NUEVO" not in SE.senales_de_la_sesion(HOY)


def test_un_valor_puede_traer_varias_senales_el_mismo_dia(bases):
    _dos_fotos("NVDA", {"phase": 1, "rs_pct": 70.0, "above_sma50": 0},
                       {"phase": 2, "rs_pct": 88.0, "above_sma50": 1, "new_high": 1})
    assert set(SE.senales_de_la_sesion(HOY)["NVDA"]) == {
        "fase2", "lider_rs", "sma50_arriba", "maximo_52"}


def test_todas_las_senales_tienen_su_texto(bases):
    """Una señal sin texto llegaría al Telegram del usuario como una clave
    interna («sma50_abajo»)."""
    for clave in SE.SENALES:
        assert SE.texto_de(clave) and SE.texto_de(clave) != clave


# ── Las alertas ─────────────────────────────────────────────────────────────

def test_crear_una_alerta_de_senal(bases):
    r = W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="fase2")
    assert r["ok"] is True
    a = W.get_alerts(ANA)["data"][0]
    assert a["metric"] == "senal" and a["senal"] == "fase2"
    assert a["recurring"] == 1, "una señal es recurrente: «avísame cada vez que pase»"


def test_una_senal_inventada_se_rechaza(bases):
    assert W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="lo_que_sea")["ok"] is False
    assert W.create_alert(ANA, "NVDA", "above", 0, metric="senal")["ok"] is False


def test_la_alerta_salta_con_su_senal_y_solo_con_la_suya(bases):
    _dos_fotos("NVDA", {"phase": 1}, {"phase": 2})
    W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="fase2")
    W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="minimo_52")
    W.create_alert(ANA, "AMD", "above", 0, metric="senal", senal="fase2")

    disparadas = W.check_signal_alerts(HOY)

    assert [(a["ticker"], a["senal"]) for a in disparadas] == [("NVDA", "fase2")]
    estados = {(a["ticker"], a["senal"]): a["status"] for a in W.get_alerts(ANA)["data"]}
    assert estados[("NVDA", "fase2")] == "triggered"
    assert estados[("NVDA", "minimo_52")] == "active"
    assert estados[("AMD", "fase2")] == "active"


def test_la_misma_foto_no_dispara_dos_veces(bases):
    """Son recurrentes, así que vuelven a 'active' tras el cooldown — y la
    señal de esa foto sigue ahí hasta que entre la sesión siguiente."""
    _dos_fotos("NVDA", {"phase": 1}, {"phase": 2})
    W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="fase2")
    assert len(W.check_signal_alerts(HOY)) == 1

    conn = W._conn()                      # simula el rearme del cooldown
    conn.execute("UPDATE alerts SET status = 'active'")
    conn.commit()
    conn.close()

    assert W.check_signal_alerts(HOY) == [], "ha vuelto a avisar con la misma sesión"


def test_con_una_sesion_nueva_si_vuelve_a_avisar(bases):
    _dos_fotos("NVDA", {"phase": 1}, {"phase": 2})
    W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="fase2")
    W.check_signal_alerts(HOY)

    _foto("2026-09-14", "NVDA", phase=2)          # sigue en 2: sin señal
    _foto("2026-09-15", "NVDA", phase=1)
    _foto("2026-09-16", "NVDA", phase=2)          # y vuelve a entrar
    conn = W._conn()
    conn.execute("UPDATE alerts SET status = 'active'")
    conn.commit()
    conn.close()

    assert len(W.check_signal_alerts("2026-09-16")) == 1


def test_el_bucle_de_90_segundos_NO_mira_las_de_senal(bases, monkeypatch):
    """Pedirle el precio a Yahoo cada 90 s para una señal que solo cambia una
    vez al día es gasto por nada."""
    W.create_alert(ANA, "NVDA", "above", 0, metric="senal", senal="fase2")
    monkeypatch.setattr("services.cartera_service.fetch_live_prices",
                        lambda t: pytest.fail("ha pedido precios para una alerta de señal"))
    assert W.check_all_active_alerts() == []


def test_el_aviso_de_Telegram_no_habla_de_precios(bases, monkeypatch):
    """La señal es de la sesión cerrada. Poner un precio al lado invitaría a
    leerla como algo que está pasando ahora mismo."""
    enviados = []
    monkeypatch.setattr("services.users_service.get_telegram_chat_ids", lambda ids: {ANA: "123"})
    monkeypatch.setattr("services.telegram_service.enviar_telegram",
                        lambda texto, chat_id=None: enviados.append(texto))
    W.notify_triggered_alerts([{ "user_id": ANA, "ticker": "NVDA", "metric": "senal",
                                 "senal": "fase2", "sesion_disparo": HOY,
                                 "condition": "touch", "target_price": 0 }])
    assert len(enviados) == 1
    assert "NVDA" in enviados[0] and "Fase 2" in enviados[0] and HOY in enviados[0]
    assert "Precio" not in enviados[0]


# ── El enganche: que alguien lo llame, y una sola vez por sesión ────────────

def test_el_snapshot_dice_si_ha_escrito_una_sesion_nueva(bases, monkeypatch):
    """Es lo que permite comprobar las señales UNA vez por sesión sin un bucle
    de 24 h, que derivaría de cuándo se reinició el contenedor."""
    monkeypatch.setattr("services.scanner_service.get_breadth_history",
                        lambda: [{"date": HOY, "advances": 1, "declines": 1, "total_valores": 500}],
                        raising=False)
    monkeypatch.setattr("services.scanner_service.get_universe_stocks",
                        lambda: {"NVDA": {"precio": 1.0, "rs_pct": 50.0}}, raising=False)
    for f in ("_maybe_write_mercado", "_maybe_write_cartera", "_maybe_write_tematico",
              "_corregir_amplitud_truncada"):
        monkeypatch.setattr(S, f, lambda *a, **k: None)

    assert S.maybe_write_daily_snapshot() == HOY, "no avisa de que hay sesión nueva"
    assert S.maybe_write_daily_snapshot() is None, "la segunda pasada dice que hay novedad"


def test_el_bucle_comprueba_las_senales_cuando_entra_la_sesion():
    """Que la función exista no sirve de nada si nadie la llama. Se mira el
    árbol del código, no el texto: un comentario que la mencionara no cuenta."""
    import ast
    import inspect
    import textwrap
    import routers.ws as ws

    arbol = ast.parse(textwrap.dedent(inspect.getsource(ws.market_cache_warm_loop)))

    def _menciona(nodo, nombre):
        return any(isinstance(n, ast.Name) and n.id == nombre or
                   isinstance(n, ast.Constant) and n.value == nombre
                   for n in ast.walk(nodo))

    guardas = [n for n in ast.walk(arbol)
               if isinstance(n, ast.If) and _menciona(n.test, "sesion_nueva")]
    assert guardas, "las señales se comprueban sin mirar si hay sesión nueva"
    assert any(_menciona(g, "check_signal_alerts") for g in guardas), (
        "el bucle no comprueba las señales cuando entra la foto de la sesión")
    assert any(_menciona(g, "notify_triggered_alerts") for g in guardas), (
        "las dispara pero no las avisa por Telegram")


def test_la_pantalla_conoce_las_mismas_senales_que_el_backend():
    """Si se añade una señal solo en el backend, el usuario ve una clave
    interna en la tabla; si solo en la pantalla, crea una alerta que nunca
    salta."""
    ruta = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend', 'pages', 'watchlist.js')
    js = open(ruta, encoding="utf-8").read()
    bloque = re.search(r"const SENAL_CORTA = \{(.*?)\};", js, re.S)
    assert bloque, "la pantalla ya no tiene la lista de señales"
    en_pantalla = set(re.findall(r"(\w+):\s*'", bloque.group(1)))
    assert en_pantalla == set(SE.SENALES), (
        f"solo en la pantalla: {en_pantalla - set(SE.SENALES)} · "
        f"solo en el backend: {set(SE.SENALES) - en_pantalla}")
