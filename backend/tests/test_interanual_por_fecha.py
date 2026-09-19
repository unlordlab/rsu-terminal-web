"""
El interanual, por FECHA: el IPC de octubre de 2025 no existe y todo lo demás se corría un mes.

EL CASO, 19/09/2026. Al preguntar por el M2 salió que el IPC interanual de agosto
daba 3,40% y los briefings llevaban semanas citando 3,71%. El briefing y Market
tomaban «la observación 12 (o 13) posiciones atrás», y como FRED no tiene
octubre de 2025 (no se publicó), esa posición era JULIO: se comparaban trece
meses. Medido contra FRED: IPC general 3,71% → 3,35%, subyacente 2,76% → 2,45%.
PCE, ventas minoristas y producción industrial no tienen el hueco y daban igual.

Y de paso, el M2 real que pidió el usuario: el crecimiento del M2 descontada la
inflación del mismo mes, con la serie mensual desestacionalizada (la semanal
daba +5,30% o +6,05% según qué semana de hace un año se tomara).

Uso:
    cd backend
    python -m pytest tests/test_interanual_por_fecha.py -v
"""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'shared'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

import interanual as I  # noqa: E402

FRONT = os.path.join(os.path.dirname(__file__), '..', '..', 'frontend')

# El IPC general real de FRED (CPIAUCSL), con el hueco de octubre de 2025.
IPC = [("2025-07-01", 322.169), ("2025-08-01", 323.291), ("2025-09-01", 324.245),
       ("2025-11-01", 325.031), ("2025-12-01", 325.656), ("2026-01-01", 326.588),
       ("2026-02-01", 327.461), ("2026-03-01", 328.614), ("2026-04-01", 329.807),
       ("2026-05-01", 331.022), ("2026-06-01", 332.568), ("2026-07-01", 333.197),
       ("2026-08-01", 334.131)]


# ── shared/interanual.py ─────────────────────────────────────────────────────

def test_EL_CASO_el_ipc_de_agosto_se_compara_con_agosto():
    assert I.valor_hace_un_ano(IPC) == 323.291
    assert round(I.variacion_interanual(IPC), 2) == 3.35
    assert round((IPC[-1][1] / IPC[-13][1] - 1) * 100, 2) == 3.71, "el caso de partida: doce posiciones atrás era julio"


def test_sin_el_mismo_mes_del_ano_anterior_no_hay_interanual():
    """Octubre de 2026 no tendría con quién compararse: nunca el vecino."""
    assert I.variacion_interanual(IPC + [("2026-10-01", 335.0)]) is None


def test_una_serie_semanal_admite_la_semana_anterior_mas_cercana():
    semanal = [("2025-07-28", 21884.0), ("2025-08-04", 22039.5), ("2026-08-03", 23207.7)]
    assert I.valor_hace_un_ano(semanal, tolerancia_dias=6) == 21884.0, "la anterior, nunca la posterior"
    assert I.valor_hace_un_ano(semanal) is None


def test_el_orden_de_la_lista_da_igual():
    assert round(I.variacion_interanual(list(reversed(IPC))), 2) == 3.35


def test_29_de_febrero():
    assert I.valor_hace_un_ano([("2027-02-28", 1.0), ("2028-02-29", 2.0)], "2028-02-29") == 1.0


# ── El briefing ──────────────────────────────────────────────────────────────

def test_EL_CASO_el_briefing_da_3_35_y_no_3_71():
    import daily_briefing as D
    obs = list(reversed(IPC))[:16]
    with patch.object(D, "FRED_KEY", "x"), \
         patch.object(D, "FRED_SERIES", [("CPIAUCSL", "IPC general", "mm_aa")]), \
         patch.object(D, "_fred_observaciones", lambda s, n=16: obs), \
         patch.object(D, "_fred_publicado_el", lambda s: "2026-09-11"):
        fila = D.get_macro_indicators()[0]
    assert fila["extra"] == "+3.35% interanual", fila
    assert fila["dato"] == "+0.28% m/m"


def test_tras_el_hueco_no_hay_m_m_de_dos_meses():
    """Noviembre frente a septiembre no es «m/m»."""
    import daily_briefing as D
    obs = [("2025-11-01", 325.031), ("2025-09-01", 324.245), ("2025-08-01", 323.291)]
    with patch.object(D, "FRED_KEY", "x"), \
         patch.object(D, "FRED_SERIES", [("CPIAUCSL", "IPC general", "mm_aa")]), \
         patch.object(D, "_fred_observaciones", lambda s, n=16: obs), \
         patch.object(D, "_fred_publicado_el", lambda s: "2025-12-18"):
        fila = D.get_macro_indicators()[0]
    assert fila["dato"] == "m/m no disponible (falta el mes anterior)"


def test_el_briefing_pide_observaciones_de_sobra_para_el_hueco():
    import inspect
    import daily_briefing as D
    assert inspect.signature(D._fred_observaciones).parameters["n"].default >= 15


# ── Market ───────────────────────────────────────────────────────────────────

def _fred_falso(series):
    return lambda sid, *a, **k: series.get(sid, [])


def test_la_tarjeta_de_ipc_de_market_por_fecha():
    import services.market_service as M
    from services.cache import cache
    with patch.object(cache, "get", lambda *a, **k: None), patch.object(cache, "set", lambda *a, **k: None), \
         patch.object(M, "fred_csv", _fred_falso({"CPIAUCSL": IPC})):
        macro = M.get_fed_macro()
    ipc = macro["indicators"]["cpi_yoy"]
    assert ipc and ipc["yoy"] == 3.35, macro


M2SL = [("2025-06-01", 21831.0), ("2025-07-01", 22025.5), ("2026-06-01", 23003.0), ("2026-07-01", 23218.0)]
IPC_JUL = [("2025-07-01", 322.169), ("2026-07-01", 332.797)]
WM2NS = [("2025-08-04", 22039.5), ("2026-07-27", 23043.3), ("2026-08-03", 23207.7)]


def test_EL_M2_real_descuenta_la_inflacion_del_mismo_mes():
    import services.market_service as M
    from services.cache import cache
    with patch.object(cache, "get", lambda *a, **k: None), patch.object(cache, "set", lambda *a, **k: None), \
         patch.object(M, "fred_csv", _fred_falso({"WM2NS": WM2NS, "M2SL": M2SL, "CPIAUCSL": IPC_JUL})):
        m2 = M.get_liquidity()["m2"]
    assert m2["yoy_pct"] == 5.41 and m2["yoy_mes"] == "2026-07-01", "el interanual, de la mensual"
    assert m2["ipc_yoy_pct"] == 3.3
    # (23218/22025,5) / (332,797/322,169) − 1, sin redondear antes: 2,047 → 2,05
    assert m2["real_yoy_pct"] == 2.05, "5,41% de M2 frente a 3,30% de IPC"
    assert m2["current"] == 23.208, "el nivel sigue siendo el semanal, el más reciente"


def test_sin_ipc_de_ese_mes_no_hay_m2_real():
    import services.market_service as M
    from services.cache import cache
    with patch.object(cache, "get", lambda *a, **k: None), patch.object(cache, "set", lambda *a, **k: None), \
         patch.object(M, "fred_csv", _fred_falso({"WM2NS": WM2NS, "M2SL": M2SL, "CPIAUCSL": IPC_JUL[:1]})):
        m2 = M.get_liquidity()["m2"]
    assert m2["yoy_pct"] == 5.41 and m2["real_yoy_pct"] is None


def test_la_tarjeta_ensena_el_m2_real_con_su_explicacion():
    with open(os.path.join(FRONT, 'pages', 'market.js'), encoding='utf-8') as f:
        market = f.read()
    assert "m2.real_yoy_pct" in market and "tt('m2-real')" in market
    assert "+ m2RealStr +" in market
    with open(os.path.join(FRONT, 'components', 'tooltip.js'), encoding='utf-8') as f:
        assert '"m2-real": {' in f.read()


def test_el_ipc_es_el_del_mes_del_m2_aunque_haya_uno_mas_reciente():
    """Lo normal: el IPC de agosto sale antes que el M2 de agosto. El M2 de julio
    se descuenta con el IPC de JULIO, no con el último publicado."""
    import services.market_service as M
    from services.cache import cache
    ipc = IPC_JUL + [("2025-08-01", 323.291), ("2026-08-01", 334.131)]
    with patch.object(cache, "get", lambda *a, **k: None), patch.object(cache, "set", lambda *a, **k: None), \
         patch.object(M, "fred_csv", _fred_falso({"WM2NS": WM2NS, "M2SL": M2SL, "CPIAUCSL": ipc})):
        m2 = M.get_liquidity()["m2"]
    assert m2["ipc_yoy_pct"] == 3.3, "el de julio (3,30%), no el de agosto (3,35%)"
