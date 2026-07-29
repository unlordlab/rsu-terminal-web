"""
Cinco números de Research que podían estar mal (29/07/2026).

Verificados uno a uno contra datos reales antes de tocar nada, porque no
todos resultaron ser lo que decía la auditoría:

  #8  REAL Y MATERIAL. La ficha enseñaba DOS máximos de 52 semanas distintos
      a la vez: la tarjeta usaba info['fiftyTwoWeekHigh'] y Niveles Técnicos
      recalculaba close.tail(252).max(). Discrepaban hasta un 5,9% (KO). Y
      eran dos diferencias apiladas: cierre vs. máximo INTRADÍA, y precios
      AJUSTADOS por dividendos vs. crudos -- history() ajusta por defecto, así
      que cuanto más dividendo paga una empresa más se hunde su histórico.
      Efecto en pantalla: AAPL salía a 0,0% de su máximo (o sea, "en
      máximos") cuando está un 1,7% por debajo; KO pasaba de -1,0% a -6,8%.

  #7  LATENTE. `items[0]` sin ordenar. Hoy la ventana de 90 días devuelve un
      único elemento por ticker (AAPL/JPM/WMT/NKE/KO), así que acierta
      siempre -- pero basta con dos publicaciones en la ventana.

  #9  LATENTE. shortPercentOfFloat es una fracción en los 6 tickers
      comprobados (GME 0.1354 con 12,78 días para cubrir, coherente). Un
      cambio de unidad al otro lado multiplicaría por 100 sin avisar.

  #17 REAL. Varias monedas comparten símbolo exacto: "DOT" devuelve polkadot
      (rank 56), dot (rank 2364) y más. Se cogía la primera que llegara.

  #18 Se fijó auto_adjust explícito: el valor por defecto de yfinance ha
      cambiado entre versiones, así que la estacionalidad podía moverse sola
      al actualizar una dependencia.

Uso:
    cd backend
    python -m pytest tests/test_research_datos_correctos.py -v
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import services.research_service as rs  # noqa: E402


# ── #7 · próxima presentación de resultados ──────────────────────────────────

def _respuesta_finnhub(items):
    r = MagicMock(status_code=200)
    r.json.return_value = {"earningsCalendar": items}
    return r


def test_earnings_coge_la_fecha_mas_proxima_no_la_primera_de_la_lista():
    from datetime import datetime, timedelta
    hoy = datetime.now()
    lejos = (hoy + timedelta(days=80)).strftime('%Y-%m-%d')
    cerca = (hoy + timedelta(days=10)).strftime('%Y-%m-%d')
    items = [
        {"date": lejos, "epsEstimate": 2.0, "hour": "amc"},
        {"date": cerca, "epsEstimate": 1.0, "hour": "bmo"},
    ]
    with patch.object(rs.settings, "finnhub_api_key", "clave"), \
         patch.object(rs.requests, "get", return_value=_respuesta_finnhub(items)):
        r = rs._get_next_earnings("TEST")
    assert r["date"] == cerca, (
        f"Finnhub no documenta ningún orden: hay que ordenar por fecha. "
        f"Salió {r['date']}, se esperaba {cerca}."
    )


def test_earnings_descarta_lo_que_ya_ha_pasado():
    """from_date es HOY, así que una empresa que publicó esta mañana seguiría
    apareciendo como 'próxima presentación'."""
    from datetime import datetime, timedelta
    hoy = datetime.now()
    ayer     = (hoy - timedelta(days=1)).strftime('%Y-%m-%d')
    proxima  = (hoy + timedelta(days=30)).strftime('%Y-%m-%d')
    items = [{"date": ayer, "epsEstimate": 1.0}, {"date": proxima, "epsEstimate": 2.0}]
    with patch.object(rs.settings, "finnhub_api_key", "clave"), \
         patch.object(rs.requests, "get", return_value=_respuesta_finnhub(items)):
        r = rs._get_next_earnings("TEST")
    assert r["date"] == proxima


def test_earnings_sin_nada_futuro_devuelve_vacio():
    from datetime import datetime, timedelta
    ayer = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    with patch.object(rs.settings, "finnhub_api_key", "clave"), \
         patch.object(rs.requests, "get", return_value=_respuesta_finnhub([{"date": ayer}])):
        assert rs._get_next_earnings("TEST") == {}


# ── #9 · unidad del short interest ───────────────────────────────────────────

def _info_short(valor):
    return {"shortPercentOfFloat": valor, "sharesShort": 1_000_000, "shortRatio": 3.0}


def test_short_percent_como_fraccion_se_convierte_a_porcentaje():
    """El caso normal y el único que se da hoy: GME devuelve 0.1354."""
    with patch.object(rs, "_info_de", lambda t: _info_short(0.1354)):
        assert rs._get_short_interest("TEST")["short_pct"] == 13.54


def test_short_percent_ya_en_porcentaje_no_se_multiplica_otra_vez():
    """Si la API cambiara de unidad, 'GME: 1354% del float en corto' se
    colaría hasta el squeeze score. Por encima del 100% del float es
    imposible por definición, así que sirve de discriminador exacto."""
    with patch.object(rs, "_info_de", lambda t: _info_short(13.54)):
        assert rs._get_short_interest("TEST")["short_pct"] == 13.54


def test_short_percent_alto_pero_creible_sigue_pasando():
    """Que la defensa no se coma un short interest legítimamente alto."""
    with patch.object(rs, "_info_de", lambda t: _info_short(0.87)):
        assert rs._get_short_interest("TEST")["short_pct"] == 87.0


# ── #17 · resolución de criptomonedas ────────────────────────────────────────

def _respuesta_coingecko(coins):
    r = MagicMock(status_code=200)
    r.json.return_value = {"coins": coins}
    return r


# Ojo al escribir estos tests: _CRYPTO_ID_OVERRIDES resuelve a mano 26
# símbolos mayores (BTC, ETH, SOL, DOT...) ANTES de llegar a la búsqueda, así
# que usarlos aquí no prueba nada -- probaría la tabla. Se usa un símbolo
# fuera de esa lista, que además es donde vive el riesgo real: la cola larga
# es justo donde aparecen monedas residuales con el símbolo copiado.
assert "AAVE" not in rs._CRYPTO_ID_OVERRIDES, (
    "Si AAVE entra en la tabla de overrides, estos tests dejan de probar la "
    "búsqueda: cambiar el símbolo por otro que no esté."
)


def test_cripto_desempata_por_capitalizacion_no_por_orden_de_llegada():
    """Mismo patrón real que 'DOT' el 29/07/2026 (polkadot rank 56 frente a
    dot rank 2364), con la moneda residual puesta primero a propósito."""
    coins = [
        {"id": "aave-residual", "symbol": "AAVE", "market_cap_rank": 2364},
        {"id": "aave",          "symbol": "AAVE", "market_cap_rank": 56},
    ]
    with patch.object(rs.requests, "get", return_value=_respuesta_coingecko(coins)):
        assert rs._resolve_coingecko_id("AAVE") == "aave"


def test_cripto_sin_coincidencia_exacta_no_resuelve_a_otra_moneda():
    """Coger coins[0] era presentar el perfil de una moneda distinta de la
    que se pidió como si fuera la buena."""
    coins = [{"id": "otracosa", "symbol": "XYZ", "market_cap_rank": 10}]
    with patch.object(rs.requests, "get", return_value=_respuesta_coingecko(coins)):
        assert rs._resolve_coingecko_id("NOEXISTE") is None


def test_cripto_sin_rank_no_gana_a_una_con_rank():
    """market_cap_rank puede venir a None; eso no puede colocarla la primera."""
    coins = [
        {"id": "sinrank", "symbol": "AAVE", "market_cap_rank": None},
        {"id": "aave",    "symbol": "AAVE", "market_cap_rank": 56},
    ]
    with patch.object(rs.requests, "get", return_value=_respuesta_coingecko(coins)):
        assert rs._resolve_coingecko_id("AAVE") == "aave"


# ── #18 · estacionalidad con auto_adjust explícito ───────────────────────────

def test_la_estacionalidad_fija_auto_adjust_y_no_lo_hereda_de_la_libreria():
    """El default de yfinance ha cambiado entre versiones: sin fijarlo, la
    estacionalidad de un valor con dividendo se movería sola al actualizar
    una dependencia, sin que nadie tocara este código."""
    llamada = {}

    class _Ticker:
        def __init__(self, *a, **k): pass
        def history(self, *a, **k):
            llamada.update(k)
            import pandas as pd
            return pd.DataFrame()

    with patch.object(rs.yf, "Ticker", _Ticker):
        rs._get_seasonality("TEST")

    assert "auto_adjust" in llamada, (
        "auto_adjust tiene que ser explícito, no heredado del default de yfinance."
    )
    assert llamada["auto_adjust"] is True, (
        "Se fija en True a propósito: con ajuste cada mes mide retorno TOTAL "
        "(precio + dividendo), que es lo que se lleva quien estuviera invertido."
    )


# ── #8 · un solo máximo de 52 semanas en toda la ficha ───────────────────────

def test_niveles_tecnicos_usa_el_mismo_maximo_52s_que_la_tarjeta():
    """El hallazgo con impacto real medido: la ficha enseñaba dos cifras
    distintas del mismo concepto. Con KO discrepaban un 5,9% (90,22 en la
    tarjeta contra 84,92 en Niveles Técnicos) y AAPL salía a 0,0% de su
    máximo -- "en máximos"-- cuando está un 1,7% por debajo."""
    import pandas as pd
    import numpy as np

    # Serie de cierres AJUSTADOS cuyo máximo (110) NO coincide con el máximo
    # intradía sin ajustar que reporta Yahoo (125): justo la situación real de
    # cualquier valor que pague dividendo.
    n = 300
    cierres = np.linspace(80.0, 110.0, n)
    cierres[-1] = 100.0   # precio actual por debajo del máximo
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    hist = pd.DataFrame({
        "Open": cierres, "High": cierres, "Low": cierres,
        "Close": cierres, "Volume": [1_000_000] * n,
    }, index=idx)

    class _Ticker:
        def __init__(self, *a, **k): pass
        def history(self, *a, **k): return hist

    info_yahoo = {"fiftyTwoWeekHigh": 125.0, "fiftyTwoWeekLow": 70.0}

    with patch.object(rs.yf, "Ticker", _Ticker), \
         patch.object(rs, "_info_de", lambda t: info_yahoo):
        r = rs._get_technical_levels("TEST")

    esperado = round((100.0 - 125.0) / 125.0 * 100, 1)   # -20.0
    assert r["vs_52h"] == esperado, (
        f"vs_52h debe medirse contra el MISMO máximo que muestra la tarjeta "
        f"(125,0), no contra el máximo de cierres ajustados (110,0). Salió "
        f"{r['vs_52h']}%, se esperaba {esperado}%."
    )
    esperado_low = round((100.0 - 70.0) / 70.0 * 100, 1)
    assert r["vs_52l"] == esperado_low


def test_sin_maximo_de_yahoo_se_reconstruye_sin_ajustar_no_con_cierres():
    """Si falta el dato de Yahoo, el sustituto tiene que seguir el MISMO
    convenio (intradía, sin ajustar por dividendos), no cierres ajustados."""
    import pandas as pd
    import numpy as np

    n = 300
    idx = pd.date_range("2024-01-01", periods=n, freq="B")
    cierres = np.linspace(80.0, 110.0, n)
    cierres[-1] = 100.0
    ajustado = pd.DataFrame({
        "Open": cierres, "High": cierres, "Low": cierres,
        "Close": cierres, "Volume": [1_000_000] * n,
    }, index=idx)
    # El crudo tiene máximos intradía más altos que cualquier cierre ajustado.
    crudo = ajustado.copy()
    crudo["High"] = cierres + 15.0
    crudo["Low"]  = cierres - 15.0

    class _Ticker:
        def __init__(self, *a, **k): pass
        def history(self, *a, **k):
            return crudo if k.get("auto_adjust") is False else ajustado

    with patch.object(rs.yf, "Ticker", _Ticker), \
         patch.object(rs, "_info_de", lambda t: {}):
        r = rs._get_technical_levels("TEST")

    high_crudo = round(float(crudo["High"].tail(252).max()), 2)
    esperado = round((100.0 - high_crudo) / high_crudo * 100, 1)
    assert r["vs_52h"] == esperado, (
        f"Sin dato de Yahoo hay que reconstruirlo con máximos intradía sin "
        f"ajustar ({high_crudo}). Salió {r['vs_52h']}%, esperado {esperado}%."
    )
