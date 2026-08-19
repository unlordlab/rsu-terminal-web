"""
Forzar los avisos de Cartera es cosa del titular, y un Telegram fallido no
puede tragarse el aviso.

EL HALLAZGO (auditoria de Cartera, #B9). `POST /cartera/notificaciones/check`
lo podia disparar cualquier usuario de pago. El modulo entero esta tras el
tier de pago, asi que no era «cualquiera» -- pero es que la cartera no es por
usuario: es UNA, la del titular, leida de su hoja, y sus avisos van a SU
Telegram. Forzarlos no le sirve a nadie mas, y en cambio permitia que un
usuario cualquiera decidiera CUANDO llega un mensaje al chat del dueño.

LO QUE APARECIO AL MIRARLO DE CERCA, y que era peor. El envio funciona
reservando primero la clave de dedup y mandando despues (asi dos llamadas
solapadas no duplican el aviso). Pero **nadie miraba si el envio habia
salido**: si Telegram fallaba -sin red, HTTP 429, la API caida- la reserva ya
estaba puesta y comiteada, asi que el aviso de esa apertura o ese cierre no se
mandaba NUNCA MAS; todas las pasadas siguientes lo veian como «ya avisado». Y
sin rastro en ninguna pantalla, porque los avisos de Cartera solo existen en
Telegram.

Uso:
    cd backend
    python -m pytest tests/test_cartera_avisos_solo_titular.py -v
"""
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import auth as A  # noqa: E402
import services.cartera_tracking_service as T  # noqa: E402


DUENO = "marc@ejemplo.com"


@pytest.fixture
def base(tmp_path, monkeypatch):
    monkeypatch.setattr(T, "DB_PATH", str(tmp_path / "avisos.db"), raising=False)
    T.init_db()
    return T.DB_PATH


def _bootstrap():
    """La primera ejecucion NO envia: memoriza lo que ya hay para no soltar un
    aluvion con todo el historico de la hoja. Tiene que memorizar ALGO -- con
    la cartera vacia la tabla se queda vacia y la pasada siguiente se vuelve a
    considerar la primera."""
    with patch("services.cartera_service.get_cartera",
               return_value=_cartera([_pos("VIEJA", "2026-01-02")])):
        r = T.procesar_cartera_notificaciones()
    assert r["bootstrap"] is True and r["enviadas"] == 0
    return r


def _cartera(abiertas):
    return {"ok": True, "abiertas": abiertas, "cerradas": []}


def _pos(ticker, fecha="2026-08-19"):
    # Las claves son las que usa _clave(): ticker|fecha|compra|tipo.
    return {"ticker": ticker, "fecha": fecha, "compra": 10.0, "actual": 11.0,
            "shares": 100, "nivel": "CORE", "inv": 1000.0, "pnl": 10.0}


# ── Quien puede forzar los avisos ────────────────────────────────────────────

def test_un_usuario_de_pago_cualquiera_ya_no_es_el_titular():
    """El hallazgo #B9 en una linea."""
    with patch.object(A.settings, "owner_email", DUENO):
        assert A.es_titular({"sub": "otra.persona@ejemplo.com", "tier": "tier1"}) is False
        assert A.es_titular({"sub": DUENO, "tier": "tier1"}) is True


def test_el_correo_se_compara_normalizado():
    """El login guarda el correo en minusculas; si el .env lleva una mayuscula
    o un espacio de mas, el propio dueño dejaria de reconocerse."""
    with patch.object(A.settings, "owner_email", "  Marc@Ejemplo.COM "):
        assert A.es_titular({"sub": DUENO}) is True


def test_sin_owner_email_configurado_no_puede_forzarlo_nadie():
    """Cerrado por defecto. Lo unico que se pierde es la inmediatez del boton:
    el bucle de 15 minutos sigue mandando los avisos igual."""
    with patch.object(A.settings, "owner_email", ""):
        assert A.es_titular({"sub": DUENO}) is False
        assert A.es_titular({"sub": "quien.sea@ejemplo.com"}) is False


def test_la_dependencia_corta_con_403_no_con_401():
    """403 y no 401: la sesion es valida, lo que falta es el derecho."""
    from fastapi import HTTPException
    with patch.object(A.settings, "owner_email", DUENO):
        with pytest.raises(HTTPException) as e:
            A.verify_owner({"sub": "otra.persona@ejemplo.com"})
        assert e.value.status_code == 403
        assert A.verify_owner({"sub": DUENO})["sub"] == DUENO


def test_el_endpoint_de_avisos_exige_titular_no_solo_sesion():
    """Que la dependencia exista no basta: hay que comprobar que es LA que
    protege este endpoint. Si alguien la devuelve a verify_token, este test
    cae."""
    import inspect
    import routers.cartera as R
    firma = inspect.signature(R.cartera_notificaciones_check)
    dep = firma.parameters["user"].default
    assert dep.dependency is A.verify_owner, (
        f"el endpoint se protege con {dep.dependency.__name__}, no con verify_owner")


# ── Un Telegram fallido no puede perder el aviso ─────────────────────────────

def test_si_telegram_falla_el_aviso_se_reintenta_en_la_proxima_pasada(base):
    """EL test. Antes, un fallo transitorio de Telegram dejaba la reserva
    puesta y el aviso se perdia para siempre."""
    cartera = _cartera([_pos("AAPL")])
    _bootstrap()

    with patch("services.cartera_service.get_cartera", return_value=cartera), \
         patch.object(T, "enviar_telegram", return_value=False) as fallo:
        r1 = T.procesar_cartera_notificaciones()
    assert fallo.called
    assert r1["enviadas"] == 0 and r1["fallidas"] == 1

    with patch("services.cartera_service.get_cartera", return_value=cartera), \
         patch.object(T, "enviar_telegram", return_value=True) as ok:
        r2 = T.procesar_cartera_notificaciones()
    assert r2["enviadas"] == 1, (
        "el aviso se ha perdido: la reserva se quedo puesta pese a que el "
        "envio fallo, asi que ninguna pasada posterior lo vuelve a intentar")
    assert ok.called


def test_un_envio_bueno_sigue_sin_repetirse(base):
    """Y el arreglo no puede abrir la puerta a lo contrario: soltar la reserva
    solo pasa cuando el envio ha fallado."""
    cartera = _cartera([_pos("AAPL")])
    _bootstrap()

    with patch("services.cartera_service.get_cartera", return_value=cartera), \
         patch.object(T, "enviar_telegram", return_value=True):
        primera = T.procesar_cartera_notificaciones()
        segunda = T.procesar_cartera_notificaciones()
        tercera = T.procesar_cartera_notificaciones()
    assert primera["enviadas"] == 1
    assert (segunda["enviadas"], tercera["enviadas"]) == (0, 0)
    assert (segunda["fallidas"], tercera["fallidas"]) == (0, 0)


def test_el_fallo_se_cuenta_y_se_devuelve(base):
    """Un fallo silencioso es como no tenerlo: quien llama tiene que poder
    verlo."""
    cartera = _cartera([_pos("AAPL"), _pos("MSFT")])
    _bootstrap()
    with patch("services.cartera_service.get_cartera", return_value=cartera), \
         patch.object(T, "enviar_telegram", side_effect=[True, False]):
        r = T.procesar_cartera_notificaciones()
    assert r["enviadas"] == 1 and r["fallidas"] == 1


def test_por_HTTP_el_usuario_de_pago_que_no_es_titular_recibe_403():
    """Comprobacion a nivel de peticion, no solo de la funcion: el router
    entero va detras del tier de pago, asi que hay que confirmar que la
    restriccion del titular se aplica ADEMAS de esa, y que un usuario de pago
    legitimo se lleva un 403 aqui."""
    from fastapi.testclient import TestClient
    from main import app
    from auth import verify_token
    from middleware.rate_limit import _store

    def _como(correo):
        return lambda: {"sub": correo, "tier": "tier1"}

    with patch.object(A.settings, "owner_email", DUENO), \
         patch("services.cartera_tracking_service.procesar_cartera_notificaciones",
               return_value={"enviadas": 0, "migradas": 0, "fallidas": 0, "bootstrap": False}):
        _store.clear()
        app.dependency_overrides[verify_token] = _como("otra.persona@ejemplo.com")
        try:
            with TestClient(app) as c:
                ajeno = c.post("/api/v1/cartera/notificaciones/check")
            app.dependency_overrides[verify_token] = _como(DUENO)
            with TestClient(app) as c:
                propio = c.post("/api/v1/cartera/notificaciones/check")
        finally:
            app.dependency_overrides.clear()
            _store.clear()

    assert ajeno.status_code == 403, ajeno.status_code
    assert propio.status_code == 200, propio.status_code
