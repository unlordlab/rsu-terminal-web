"""
El disparo del escaneo deja de esperar a que termine.

EL FALLO, diagnosticado el 19/08/2026 gracias al aviso que se construyó el día
anterior. El escaneo diario llevaba dos noches marcado como fallido. El
Telegram, ahora que dice qué pasa, lo resolvió en un mensaje:

    HTTP 504 Gateway Time-out — nginx/1.28.3 (Ubuntu)

No era el backend: era **Nginx cortando la petición a los 60 segundos**
(`proxy_read_timeout` por defecto) mientras el escaneo tarda ~15 minutos. El
disparador recibía el 504 del PROXY y apuntaba el día como perdido.

Y LO IMPORTANTE: el escaneo SÍ terminaba y SÍ guardaba. La sesión del 18/08
quedó con 575 de 579 valores (99,3%) pese a los dos "fallos". O sea que el
aviso estaba midiendo la conexión, no el trabajo -- exactamente el error que
la tanda anterior venía a corregir, un piso más abajo.

POR QUÉ NO SE SUBE EL TIEMPO DE ESPERA DE NGINX. Sería tapar el síntoma: una
petición HTTP de quince minutos es frágil por naturaleza (cualquier proxy,
balanceador o cliente la puede cortar), y encima la configuración de Nginx ni
siquiera vive en este repositorio, así que el arreglo se quedaría fuera del
control del proyecto. Se rompe la dependencia: 202 al arrancar, y el estado se
pregunta aparte.

Uso:
    cd backend
    python -m pytest tests/test_options_scan_asincrono.py -v
"""
import os
import sys
import time
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import routers.options as R  # noqa: E402
from config import settings  # noqa: E402
from main import app  # noqa: E402

CLAVE = {"X-Admin-Key": settings.admin_key}


def _limpiar():
    # El limitador de peticiones es COMPARTIDO por toda la suite y cuenta 60
    # por minuto. Este fichero hace muchas llamadas, y sin vaciarlo el
    # siguiente test que pida algo se lleva un 429 en vez de lo que espera --
    # pasó de verdad con test_smoke, que pedía un 401 y recibía un 429.
    from middleware.rate_limit import _store
    _store.clear()
    if R._scan_lock.locked():
        try:
            R._scan_lock.release()
        except RuntimeError:
            pass
    R._ultimo_scan.update({"iniciado_en": None, "terminado_en": None,
                           "resultado": None, "error": None})


def _esperar_a_que_suelte(intentos=100):
    """El escaneo corre en un hilo; hay que darle tiempo a acabar."""
    for _ in range(intentos):
        if not R._scan_lock.locked():
            return True
        time.sleep(0.05)
    return False


# ── Arranca y responde ───────────────────────────────────────────────────────

def test_el_disparo_responde_202_sin_esperar_al_escaneo():
    """EL test. Antes esperaba los ~15 minutos que dura y Nginx cortaba a los
    60 segundos."""
    _limpiar()
    lento = {"llamado": False}

    def _scan_lento():
        lento["llamado"] = True
        time.sleep(0.4)          # simula un escaneo que tarda
        return {"ok": True, "inserted": 5, "total": 10}

    with patch("services.options_service.run_and_save_scan", _scan_lento):
        with TestClient(app) as c:
            t0 = time.time()
            r = c.post("/api/v1/options/scan-now", headers=CLAVE)
            tardanza = time.time() - t0
        assert r.status_code == 202, r.status_code
        assert r.json()["iniciado"] is True
        assert tardanza < 0.3, f"ha esperado {tardanza:.2f}s: sigue siendo sincrono"
        assert _esperar_a_que_suelte(), "el escaneo no ha terminado"
        assert lento["llamado"] is True, "respondio 202 pero no llego a escanear"
    _limpiar()


def test_mientras_escanea_el_estado_dice_que_esta_en_curso():
    _limpiar()

    def _scan_lento():
        time.sleep(0.5)
        return {"ok": True, "inserted": 1, "total": 1}

    with patch("services.options_service.run_and_save_scan", _scan_lento):
        with TestClient(app) as c:
            c.post("/api/v1/options/scan-now", headers=CLAVE)
            e = c.get("/api/v1/options/scan-estado", headers=CLAVE).json()
            assert e["en_curso"] is True
            assert e["iniciado_en"], "no dice cuando arranco"
            assert _esperar_a_que_suelte()
            fin = c.get("/api/v1/options/scan-estado", headers=CLAVE).json()
    assert fin["en_curso"] is False
    assert fin["terminado_en"], "no dice cuando termino"
    assert fin["error"] is None
    assert fin["resultado"]["inserted"] == 1
    _limpiar()


def test_un_escaneo_que_revienta_queda_registrado_con_su_motivo():
    """Sin esto volveríamos al punto de partida: un fallo que no se ve. El
    disparador mira `error` para decidir, así que tiene que llegar."""
    _limpiar()

    def _scan_roto():
        raise RuntimeError("Yahoo no responde")

    with patch("services.options_service.run_and_save_scan", _scan_roto):
        with TestClient(app) as c:
            assert c.post("/api/v1/options/scan-now", headers=CLAVE).status_code == 202
            assert _esperar_a_que_suelte()
            e = c.get("/api/v1/options/scan-estado", headers=CLAVE).json()
    assert e["en_curso"] is False
    assert "Yahoo no responde" in e["error"], e["error"]
    _limpiar()


def test_un_escaneo_que_devuelve_ok_false_tambien_cuenta_como_error():
    _limpiar()
    with patch("services.options_service.run_and_save_scan",
               lambda: {"ok": False, "error": "sin cobertura"}):
        with TestClient(app) as c:
            c.post("/api/v1/options/scan-now", headers=CLAVE)
            assert _esperar_a_que_suelte()
            e = c.get("/api/v1/options/scan-estado", headers=CLAVE).json()
    assert e["error"] == "sin cobertura"
    _limpiar()


# ── El candado ───────────────────────────────────────────────────────────────

def test_el_candado_se_suelta_al_TERMINAR_no_al_responder():
    """Si se soltara al responder el 202, un segundo disparo entraría mientras
    el primero sigue escaneando: dos escaneos completos a la vez contra la
    misma base y la misma API, que es justo lo que el candado existe para
    evitar."""
    _limpiar()

    def _scan_lento():
        time.sleep(0.5)
        return {"ok": True}

    with patch("services.options_service.run_and_save_scan", _scan_lento):
        with TestClient(app) as c:
            primera = c.post("/api/v1/options/scan-now", headers=CLAVE)
            segunda = c.post("/api/v1/options/scan-now", headers=CLAVE)
            assert primera.status_code == 202
            assert segunda.status_code == 409, (
                f"la segunda entro con {segunda.status_code}: el candado se "
                f"suelta antes de tiempo y habria dos escaneos a la vez")
            assert segunda.json()["en_curso"] is True
            assert _esperar_a_que_suelte()
            # Y cuando termina, se puede volver a lanzar.
            tercera = c.post("/api/v1/options/scan-now", headers=CLAVE)
            assert tercera.status_code == 202
            assert _esperar_a_que_suelte()
    _limpiar()


def test_si_el_escaneo_revienta_el_candado_igual_se_suelta():
    """Un candado que se queda cerrado por una excepción deja el módulo sin
    escaneos hasta el siguiente reinicio, y sin decir por qué."""
    _limpiar()
    with patch("services.options_service.run_and_save_scan",
               lambda: (_ for _ in ()).throw(RuntimeError("boom"))):
        with TestClient(app) as c:
            c.post("/api/v1/options/scan-now", headers=CLAVE)
            assert _esperar_a_que_suelte(), "el candado se ha quedado cerrado"
    assert not R._scan_lock.locked()
    _limpiar()


# ── Seguridad, que no se afloje al reescribir ────────────────────────────────

def test_los_dos_endpoints_siguen_exigiendo_la_clave_de_administrador():
    _limpiar()
    with TestClient(app) as c:
        assert c.post("/api/v1/options/scan-now").status_code in (401, 403)
        assert c.get("/api/v1/options/scan-estado").status_code in (401, 403)
        mala = {"X-Admin-Key": "no-es"}
        assert c.post("/api/v1/options/scan-now", headers=mala).status_code == 401
        assert c.get("/api/v1/options/scan-estado", headers=mala).status_code == 401
    _limpiar()
