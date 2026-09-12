"""
Watchlist #10: el chat no tenía tope por usuario.

EL CASO. El chat solo tenía el `rate_limit` global del router y el manejo del
429 de Groq: nada impedía que una sola cuenta se pasara el día preguntando. Y el
coste no es solo de dinero — los límites de Groq son por minuto y por modelo,
así que un usuario a fuego deja sin chat a TODOS los demás.

EL TOPE es de 40 preguntas en una ventana MÓVIL de 24 horas. Móvil y no «se
reinicia a medianoche» por dos razones: la base guarda UTC y quien pregunta está
en Madrid (el corte caería a las 2 de la madrugada, que no le dice nada a
nadie), y con un corte fijo el tope real se duplica pegando dos ráfagas a un
lado y otro.

Uso:
    cd backend
    python -m pytest tests/test_chat_tope_por_usuario.py -v
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.chat_service as C  # noqa: E402

TOPE = C.LIMITE_PREGUNTAS_24H


@pytest.fixture
def chat(monkeypatch):
    """Base temporal y un Groq simulado que cuenta cuántas veces se le llama."""
    tmp = os.path.join(tempfile.mkdtemp(), "chat.db")
    monkeypatch.setattr(C, "DB_PATH", tmp)
    C.init_db()
    llamadas = []
    monkeypatch.setattr(C, "_llamar_groq",
                        lambda *a, **k: llamadas.append(1) or "respuesta del modelo")
    monkeypatch.setattr(C, "_buscar_chunks_relevantes", lambda *a, **k: [])
    return llamadas


def _preguntas(usuario, cuantas, hace_horas=0.0):
    conn = C._conn()
    cuando = (datetime.utcnow() - timedelta(hours=hace_horas)).isoformat()
    for _ in range(cuantas):
        conn.execute("INSERT INTO mensajes (usuario, rol, mensaje, creado_en) VALUES (?,?,?,?)",
                     (usuario, "user", "pregunta", cuando))
        conn.execute("INSERT INTO mensajes (usuario, rol, mensaje, creado_en) VALUES (?,?,?,?)",
                     (usuario, "assistant", "respuesta", cuando))
    conn.commit()
    conn.close()


# ── El tope ─────────────────────────────────────────────────────────────────

def test_por_debajo_del_tope_se_responde_normal(chat):
    _preguntas("ana@x.com", TOPE - 1)
    r = C.enviar_mensaje("ana@x.com", "¿qué es el RVOL?")
    assert r["ok"] is True and r["respuesta"] == "respuesta del modelo"
    assert len(chat) == 1


def test_al_llegar_al_tope_NO_se_llama_al_modelo(chat):
    """EL test: comprobarlo después de llamar costaría justo lo que se evita."""
    _preguntas("ana@x.com", TOPE)
    r = C.enviar_mensaje("ana@x.com", "otra más")
    assert r["ok"] is False and r.get("limite") is True
    assert chat == [], "ha llamado a Groq pese a estar en el tope"
    assert str(TOPE) in r["error"], f"el aviso no dice cuál es el tope: {r['error']}"


def test_el_tope_es_por_CUENTA_no_global(chat):
    """Que uno se pase no puede dejar sin chat a los demás: eso es exactamente
    lo que este tope viene a evitar."""
    _preguntas("ana@x.com", TOPE)
    assert C.enviar_mensaje("ana@x.com", "otra")["ok"] is False
    assert C.enviar_mensaje("luis@x.com", "la primera mía")["ok"] is True


def test_las_de_hace_mas_de_24_horas_ya_no_cuentan(chat):
    """La ventana es móvil: lo de anteayer no gasta cupo de hoy."""
    _preguntas("ana@x.com", TOPE, hace_horas=25)
    assert C.enviar_mensaje("ana@x.com", "hoy")["ok"] is True


def test_las_respuestas_del_asistente_no_gastan_cupo(chat):
    """La tabla guarda las dos caras de la conversación; el tope es de
    PREGUNTAS. Contar las dos lo dejaría en la mitad sin querer."""
    _preguntas("ana@x.com", TOPE // 2)          # mete 20 de usuario y 20 del asistente
    r = C.enviar_mensaje("ana@x.com", "¿voy por la mitad?")
    assert r["ok"] is True


def test_el_aviso_dice_cuando_se_puede_volver(chat):
    """«Vuelve más tarde» no sirve de nada: la plaza se libera cuando la más
    antigua de las que cuentan cumple 24 horas, y eso se puede decir."""
    _preguntas("ana@x.com", TOPE, hace_horas=21)
    r = C.enviar_mensaje("ana@x.com", "otra")
    assert "dentro de 2 hora" in r["error"] or "dentro de 3 hora" in r["error"], r["error"]


def test_el_aviso_en_minutos_cuando_queda_poco(chat):
    _preguntas("ana@x.com", TOPE, hace_horas=23.5)
    r = C.enviar_mensaje("ana@x.com", "otra")
    assert "minutos" in r["error"], r["error"]


def test_una_pregunta_vacia_no_gasta_cupo(chat):
    _preguntas("ana@x.com", TOPE - 1)
    C.enviar_mensaje("ana@x.com", "   ")
    r = C.enviar_mensaje("ana@x.com", "la de verdad")
    assert r["ok"] is True, "el mensaje vacío ha consumido la última pregunta"


def test_el_contador_cuenta_lo_que_se_guarda(chat):
    """Cierre del círculo: tras 40 respondidas de verdad, la 41 se corta."""
    for i in range(TOPE):
        assert C.enviar_mensaje("ana@x.com", f"pregunta {i}")["ok"] is True
    assert C.enviar_mensaje("ana@x.com", "la 41")["ok"] is False
    assert len(chat) == TOPE
