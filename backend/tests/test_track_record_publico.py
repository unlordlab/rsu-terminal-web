"""
El Track Record, público desde el 14/09/2026, y lo que se le añadió.

DECISIÓN DEL USUARIO: la página se ve SIN cuenta. Es la prueba de que las
herramientas funcionan, y una prueba que solo ve quien ya ha pagado no
convence a nadie.

LO QUE SE RETIENE a quien no está suscrito, y solo eso:
  · de las tesis, precio objetivo, título, nombre, autor y rating (la página
    no los pinta, y en la respuesta eran el resumen de una tesis de pago);
  · el ticker de las tesis de menos de 30 días. Su resultado sigue contando en
    los totales y la fila se ve: nada se filtra, solo se aplaza.

LO QUE SE COMPROBÓ EN EL NAVEGADOR sin sesión: la primera versión rebotaba al
login. El ticker del topbar pedía /market/indices, recibía 401 y el
interceptor de sesión caducada mandaba al visitante fuera — el mismo fallo que
tuvo la política de privacidad el 18/08.

Y además: RSU Score y Options Flow se ven también aquí, las previsiones del
Roadmap salen de un registro con revisiones fechadas, y la página ya no da
error si fallan el Algoritmo y las tesis pero CANSLIM ha cargado.

Uso:
    cd backend
    python -m pytest tests/test_track_record_publico.py -v
"""
import inspect
import os
import re
import sqlite3
import sys
import uuid
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402
from auth import create_token  # noqa: E402
from services import users_service  # noqa: E402
import services.track_record_service as T  # noqa: E402
import routers.track_record as R  # noqa: E402

FRONT = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')
URL = "/api/v1/track-record/"


def _leer(*partes):
    with open(os.path.join(FRONT, *partes), encoding='utf-8') as f:
        return f.read()


def _fecha(dias_atras):
    return (datetime.now(timezone.utc).date() - timedelta(days=dias_atras)).isoformat()


def _datos():
    comun = {"precio_objetivo": 250.0, "titulo": "Tesis de pago", "nombre": "Empresa", "autor": "Gael",
             "rating": "BUY", "estado_dato": "ok", "retorno_pct": 5.0, "vs_spy_pp": 1.0}
    return {
        "ok": True,
        "algoritmo": {"n_senales": 0},
        "canslim": {"n_filas": 0},
        "rsu_score": {"n_registros": 0, "tramos": []},
        "options": {"ok": True, "senales": 0},
        "tesis": {"n_tesis": 2, "tesis": [
            {**comun, "ticker": "NVDA", "fecha": _fecha(3)},
            {**comun, "ticker": "AAPL", "fecha": _fecha(90)},
        ]},
    }


@pytest.fixture
def cliente(monkeypatch):
    from middleware.rate_limit import _store
    _store.clear()
    datos = _datos()
    monkeypatch.setattr(R, "get_track_record", lambda: datos)
    creados = []

    def token(tier):
        email = f"test-tr-{uuid.uuid4().hex[:10]}@local.test"
        users_service.create_user(email, "probando1234")
        creados.append(email)
        if tier != "free":
            users_service.set_tier(email, tier)
        u = users_service.get_user_by_email(email)
        return create_token({"sub": u["email"], "tier": u["tier"], "tv": u["token_version"]})

    yield TestClient(app), token, datos
    conn = sqlite3.connect(users_service.DB_PATH)
    try:
        for e in creados:
            conn.execute("DELETE FROM users WHERE email = ?", (e,))
        conn.commit()
    finally:
        conn.close()


def _tesis(r):
    return {(t.get("ticker") or "RESERVADA"): t for t in r.json()["tesis"]["tesis"]}


# ── Quién ve qué ────────────────────────────────────────────────────────────

def test_sin_cuenta_se_ve_y_no_pide_login(cliente):
    client, _, _ = cliente
    r = client.get(URL)
    assert r.status_code == 200
    assert r.json()["visitante"] == "anonimo"


def test_una_sesion_caducada_ve_lo_mismo_que_un_visitante(cliente):
    """Nunca 401: el interceptor del frontend lo mandaría al login desde una
    página abierta."""
    client, _, _ = cliente
    r = client.get(URL, headers={"Authorization": "Bearer token-que-no-vale"})
    assert r.status_code == 200 and r.json()["visitante"] == "anonimo"


def test_sin_suscripcion_la_tesis_reciente_no_dice_el_valor(cliente):
    client, token, _ = cliente
    for cabeceras in ({}, {"Authorization": f"Bearer {token('free')}"}):
        tesis = _tesis(client.get(URL, headers=cabeceras))
        assert "NVDA" not in tesis, "una tesis de 3 días no puede enseñar su ticker gratis"
        reservada = tesis["RESERVADA"]
        assert reservada["retorno_pct"] == 5.0, "el resultado sí se ve: nada se filtra"
        assert reservada["reservada_hasta"] == (datetime.fromisoformat(_fecha(3)) + timedelta(days=30)).date().isoformat()
        vieja = tesis["AAPL"]
        for campo in ("precio_objetivo", "titulo", "nombre", "autor", "rating"):
            assert campo not in vieja and campo not in reservada, campo


def test_el_suscriptor_lo_ve_todo(cliente):
    client, token, _ = cliente
    r = client.get(URL, headers={"Authorization": f"Bearer {token('tier1')}"})
    assert r.json()["visitante"] == "suscriptor"
    tesis = _tesis(r)
    assert "NVDA" in tesis and tesis["NVDA"]["precio_objetivo"] == 250.0
    assert "reservada_hasta" not in tesis["NVDA"]


def test_no_se_toca_la_cache_compartida(cliente):
    """La respuesta del anónimo sale de una copia: si se modificara el objeto
    cacheado, el siguiente suscriptor recibiría la versión recortada."""
    client, token, datos = cliente
    client.get(URL)
    assert datos["tesis"]["tesis"][0]["ticker"] == "NVDA"
    assert datos["tesis"]["tesis"][0]["precio_objetivo"] == 250.0


def test_el_plazo_de_reserva_es_de_un_mes():
    assert T.DIAS_RESERVA_TESIS == 30


# ── Las fuentes ─────────────────────────────────────────────────────────────

def _sin_cache(monkeypatch):
    from services.cache import cache
    monkeypatch.setattr(cache, "get", lambda *a, **k: None)
    monkeypatch.setattr(cache, "set", lambda *a, **k: None)


def _rota():
    raise RuntimeError("fuente caída")


def test_basta_una_fuente_para_que_la_pagina_salga(monkeypatch):
    """Hasta el 14/09, con el Algoritmo y las tesis caídos daba error aunque
    CANSLIM hubiera cargado bien."""
    _sin_cache(monkeypatch)
    for f in ("_track_record_algoritmo", "_track_record_tesis", "_track_record_rsu_score", "_track_record_options"):
        monkeypatch.setattr(T, f, _rota)
    monkeypatch.setattr(T, "_track_record_canslim", lambda: {"n_filas": 3})
    r = T.get_track_record.__wrapped__() if hasattr(T.get_track_record, "__wrapped__") else T.get_track_record()
    assert r["ok"] and r["canslim"] == {"n_filas": 3} and r["algoritmo"] is None


def test_si_fallan_todas_se_dice(monkeypatch):
    _sin_cache(monkeypatch)
    for f in ("_track_record_algoritmo", "_track_record_tesis", "_track_record_canslim",
              "_track_record_rsu_score", "_track_record_options"):
        monkeypatch.setattr(T, f, _rota)
    assert T.get_track_record()["ok"] is False


def test_rsu_score_y_options_entran_en_la_respuesta(monkeypatch):
    _sin_cache(monkeypatch)
    for f in ("_track_record_algoritmo", "_track_record_tesis", "_track_record_canslim"):
        monkeypatch.setattr(T, f, lambda: None)
    monkeypatch.setattr(T, "_track_record_rsu_score", lambda: {"n_registros": 7})
    monkeypatch.setattr(T, "_track_record_options", lambda: {"ok": True, "senales": 9})
    r = T.get_track_record()
    assert r["rsu_score"] == {"n_registros": 7} and r["options"]["senales"] == 9


def test_el_resumen_de_rsu_score_dice_cuantos_tienen_resultado():
    from services.rsu_score_tracking_service import obtener_resumen_por_bucket
    tramos = obtener_resumen_por_bucket()
    assert tramos and all("n_20d" in t and "n_60d" in t for t in tramos)


def test_rsu_score_dice_si_ya_hay_filas_comparadas_con_el_spy(monkeypatch):
    """Desde el mismo 14/09 el RSU Score se compara con el índice
    (test_track_record_ampliado.py). El aviso de «aún sin comparar» solo sale
    mientras ninguna fila tiene los dos datos."""
    import services.rsu_score_tracking_service as S
    tramo = {"bucket": "X", "rango": "0-100", "n": 3, "n_20d": 3, "n_vs_spy_20d": 0, "n_vs_spy_5d": 0}
    monkeypatch.setattr(S, "obtener_resumen_por_bucket", lambda: [tramo])
    assert T._track_record_rsu_score()["comparado_con_spy"] is False
    monkeypatch.setattr(S, "obtener_resumen_por_bucket", lambda: [{**tramo, "n_vs_spy_20d": 2}])
    assert T._track_record_rsu_score()["comparado_con_spy"] is True


def test_peticiones_simultaneas_no_repiten_el_calculo():
    fuente = inspect.getsource(T)
    assert re.search(r"@_single_flight\s*\ndef get_track_record", fuente)
    assert 'cache.single_flight("track_record:all")' in fuente


# ── Frontend ────────────────────────────────────────────────────────────────

def test_la_ruta_ya_no_esta_protegida():
    router = _leer('core', 'router.js')
    protegidas = re.search(r"const protectedRoutes = \[([^\]]*)\]", router).group(1)
    assert "'/track-record'" not in protegidas
    assert "'/track-record'" in re.search(r"PAGINAS_PUBLICAS_CONTADAS = new Set\(\[([^\]]*)\]", router).group(1), \
        "la visita de quien tiene sesión se sigue contando"


def test_sin_sesion_el_ticker_no_pide_datos_protegidos():
    """EL fallo del navegador: /market/indices → 401 → login."""
    ws = _leer('core', 'websocket.js')
    assert "'/track-record'" in re.search(r"RUTAS_PUBLICAS = \[([^\]]*)\]", ws).group(1)
    funcion = ws[ws.index("export function paginaSinSesion"):]
    funcion = funcion[:funcion.index("\n}")]
    assert "RUTAS_PUBLICAS.includes(ruta) && !isLoggedIn()" in funcion, \
        "con sesión, el ticker en directo tiene que seguir funcionando"
    init = ws[ws.index("export function initWebSocket"):]
    assert "if (paginaSinSesion()) return;" in init[:300]
    topbar = _leer('components', 'topbar.js')
    respaldo = topbar[topbar.index("async function respaldoPorHttp"):]
    assert "if (paginaSinSesion()) return;" in respaldo[:400]


def test_la_pagina_pinta_las_secciones_nuevas_y_el_aviso():
    js = _leer('pages', 'track_record.js')
    for llamada in ("avisoVisitante(data)", "seccionRsuScore(data.rsu_score)", "seccionOptions(data.options)",
                    "seccionPrevisiones(data)", "seccionTesis(data.tesis, data)"):
        assert llamada in js, llamada
    assert "🔒 reservada" in js
    assert "data-ir=\"/register\"" in js


# ── Previsiones del Roadmap ─────────────────────────────────────────────────

def test_el_roadmap_y_el_track_record_leen_el_mismo_registro():
    for pagina in ('roadmap.js', 'track_record.js'):
        assert "from '/core/previsiones.js'" in _leer('pages', pagina), pagina
    assert "PREVISIONES.map" in _leer('pages', 'roadmap.js')


def test_cada_prevision_tiene_revisiones_fechadas_y_veredicto_valido():
    src = _leer('core', 'previsiones.js')
    veredictos = set(re.findall(r"^\s{4}(\w+):\s+\{ icono", src, re.M))
    assert veredictos == {"cumplida", "parcial", "fallida", "pendiente"}
    revisiones = re.findall(r"\{ fecha: (null|'[\d-]+'), veredicto: '(\w+)'", src)
    assert len(revisiones) >= 4
    for fecha, veredicto in revisiones:
        assert veredicto in veredictos
        assert (fecha == "null") == (veredicto == "pendiente"), "solo lo pendiente va sin fecha"
