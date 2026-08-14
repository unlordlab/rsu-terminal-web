"""
Avisar de una apertura o un cierre dos veces no manda dos mensajes.

Esta garantía existía desde julio de 2026 (clave única por operación e
`INSERT OR IGNORE`: solo envía quien gana la inserción) pero **no tenía ni un
test**, y hasta ahora tampoco hacía mucha falta: la comprobación solo la
disparaba un bucle cada 15 minutos, así que nadie la ejecutaba dos veces
seguidas.

Desde el 14/08/2026 la dispara también el botón «Actualizar» de Cartera, para
no esperar ese cuarto de hora tras apuntar una operación en la hoja. Con eso,
la idempotencia pasa de ser una propiedad tranquila a ser lo único que separa
«pulsar el botón tres veces» de «recibir el mismo aviso tres veces».

Uso:
    cd backend
    python -m pytest tests/test_cartera_notificaciones_idempotentes.py -v
"""
import sys, os, sqlite3
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.cartera_tracking_service as T  # noqa: E402


@pytest.fixture
def base(tmp_path, monkeypatch):
    """Base propia por test: no se toca la real."""
    ruta = str(tmp_path / "avisos.db")
    monkeypatch.setattr(T, "DB_PATH", ruta, raising=False)
    T.init_db()
    return ruta


def _intentar_registrar(conn, clave, cuando):
    """Devuelve True si esta inserción es la que 'gana' -- que es exactamente
    la condición que el servicio usa para decidir si envía el mensaje."""
    cur = conn.execute(
        "INSERT OR IGNORE INTO notificadas (clave, tipo, ticker, enviado_en) VALUES (?,?,?,?)",
        (clave, clave.split("|")[2], clave.split("|")[0], cuando))
    return cur.rowcount == 1


def test_la_misma_operacion_no_se_registra_dos_veces(base):
    """El corazón del asunto: una operación solo puede 'ganar' una vez, y solo
    quien gana envía. Es lo que convierte tres pulsaciones del botón en un
    único mensaje."""
    conn = T._conn()
    clave = "AAPL|2026-08-14|apertura"
    primera = _intentar_registrar(conn, clave, "2026-08-14T10:00:00")
    segunda = _intentar_registrar(conn, clave, "2026-08-14T10:00:01")
    tercera = _intentar_registrar(conn, clave, "2026-08-14T10:00:02")
    conn.commit(); conn.close()
    assert primera is True, "la primera vez tiene que ganar y enviar"
    assert (segunda, tercera) == (False, False), "repetir NO puede volver a enviar"


def test_la_clave_es_unica_en_el_esquema(base):
    """Si alguien quita el UNIQUE, la deduplicación deja de existir y el botón
    pasa a poder mandar un mensaje por pulsación."""
    conn = T._conn()
    fila = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='notificadas'"
    ).fetchone()
    conn.close()
    assert fila is not None, "no existe la tabla de avisos"
    assert "UNIQUE" in fila[0].upper(), (
        "la columna `clave` tiene que ser UNIQUE: es lo que impide el aviso repetido")


def test_operaciones_distintas_del_mismo_ticker_si_se_avisan_por_separado(base):
    """La clave lleva la fecha y el tipo, no solo el ticker: comprar y vender
    el mismo valor son dos avisos legítimos, y comprarlo dos veces en fechas
    distintas también."""
    conn = T._conn()
    claves = ["AAPL|2026-08-14|apertura", "AAPL|2026-08-14|cierre",
              "AAPL|2026-09-01|apertura"]
    ganadas = 0
    for c in claves:
        cur = conn.execute(
            "INSERT OR IGNORE INTO notificadas (clave, tipo, ticker, enviado_en) VALUES (?,?,?,?)",
            (c, c.split("|")[2], "AAPL", "2026-08-14T10:00:00"))
        ganadas += cur.rowcount
    conn.commit(); conn.close()
    assert ganadas == 3, "tres operaciones distintas son tres avisos distintos"


def test_un_fallo_al_leer_la_cartera_no_envia_nada(base):
    """Si la hoja no se puede leer, no se inventa una lista de operaciones ni
    se manda nada: se devuelve el error."""
    with patch.object(T, "enviar_telegram") as telegram, \
         patch("services.cartera_service.get_cartera", return_value={"ok": False, "error": "hoja caída"}):
        r = T.procesar_cartera_notificaciones()
    assert "error" in r
    telegram.assert_not_called()
