"""
La fecha de resultados llevaba meses sin leerse, y nadie se enteró.

CÓMO SE ENCONTRÓ, 21/08/2026. Al separar la ventaja del flujo entre contratos
cerca y lejos de resultados, el bloque «cerca» salió con CERO contratos. No era
que no los hubiera: en la base de producción, `near_earnings` estaba a 0 y
`earnings_rel` a NULL en el 100% de las filas guardadas. Ni una marca en meses.

LA CAUSA. `tk.calendar` de yfinance devolvía un DataFrame y hoy devuelve un
**dict**. El código hacía `if cal is not None and not cal.empty:` -- y un dict
no tiene `.empty`, así que lanzaba AttributeError. Lo capturaba un
`except Exception: pass` mudo y la función devolvía None SIEMPRE.

QUÉ SE APAGÓ CON ELLA: la marca 📅/🕐 de la pantalla (hallazgo #10, dado por
hecho el 06/08) y cualquier análisis que separe por cercanía a resultados. El
dato estaba disponible todo el tiempo -- `cal['Earnings Date']` trae la fecha--,
simplemente no se leía.

LA LECCIÓN, que es la que este fichero protege: un `except` mudo alrededor de
una dependencia externa convierte un cambio de formato en una función que
devuelve None para siempre sin que nadie lo note.

Uso:
    cd backend
    python -m pytest tests/test_options_earnings_fecha.py -v
"""
import os
import sys
from datetime import date
from unittest.mock import MagicMock, patch

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.options_service as O  # noqa: E402


def _con_calendario(cal):
    tk = MagicMock()
    tk.calendar = cal
    return patch.object(O.yf, "Ticker", return_value=tk)


def test_lee_la_fecha_cuando_el_calendario_es_un_DICT():
    """EL test. Es la forma que devuelve yfinance hoy, y la que el código no
    sabía leer: `dict` no tiene `.empty`."""
    cal = {"Dividend Date": [date(2026, 11, 10)],
           "Earnings Date": [date(2026, 10, 29)],
           "Earnings Average": 1.62}
    with _con_calendario(cal):
        assert O._get_next_earnings("AAPL") == "2026-10-29"


def test_sigue_leyendo_la_fecha_si_vuelve_a_ser_un_DATAFRAME():
    """La forma antigua tiene que seguir funcionando: si yfinance vuelve atrás
    -o si una versión distinta la devuelve así- no se puede apagar otra vez."""
    cal = pd.DataFrame({"Value": [date(2026, 10, 29)]}, index=["Earnings Date"])
    with _con_calendario(cal):
        assert O._get_next_earnings("AAPL") == "2026-10-29"


def test_un_calendario_sin_fecha_de_resultados_devuelve_None():
    with _con_calendario({"Dividend Date": [date(2026, 11, 10)]}):
        assert O._get_next_earnings("AAPL") is None


def test_una_lista_de_fechas_vacia_no_revienta():
    with _con_calendario({"Earnings Date": []}):
        assert O._get_next_earnings("AAPL") is None


def test_un_calendario_vacio_o_ausente_devuelve_None():
    with _con_calendario(None):
        assert O._get_next_earnings("AAPL") is None
    with _con_calendario(pd.DataFrame()):
        assert O._get_next_earnings("AAPL") is None


def test_si_falla_se_DICE_en_vez_de_callarse(capsys):
    """Lo que escondió el fallo durante meses fue un `except Exception: pass`.
    Un fallo silencioso en una dependencia externa es indistinguible de «este
    ticker no publica resultados»."""
    tk = MagicMock()
    type(tk).calendar = property(lambda self: (_ for _ in ()).throw(RuntimeError("boom")))
    with patch.object(O.yf, "Ticker", return_value=tk):
        assert O._get_next_earnings("AAPL") is None
    salida = capsys.readouterr().out
    assert "AAPL" in salida and "boom" in salida, (
        "el fallo se ha tragado en silencio: es lo que dejó la marca de "
        "resultados muerta durante meses sin que nadie lo notara")


def test_no_queda_ningun_except_mudo_en_la_funcion():
    """El defecto no fue el cambio de formato -- eso pasa--, fue que nadie se
    enteró. Si vuelve a haber un `except` sin decir nada, esto cae."""
    import inspect
    fuente = inspect.getsource(O._get_next_earnings)
    lineas = [l.strip() for l in fuente.splitlines()]
    for i, l in enumerate(lineas):
        if l.startswith("except"):
            siguientes = " ".join(lineas[i + 1: i + 4])
            assert "print" in siguientes or "log" in siguientes, (
                f"except mudo en _get_next_earnings: {l}")
