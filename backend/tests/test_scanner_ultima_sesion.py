"""
El escaneo nocturno va una sesión por detrás casi todas las noches, y no se sabe por qué.

EL CASO, Scanner #25, encontrado el 10/09/2026 auditando el briefing. El
registro del escaneo lo decía literalmente:

    «Amplitud: sesión 2026-09-09 NO se publica — 21 valores frente a una
     mediana de 2426»

Revisadas las seis últimas noches, pasa en CUATRO (21, 26, 22 y 30 valores con
la barra del día). A las 00:15 UTC —cuatro horas después del cierre— Yahoo
solo sirve la última sesión para ~1% del universo. La protección de cobertura
funciona y no publica una amplitud sobre 21 valores, pero el resultado es que
Market, el briefing, CANSLIM, RS/RW y Temáticos enseñan casi a diario la sesión
anterior. Y las filas por ticker mezclan dos días: ~21 con el miércoles y ~477
con el martes.

LO QUE ESTE FICHERO ATA NO ES EL ARREGLO, ES LA PRUEBA. No se sabe todavía si
la fila llega vacía (cierre NaN, que `dropna()` tira) o si directamente no
llega, ni si pasa igual por `Ticker.history` que por `download`. Mover el cron
sin saberlo podría no arreglar nada. `diagnosticar_ultima_sesion()` deja esa
prueba en el registro la noche que ocurra, y el recuento en el Gist.

Uso:
    cd backend
    python -m pytest tests/test_scanner_ultima_sesion.py -v
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "shared"))

import scanner_universe as S  # noqa: E402


def _serie(hasta):
    fechas = pd.to_datetime(["2026-09-03", "2026-09-04", "2026-09-08", "2026-09-09"])
    fechas = [f for f in fechas if f <= pd.Timestamp(hasta)]
    return pd.Series(range(len(fechas)), index=pd.DatetimeIndex(fechas), dtype=float)


def _universo(con, sin):
    """`con` valores traen el miércoles 09/09; `sin`, solo hasta el martes."""
    d = {f"C{i:04d}": _serie("2026-09-09") for i in range(con)}
    d.update({f"S{i:04d}": _serie("2026-09-08") for i in range(sin)})
    return d


@pytest.fixture
def yahoo(monkeypatch):
    """Cuenta las llamadas: las noches buenas no pueden costar ninguna."""
    llamadas = []

    def descarga(tickers, **k):
        llamadas.append(("download", list(tickers)))
        idx = pd.DatetimeIndex(pd.to_datetime(["2026-09-08", "2026-09-09"]))
        return pd.DataFrame({t: [1.0, float("nan")] for t in tickers}, index=idx)

    class Ticker:
        def __init__(self, s):
            self.s = s

        def history(self, **k):
            llamadas.append(("history", self.s))
            return pd.DataFrame({"Close": [1.0]}, index=pd.DatetimeIndex(pd.to_datetime(["2026-09-08"])))

    monkeypatch.setattr(S.yf, "download", descarga)
    monkeypatch.setattr(S.yf, "Ticker", Ticker)
    return llamadas


def test_el_caso_real_21_de_2400_se_detecta_como_incompleto(yahoo, capsys):
    """EL test. Es la cifra de la noche del 09/09."""
    info = S.diagnosticar_ultima_sesion(_universo(21, 2400))
    assert info["fecha"] == "2026-09-09"
    assert info["con_barra"] == 21 and info["total"] == 2421
    assert info["completa"] is False
    assert "solo 21 de 2421" in capsys.readouterr().out


def test_se_dice_QUIENES_la_traen(yahoo, capsys):
    """Si los 21 afortunados tienen algo en común —un mercado, un tamaño— es la
    pista más rápida hacia la causa."""
    info = S.diagnosticar_ultima_sesion(_universo(3, 100))
    assert info["la_traen"] == ["C0000", "C0001", "C0002"]
    assert "C0000" in capsys.readouterr().out


def test_se_mira_la_fila_EN_CRUDO_por_los_dos_caminos(yahoo, capsys):
    """La pregunta que decide el arreglo: ¿la fila llega con el cierre vacío o
    no llega? Por `download` (el que usa el escaneo) y por `Ticker.history` (el
    que usa el briefing, que a las 07:54 ET sí trae la barra)."""
    S.diagnosticar_ultima_sesion(_universo(3, 100))
    tipos = [t for t, _ in yahoo]
    assert "download" in tipos and "history" in tipos
    # En la muestra van valores SIN la barra y alguno CON ella, para comparar.
    muestra = next(x for t, x in yahoo if t == "download")
    assert any(t.startswith("S") for t in muestra) and any(t.startswith("C") for t in muestra)
    salida = capsys.readouterr().out
    assert "SIN dropna" in salida and "NaN" in salida, "no se enseña la fila en crudo"


def test_una_noche_NORMAL_no_cuesta_ninguna_llamada(yahoo):
    """El diagnóstico es para las noches malas. Las buenas no pagan nada."""
    info = S.diagnosticar_ultima_sesion(_universo(2400, 21))
    assert info["completa"] is True
    assert yahoo == []


def test_el_diagnostico_NUNCA_tumba_el_escaneo(monkeypatch):
    """Un diagnóstico que revienta el escaneo que diagnostica sería peor que el
    problema que investiga."""
    def rota(*a, **k):
        raise RuntimeError("Yahoo caído")
    monkeypatch.setattr(S.yf, "download", rota)
    monkeypatch.setattr(S.yf, "Ticker", rota)
    info = S.diagnosticar_ultima_sesion(_universo(3, 100))
    assert info["completa"] is False


def test_sin_datos_devuelve_vacio():
    assert S.diagnosticar_ultima_sesion({}) == {}


def test_el_recuento_llega_al_Gist_sin_la_lista_de_tickers():
    """El registro del Action caduca a los 90 días; el recuento en el Gist sirve
    para contar noches. La lista de 40 tickers no hace falta ahí."""
    import ast
    import inspect
    arbol = ast.parse(inspect.getsource(S.run_scan))
    claves = [k.value for n in ast.walk(arbol) if isinstance(n, ast.Dict)
              for k in n.keys if isinstance(k, ast.Constant)]
    assert "ultima_sesion" in claves, "el recuento no se publica en el meta del Gist"
    llamadas = [n for n in ast.walk(arbol) if isinstance(n, ast.Call)
                and getattr(n.func, "id", None) == "diagnosticar_ultima_sesion"]
    assert llamadas, "run_scan() no llama al diagnóstico"
