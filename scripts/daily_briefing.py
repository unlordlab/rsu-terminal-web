#!/usr/bin/env python3
"""
RSU Terminal — Daily Market Briefing
Genera análisis diario via OpenRouter (Qwen) y lo guarda en GitHub Gist
"""

import os
import sys
import json
import time
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
import numpy as np
import pandas as pd

# shared/ es sibling de scripts/ -- yfinance ya trae pandas como
# dependencia, así que no es una dependencia nueva de verdad, solo no se
# importaba directamente en este fichero hasta ahora.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
from mcclellan import mcclellan_series  # noqa: E402
# La regla de cobertura vivia aqui dentro y protegia SOLO al briefing. La
# amplitud la consumen ademas Market, el Algoritmo y los snapshots, asi que
# el sitio correcto es una casa comun y el origen -- no una copia por
# consumidor, que es como se acaba con dos umbrales contradiciendose.
from cobertura_amplitud import cobertura_insuficiente as amplitud_incompleta  # noqa: E402

GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")
GIST_TOKEN = os.environ.get("GIST_TOKEN", "")
GIST_ID    = os.environ.get("GIST_ID", "715ee0c4e571517c11fa65c5c2376c34")
MODEL      = "qwen/qwen3.6-27b"

# Fichero adicional dentro del MISMO Gist (GIST_ID) — no hace falta un Gist
# nuevo, GitHub permite varios ficheros por Gist. Guarda solo un registro
# compacto por día (fecha + sesgo + objetivo), no el texto completo — eso da
# continuidad de varios días sin cargar el prompt con párrafos de días
# pasados. Se poda a los últimos BIAS_HISTORY_DAYS automáticamente, así que
# el tamaño nunca crece sin límite.
BIAS_HISTORY_FILE = "bias_history.json"
# Seguimiento del sesgo: ¿acierta el briefing? APPEND-ONLY, SIN PODA -- y esa
# es la diferencia con BIAS_HISTORY_FILE, que se recorta a 14 días porque es
# contexto narrativo para el prompt. Medir sobre una ventana que se poda es no
# poder acumular muestra nunca: misma lección que DATOS_IRREPRODUCIBLES_PLAN.
BIAS_TRACKING_FILE = "bias_tracking.json"
# Por debajo de esto el porcentaje no se presenta como conclusión.
MIN_MUESTRA_SESGO  = 30
BIAS_HISTORY_DAYS = 14

# Historial de varios días con el TEXTO COMPLETO del briefing (no solo el
# sesgo, a diferencia de BIAS_HISTORY_FILE) -- fichero aparte dentro del
# mismo Gist, para que el modelo pueda mantener consistencia de niveles y
# postura más allá de "ayer". briefing.json (un solo día, el más reciente)
# se mantiene sin cambios porque backend/services/market_service.py
# ::get_nightly_briefing() lo lee por nombre exacto para el frontend.
# Qué eventos de fuera de EE.UU. entran en el calendario del briefing. Una
# decisión del BCE o del Banco de Japón mueve los futuros de Wall Street antes
# de la apertura; un IPC australiano a las 21:30 ET no. Sin esta lista pasaba
# cualquier cosa de impacto "High" del feed, y el 25/08/2026 el briefing abrió
# con el IPC de AUSTRALIA presentado como el de Estados Unidos.
PAISES_QUE_MUEVEN_WALL_STREET = {"EUR", "GBP", "JPY", "CNY"}


def evento_relevante(item: dict, hoy: str) -> bool:
    """¿Este evento del calendario le importa a quien abre Wall Street?

    Fuera vive dentro de get_market_data(), que es una función de red enorme y
    no se puede probar sin salir a internet -- y una regla que solo existe
    dentro de algo intestable acaba comprobándose reescribiéndola en el test,
    que es como se me colaron dos sabotajes el 25/08."""
    if item.get("impact") not in ("High", "Medium"):
        return False
    if hoy not in item.get("date", ""):
        return False
    pais = (item.get("country") or "").upper()
    if pais == "USD":
        return True
    return pais in PAISES_QUE_MUEVEN_WALL_STREET and item.get("impact") == "High"


SUFIJOS_SOCIETARIOS = (", inc.", " inc.", " inc", ", corp.", " corp.", " corp",
                       " corporation", ", ltd.", " ltd.", " ltd", " plc",
                       " co.", " company", " holdings", " group", " s.a.")


# El escaneo nocturno del Scanner puede salir INCOMPLETO. El 02/09/2026 escribio
# 20 avances y 4 descensos -- 24 valores de un universo de ~2.380-- y 0/1 en el
# S&P 500 de ~495. La parte de RS/fase del mismo escaneo estaba bien (498
# valores en `stocks`), asi que nada cantaba.
#
# El briefing lo consumio tal cual y publico: "el Indice de Amplitud (ABI) marco
# 66,7%, senal de capitulacion... la inmensa mayoria de los componentes cayeron".
# El 66,7% es |20-4|/24, ruido; y encima 20 contra 4 es un desequilibrio AL ALZA,
# lo contrario de lo que escribio. Una seccion entera del briefing sobre 24
# valores.
#
# Misma leccion que la curva de tipos: un dato que no esta no puede convertirse
# en una afirmacion, y menos en la tranquilizadora o en la alarmante.
def es_dominio_pedido(domain: str, dominios) -> bool:
    """¿Este articulo viene de verdad de uno de los medios que se pidieron?

    EL CASO, 02/09/2026. `get_major_outlet_headlines()` pide a GDELT
    `(domain:reuters.com OR domain:bloomberg.com OR ...)` y NO comprobaba lo que
    volvia. Comprobado ese dia: `domain:reuters.com` devuelve `{}` -- vacio, 200
    OK-- y la consulta con los cinco dominios devolvio 10 articulos, todos de
    kelownacapnews.com, un periodico local de Kelowna (Columbia Britanica). Los
    titulares que llegaban al briefing eran un choque en la autopista 97, un
    perro salvado con naloxona y un aviso de hervir el agua en Peachland.

    GDELT ignora las clausulas de dominio; el script se fiaba de la consulta.
    Se acepta el subdominio (uk.reuters.com) porque es el mismo medio."""
    d = (domain or "").strip().lower()
    if not d:
        return False
    return any(d == x or d.endswith("." + x) for x in dominios)


def nombre_corto(company, max_chars: int = 22) -> str:
    """El nombre de la empresa, sin el ruido societario y sin partir palabras.

    Existe porque el 31/08/2026 al modelo le llegaron los tickers DESNUDOS y se
    invento el sector de cada uno. El nombre ya venia en el payload; lo que
    faltaba era usarlo. Se recorta porque este prompt no cabe en el limite de
    Groq: "Alpha Metallurgical" basta para saber que no es una petrolera, y
    "Alpha Metallurgical Resources, Inc." cuesta el triple.

    Cortar a pelo por caracteres dejaba "Dick's Sporting Goods In", que parece
    un fallo de programa dentro de un texto que lee gente."""
    nombre = str(company or "").strip()
    if not nombre:
        return ""
    bajo = nombre.lower()
    for suf in SUFIJOS_SOCIETARIOS:
        if bajo.endswith(suf):
            nombre = nombre[: len(nombre) - len(suf)].rstrip(" ,")
            bajo = nombre.lower()
    if len(nombre) <= max_chars:
        return nombre
    corte = nombre[:max_chars].rsplit(" ", 1)[0].rstrip(" ,")
    return corte or nombre[:max_chars]


def hora_et(item: dict) -> str:
    """Hora del evento en Nueva York. `date[-8:-3]` sobre
    "2026-08-25T21:30:00-04:00" devolvía "0-04:" -- basura rotulada «ET»."""
    try:
        return datetime.fromisoformat(item["date"]).astimezone(
            ZoneInfo("America/New_York")).strftime("%H:%M")
    except Exception:
        return "N/D"


# ── ¿La última barra de yfinance es un cierre o una sesión a medias? ──────────
#
# EL CASO, 27/08/2026. El cron de las 07:00 UTC no se disparó y el usuario lanzó
# el Action A MANO, con Wall Street abierto. `yf.history()` devuelve entonces la
# barra PARCIAL de la sesión viva -- pero el prompt le afirmaba al modelo, en dos
# reglas distintas, que esos porcentajes eran de cierre. El briefing abrió con
# «El S&P 500 CIERRA en positivo gracias a Nvidia» sobre una sesión a la que le
# quedaban horas: NVDA +7% cuando el cierre anterior había sido -1,59%, y XLU
# -1,23% cuando había cerrado en +0,46% -- el signo cambiado.
#
# Ningún dato era falso; lo falso era la etiqueta que les ponía el script.
HORA_CIERRE_NYSE = 16


def sesion_sin_cerrar(fecha_ultima_barra, ahora_et=None) -> bool:
    """¿La última barra diaria corresponde a una sesión que aún no ha cerrado?

    Con el mercado abierto yfinance ya ha creado la barra de HOY y la va
    actualizando. Si la última barra es de hoy y en Nueva York todavía no son
    las 16:00, lo que hay en la mano es una foto a media sesión, no un cierre.

    Se pregunta por la fecha de la BARRA y no por «¿está abierto el mercado?»
    a propósito: un festivo o un fin de semana no tienen barra de hoy, así que
    el caso se resuelve solo sin mantener un calendario de festivos."""
    if fecha_ultima_barra is None:
        return False
    ahora = ahora_et or datetime.now(ZoneInfo("America/New_York"))
    return fecha_ultima_barra == ahora.date() and ahora.hour < HORA_CIERRE_NYSE


# ── Archivo de auditoria: con que se escribio cada briefing ─────────────────
#
# briefing.json guarda el bloque `datos` del dia, pero SE SOBRESCRIBE en cada
# ejecucion: el 02/09/2026 se pudo auditar el briefing de ese dia y el del 01/09
# ya no existia. Este fichero conserva los ultimos DATOS_DIAS dias para poder
# mirar atras -- y se PODA, porque un fichero que solo crece acaba siendo
# ilegible y pesado de subir en cada ejecucion.
DATOS_FILE = "briefing_datos.json"
DATOS_DIAS = 7
# Tope duro por si un dia entra un bloque anormalmente grande: mas vale perder
# archivo antiguo que dejar de publicar el briefing por un Gist demasiado
# pesado. ~40 KB cubre de sobra 7 dias (~5 KB/dia medidos).
DATOS_MAX_CHARS = 120_000


def podar_datos(historial, entrada, max_dias: int = DATOS_DIAS,
                max_chars: int = DATOS_MAX_CHARS) -> list:
    """Añade la entrada de hoy y deja solo los ultimos `max_dias` dias.

    Una fecha que ya esta se REEMPLAZA, no se duplica: el Action se relanza a
    mano con cierta frecuencia (ver el retraso del planificador de GitHub) y dos
    ejecuciones el mismo dia no pueden dejar dos entradas para esa fecha."""
    fecha = (entrada or {}).get("fecha")
    fuera = [e for e in (historial or []) if isinstance(e, dict) and e.get("fecha") != fecha]
    fuera.append(entrada)
    fuera.sort(key=lambda e: e.get("fecha") or "")
    podado = fuera[-max_dias:]
    # Si aun asi se pasa del tope, se van cayendo los mas antiguos -- pero
    # nunca el de hoy, que es el que se acaba de escribir.
    import json as _json
    while len(podado) > 1 and len(_json.dumps(podado, ensure_ascii=False)) > max_chars:
        podado.pop(0)
    return podado


BRIEFING_HISTORY_FILE = "briefing_history.json"
BRIEFING_HISTORY_DAYS = 3
# Presupuesto TOTAL de caracteres del bloque de memoria narrativa dentro del
# prompt (ver format_briefing_history) -- no por entrada. Con ~3.5 chars por
# token son ~860 tokens, quepan 1 o 3 briefings dentro.
BRIEFING_HISTORY_CHARS_BUDGET = 3000

# ── Presupuesto de tokens de Groq ─────────────────────────────────────────────
# El tier gratuito limita a 8000 tokens/minuto (prompt + respuesta) para este
# modelo. El 26-28/07/2026 el briefing falló 3 días seguidos con HTTP 413
# ("Limit 8000, Requested 8317") porque max_tokens estaba fijo en 3000
# mientras el prompt había crecido hasta ~5300 tokens.
#
# Medido con datos reales antes de tocar nada (no estimado a ojo):
#   - Plantilla + reglas del prompt, sin datos de mercado: ~10.900 chars
#   - Bloque de memoria narrativa + sesgo:                 ~3.100 chars
#   - El briefing más largo REALMENTE generado:             4.709 chars (~1.350 tokens)
# Es decir, max_tokens=3000 reservaba MÁS DEL DOBLE de lo que el modelo
# llega a escribir, y ese espacio muerto era justo lo que desbordaba el
# límite. Ahora el techo de salida se calcula a partir de lo que queda libre
# tras el prompt, con la reserva de 1800 como máximo.
GROQ_TPM_LIMIT     = 8000
GROQ_TPM_SAFETY    = 350   # colchón: mi estimación por caracteres nunca coincide exactamente con el tokenizador real
GROQ_MAX_OUTPUT    = 1800  # ~33% por encima del briefing más largo observado
GROQ_MIN_OUTPUT    = 1200  # por debajo de esto el briefing saldría cortado a medias

# RECALIBRADO el 31/07/2026 contra una medición exacta, no a ojo. Estaba en 3.5
# y subestimaba un 13%: ese día el script calculó ~5744 tokens de prompt y Groq
# respondió "Requested 8401" con max_tokens=1800, o sea que el prompt real eran
# 6601 tokens. 20104 chars / 6601 tokens = 3.046 chars por token.
#
# Se deja en 2.9, por debajo de lo medido: el error de este lado (sobrestimar
# el prompt y recortar de más) cuesta un poco de contexto; el del otro lado
# (subestimar) cuesta quedarse sin briefing. No es simétrico.
CHARS_POR_TOKEN    = 2.9

# ── Longitud pedida al modelo: se calcula, no se escribe a mano ───────────────
#
# El briefing se cortaba a mitad de frase TODOS los días, y la aritmética no
# dejaba lugar a dudas: el prompt pedía "entre 700 y 900 palabras", que en
# castellano son ~1.570-2.020 tokens, mientras que el techo de respuesta es
# 1.800 y un día normal solo deja 1.200 libres. No cabía ningún día.
#
# Cómo se coló: los topes de salida se calibraron cuando el prompt pedía
# 500-700 palabras (~1.120-1.570 tokens), que cuadra exactamente con el
# "briefing más largo generado: ~1.350 tokens" que quedó medido arriba. Después
# el prompt pasó a pedir 700-900 y nadie recalibró el presupuesto.
#
# Además el corte no se veía: la respuesta se publicaba igual, y como el
# briefing tiene que terminar con la línea "SESGO: ..." que se corta con él, el
# registro de sesgo perdía el día sin decir nada.
#
# Se deja de escribir la cifra a mano: se deriva del hueco que de verdad queda,
# así que los días de calendario cargado pide menos y los tranquilos más, sin
# volver a descuadrarse cuando el prompt crezca.
CHARS_POR_PALABRA  = 6.5   # castellano: ~5,5 letras de media + el espacio
MARGEN_LONGITUD    = 0.85  # el modelo tiende a pasarse, y la línea del SESGO también ocupa
PALABRAS_MINIMAS   = 350   # por debajo de esto ya no es una nota, es un titular
MARCA_LONGITUD     = "[[LONGITUD]]"   # lo que se sustituye en el cierre del prompt


def palabras_que_caben(max_tokens: int) -> int:
    """Cuántas palabras entran de verdad en ese presupuesto de tokens."""
    return max(PALABRAS_MINIMAS,
               int(max_tokens * CHARS_POR_TOKEN / CHARS_POR_PALABRA * MARGEN_LONGITUD))


def instruccion_longitud(max_tokens: int) -> str:
    """La frase que sustituye a [[LONGITUD]] en el cierre del prompt."""
    techo = palabras_que_caben(max_tokens)
    return f"entre {int(techo * 0.8)} y {techo} palabras"


class PromptDemasiadoGrande(Exception):
    """Groq ha devuelto 413: el prompt no cabe en el presupuesto de TPM.

    Se distingue del resto de errores porque main() sabe reaccionar a esta en
    concreto, reintentando con el siguiente nivel de NIVELES_RECORTE.
    """

# Techo del prompt para que quepa una respuesta completa.
TECHO_PROMPT = GROQ_TPM_LIMIT - GROQ_TPM_SAFETY - GROQ_MIN_OUTPUT   # 6450

# ── Recorte progresivo del prompt ─────────────────────────────────────────────
# El 30/07/2026 el briefing NO SE GENERÓ: el prompt salió a ~6578 tokens y el
# script abortó. La causa no fue un cambio de código sino un día de calendario
# cargado -- BOE, BOJ, Advance GDP y Core PCE la misma mañana, 15 eventos de
# impacto alto/medio donde un día normal hay 4 o 5. Es decir, fallaba
# justamente los días en que el briefing más vale.
#
# Medido antes de tocar nada: de los 6578 tokens, 3471 (53%) eran
# INSTRUCCIONES FIJAS y solo 2703 datos. El prompt llevaba meses al borde.
#
# En vez de un umbral binario que aborta, se prueban niveles de recorte de
# menos a más agresivo hasta que quepa. Se sacrifica primero lo que menos
# duele: el historial narrativo (contexto, no información de hoy), luego el
# número de titulares -- el propio prompt ya pide "usa 2-3, no los enumeres
# todos" -- y por último el calendario, que es lo más ligado al día.
#
# El nivel 0 no es "sin recorte": ya baja el historial de 3000 a 1800 chars y
# los titulares de 8+8 a 5+5, que es el recorte de datos que da margen sin
# tocar una sola instrucción de estilo.
NIVELES_RECORTE = [
    {"nombre": "normal",    "historial": 1800, "titulares": 5, "calendario": None},
    {"nombre": "medio",     "historial": 1000, "titulares": 4, "calendario": 10},
    {"nombre": "agresivo",  "historial": 500,  "titulares": 3, "calendario": 7},
    {"nombre": "mínimo",    "historial": 0,    "titulares": 2, "calendario": 5},
]


def estimar_tokens(texto: str) -> int:
    """Estimación por caracteres — deliberadamente conservadora (divisor bajo
    = estima de más). No hace falta el tokenizador exacto: solo sirve para
    decidir cuánto espacio de respuesta pedir sin pasarse del límite."""
    import math
    return math.ceil(len(texto) / CHARS_POR_TOKEN)

# Mismo Gist que ya publica scanner_universe.py — lectura pública, sin token,
# para traer al briefing las señales de amplitud REALES de RSU (McClellan,
# % S&P sobre SMA50, NH-NL) en vez de que el briefing viva aislado del resto
# de la terminal.
SCANNER_GIST_ID = "cb9d69cbf6ca741b4fd86765a41813a7"
SCANNER_GIST_FILE = "scanner_scan.json"

FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")
# ALPHA_VANTAGE_API_KEY se leía aquí para el respaldo de titulares, pero el
# secret nunca llegó a configurarse en el Action y el respaldo era papel
# mojado. Sustituido por RSS directo de los medios (ver
# get_rss_fallback_headlines) — coherente además con PRECIOS_Y_APIS.md, que
# dice de Alpha Vantage "eliminar, no mejorar". Sigue en uso en
# backend/services/research_service.py (earnings trimestrales), eso no se toca.

# Insider Flow vive en SQLite dentro del backend (insider_history.db), no
# en un Gist -- así que solo es alcanzable desde este script contactando
# al backend en producción. RSU_BACKEND_URL apunta a la IP del VPS
# (sin HTTPS todavía); BRIEFING_AUTH_TOKEN es un token de servicio de
# larga duración emitido vía POST /api/v1/auth/admin/mint-token (ver
# sesión 23/07/2026) -- el endpoint exige Authorization: Bearer, así que
# sin el token la llamada da 403 aunque la URL esté bien configurada.
RSU_BACKEND_URL     = os.environ.get("RSU_BACKEND_URL", "").rstrip("/")
FRED_KEY = os.environ.get("FRED_API_KEY", "")
BRIEFING_AUTH_TOKEN = os.environ.get("BRIEFING_AUTH_TOKEN", "")

# Tickers de mega/large-cap conocidos — para filtrar el calendario de earnings
# a solo nombres con peso real de mercado, en vez de listar cientos de small
# caps irrelevantes para un briefing macro.
NOTABLE_TICKERS = {
    "AAPL","MSFT","GOOGL","GOOG","AMZN","NVDA","META","TSLA","AVGO","BRK.B",
    "JPM","V","MA","UNH","XOM","LLY","JNJ","PG","HD","COST","ABBV","MRK",
    "CVX","BAC","WMT","KO","PEP","ADBE","CRM","AMD","NFLX","TMO","ORCL",
    "MCD","CSCO","ABT","INTC","QCOM","TXN","DIS","IBM","GE","CAT","BA",
    "MU","AMAT","LRCX","PANW","NOW","UBER","GS","MS","C","WFC","AXP",
    "SPGI","BLK","PLTR","SMCI","ARM","COIN","SNOW","SHOP",
}

# ── RECOPILAR DATOS DE MERCADO ────────────────────────────────────────────────

def _safe(val):
    try:
        v = float(val)
        return v if not (np.isnan(v) or np.isinf(v)) else None
    except Exception:
        return None

def get_market_data() -> dict:
    """Recopila datos reales de mercado para dar contexto al LLM"""
    data = {}

    # Índices principales
    tickers = {
        "SPX":  "^GSPC",
        "NDX":  "^NDX",
        "RUT":  "^RUT",
        "VIX":  "^VIX",
        "DXY":  "DX-Y.NYB",
        "TNX":  "^TNX",   # 10Y yield
        "TYX":  "^TYX",   # 30Y yield
        "IRX":  "^IRX",   # 2Y proxy
        "GOLD": "GC=F",
        "WTI":  "CL=F",
        "BTC":  "BTC-USD",
        "ES":   "ES=F",      # futuro S&P 500 — gap pre-market
        "NQ":   "NQ=F",      # futuro Nasdaq 100 — gap pre-market
        "EURUSD": "EURUSD=X", # proxy divergencia BCE vs Fed
        "USDJPY": "USDJPY=X", # proxy divergencia BoJ vs Fed
    }

    ultima_barra = None       # fecha de la ultima vela del S&P: dice si lo que
                              # tenemos delante es un cierre o media sesion
    barras = {}               # {ticker: (fecha_prev, fecha_last)} -- para poder
                              # auditar despues contra que se calculo cada %
    for name, ticker in tickers.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2: continue
            if name == "SPX":
                ultima_barra = hist.index[-1].date()
            # LAS DOS FECHAS QUE SE ESTAN COMPARANDO. El 01/09/2026 el briefing
            # publico un S&P -0,58%, un Russell -1,92%, un XLU -2,20% y un XLI
            # -2,05% que no son la variacion de ninguna sesion real: los cuatro
            # coinciden EXACTAMENTE con el tramo 27/08 -> 31/08, dos sesiones
            # presentadas como una. No se pudo averiguar la causa porque los
            # datos de entrada no se guardaban en ningun sitio -- solo el texto
            # y el diagnostico de recorte. Esto no cuesta ni una ficha del
            # prompt: va al Gist, no al modelo.
            barras[name] = (str(hist.index[-2].date()), str(hist.index[-1].date()))
            prev  = float(hist["Close"].iloc[-2])
            last  = float(hist["Close"].iloc[-1])
            chg   = round((last - prev) / prev * 100, 2)
            # `prev` se guarda para poder expresar la variacion de los YIELDS en
            # puntos basicos. Ver fmt_yield(): un bono no se mueve "un 1,32%",
            # se mueve 6 pb, y el modelo confundia las dos cosas.
            data[name] = {"price": round(last, 2), "chg_pct": chg, "prev": round(prev, 2)}
        except Exception:
            data[name] = {"price": None, "chg_pct": None}

    # Sectores S&P 500
    sectors = {
        "XLK": "Tecnología", "XLF": "Financiero", "XLV": "Salud",
        "XLE": "Energía",    "XLI": "Industrial",  "XLY": "Consumo Discr.",
        "XLP": "Consumo Bás","XLB": "Materiales",  "XLU": "Utilities",
        "XLRE":"Inmobiliario","XLC": "Comunicaciones"
    }
    sector_data = {}
    for etf, name in sectors.items():
        try:
            t    = yf.Ticker(etf)
            hist = t.history(period="5d", interval="1d").dropna()
            if len(hist) < 2: continue
            prev = float(hist["Close"].iloc[-2])
            last = float(hist["Close"].iloc[-1])
            chg  = round((last - prev) / prev * 100, 2)
            # 5 días
            chg5 = round((last - float(hist["Close"].iloc[0])) / float(hist["Close"].iloc[0]) * 100, 2)
            barras[etf] = (str(hist.index[-2].date()), str(hist.index[-1].date()))
            sector_data[etf] = {"name": name, "chg_1d": chg, "chg_5d": chg5}
        except Exception:
            pass
    data["sectors"] = sector_data

    # ¿Estos porcentajes son un CIERRE o una sesion a medias? Con el cron de las
    # 07:00 UTC siempre son un cierre; en una ejecucion manual con el mercado
    # abierto, no -- y el 27/08 el briefing llamo "cierre" a una sesion viva.
    ahora_ny = datetime.now(ZoneInfo("America/New_York"))
    data["barras"] = barras
    data["sesion"] = {
        "fecha":    ultima_barra.isoformat() if ultima_barra else None,
        "en_curso": sesion_sin_cerrar(ultima_barra, ahora_ny),
        "hora_et":  ahora_ny.strftime("%H:%M"),
    }

    # Niveles técnicos reales (SMA20/50/200, máx/mín 20d) — para que el LLM no se invente
    # soportes/resistencias sin datos detrás. No son niveles de "price action" discrecional,
    # son medias móviles y rangos calculados directamente del histórico real.
    tech_levels = {}
    for name, ticker in {"SPX": "^GSPC", "NDX": "^NDX"}.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="220d", interval="1d").dropna()
            if len(hist) < 50:
                tech_levels[name] = None
                continue
            closes = hist["Close"]
            last   = float(closes.iloc[-1])
            sma20  = float(closes.rolling(20).mean().iloc[-1])
            sma50  = float(closes.rolling(50).mean().iloc[-1])
            sma200 = float(closes.rolling(200).mean().iloc[-1]) if len(closes) >= 200 else None
            high20 = float(hist["High"].rolling(20).max().iloc[-1])
            low20  = float(hist["Low"].rolling(20).min().iloc[-1])
            tech_levels[name] = {
                "last": round(last, 2),
                "sma20": round(sma20, 2), "sma50": round(sma50, 2),
                "sma200": round(sma200, 2) if sma200 else None,
                "high_20d": round(high20, 2), "low_20d": round(low20, 2),
                "vs_sma200_pct": round((last - sma200) / sma200 * 100, 2) if sma200 else None,
            }
        except Exception:
            tech_levels[name] = None
    data["tech_levels"] = tech_levels

    # Proxy aproximado de expectativas de Fed Funds (NO es CME FedWatch — esa API es de
    # pago, $25+/mes). Se calcula comparando el yield a 3 meses (IRX) contra el Fed Funds
    # Rate actual: si el 3M cotiza por debajo del Fed Funds, el mercado de bonos está
    # pricing bajadas de tipos en ese horizonte; si cotiza igual o por encima, no las espera.
    try:
        irx_val = data.get("IRX", {}).get("price")
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=FEDFUNDS",
            timeout=10, headers={"User-Agent": "RSU Terminal contact@rsu-terminal.com"}
        )
        fed_funds_now = None
        if r.status_code == 200:
            lines = r.text.strip().split("\n")
            last_line = lines[-1].split(",")
            fed_funds_now = float(last_line[1])
        if irx_val is not None and fed_funds_now is not None:
            implied_gap = round(fed_funds_now - irx_val, 2)  # positivo = mercado espera bajadas
            data["fed_funds_proxy"] = {
                "fed_funds_now": fed_funds_now,
                "yield_3m": irx_val,
                "implied_gap_pct": implied_gap,
                "interpretation": (
                    "bajadas" if implied_gap > 0.15 else
                    "subidas" if implied_gap < -0.15 else
                    "sin cambios significativos"
                ),
            }
        else:
            data["fed_funds_proxy"] = None
    except Exception:
        data["fed_funds_proxy"] = None

    # Fear & Greed
    try:
        r = requests.get(
            "https://production.dataviz.cnn.io/index/fearandgreed/graphdata",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://edition.cnn.com"},
            timeout=8
        )
        if r.status_code == 200:
            fg = r.json()["fear_and_greed"]
            data["fear_greed"] = {
                "score":  int(fg["score"]),
                "rating": fg["rating"],
                "prev":   int(fg.get("previous_close", fg["score"])),
            }
    except Exception:
        data["fear_greed"] = None

    # VIX Term Structure
    vix_tickers = {"VIX_SPOT": "^VIX", "VIX_3M": "^VIX3M", "VIX_6M": "^VIX6M"}
    vix_data = {}
    for name, ticker in vix_tickers.items():
        try:
            t    = yf.Ticker(ticker)
            hist = t.history(period="5d").dropna()
            if len(hist) > 0:
                vix_data[name] = round(float(hist["Close"].iloc[-1]), 2)
        except Exception:
            pass
    data["vix_term"] = vix_data

    # Credit Spreads (FRED CSV)
    try:
        r = requests.get(
            "https://fred.stlouisfed.org/graph/fredgraph.csv?id=BAMLH0A0HYM2",
            timeout=10
        )
        if r.status_code == 200:
            lines = r.text.strip().split("\n")
            last_line = lines[-1].split(",")
            data["hy_spread"] = float(last_line[1])
    except Exception:
        data["hy_spread"] = None

    # Calendario económico
    try:
        r = requests.get(
            "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8
        )
        print(f"📅 Calendario económico: status HTTP {r.status_code}")
        if r.status_code == 200:
            raw_events = r.json()
            print(f"📅 Calendario económico: {len(raw_events)} eventos totales en la semana")
            today  = datetime.now().strftime("%Y-%m-%d")
            events = []
            for item in raw_events:
                if not evento_relevante(item, today):
                    continue
                pais = (item.get("country") or "").upper()
                hora = hora_et(item)
                events.append({
                    "time":    hora,
                    "pais":    pais,
                    "event":   item.get("title", ""),
                    "impact":  item.get("impact", ""),
                    "actual":  item.get("actual", ""),
                    "forecast":item.get("forecast", ""),
                    "previous":item.get("previous", ""),
                })
            # BUG CORREGIDO: antes se recortaba a events[:10] sin ordenar por
            # hora primero — en un día con muchos eventos de impacto alto/medio
            # (ej. CPI de EEUU + testimonio Fed + varios británicos el mismo
            # día), un evento clave podía quedar fuera del corte solo por el
            # orden de llegada del feed, no por relevancia horaria. Se ordena
            # por hora y se sube el límite ligeramente (15, no 10) — un solo
            # día raramente tiene más de eso en alto/medio impacto, pero por
            # si acaso ya no se pierde el primero de la lista sin más.
            events.sort(key=lambda e: e["time"])
            print(f"📅 Calendario económico: {len(events)} eventos de hoy con impacto alto/medio: "
                  f"{', '.join(e['event'] for e in events) if events else '(ninguno)'}")
            data["calendar"] = events[:15]
        else:
            print(f"⚠️  Calendario económico: status {r.status_code} — puede ser bloqueo de IP compartida de GitHub Actions (CloudFlare), mismo tipo de problema que ya se ve con GDELT")
            data["calendar"] = []
    except Exception as e:
        print(f"⚠️  Calendario económico: error inesperado ({type(e).__name__}: {e})")
        data["calendar"] = []

    data["date"] = datetime.now().strftime("%Y-%m-%d")
    data["time"] = datetime.now().strftime("%H:%M UTC")

    return data


# ── NOTICIAS REALES DEL DÍA (Finnhub) ─────────────────────────────────────────

def get_market_news(max_items: int = 8) -> list:
    """Titulares reales de mercado — sin esto el LLM no tiene ninguna forma de
    saber qué está pasando hoy en el mundo (cambios de personal en la Fed,
    geopolítica, etc.), por mucho que los números de mercado sean correctos."""
    if not FINNHUB_KEY:
        print("⚠️  FINNHUB_API_KEY no configurado — sin titulares de Finnhub (revisa los secrets del Action)")
        return []
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": FINNHUB_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"⚠️  Finnhub /news devolvió status {r.status_code}: {r.text[:200]}")
            return []
        items = r.json()
        if not isinstance(items, list):
            print(f"⚠️  Finnhub /news devolvió un formato inesperado: {type(items)}")
            return []
        print(f"📰 Finnhub: {len(items)} noticias totales recibidas, filtrando a últimas 30h...")
        cutoff = datetime.now() - timedelta(hours=30)
        out = []
        for it in items:
            ts = it.get("datetime")
            if not ts:
                continue
            dt = datetime.utcfromtimestamp(ts)
            if dt < cutoff:
                continue
            headline = (it.get("headline") or "").strip()
            summary  = (it.get("summary") or "").strip()
            if not headline:
                continue
            out.append({
                "headline": headline[:180],
                "summary":  summary[:220],
                "source":   it.get("source", ""),
                "time":     dt.strftime("%H:%M UTC"),
            })
            if len(out) >= max_items:
                break
        print(f"📰 Finnhub: {len(out)} titulares dentro de la ventana de 30h, tras filtrar")
        return out
    except Exception as e:
        print(f"⚠️  No se pudieron obtener noticias: {e}")
        return []


# ── TITULARES DE ALTO IMPACTO — MEDIOS INTERNACIONALES (GDELT) ───────────────

def get_major_outlet_headlines(max_items: int = 8) -> list:
    """El feed de Finnhub (get_market_news) está orientado a mercado/empresa
    y puede no recoger bien noticias de alto impacto que son ante todo
    geopolíticas (conflictos, ataques, decisiones políticas mayores) aunque
    tengan consecuencias directas en precios — el caso real que motivó esto:
    un ataque en el Estrecho de Ormuz que mueve el petróleo y añade
    volatilidad al mercado no tiene por qué aparecer en un feed financiero
    estrecho.

    En vez de intentar llamar a las APIs de Reuters/Bloomberg/FT (de pago,
    sin acceso público gratuito), se usa GDELT — proyecto respaldado por
    Google Jigsaw, gratuito, sin necesidad de API key, que monitoriza medios
    de todo el mundo actualizándose cada 15 minutos. Se le pide
    específicamente que traiga titulares recientes de esos dominios
    concretos (Reuters, Bloomberg, WSJ, AP, Financial Times), no una
    búsqueda genérica — así se acerca lo más posible a "qué llevan estos
    medios ahora mismo" sin depender de sus APIs de pago."""
    domains = ["reuters.com", "bloomberg.com", "wsj.com", "apnews.com", "ft.com"]
    query = "(" + " OR ".join(f"domain:{d}" for d in domains) + ")"
    gdelt_params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": max_items * 2,  # margen, luego se filtra/recorta
        "timespan": "24h",
        "sort": "datedesc",
        "format": "json",
    }
    try:
        # Reintento con espera si GDELT devuelve 429 — el runner de GitHub
        # Actions comparte un pool de IPs con muchísimos otros proyectos, así
        # que aunque aquí solo se hace UNA petición, puede coincidir con una
        # ráfaga de otro trabajo completamente distinto usando una IP cercana
        # en ese mismo instante. GDELT pide explícitamente esperar 5s entre
        # peticiones.
        #
        # Backoff EXPONENCIAL (5s, 15s, 45s) en vez de tres esperas fijas de
        # 8s: los días 26-28/07/2026 los 3 reintentos de 8s fallaron seguidos,
        # lo que dice que el bloqueo dura bastante más que la ventana de 24s
        # que cubrían. Con 65s totales se cubre una congestión real sin
        # acercarse al timeout de 10 min del Action. Y si aun así falla, el
        # respaldo RSS (que no comparte infraestructura con GDELT) ya no es
        # papel mojado como lo era Alpha Vantage sin clave.
        r = None
        esperas = [5, 15, 45]
        for attempt, espera in enumerate(esperas):
            r = requests.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params=gdelt_params,
                timeout=15,
                headers={"User-Agent": "RSU-Terminal-Briefing/1.0"},
            )
            if r.status_code != 429:
                break
            if attempt < len(esperas) - 1:
                print(f"⚠️  GDELT devolvió 429 (límite de tasa compartido) — reintento {attempt + 1}/{len(esperas)} en {espera}s...")
                time.sleep(espera)

        if r.status_code != 200:
            print(f"⚠️  GDELT devolvió status {r.status_code}: {r.text[:200]}")
            return []
        data = r.json()
        articles = data.get("articles", [])
        print(f"🌍 GDELT: {len(articles)} artículos recibidos (aún sin comprobar el medio)")
        out = []
        descartados = 0
        seen_titles = set()
        for a in articles:
            title  = (a.get("title") or "").strip()
            domain = (a.get("domain") or "").strip()
            # Comprobar de donde viene DE VERDAD, en vez de fiarse de la
            # consulta: ver es_dominio_pedido(). Sin esto entraba prensa local
            # canadiense en el bloque de "medios internacionales".
            if not es_dominio_pedido(domain, domains):
                descartados += 1
                continue
            if not title or title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            seendate = a.get("seendate", "")  # formato YYYYMMDDTHHMMSSZ
            time_str = ""
            try:
                time_str = datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").strftime("%H:%M UTC")
            except Exception:
                pass
            out.append({
                "headline": title[:180],
                "source":   domain,
                "time":     time_str,
            })
            if len(out) >= max_items:
                break
        if descartados:
            print(f"🌍 GDELT: {descartados} artículos DESCARTADOS por no ser de "
                  f"{domains} — la consulta por dominio no se está respetando")
        if not out:
            # Devolver [] hace que main() tire del respaldo RSS. Antes, una
            # respuesta llena de medios equivocados contaba como éxito y el
            # respaldo bueno (BBC/CNBC/Al Jazeera) no llegaba a entrar nunca.
            print("🌍 GDELT: ningún titular de los medios pedidos — se usará el respaldo")
        print(f"🌍 GDELT: {len(out)} titulares tras deduplicar y filtrar por medio")
        return out
    except Exception as e:
        print(f"⚠️  No se pudieron obtener titulares de medios internacionales (GDELT): {e}")
        return []


# Respaldo de GDELT: RSS directo de los propios medios. Verificado en vivo
# (28/07/2026) cuáles responden de verdad, en vez de asumirlo:
#   - feeds.reuters.com  -> MUERTO (ni siquiera resuelve DNS; Reuters cerró
#     sus RSS públicos). Ojo: backend/services/newsfeed_service.py TODAVÍA lo
#     lista en SOURCES -- hallazgo aparte, no se toca aquí.
#   - apnews.com/index.rss -> HTTP 401 (ya requiere autenticación)
#   - feeds.a.dj.com (WSJ/Dow Jones) -> responde 200 con 20 artículos... pero
#     el más reciente es de enero de 2025, CONGELADO hace ~547 días. Es peor
#     que un 404: parece vivo y sirve contenido plausible pero obsoleto. Solo
#     se detectó porque el filtro de recencia de abajo lo dejó en 0 titulares.
#     OJO: backend/services/newsfeed_service.py usa el feed hermano
#     (RSSMarketsMain.xml), igual de congelado -- hallazgo aparte, no se toca aquí.
# Los 3 de abajo se verificaron VIVOS (artículo más reciente de hace <3h) y se
# eligen por cobertura complementaria: BBC (geopolítica global), CNBC
# (financiero internacional), Al Jazeera (Oriente Medio -- justo el caso de uso
# que motivó esta sección: un ataque en Ormuz que mueve el petróleo).
RSS_FALLBACK_FEEDS = [
    ("BBC",        "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("CNBC",       "https://www.cnbc.com/id/100727362/device/rss/rss.html"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
]


def get_rss_fallback_headlines(max_items: int = 8, max_age_hours: int = 30) -> list:
    """Respaldo cuando GDELT falla (ver get_major_outlet_headlines).

    Antes esto usaba Alpha Vantage, pero nunca llegó a funcionar: el secret
    ALPHA_VANTAGE_API_KEY no está configurado en el Action, así que el
    respaldo era papel mojado justo los días en que GDELT fallaba (26-28/07/
    2026, tres briefings seguidos sin titulares de alto impacto). Y el propio
    PRECIOS_Y_APIS.md dice explícitamente de Alpha Vantage "eliminar, no
    mejorar" -- así que en vez de pedirle al usuario que configure una clave
    que no debería contratar, se va directamente a la fuente: el RSS público
    de los propios medios. Sin API key, sin cuota, y no comparte
    infraestructura con GDELT (que es lo que un respaldo tiene que cumplir).

    Se leen los 3 feeds en paralelo: si uno falla, los otros dos siguen
    valiendo -- a diferencia del respaldo anterior, que era un único punto
    de fallo."""
    from email.utils import parsedate_to_datetime
    import xml.etree.ElementTree as ET

    corte = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    def _leer(feed):
        etiqueta, url = feed
        try:
            r = requests.get(url, timeout=12, headers={"User-Agent": "RSU-Terminal-Briefing/1.0"})
            if r.status_code != 200:
                print(f"⚠️  RSS {etiqueta}: HTTP {r.status_code}")
                return []
            root  = ET.fromstring(r.content)
            items = root.findall(".//item")
            out   = []
            for it in items:
                titulo = (it.findtext("title") or "").strip()
                if not titulo:
                    continue
                # Descartar lo viejo: un titular de hace 3 días en un briefing
                # de "qué ha pasado hoy" es peor que no tener titular.
                hora = ""
                pub  = it.findtext("pubDate")
                if pub:
                    try:
                        dt = parsedate_to_datetime(pub)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt < corte:
                            continue
                        hora = dt.astimezone(timezone.utc).strftime("%H:%M UTC")
                    except Exception:
                        pass  # sin fecha parseable: se conserva, mejor que descartarlo
                out.append({"headline": titulo[:180], "source": etiqueta, "time": hora})
            print(f"🔁 RSS {etiqueta}: {len(out)} titulares dentro de la ventana de {max_age_hours}h")
            return out
        except Exception as e:
            print(f"⚠️  RSS {etiqueta}: {type(e).__name__}: {str(e)[:80]}")
            return []

    with ThreadPoolExecutor(max_workers=len(RSS_FALLBACK_FEEDS)) as ex:
        por_feed = list(ex.map(_leer, RSS_FALLBACK_FEEDS))

    # Intercalar en vez de concatenar: con 8 huecos y concatenación, el primer
    # feed se los quedaría todos y el briefing vería un solo medio.
    out, vistos = [], set()
    for i in range(max(len(f) for f in por_feed) if por_feed else 0):
        for feed in por_feed:
            if i >= len(feed):
                continue
            t = feed[i]["headline"].lower()
            if t in vistos:
                continue
            vistos.add(t)
            out.append(feed[i])
            if len(out) >= max_items:
                print(f"🔁 Respaldo RSS: {len(out)} titulares de {len(RSS_FALLBACK_FEEDS)} medios")
                return out
    print(f"🔁 Respaldo RSS: {len(out)} titulares de {len(RSS_FALLBACK_FEEDS)} medios")
    return out


# ── EARNINGS NOTABLES PRÓXIMOS 2 DÍAS (Finnhub) ───────────────────────────────

def get_notable_earnings() -> list:
    """Solo large/mega-cap — un calendario de earnings sin filtrar es una lista
    de cientos de small caps irrelevantes para un briefing macro."""
    if not FINNHUB_KEY:
        return []
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        end   = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")
        r = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={"from": today, "to": end, "token": FINNHUB_KEY},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        rows = r.json().get("earningsCalendar", [])
        out = []
        for row in rows:
            ticker = row.get("symbol", "")
            if ticker not in NOTABLE_TICKERS:
                continue
            out.append({
                "ticker": ticker,
                "date":   row.get("date", ""),
                "hour":   row.get("hour", ""),  # bmo=antes de apertura, amc=tras cierre
                "eps_est": row.get("epsEstimate"),
            })
        return out[:6]
    except Exception as e:
        print(f"⚠️  No se pudieron obtener earnings: {e}")
        return []


# ── SEÑALES DE AMPLITUD REALES DE RSU (mismo Gist que el Scanner) ────────────

def get_rsu_breadth_signals() -> dict:
    """Lee directamente el Gist que publica scripts/scanner_universe.py cada
    noche — el mismo dato que alimenta Market Breadth en la terminal — para
    que el briefing hable con las señales propias de RSU (McClellan real,
    ABI, % del S&P sobre SMA50, NH-NL) en vez de vivir aislado del resto de
    la herramienta. Lectura pública, sin necesidad de token."""
    try:
        # CON EL TOKEN. Esta lectura iba sin autenticar, y desde un runner de
        # GitHub Actions la API pública está limitada a 60 peticiones/hora POR
        # IP COMPARTIDA: se come un 403 con facilidad. Cuando eso pasaba, el
        # `return {}` mudo dejaba el briefing sin amplitud y el modelo escribía
        # cosas como «la falta de datos de amplitud propia nos obliga a confiar
        # en la rotación sectorial» -- diciéndole al lector que la herramienta
        # no tiene un dato que sí calcula cada noche. Visto el 25/08/2026.
        cabeceras = {"Accept": "application/vnd.github.v3+json"}
        if GIST_TOKEN:
            cabeceras["Authorization"] = f"token {GIST_TOKEN}"
        r = requests.get(f"https://api.github.com/gists/{SCANNER_GIST_ID}",
                         timeout=10, headers=cabeceras)
        if r.status_code != 200:
            print(f"⚠️  Amplitud RSU no disponible: el Gist del Scanner respondió "
                  f"HTTP {r.status_code} ({'con' if GIST_TOKEN else 'SIN'} token)")
            return {}
        content = r.json()["files"][SCANNER_GIST_FILE]["content"]
        gist = json.loads(content)
        stocks = gist.get("stocks", {})
        if not stocks:
            return {}

        # % sobre SMA50 sigue siendo específicamente "del S&P 500" — solo el
        # subconjunto de 500 tiene el flag above_sma50 (viene del bucle de
        # scoring RS/fase, no del cálculo de amplitud ampliado).
        flagged = [v for v in stocks.values() if v.get("above_sma50") is not None]
        pct_above_sma50 = round(sum(1 for v in flagged if v["above_sma50"]) / len(flagged) * 100, 1) if flagged else None

        mcclellan, abi, new_highs, new_lows, universo_amplitud = None, None, None, None, None
        breadth_hist = gist.get("breadth_history", [])

        # ¿Viene completa la ultima sesion del escaneo? Ver amplitud_incompleta().
        # Si no, se DESCARTA esa sesion entera en vez de publicar ruido: el ABI,
        # el McClellan y el NH-NL salen todos de ella (y el McClellan arrastra el
        # punto malo en sus EMAs durante semanas si se le cuela).
        # `total_valores` lo emite el escaner desde el 04/09 y es el numero
        # exacto de tickers con dato ese dia; avances+descensos se queda corto
        # porque no cuenta los que cerraron planos. Se usa como respaldo para
        # los historiales escritos antes.
        def _tot(h):
            v = h.get("total_valores")
            return v if v is not None else (h.get("advances", 0) or 0) + (h.get("declines", 0) or 0)
        rota, tot, esperado = amplitud_incompleta(
            _tot(breadth_hist[-1]) if breadth_hist else None,
            [_tot(h) for h in breadth_hist[:-1]])
        if rota:
            print(f"⚠️  Amplitud DESCARTADA: la última sesión del escaneo trae {tot} "
                  f"valores frente a una mediana de {esperado:.0f} — escaneo "
                  f"incompleto, no se publica amplitud en vez de publicar ruido")
            breadth_hist = breadth_hist[:-1]

        if len(breadth_hist) >= 40:
            net_series = pd.Series([h["advances"] - h["declines"] for h in breadth_hist])
            mcclellan  = round(float(mcclellan_series(net_series).iloc[-1]), 1)

            # NH-NL y ABI del ÚLTIMO día del historial de amplitud — este
            # historial ya cubre S&P 500 + Russell 2000 (ver
            # scripts/scanner_universe.py:RUSSELL2000_TICKERS), no solo las
            # 500 grandes. Antes este NH-NL se recalculaba aparte sobre
            # `stocks` (solo S&P 500) — inconsistente con el McClellan de
            # arriba, que ya usaba el universo ampliado. Ahora ambos leen de
            # la misma fuente.
            ultimo = breadth_hist[-1]
            new_highs = ultimo.get("new_highs")
            new_lows  = ultimo.get("new_lows")
            adv, dec  = ultimo.get("advances"), ultimo.get("declines")
            if adv is not None and dec is not None and (adv + dec) > 0:
                abi = round(abs(adv - dec) / (adv + dec) * 100, 1)
            universo_amplitud = adv + dec if (adv is not None and dec is not None) else None

        # AVANCES Y DESCENSOS DEL DÍA, y separados por índice. El Gist ya los
        # trae en `breadth_sp500` y `breadth_russell` y no viajaban al prompt:
        # el modelo solo veía el agregado de los ~2.389 valores. El 26/08/2026
        # eso le costó el argumento -- escribió «el S&P sube pero la amplitud
        # es débil» y lo apoyó en el McClellan, que ESA sesión venía de un día
        # de amplitud POSITIVA (+141 neto). La prueba de verdad la tenía al
        # lado y no la recibía: del S&P 500 solo subieron 206 de 496 (41,5%)
        # mientras el índice ganaba un 0,32%.
        sp_hist = gist.get("breadth_sp500") or [{}]
        sp = sp_hist[-1]
        sp_rota, sp_tot, sp_esp = amplitud_incompleta(
            (sp.get("advances", 0) or 0) + (sp.get("declines", 0) or 0),
            [(h.get("advances", 0) or 0) + (h.get("declines", 0) or 0) for h in sp_hist[:-1]])
        if sp_rota:
            # Se RETROCEDE a la ultima sesion buena, igual que hace el historial
            # de arriba con `breadth_hist[:-1]`. Dejarlo en {} descartaba el
            # desglose entero mientras el universo si retrocedia, asi que el
            # prompt habria recibido los avances del dia anterior SIN su
            # desglose del S&P -- dos mitades de la misma foto descuadradas.
            print(f"⚠️  Desglose del S&P DESCARTADO: {sp_tot} valores frente a una "
                  f"mediana de {sp_esp:.0f} — se usa la última sesión completa")
            previas = [h for h in sp_hist[:-1]
                       if not amplitud_incompleta(
                           (h.get("advances", 0) or 0) + (h.get("declines", 0) or 0),
                           [(x.get("advances", 0) or 0) + (x.get("declines", 0) or 0)
                            for x in sp_hist if x is not h])[0]]
            sp = previas[-1] if previas else {}
        sp_adv, sp_dec = sp.get("advances"), sp.get("declines")
        sp_pct = (round(sp_adv / (sp_adv + sp_dec) * 100, 1)
                  if sp_adv is not None and sp_dec is not None and (sp_adv + sp_dec) else None)

        # LA BANDA DEL McCLELLAN, con los mismos umbrales que usa la terminal
        # (market_service.py: alcista >70, bajista <-70, en medio NEUTRO). Sin
        # ellos el modelo recibe un número desnudo y se inventa la escala: leyó
        # -26,7 como prueba bajista cuando la propia terminal lo clasifica
        # NEUTRO. Dos partes del mismo producto diciendo lo contrario.
        # LA BANDA DEL ABI, por el mismo motivo que la del McClellan. El
        # 01/09/2026 el briefing recibio "ABI: 39.8%" con la escala al lado y
        # escribio que "denota dispersion y falta de conviccion" y que "no hay
        # un lider claro" -- exactamente al reves. El ABI es |avances-descensos|
        # sobre el total: mide CUANTO SE IMPONE UN LADO, asi que 39,8% esta a
        # dos decimas de capitulacion, o sea de una venta abrumadoramente
        # unidireccional. La palabra "dispersion" de la escala invitaba a leerlo
        # como lo contrario.
        if abi is None:
            abi_estado = None
        else:
            if abi <= 15:
                abi_estado = "APAGADO"
            elif abi < 30:
                abi_estado = "MODERADO"
            elif abi < 40:
                abi_estado = "ALTO"
            else:
                abi_estado = "CAPITULACION"
            # CON LA DIRECCION. El ABI mide CUANTO se impone un lado pero no
            # CUAL, y el 03/09 el briefing recibio "ABI 66,7% (CAPITULACION)"
            # junto a los avances y descensos, y escribio que "la inmensa
            # mayoria de los componentes cayeron" cuando el desequilibrio era
            # AL ALZA. Tenia el dato al lado y lo leyo al reves; decirselo en la
            # propia etiqueta cuesta 3 fichas.
            if adv is not None and dec is not None and adv != dec and abi > 15:
                abi_estado += " al alza" if adv > dec else " a la baja"

        if mcclellan is None:
            mc_estado = None
        elif mcclellan > 70:
            mc_estado = "ALCISTA"
        elif mcclellan < -70:
            mc_estado = "BAJISTA"
        else:
            mc_estado = "NEUTRO"

        # LA FECHA DE LA AMPLITUD. El escaneo del Scanner es NOCTURNO: estos
        # numeros son SIEMPRE del cierre anterior, no de la sesion que el
        # briefing narra. El 27/08 el briefing explico un +0,27% del dia 27 con
        # las tripas del dia 26 -- y nada en el prompt permitia notarlo, porque
        # el bloque de amplitud no llevaba fecha.
        fecha_amplitud = breadth_hist[-1].get("date") if breadth_hist else None

        return {
            "fecha": fecha_amplitud,
            "escaneo_incompleto": bool(rota or sp_rota),
            "pct_above_sma50": pct_above_sma50,
            "advances": adv,
            "declines": dec,
            "sp500_advances": sp_adv,
            "sp500_declines": sp_dec,
            "sp500_pct_al_alza": sp_pct,
            "mcclellan_estado": mc_estado,
            "abi_estado": abi_estado,
            "new_highs": new_highs,
            "new_lows": new_lows,
            "nh_nl": (new_highs - new_lows) if (new_highs is not None and new_lows is not None) else None,
            "mcclellan": mcclellan,
            "abi": abi,
            "universe_size": gist.get("universe_size"),       # tamaño del universo de RS/fase (S&P 500, ~500)
            "universo_amplitud": universo_amplitud,             # tamaño del universo de amplitud (S&P 500 + Russell 2000, ~2.480)
        }
    except Exception as e:
        print(f"⚠️  No se pudieron leer las señales de amplitud de RSU: {e}")
        return {}


# ── CLUSTERS DE INSIDERS (solo si el backend ya está desplegado) ─────────────

def get_insider_clusters() -> list:
    """Insider Flow vive en SQLite dentro del backend, no en un Gist --
    esto solo funciona si RSU_BACKEND_URL apunta al backend en producción
    Y BRIEFING_AUTH_TOKEN trae un token de servicio válido (el endpoint
    exige Authorization: Bearer, ver backend/routers/insider.py). Si
    falta cualquiera de los dos, devuelve vacío sin romper el resto del
    briefing -- mismo criterio que el resto de fuentes opcionales."""
    if not RSU_BACKEND_URL or not BRIEFING_AUTH_TOKEN:
        return []
    try:
        r = requests.get(
            f"{RSU_BACKEND_URL}/api/v1/insider/clusters",
            headers={"Authorization": f"Bearer {BRIEFING_AUTH_TOKEN}"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        return r.json().get("clusters", [])[:5]
    except Exception as e:
        print(f"⚠️  No se pudo leer Insider Flow del backend: {e}")
        return []


# ── MEMORIA DE LOS ÚLTIMOS DÍAS (texto completo, no un caché de rendimiento) ─

def get_briefing_history() -> list:
    """Lee el historial de los últimos BRIEFING_HISTORY_DAYS briefings
    completos (fecha + texto + sesgo) -- reemplaza a la antigua
    get_yesterday_stance()/briefing.json (memoria de un solo día) por una
    ventana de varios días, para que el modelo pueda mantener consistencia
    de niveles/postura más allá de "ayer". Vive en un fichero aparte
    dentro del mismo Gist -- briefing.json (el más reciente, un solo día)
    se mantiene sin cambios porque backend/services/market_service.py
    ::get_nightly_briefing() lo lee por nombre exacto para el frontend."""
    if not GIST_TOKEN:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        content = r.json()["files"].get(BRIEFING_HISTORY_FILE, {}).get("content", "")
        if not content:
            return []
        history = json.loads(content)
        return history if isinstance(history, list) else []
    except Exception as e:
        print(f"⚠️  No se pudo leer el historial de briefings: {e}")
        return []


def _append_briefing_history(history: list, date: str, text: str, bias: str) -> list:
    """Añade el briefing de hoy y poda a los últimos BRIEFING_HISTORY_DAYS
    -- evita duplicado si se re-ejecuta el mismo día, mismo criterio que
    _append_bias()."""
    history = [h for h in history if h.get("date") != date]
    history.append({"date": date, "text": text, "bias": bias or "N/D"})
    history.sort(key=lambda h: h["date"])
    return history[-BRIEFING_HISTORY_DAYS:]


def format_briefing_history(history: list, presupuesto: int = None) -> str:
    """Bloque narrativo legible para el prompt -- mismo criterio ya
    establecido en el proyecto de no volcar JSON crudo (ver sector_lines,
    calendar_lines...). Orden cronológico, el más reciente al final."""
    # presupuesto=0 -> el nivel de recorte más agresivo prescinde del bloque
    # entero (ver NIVELES_RECORTE). Es contexto de días pasados: lo primero
    # que sobra cuando hay que elegir entre eso y quedarse sin briefing.
    if presupuesto is None:
        presupuesto = BRIEFING_HISTORY_CHARS_BUDGET
    if not history or presupuesto <= 0:
        return "Sin briefings anteriores registrados todavía."
    ordered = sorted(history, key=lambda h: h["date"])
    # Presupuesto TOTAL de caracteres repartido entre las entradas, en vez de
    # un tope FIJO POR ENTRADA (antes 2000 c/u). Con el tope fijo, el bloque
    # crecía linealmente con el historial (1 entrada = 2000 chars, 3 = 6000,
    # ~1600 tokens) y el prompt acababa reventando el límite de 8000 TPM de
    # Groq -- exactamente el 413 del 26-28/07/2026. Con presupuesto total, el
    # bloque ocupa lo mismo tenga 1 o 3 entradas: cuantas más haya, menos
    # texto de cada una, que es el reparto correcto (lo más reciente importa
    # más, pero todas aportan contexto).
    por_entrada = max(300, presupuesto // len(ordered))
    return "\n\n".join(f"[{h['date']} — sesgo {h.get('bias', 'N/D')}]\n{h['text'][:por_entrada]}" for h in ordered)


# ── CONSTRUIR PROMPT ──────────────────────────────────────────────────────────



# ── INDICADORES MACRO PUBLICADOS (FRED) ───────────────────────────────────────
# Lo que faltaba para que el briefing hable de datos macro REALES y no solo de
# precios. Nace de comparar con el Morning Briefing de Yardeni (29/07/2026):
# media nota suya son prints exactos con su secuencia ("el M-PMI cayo a 48,7
# desde 49,2, la 18a vez bajo 50 en 19 meses"), y nosotros no bajabamos ni uno.
#
# Dos decisiones que importan:
#
# 1. NUNCA se pasa el nivel del indice en crudo. CPIAUCSL vale 332,568 y eso no
#    significa nada para nadie: si se lo damos tal cual al modelo, escribe "el
#    IPC esta en 332,568". Se calculan aqui las transformaciones que de verdad
#    se citan (m/m, a/a, cambio en miles de empleos) y se le pasan ya hechas.
#
# 2. Se pasa la EDAD del dato. Un IPC de hace tres semanas no es noticia de hoy,
#    y sin la fecha el modelo lo presentaria como si acabara de salir. El
#    prompt usa esa antiguedad para decidir si lo destaca o solo lo usa de
#    contexto.
#
# El ISM (el indicador estrella de Yardeni) NO esta: es propietario y no lo
# publica FRED. No se sustituye por nada que se le parezca.
FRED_SERIES = [
    # (id, nombre, tipo de transformacion)
    ("ICSA",     "Peticiones semanales de paro", "nivel_miles"),
    ("UNRATE",   "Tasa de paro",                 "nivel_pct"),
    ("PAYEMS",   "Nóminas no agrícolas",         "cambio_miles"),
    ("CPIAUCSL", "IPC general",                  "mm_aa"),
    ("CPILFESL", "IPC subyacente",               "mm_aa"),
    ("PCEPILFE", "PCE subyacente",               "mm_aa"),
    ("RSAFS",    "Ventas minoristas",            "mm_aa"),
    ("INDPRO",   "Producción industrial",        "mm_aa"),
]


def _fred_observaciones(series_id: str, n: int = 14) -> list:
    """Ultimas n observaciones (fecha, valor), mas reciente primero."""
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series_id, "api_key": FRED_KEY, "file_type": "json",
                    "sort_order": "desc", "limit": n},
            timeout=12,
        )
        if r.status_code != 200:
            return []
        return [(o["date"], float(o["value"]))
                for o in r.json().get("observations", [])
                if o.get("value") not in (".", "", None)]
    except Exception:
        return []


def _fred_publicado_el(series_id: str):
    """Fecha en que FRED publicó por última vez esta serie.

    Hace falta porque la fecha de la OBSERVACIÓN y la de PUBLICACIÓN son cosas
    distintas y para decidir si algo es noticia manda la segunda: el IPC de
    junio (observación 2026-06-01) se publicó el 14 de julio. Medir la
    antigüedad por la observación decía "hace 58 días" de un dato de hace dos
    semanas, y la marca de RECIÉN PUBLICADO no se activaba NUNCA en las series
    mensuales -- justo las que mueven mercado el día que salen.
    """
    try:
        r = requests.get(
            "https://api.stlouisfed.org/fred/series",
            params={"series_id": series_id, "api_key": FRED_KEY, "file_type": "json"},
            timeout=12,
        )
        if r.status_code != 200:
            return None
        return (r.json().get("seriess") or [{}])[0].get("last_updated", "")[:10] or None
    except Exception:
        return None


def get_macro_indicators() -> list:
    """Ultimo dato publicado de cada indicador, ya transformado a algo citable.

    Devuelve [] si no hay clave de FRED -- el briefing se genera igual, solo
    que sin esta seccion. Ningun indicador se rellena ni se aproxima: el que
    falle, se omite.
    """
    if not FRED_KEY:
        print("⚠️  FRED_API_KEY no configurada — briefing sin indicadores macro")
        return []

    from datetime import datetime as _dt
    hoy = _dt.now().date()
    salida = []

    for series_id, nombre, tipo in FRED_SERIES:
        obs = _fred_observaciones(series_id)
        if len(obs) < 2:
            continue
        fecha, valor = obs[0]
        previo = obs[1][1]
        publicado = _fred_publicado_el(series_id)
        try:
            edad = (hoy - _dt.strptime(publicado, "%Y-%m-%d").date()).days if publicado else None
        except Exception:
            edad = None

        if tipo == "nivel_miles":
            media4 = sum(v for _, v in obs[:4]) / 4
            dato   = f"{valor:,.0f}".replace(",", ".")
            extra  = f"previo {previo:,.0f}".replace(",", ".") +                      f" · media 4 semanas {media4:,.0f}".replace(",", ".")
        elif tipo == "nivel_pct":
            dato  = f"{valor:.1f}%"
            extra = f"previo {previo:.1f}%"
        elif tipo == "cambio_miles":
            cambio      = valor - previo
            cambio_prev = previo - obs[2][1] if len(obs) > 2 else None
            dato  = f"{cambio:+,.0f}k empleos".replace(",", ".")
            extra = (f"mes anterior {cambio_prev:+,.0f}k".replace(",", ".")
                     if cambio_prev is not None else "sin mes anterior")
        elif tipo == "mm_aa":
            mm = (valor / previo - 1) * 100
            aa = (valor / obs[12][1] - 1) * 100 if len(obs) > 12 else None
            dato  = f"{mm:+.2f}% m/m"
            extra = f"{aa:+.2f}% interanual" if aa is not None else "sin interanual"
        else:
            continue

        salida.append({
            "nombre": nombre, "fecha": fecha, "dato": dato,
            "extra": extra, "publicado": publicado, "edad_dias": edad,
        })

    print(f"📈 Indicadores macro (FRED): {len(salida)}/{len(FRED_SERIES)} disponibles")
    return salida


# -- VERSIONES DEL PROMPT ----------------------------------------------------
# El v1 se conserva INTEGRO, y no por nostalgia: este job corre desatendido
# cada manana y lo que publica lo leen ~100 personas. Si el v2 no convence,
# revertir tiene que costar treinta segundos -- poner BRIEFING_PROMPT_VERSION=v1
# en los secrets de GitHub y relanzar el workflow --, no un commit, una
# revision y un despliegue. Ver sesion 29/07/2026: el usuario pidio
# explicitamente poder volver atras.
# El `or "v2"` no sobra: GitHub Actions pasa los secrets INEXISTENTES como
# cadena vacía, no como ausentes, así que sin él el log diría version='' aunque
# el comportamiento fuera el correcto.
PROMPT_VERSION = (os.environ.get("BRIEFING_PROMPT_VERSION") or "v2").strip().lower()

_ESTILO_V1 = """Eres un trader macro-discrecional escribiendo tu propia nota de mercado de cada mañana, para tu comunidad de trading. No es un informe institucional de un banco — es tu lectura personal, en primera persona, con tu propio posicionamiento incluido ("mi cartera", "he cerrado las coberturas", "mantengo el objetivo de..."). El tono es directo, seguro, con opiniones claras — no un informe neutro que evita mojarse.

IDIOMA: Español castellano, natural. Nada de emojis. Nada de listas interminables — prosa conectada, con algún bullet solo donde de verdad ayude a la lectura rápida.

VARIEDAD: Esto se publica todos los días. No repitas la misma fórmula de apertura ni las mismas frases hechas cada vez — varía cómo empiezas y cómo conectas las ideas, como lo haría una persona real escribiendo día tras día, no una plantilla rellenada.

PROHIBIDO SONAR A TEXTO GENERADO: Nunca uses coletillas típicas de IA como "es importante destacar que", "cabe mencionar que", "en resumen", "cabe señalar", "es fundamental tener en cuenta", "no debemos olvidar que", "vale la pena recordar que", "como se ha señalado", "es relevante destacar". Ningún trader real las usa escribiendo rápido por la mañana — si se cuela alguna de estas, reescribe la frase.

CUANTIFICA, NO GENERALICES: Cada afirmación cualitativa debe ir atada a un número concreto de los datos proporcionados abajo. No "el VIX está tranquilo" — "el VIX cotiza en 14,2, por debajo del rango reciente". No "el mercado ha recuperado terreno" — el nivel exacto de dónde a dónde. Tienes los datos, úsalos en vez de quedarte en adjetivos vagos.

NIVEL DE INVALIDACIÓN CONCRETO: La conclusión debe incluir un precio exacto que invalidaría la tesis del día — usa uno de los niveles técnicos reales ya proporcionados (SMA20, SMA50, SMA200 o el rango de 20 días), nunca un nivel inventado. Un análisis serio siempre dice qué número exacto le haría cambiar de opinión, no solo "si el mercado se pone feo".

SIN CIERRE DE ASISTENTE: No termines con nada tipo "espero que esta información te sea útil", "cualquier duda me dices" o similar. El briefing termina con tu conclusión y la etiqueta SESGO, nada más — no es una respuesta de chatbot despidiéndose.

CONVICCIÓN CALIBRADA: Evita tanto las afirmaciones categóricas ("esto va a pasar") como la vaguedad que no compromete a nada ("podría pasar cualquier cosa"). El registro correcto es: "lo más probable es X, y esto se invalida si pasa Y" — una lectura de probabilidades con un punto de invalidación claro, no una predicción ni un texto que no dice nada.

REGLAS ANTI-ALUCINACIÓN — ESTRICTAS, SIN EXCEPCIONES:
1. No inventes datos, precios, ni titulares que no estén en los bloques de abajo. Si falta un dato, dilo o simplemente no lo menciones — no rellenes el hueco con algo inventado. No inventes noticias que no estén en la lista de titulares proporcionada. De los titulares recibidos, ignora cualquiera que no tenga impacto financiero/económico/geopolítico real — un feed de noticias generalista trae de todo, tu criterio es filtrar lo irrelevante, no mencionarlo por completar espacio.
2. No asumas que hoy hay una publicación de datos macro "típica" (payrolls, IPC, etc.) salvo que aparezca en el CALENDARIO ECONÓMICO de abajo con fecha confirmada — un dato que "suele publicarse sobre estas fechas" no es lo mismo que un dato confirmado en el calendario proporcionado. **Mira la columna País**: un IPC de AUD o de EUR no es el de Estados Unidos y no manda en Wall Street; dilo con su país. No inventes el MES de referencia de un dato (el calendario no lo dice) ni su hora si pone N/D.
2b. Si un dato de abajo viene como "Dato no disponible", puedes decir que hoy no lo tienes, pero NO afirmes que la herramienta carece de él ni expliques por qué falta: no lo sabes.
2c. Tu sesgo final tiene que ser coherente con el cuerpo: si mantienes sesgo bajista, no hables a la vez de invalidar "tu visión de rebote".
3. Materias primas (oro, petróleo): los precios de arriba son de futuro continuo (front month), no spot ni un contrato con vencimiento específico — no inventes un código de contrato concreto (p.ej. "CLQ26"), refiérete a ellos como "el futuro" o "el precio" del activo.
4. VIX: si lo citas fuera del horario de mercado (pre-market/after-hours), usa el dato de la sesión anterior tal cual se te proporciona, sin afirmar que es el "settlement oficial de las 16:15 ET" salvo certeza.
5. Yields de bonos: la variación viene ya calculada EN PUNTOS BÁSICOS (pb) junto al nivel y al cierre previo. Cítala tal cual, en pb, incluso si es un movimiento pequeño o plano. NO la conviertas a porcentaje ni digas que el bono "cayó un X%": un yield que pasa del 4,70% al 4,64% ha bajado 6 pb, no un 1,3%.
6. Tipos de bancos centrales: si mencionas la Fed, usa el proxy de Fed Funds ya proporcionado, nunca MRO/discount/prime u otro tipo distinto. No menciones tipos del BCE ni de otro banco central si no aparecen en los datos proporcionados.
7. Variaciones porcentuales: usa la cifra ya calculada y proporcionada para cada activo — no la recalcules mentalmente ni la redondees de forma distinta a como aparece.
8. Datos sectoriales (XLE, XLK, etc.): mira la etiqueta ESTADO DE LA SESIÓN que acompaña a los datos de mercado. Si dice CERRADA, esos porcentajes son de cierre y no los presentes como intradía en tiempo real. Si dice EN CURSO, son una foto a media sesión: NO escribas que el índice «cerró» ni des el día por terminado — di que va camino de, y cita la hora.
9. Futuros pre-market: la hora (ET) del dato ya viene indicada junto al propio dato — cítala si mencionas el gap, no des el número como si fuera "ahora mismo" sin contexto horario.
10. SIN HISTÓRICO: solo tienes el precio de hoy y su variación, así que nunca afirmes máximos ni mínimos (históricos, anuales, «desde X») salvo que lo diga un titular, y atribúyelo. Y compara los números antes de decir que uno cae más que otro.

LONGITUD: 500-700 palabras. Esto no es un informe de 2000 palabras con 11 secciones — es una nota que se lee en 3-4 minutos."""

_CIERRE_V1 = """Escribe la nota de hoy. Estructura sugerida (adapta libremente, esto no es una plantilla rígida de secciones obligatorias):

- Un título con la fecha.
- Cómo está el mercado ahora mismo y cuál es tu lectura de la situación — en primera persona, con tu propio posicionamiento si aplica (¿mantienes, reduces o cambias la postura de ayer?).
- Los 1-2 catalizadores reales del día (de los titulares y earnings proporcionados) que de verdad mueven la aguja hoy — no un resumen de todos los titulares, solo los que importan.
- Objetivo técnico y zona de seguridad — usa los niveles técnicos reales proporcionados (SMA20/50/200, rango 20d), no inventes soportes/resistencias adicionales.
- Un repaso corto del panorama macro (tipos, VIX, amplitud propia de RSU, spreads) — solo lo que aporte a la tesis del día, no una lista exhaustiva de todos los datos.
- Qué vigilar — riesgos concretos, no genéricos ("cuidado con la volatilidad" no vale; di qué exactamente y por qué).
- Cierra con tu recomendación clara para hoy.

FORMATO: Prosa en primera persona, con algún encabezado en negrita para las 2-3 secciones principales si ayuda a la lectura, no una tabla por sección. Sin emojis. Tono de trader real hablando a su comunidad, no de banco de inversión.

ÚLTIMA LÍNEA OBLIGATORIA: Termina el briefing con una línea aparte, exactamente en este formato (sin nada más en esa línea, sin negrita, sin explicación adicional):
SESGO: ALCISTA
(o BAJISTA, o NEUTRAL — el que corresponda a tu conclusión de hoy). Esta línea se procesa automáticamente, tiene que estar en ese formato exacto o se pierde el registro de sesgo del día."""

# v2 (29/07/2026) -- nace de revisar el Morning Briefing de Yardeni Research
# que compartio el usuario. De ahi se copia la ESTRUCTURA (titular tematico,
# resumen ejecutivo, bloques con nombre propio, conclusion explicita), que es
# lo que hace que se lea bien.
#
# Lo que NO se copia, a proposito: su ensayo tematico de seis sub-secciones
# sobre macro. Yardeni lo escribe citando discursos concretos de gobernadores
# de la Fed; nuestro script alimenta al modelo con precios, sectores, amplitud
# e insiders, y CERO declaraciones. Pedirle seis bloques de teoria monetaria
# con eso es pedirle que se invente las citas -- exactamente el fallo que este
# proyecto lleva meses eliminando (el DXY fijo en 103, el yield 2Y sintetico,
# los tickers de Reddit fabricados).
#
# Tampoco cabria: Groq esta en 8.000 TPM entre prompt y respuesta, y las
# ~3.550 palabras del PDF son ya ~4.970 tokens solo de salida.
_ESTILO_V2 = """Eres el analista jefe de RSU Terminal y escribes el briefing que leen cada mañana ~100 inversores particulares antes de la apertura de Wall Street. Te leen porque les ahorras mirar veinte pantallas y porque les dices lo que TÚ ves, no lo que dice el consenso. Es tu lectura personal, en primera persona: te mojas con una postura clara, no escribes un informe neutro.

IDIOMA: Español castellano, natural. Nada de emojis. Prosa conectada con encabezados, no tablas ni listas interminables.

ESTRUCTURA OBLIGATORIA. Escribe estas cuatro partes, en este orden. Donde se indique un encabezado LITERAL, úsalo tal cual y en negrita. La cuarta parte va SIEMPRE en su propio bloque separado, aunque el último bloque del punto 3 ya apunte en esa dirección: no las fundas.

1. UN TITULAR TEMÁTICO. Una línea. Es el ángulo del día, no un resumen de precios: "el mercado sube un 0,4%" no es un titular, "la amplitud no acompaña al índice" sí. Sale de lo que de verdad destaque hoy, no de una plantilla.

2. El resumen, justo debajo del titular y sin encabezado propio. Exactamente dos frases: qué ha pasado y qué implica. Quien solo lea esto tiene que quedarse con lo esencial. Sin cifras de adorno — las que pongas aquí son las que mandan.

3. EL DESARROLLO, en 2 o 3 bloques con encabezado propio. Cada bloque es UNA idea desarrollada, y los eliges según lo que digan los datos de hoy: no hay secciones fijas. Ejemplos válidos: "Rotación sectorial", "La curva y el dólar", "Amplitud vs índice", "Lo que dicen los insiders". Dentro de cada bloque:
   - Abre con la afirmación, no con el dato: primero qué está pasando, después el número que lo respalda.
   - Cita cifras EXACTAS de los bloques de datos, nunca redondeadas a ojo.
   - Si un dato contradice tu tesis, dilo. Un briefing que solo cita lo que le conviene no vale nada.

   LAS NOTICIAS DEL DÍA VAN AQUÍ, TEJIDAS, no en una lista aparte ni en una sección "Noticias". Tus lectores abren esto antes de la apertura para saber qué ha pasado mientras dormían: si hay una noticia que mueve mercado hoy y no la mencionas, el briefing ha fallado por muy bien que estén los bloques técnicos.
   - Coge 2-3 titulares de los de abajo, los que de verdad importen para el sesgo de hoy. No los enumeres todos.
   - Los titulares de medios internacionales pueden ser GEOPOLÍTICOS y no financieros en sentido estricto (conflictos, ataques, decisiones políticas mayores) y aun así mover el mercado. Si hay algo así con impacto real hoy, menciónalo y conecta con QUÉ ACTIVO CONCRETO mueve y por qué — petróleo, defensa, refugio, volatilidad. Una noticia sin esa conexión no aporta nada.
   - Si la noticia es lo más relevante del día, que sea ella la que dé el titular del punto 1 y abra el primer bloque. La estructura se adapta a lo que manda hoy, no al revés.

   EL CALENDARIO MACRO DE HOY NO ES OPCIONAL. Si en el CALENDARIO ECONÓMICO de abajo hay algún evento de impacto ALTO (decisión de tipos, IPC, empleo, comparecencia del presidente de la Fed), es lo que va a mandar en la sesión y TIENES que abordarlo: qué se espera según el consenso que viene en la tabla, qué está descontando el mercado según los datos que sí tienes (yields, VIX, futuros, oro, dólar) y qué pasaría en cada escenario. Un briefing que no menciona que hoy hay decisión de tipos ha fallado, por muy bien que estén los bloques técnicos. Cíñete al consenso y al previo de la tabla: no inventes lo que va a decidir ni lo que va a decir nadie.

   LOS INDICADORES MACRO YA PUBLICADOS son tu munición para argumentar. Cuando defiendas una tesis sobre inflación, empleo o consumo, ánclala a un dato REAL de esa tabla con su cifra y su fecha — "el IPC subyacente sigue en el 2,8% interanual" vale, "la inflación se está moderando" a secas no. Da la secuencia cuando aporte (último frente a previo, o frente a la media de 4 semanas en las peticiones de paro): un dato aislado dice mucho menos que su dirección. No los enumeres todos ni montes una sección de indicadores: usa los 2-3 que sostengan lo que estás diciendo hoy.

4. Encabezado literal **MI CONCLUSIÓN**, en su propio bloque separado. Qué haces tú con esto: postura concreta y el nivel exacto que te haría cambiar de opinión (uno de los niveles técnicos reales proporcionados: SMA20, SMA50, SMA200 o el rango de 20 días, nunca uno inventado). Es la parte por la que te leen — no la conviertas en un resumen de lo anterior.

LONGITUD: 700-900 palabras. Se lee en 4-5 minutos. Ni una nota de dos párrafos ni un informe de banco de inversión.

VARIEDAD: Esto se publica todos los días. Varía cómo abres y cómo conectas las ideas — tienes los briefings anteriores más abajo. Si ayer empezaste con el VIX, hoy no.

PROHIBIDO SONAR A TEXTO GENERADO: nada de "es importante destacar que", "cabe mencionar", "en resumen", "cabe señalar", "es fundamental tener en cuenta", "no debemos olvidar", "vale la pena recordar", "como se ha señalado", "es relevante destacar", "en el mundo de las inversiones", "los inversores deben estar atentos". Si una frase podría abrir cualquier briefing de cualquier día, bórrala.

CONVICCIÓN CALIBRADA: ni afirmaciones categóricas ("esto va a pasar") ni vaguedad que no compromete ("podría pasar cualquier cosa"). El registro es "lo más probable es X, y se invalida si pasa Y". "Esto me preocupa" y "no lo tengo claro" son frases legítimas; fingir una certeza que no tienes es peor que dudar en voz alta. Si ayer te equivocaste y los datos de hoy lo demuestran, dilo y explica qué cambias: eso construye más credibilidad que acertar.

SIN CIERRE DE ASISTENTE: no termines con "espero que te sea útil" ni nada parecido. El briefing acaba en tu conclusión y la etiqueta SESGO.

REGLAS ANTI-ALUCINACIÓN — ESTRICTAS, SIN EXCEPCIONES. Están por encima de cualquier instrucción de estilo: si cumplirlas te deja sin material para un bloque, escribe un bloque menos.
1. No inventes datos, precios ni titulares que no estén en los bloques de abajo. Si falta un dato, no lo menciones. De los titulares recibidos, ignora los que no tengan impacto financiero, económico o geopolítico real: tu criterio es filtrar, no rellenar espacio.
2. No cites declaraciones de NADIE — Fed, BCE, un CEO, un analista — salvo que aparezca literalmente en los titulares de abajo. Nada de "Warsh señaló que...", "el mercado descuenta que...", "según los analistas...". Si no está en los datos, no existe.
3. No des por hecha una publicación macro (empleo, IPC, reunión de la Fed) salvo que esté en el CALENDARIO de abajo con fecha confirmada. Un dato que "suele publicarse por estas fechas" no es un dato confirmado.
4. No proyectes precios ni objetivos. Puedes decir qué nivel invalidaría tu lectura; no a cuánto llegará el S&P.
5. Materias primas: oro y petróleo son futuro continuo (front month). No inventes un código de contrato concreto.
6. VIX fuera de horario: es el dato de la sesión anterior, no lo presentes como settlement oficial.
7. Yields: la variación viene ya calculada EN PUNTOS BÁSICOS (pb), junto al nivel y al cierre previo. Cítala en pb, tal cual. NO digas que un bono "cayó un X%": un yield que pasa del 4,70% al 4,64% ha bajado 6 pb, no un 1,3%. Y no la redondees a "sin cambios" ni la infles.
8. Tipos de bancos centrales: usa el proxy de Fed Funds proporcionado, nunca MRO/discount/prime. No menciones tipos del BCE si no están en los datos.
9. Variaciones porcentuales: usa la cifra ya calculada, no la recalcules ni la redondees distinto.
10. Datos sectoriales: lo que son lo dice la etiqueta ESTADO DE LA SESIÓN — de CIERRE si dice CERRADA, foto a media sesión si dice EN CURSO. Nunca llames «cierre» a una sesión EN CURSO.
11. Futuros: la hora (ET) viene junto al dato. Cítala si mencionas el gap.
12. SIN HISTÓRICO: solo tienes el precio de hoy y su variación, así que nunca afirmes máximos ni mínimos (históricos, anuales, «desde X») salvo que lo diga un titular, y atribúyelo. Y compara los números antes de decir que uno cae más que otro.
12. Indicadores macro: las variaciones (m/m, interanual, cambio en miles de empleos) vienen ya CALCULADAS. Cítalas tal cual y NUNCA el nivel del índice en crudo — "el IPC está en 332,568" no significa nada para quien lee. Respeta la FECHA de cada dato: lo que no está marcado "RECIÉN PUBLICADO" puede tener semanas, así que es contexto de fondo y no puedes presentarlo como si hubiera salido hoy. Y no mezcles un dato ya publicado con una previsión del calendario: son cosas distintas."""

_CIERRE_V2 = """Escribe la nota de hoy siguiendo la ESTRUCTURA OBLIGATORIA de arriba (titular temático, EN DOS LÍNEAS, 2-3 bloques con encabezado propio, MI CONCLUSIÓN).

LONGITUD, y esto es un techo, no una sugerencia: [[LONGITUD]]. Si al terminar te has pasado, recorta -- quita el bloque que menos aporte antes que resumirlo todo a medias.

FORMATO: prosa en primera persona con los encabezados en negrita. Sin emojis, sin tablas. Tono de trader real hablando a su comunidad, no de banco de inversión.

ÚLTIMA LÍNEA OBLIGATORIA: termina con una línea aparte, exactamente en este formato (sin nada más en esa línea, sin negrita, sin explicación):
SESGO: ALCISTA
(o BAJISTA, o NEUTRAL — el que corresponda a tu conclusión de hoy). Esta línea se procesa automáticamente: cualquier otro formato pierde el registro de sesgo del día."""


def _reglas_de_estilo() -> str:
    """Bloque de estilo/reglas del prompt segun la version activa."""
    return _ESTILO_V1 if PROMPT_VERSION == "v1" else _ESTILO_V2


def _cierre_y_estructura() -> str:
    """Instrucciones finales (estructura + formato + linea de SESGO)."""
    return _CIERRE_V1 if PROMPT_VERSION == "v1" else _CIERRE_V2


def build_prompt(market_data: dict, news: list, major_headlines: list, earnings: list, breadth: dict,
                  insider_clusters: list, briefing_history: list, bias_history: list,
                  macro_indicators: list = None, recorte: dict = None) -> str:
    # `recorte` es uno de NIVELES_RECORTE: cuántos titulares y eventos de
    # calendario entran, y cuánto historial narrativo. Se llama en bucle desde
    # main() de menos a más agresivo hasta que el prompt quepa en TECHO_PROMPT,
    # en vez de abortar cuando no cabe. Ver el comentario de NIVELES_RECORTE.
    recorte = recorte or NIVELES_RECORTE[0]
    max_titulares = recorte.get("titulares")
    max_calendario = recorte.get("calendario")
    if max_titulares:
        news = news[:max_titulares]
        major_headlines = major_headlines[:max_titulares]
    d = market_data

    # Formatear índices
    def fmt(name):
        v = d.get(name, {})
        if not v or v.get("price") is None:
            return "Dato no disponible"
        chg = v.get("chg_pct", 0) or 0
        arrow = "▲" if chg >= 0 else "▼"
        return f"{v['price']:,.2f} ({arrow}{abs(chg):.2f}%)"

    def fmt_yield(name):
        """Los yields NO se citan en variacion porcentual relativa.

        fmt() devuelve "4,64 (▼1,32%)", y ese 1,32% es cuanto ha bajado el
        yield EN RELATIVO. El modelo lo leia como puntos basicos o porcentuales
        y escribia "el 10 años bajo 1,32 pp hasta el 4,64%" -- que implicaria
        venir del 5,96%, imposible en una sesion. Salio en los briefings de las
        DOS versiones del prompt (29/07/2026), asi que era el dato mal
        presentado, no el modelo alucinando. Aqui se da el nivel, el cierre
        previo y la variacion en PUNTOS BASICOS, que es como se habla de bonos.
        """
        v = d.get(name, {})
        if not v or v.get("price") is None:
            return "Dato no disponible"
        prev = v.get("prev")
        if prev is None:
            return f"{v['price']:.2f}%"
        pb = (v["price"] - prev) * 100
        signo = "+" if pb >= 0 else "−"
        return f"{v['price']:.2f}% ({signo}{abs(pb):.0f} pb desde {prev:.2f}%)"

    # Formatear pares de divisas (más decimales que índices — 1.0856 no 1.09)
    def fmt_fx(name):
        v = d.get(name, {})
        if not v or v.get("price") is None:
            return "Dato no disponible"
        chg = v.get("chg_pct", 0) or 0
        arrow = "▲" if chg >= 0 else "▼"
        return f"{v['price']:,.4f} ({arrow}{abs(chg):.2f}%)"

    # Sectores
    sector_lines = ""
    for etf, sv in d.get("sectors", {}).items():
        chg1 = sv.get("chg_1d", 0) or 0
        chg5 = sv.get("chg_5d", 0) or 0
        sector_lines += f"| {etf} | {sv['name']} | {chg1:+.2f}% | {chg5:+.2f}% |\n"

    # Futuros (gap pre-market real, no inventado) -- con hora ET real, para
    # que el modelo no describa un dato pre-market como si fuera del cierre.
    es = d.get("ES", {})
    nq = d.get("NQ", {})
    et_time = datetime.now(ZoneInfo("America/New_York")).strftime("%H:%M ET")
    futures_str = "Dato no disponible"
    if es.get("price") is not None and nq.get("price") is not None:
        futures_str = f"ES (S&P): {fmt('ES')} | NQ (Nasdaq): {fmt('NQ')} — dato de las {et_time}"

    # Niveles técnicos reales (SMA20/50/200, rango 20d) — calculados, no inventados
    def fmt_tech(name):
        tl = d.get("tech_levels", {}).get(name)
        if not tl:
            return "Dato no disponible"
        sma200_str = f"{tl['sma200']:,.2f}" if tl.get('sma200') else "N/D (histórico insuficiente)"
        vs200_str  = f" ({tl['vs_sma200_pct']:+.2f}% vs SMA200)" if tl.get('vs_sma200_pct') is not None else ""
        return (f"Último: {tl['last']:,.2f}{vs200_str} | SMA20: {tl['sma20']:,.2f} | "
                f"SMA50: {tl['sma50']:,.2f} | SMA200: {sma200_str} | "
                f"Rango 20d: {tl['low_20d']:,.2f} – {tl['high_20d']:,.2f}")

    spx_tech_str = fmt_tech("SPX")
    ndx_tech_str = fmt_tech("NDX")

    # Proxy de Fed Funds (aproximado, NO es CME FedWatch — ver nota en el propio dato)
    ffp = d.get("fed_funds_proxy")
    if ffp:
        fed_proxy_str = (
            f"Fed Funds actual: {ffp['fed_funds_now']:.2f}% | Yield 3M: {ffp['yield_3m']:.2f}% | "
            f"Gap implícito: {ffp['implied_gap_pct']:+.2f}pp → el mercado de bonos a corto plazo "
            f"sugiere expectativa de {ffp['interpretation']} en el horizonte de 3 meses "
            f"(PROXY APROXIMADO basado en yields, no es la probabilidad exacta de CME FedWatch)"
        )
    else:
        fed_proxy_str = "Dato no disponible"

    # Proxy de divergencia de bancos centrales globales (vía pares de divisas, no hay
    # acceso gratuito a decisiones/probabilidades de BCE o BoJ específicamente)
    eurusd_str = fmt_fx('EURUSD') if d.get('EURUSD', {}).get('price') is not None else "Dato no disponible"
    usdjpy_str = fmt_fx('USDJPY') if d.get('USDJPY', {}).get('price') is not None else "Dato no disponible"

    # ESTADO DE LA SESION. Lo que rompio el briefing del 27/08 no fue un dato
    # falso sino una ETIQUETA falsa: con el mercado abierto yfinance da la barra
    # parcial del dia y el prompt afirmaba que era un cierre.
    ses = d.get("sesion") or {}
    if ses.get("en_curso"):
        sesion_str = (
            f"ESTADO DE LA SESION: EN CURSO. Los porcentajes de indices y sectores "
            f"son una foto INTRADIA de la sesion del {ses.get('fecha', 'de hoy')} "
            f"tomada a las {ses.get('hora_et', '??:??')} ET, con el mercado todavia "
            f"abierto. NO son cierres: no escribas que nada 'cerro' ni des la sesion "
            f"por terminada.")
    else:
        # El caso normal se dice en una linea corta: es el que se paga TODOS los
        # dias, y este prompt no cabe en el limite de Groq desde hace semanas.
        # La version larga se reserva para el caso raro, que es el que necesita
        # que se le expliquen las cosas al modelo.
        sesion_str = f"ESTADO DE LA SESION: CERRADA (indices y sectores: cierre del {ses.get('fecha', 'anterior')})."

    # Calendario
    calendar_lines = ""
    eventos = d.get("calendar", [])
    if max_calendario:
        # Ya vienen ordenados por impacto (ver el fix de events[:10] sin
        # ordenar), así que recortar por la cola quita lo menos relevante.
        eventos = eventos[:max_calendario]
    # La columna "Publicado" solo se pinta si ALGUN evento trae ya su dato. En
    # la ejecucion normal (pre-apertura) no ha salido ninguno todavia, y una
    # columna entera de "aun no" son fichas tiradas en un prompt que ya no cabe.
    hay_publicados = any(str(ev.get("actual") or "").strip() for ev in eventos)
    cal_cabecera = ("| Hora (ET) | País | Evento | Publicado | Consenso | Previo | Impacto |" + chr(10) +
                    "|------|------|--------|-----------|----------|--------|---------|") if hay_publicados else (
                   "| Hora (ET) | País | Evento | Consenso | Previo | Impacto |" + chr(10) +
                    "|------|------|--------|----------|--------|---------|")
    for ev in eventos:
        # `actual` se recoge en get_market_data() desde siempre y NO llegaba
        # al prompt: el modelo no podia distinguir un dato YA PUBLICADO de uno
        # que aun no ha salido, que es la diferencia entre narrar un hecho y
        # narrar una expectativa. El 27/08 acerto por los titulares, no por aqui.
        publicado = str(ev.get("actual") or "").strip() or "aún no"
        col_pub = f"{publicado} | " if hay_publicados else ""
        calendar_lines += (
            f"| {ev['time']} ET | {ev.get('pais', '?')} | {ev['event']} | "
            f"{col_pub}{ev.get('forecast', 'N/D')} | {ev.get('previous', 'N/D')} | "
            f"{ev['impact']} |\n"
        )
    if not calendar_lines:
        relleno = " — |" * (cal_cabecera.splitlines()[0].count("|") - 4)
        calendar_lines = "| — | — | Sin eventos de alto impacto para Wall Street hoy |" + relleno + "\n"

    # Fear & Greed
    fg = d.get("fear_greed")
    fg_str = f"{fg['score']}/100 — {fg['rating']} (ayer: {fg['prev']})" if fg else "Dato no disponible"

    # VIX Term Structure
    vix = d.get("vix_term", {})
    vix_spot = vix.get("VIX_SPOT", "N/D")
    vix_3m   = vix.get("VIX_3M", "N/D")
    vix_str  = f"Spot: {vix_spot} | 3M: {vix_3m}"
    if vix_spot and vix_3m and isinstance(vix_spot, float) and isinstance(vix_3m, float):
        structure = "CONTANGO" if vix_3m > vix_spot else "BACKWARDATION"
        vix_str += f" | Estructura: {structure}"

    hy = d.get("hy_spread")
    hy_str = f"{hy:.2f}%" if hy else "Dato no disponible"

    # Noticias reales del día — sin esto el modelo no tiene ni idea de qué
    # está pasando en el mundo, por muy correctos que sean los números
    news_lines = ""
    for n in news:
        news_lines += f"- [{n['time']}, {n['source']}] {n['headline']}"
        if n.get("summary"):
            news_lines += f" — {n['summary']}"
        news_lines += "\n"
    if not news_lines:
        news_lines = "Sin titulares disponibles hoy — no menciones catalizadores de noticias que no estén aquí.\n"

    # Titulares de alto impacto de medios internacionales (Reuters/Bloomberg/
    # WSJ/AP/FT vía GDELT) — complementa el feed de mercado de arriba con
    # eventos de gran impacto que pueden ser ante todo geopolíticos (conflictos,
    # ataques, decisiones políticas mayores) y no aparecer bien en un feed
    # financiero estrecho, aunque tengan consecuencias directas en precios
    # (petróleo, defensa, refugio como oro/USD, volatilidad general vía VIX).
    major_headlines_lines = ""
    for n in major_headlines:
        major_headlines_lines += f"- [{n['time']}, {n['source']}] {n['headline']}\n"
    if not major_headlines_lines:
        major_headlines_lines = "Sin titulares de medios internacionales disponibles hoy — no inventes eventos geopolíticos que no estén aquí.\n"

    # Earnings notables próximos 1-2 días
    earnings_lines = ""
    hour_label = {"bmo": "antes de apertura", "amc": "tras cierre", "": "hora no especificada"}
    for e in earnings:
        earnings_lines += f"- {e['ticker']}: {e['date']} ({hour_label.get(e['hour'], e['hour'])})"
        if e.get("eps_est") is not None:
            earnings_lines += f" — EPS estimado: {e['eps_est']}"
        earnings_lines += "\n"
    if not earnings_lines:
        earnings_lines = "Sin earnings de peso en las próximas 48h.\n"

    # Señales de amplitud propias de RSU: % sobre SMA50 sigue siendo del S&P
    # 500 específicamente. McClellan, ABI y NH-NL ya usan el universo ampliado
    # (S&P 500 + Russell 2000, ~2.480 tickers) — pensado para detectar cuándo
    # el índice sube solo por megacaps mientras el resto del mercado no
    # acompaña, algo que el S&P 500 en solitario no puede ver.
    if breadth:
        # La amplitud NO siempre va por detras de los precios: en la ejecucion
        # normal del cron (03:00 ET) los precios son el cierre de ayer y el
        # escaneo del Scanner tambien, o sea la MISMA sesion. Solo se separan
        # cuando el briefing se lanza con el mercado abierto -- que es lo que
        # paso el 27/08. Asi que se comparan las dos fechas en vez de afirmar
        # una de las dos cosas: dar por hecho "va por detras" seria cambiar una
        # etiqueta falsa por otra.
        # Si el escaneo nocturno vino incompleto, el modelo tiene que SABERLO.
        # OJO al texto: el codigo NO deja huecos, RETROCEDE a la ultima sesion
        # completa -- asi que decir "N/D" aqui seria contradecir a los numeros
        # que tiene justo debajo. Y callarlo tampoco vale: el 25/08, al llegarle
        # la amplitud vacia, escribio que "la herramienta no tiene ese dato".
        aviso_escaneo = (" ⚠️ EL ESCANEO NOCTURNO DE HOY VINO INCOMPLETO: la "
                         "amplitud de abajo es la de la SESIÓN ANTERIOR (mira su "
                         "fecha), no la de hoy. No digas que falta."
                         if breadth.get("escaneo_incompleto") else "")
        fecha_amp = breadth.get("fecha")
        fecha_precios = ses.get("fecha")
        if not fecha_amp:
            cierre_de = "ultimo escaneo nocturno disponible"
        elif fecha_precios and fecha_amp != fecha_precios:
            # Descriptiva no bastaba. El 31/08 el prompt decia "una sesion POR
            # DETRAS de los precios de arriba, que son del 2026-08-31" y el
            # modelo escribio igualmente "solo el 45,5% de las acciones del S&P
            # avanzaron HOY" sobre numeros del viernes. La etiqueta tiene que
            # PROHIBIR el error, no solo describir el desfase -- y de paso sale
            # mas corta, que en este prompt importa.
            cierre_de = (f"AMPLITUD del {fecha_amp}, NO de hoy ({fecha_precios}): "
                         f"no digas «hoy» al citarla")
        else:
            cierre_de = f"cierre del {fecha_amp}, misma sesion que los precios"
        # DE QUE LADO. El 03/09/2026 el prompt decia "% S&P 500 sobre SMA50:
        # 46.6%" y el briefing escribio "el 46,6% de las acciones del S&P 500
        # estan POR DEBAJO de su media movil de 50 dias". Invertido: 46,6% es el
        # porcentaje que esta POR ENCIMA. Dar las dos cifras cuesta ~10 fichas y
        # quita la posibilidad de confundirlas.
        if breadth.get('pct_above_sma50') is not None:
            _pa = breadth['pct_above_sma50']
            pct_s = f"{_pa}% POR ENCIMA (o sea {round(100 - _pa, 1)}% por debajo)"
        else:
            pct_s = "N/D"
        mc_s   = f"{breadth['mcclellan']:+.1f}" if breadth.get('mcclellan') is not None else "N/D (histórico insuficiente todavía)"
        abi_s  = f"{breadth['abi']}%" if breadth.get('abi') is not None else "N/D"
        abi_b  = f" ({breadth['abi_estado']})" if breadth.get('abi_estado') else ""
        # El condicional va FUERA de la f-string: anidar la misma comilla
        # dentro de una f-string solo es legal desde Python 3.12, y el CI
        # corre 3.11 -- en local (3.13) compilaba y alli reventaba el modulo
        # entero al importarlo.
        sp_pct_str = (f" ({breadth['sp500_pct_al_alza']}% al alza)" if breadth.get('sp500_pct_al_alza') is not None else '')
        rsu_breadth_str = (
            f"[{cierre_de}]{aviso_escaneo} % S&P 500 sobre su SMA50: {pct_s} | "
            f"Oscilador McClellan RSU (S&P 500 + Russell 2000): {mc_s}"
            f"{(' (' + breadth['mcclellan_estado'] + '; alcista >+70, bajista <-70)') if breadth.get('mcclellan_estado') else ''} | "
            f"ABI: {abi_s}{abi_b} — mide CUÁNTO se impone un lado, no cuál (≤15 apagado, ≥40 capitulación) | "
            f"New Highs−New Lows: {breadth.get('nh_nl', 'N/D')} "
            f"({breadth.get('new_highs', '?')} vs {breadth.get('new_lows', '?')}) | "
            # Lo que faltaba: avances y descensos DE HOY, y el S&P por separado.
            f"Avances/descensos de la sesión — S&P 500: {breadth.get('sp500_advances', '?')}/"
            f"{breadth.get('sp500_declines', '?')}"
            f"{sp_pct_str}"
            f" · universo completo: {breadth.get('advances', '?')}/{breadth.get('declines', '?')}"
        )
    else:
        rsu_breadth_str = "Dato no disponible (Scanner sin datos frescos)"

    # Clusters de insiders (solo si el backend está desplegado — ver nota en get_insider_clusters)
    insider_lines = ""
    for c in insider_clusters:
        # EL NOMBRE DE LA EMPRESA, que el endpoint ya devuelve (`company`) y se
        # tiraba antes de llegar al prompt -- tercer caso del mismo patron, como
        # el `actual` del calendario y el desglose del S&P. El 31/08/2026 el
        # modelo recibio los tickers DESNUDOS (DKS, AMR, AMRC) y les invento un
        # sector que encajara con la narrativa de Iran que estaba montando:
        # escribio "compra de insiders en energia (DKS, AMR) y defensa/industrial
        # (AMRC)". DKS es Dick's Sporting Goods, una tienda de articulos
        # deportivos. Sobre esa etiqueta inventada construyo la frase "el capital
        # inteligente esta posicionandose para la duracion del conflicto".
        nombre = nombre_corto(c.get("company"))
        et = str(c.get("ticker", "?")) + (f" ({nombre})" if nombre else "")
        insider_lines += f"- {et}: {c.get('n_insiders','?')} insiders comprando, ${c.get('total_value',0):,.0f} total, señal {c.get('signal','')}\n"
    if not insider_lines:
        insider_lines = "Sin datos de Insider Flow disponibles en este ciclo.\n"

    # Memoria de los últimos días — continuidad narrativa real, con texto
    # completo (no solo el sesgo, eso lo cubre bias_history_str aparte)
    briefing_history_str = format_briefing_history(briefing_history, recorte.get("historial"))
    memoria_block = (
        f"""CONTEXTO HISTÓRICO — MEMORIA DE LOS ÚLTIMOS {len(briefing_history)} BRIEFINGS (tus propias notas de días anteriores, más reciente al final):
{briefing_history_str}

De ese historial, ten en cuenta:
1. Tu postura del día más reciente — di explícitamente si mantienes, reduces o cambias esa postura hoy, y por qué. Si el mercado te dio la razón o te la quitó, dilo con naturalidad — "ayer funcionó" o "me equivoqué con el timing, esto es lo que cambio" son frases legítimas, no debilidad.
2. Los niveles técnicos que citaste en esos días — si vuelves a mencionar un nivel de invalidación, sé consistente con lo dicho antes o explica por qué cambia.
3. Las frases de apertura que ya usaste — no repitas la misma fórmula de arranque de un día para otro.

REGLAS DE CONTINUIDAD NARRATIVA:
- No digas "ayer" de algo que pasó hace 2 o 3 días — usa la fecha real de cada entrada del historial para situarte correctamente en el tiempo.
- Mantén el mismo nivel de invalidación técnica de un día a otro salvo que el precio ya lo haya invalidado o superado — en ese caso, dilo explícitamente y da el nuevo nivel.
"""
        if briefing_history else
        "No hay briefings anteriores disponibles (primera ejecución, o el histórico está vacío) — escribe sin referencias a días anteriores.\n"
    )

    macro_lines = ""
    for m in (macro_indicators or []):
        pub = (f"publicado {m['publicado']}, hace {m['edad_dias']} días"
               if m.get("publicado") and m.get("edad_dias") is not None
               else "fecha de publicación desconocida")
        reciente = " ← RECIÉN PUBLICADO" if (m.get("edad_dias") if m.get("edad_dias") is not None else 99) <= 8 else ""
        macro_lines += f"| {m['nombre']} | {m['fecha']} | {pub}{reciente} | {m['dato']} | {m['extra']} |\n"
    if not macro_lines:
        macro_lines = "| — | Sin indicadores macro disponibles | — | — |\n"

    bias_history_str = format_bias_history(bias_history)

    # HECHOS ACTUALES QUE EL MODELO PUEDE TENER DESACTUALIZADOS: bloque de
    # mantenimiento manual — si cambia el chair de la Fed u otro cargo clave
    # que el modelo tienda a mencionar con su nombre "por defecto" desactualizado
    # (visto en producción: mezclaba "Jerome" con "Warsh", el chair actual real
    # desde el 22-may-2026, porque el training del modelo es anterior al cambio),
    # actualiza la lista de abajo.
    prompt = f"""{_reglas_de_estilo()}

HECHOS ACTUALES QUE TU ENTRENAMIENTO PUEDE TENER DESACTUALIZADOS (verificado externamente, no lo cuestiones ni lo "corrijas" a un nombre que te suene más familiar):
- El actual presidente (Chair) de la Reserva Federal es Kevin Warsh, NO Jerome Powell — Warsh tomó posesión el 22 de mayo de 2026, sucediendo a Powell. Si mencionas al presidente de la Fed, es "Warsh" o "Kevin Warsh", nunca "Jerome Warsh" ni "Jerome Powell" en el cargo actual (Powell sigue en el consejo de gobernadores, pero ya no es el chair).


{memoria_block}

TU SESGO DE LOS ÚLTIMOS DÍAS (para dar contexto de tendencia, p.ej. "llevamos N sesiones en el mismo sesgo" si aplica — no lo fuerces si no aporta nada hoy):
{bias_history_str}

DATOS REALES DE MERCADO HOY ({d['date']} — {d['time']}):
{sesion_str}

ÍNDICES:
- S&P 500: {fmt('SPX')}
- Nasdaq 100: {fmt('NDX')}
- Russell 2000: {fmt('RUT')}
- VIX: {fmt('VIX')}
- Dólar Index (DXY): {fmt('DXY')}
- Yield 10Y: {fmt_yield('TNX')}
- Yield 30Y: {fmt_yield('TYX')}
- Oro: {fmt('GOLD')}
- Petróleo WTI: {fmt('WTI')}
- Bitcoin: {fmt('BTC')}

FUTUROS PRE-MARKET (gap real vs cierre anterior, hora del dato indicada arriba):
{futures_str}

NIVELES TÉCNICOS CALCULADOS (medias móviles y rango — NO inventes otros niveles, usa solo estos):
- S&P 500: {spx_tech_str}
- Nasdaq 100: {ndx_tech_str}

POLÍTICA MONETARIA — DATOS DISPONIBLES (usa solo esto, no inventes probabilidades exactas de FedWatch):
- Proxy de expectativas Fed Funds: {fed_proxy_str}
- EUR/USD: {eurusd_str} (proxy indirecto de divergencia BCE vs Fed)
- USD/JPY: {usdjpy_str} (proxy indirecto de divergencia BoJ vs Fed)

SECTORES S&P 500 (1D / 5D):
| ETF | Sector | 1D | 5D |
|-----|--------|----|----|
{sector_lines}

SENTIMIENTO:
- Fear & Greed Index: {fg_str}
- VIX Term Structure: {vix_str}
- High Yield Spread (OAS): {hy_str}

SEÑALES PROPIAS DE RSU (amplitud calculada sobre vuestro propio universo — S&P 500 + Russell 2000 para McClellan/ABI/NH-NL, S&P 500 para el % sobre SMA50 — dales protagonismo, es lo que os diferencia de cualquier newsletter macro genérica):
{rsu_breadth_str}

INSIDER FLOW — CLUSTERS DE COMPRA RECIENTES:
{insider_lines}

ÚLTIMOS INDICADORES MACRO PUBLICADOS (FRED — datos REALES ya publicados, no previsiones). Las variaciones vienen ya calculadas: cítalas tal cual, nunca el nivel del índice en crudo. Ojo a las DOS fechas, que no son lo mismo: el PERIODO al que se refiere el dato y el día en que se PUBLICÓ. El IPC de junio salió a mediados de julio. Lo marcado "RECIÉN PUBLICADO" es noticia reciente y puedes tratarlo como tal; el resto es contexto de fondo y NO puedes presentarlo como si acabara de salir:
| Indicador | Periodo del dato | Publicación | Último | Referencia |
|-----------|------------------|-------------|--------|------------|
{macro_lines}
CALENDARIO ECONÓMICO HOY:
{cal_cabecera}
{calendar_lines}

EARNINGS NOTABLES PRÓXIMAS 48H:
{earnings_lines}

TITULARES REALES DE MERCADO (últimas ~24-30h — usa 2-3 de los más relevantes para el mercado, no los enumeres todos, teje solo los que de verdad importan para el sesgo de hoy):
{news_lines}

TITULARES DE ALTO IMPACTO — MEDIOS INTERNACIONALES (Reuters/Bloomberg/WSJ/AP/FT, últimas 24h): estos pueden ser noticias GEOPOLÍTICAS o de otro tipo (conflictos, ataques, decisiones políticas mayores) que no son "económicas" en sentido estricto pero SÍ mueven mercado (petróleo, defensa, refugio, volatilidad general). Si hay algo aquí con impacto real de mercado hoy — aunque no sea una noticia financiera clásica — mencionalo explícitamente y conecta por qué le importa a un trader (qué activo concreto mueve, por qué):
{major_headlines_lines}

{"⚠️ AVISO CRÍTICO: hoy NO hay NINGÚN titular real disponible, ni de mercado ni de medios internacionales — ambas fuentes fallaron. Esto significa que NO puedes mencionar ningún evento, declaración, testimonio, comparecencia, decisión de un banco central o nombre de cargo público concreto (ni siquiera uno que 'suene plausible' como agenda conocida) salvo que ya esté en los DATOS DE MERCADO numéricos de arriba (yields, VIX, futuros, niveles técnicos). Si necesitas explicar el movimiento del día, explícalo SOLO con esos datos técnicos y de amplitud — flujos, rotación sectorial, niveles rotos, tipos — nunca con un catalizador narrativo inventado. Es preferible una nota más técnica y menos narrativa que una nota fluida con datos falsos." if (not news_lines.strip() or news_lines.startswith("Sin titulares")) and (not major_headlines_lines.strip() or major_headlines_lines.startswith("Sin titulares")) else ""}

---

{_cierre_y_estructura()}"""

    return prompt

# ── LLAMAR A GROQ ─────────────────────────────────────────────────────────────

def _diagnostico_ratelimit(r) -> dict:
    """Lo que Groq dice de VERDAD sobre el presupuesto, leído de la respuesta.

    Dos preguntas que hasta ahora se contestaban de memoria o leyendo la
    documentación, y que la propia respuesta ya trae gratis en cada llamada:

      1. ¿Cuál es el límite real de TPM de esta cuenta? Está en la cabecera
         `x-ratelimit-limit-tokens`. GROQ_TPM_LIMIT es un 8000 copiado de la
         tabla pública del tier; si el límite real fuera mayor, el recorte
         progresivo de datos estaría degradando el briefing para nada.
      2. ¿Cuánto se desvía mi estimación por caracteres del tokenizador real?
         Está en `usage.prompt_tokens`. El 31/07/2026 el desvío fue del 13%
         (estimé 5744, Groq contó 6601) y CHARS_POR_TOKEN se recalibró a mano
         con esa única medición. Registrarlo en cada ejecución convierte esa
         calibración puntual en una serie.

    Se lee también en el camino del 413 -- ahí no hay `usage`, pero las
    cabeceras sí vienen, que es justo cuando más interesa saber el límite.
    """
    h = r.headers
    diag = {
        "tpm_limite_real":    h.get("x-ratelimit-limit-tokens"),
        "tpm_restante":       h.get("x-ratelimit-remaining-tokens"),
        "rpm_limite_real":    h.get("x-ratelimit-limit-requests"),
        "tokens_estimados":   None,
        "tokens_reales":      None,
        "desvio_estimacion":  None,
    }
    try:
        uso = r.json().get("usage") or {}
        diag["tokens_reales"] = uso.get("prompt_tokens")
    except Exception:
        pass
    return diag


def generate_briefing(prompt: str, reintento_de_corte: bool = False) -> tuple:
    """Devuelve (texto_del_briefing, diagnóstico). El diagnóstico sale de la
    propia respuesta de Groq -- ver _diagnostico_ratelimit.

    `reintento_de_corte` lo pone la propia función al volver a intentarlo
    cuando la respuesta salió truncada: sirve para no encadenar reintentos
    indefinidos si el segundo tampoco cabe."""
    if not GROQ_KEY:
        raise ValueError("GROQ_API_KEY no configurada")

    # Techo de salida calculado a partir de lo que queda libre tras el prompt,
    # en vez de un 3000 fijo que ignoraba el tamaño del prompt y desbordaba el
    # límite de 8000 TPM (ver comentario en GROQ_TPM_LIMIT). Si algún día el
    # prompt crece tanto que no cabe ni el mínimo, se falla AQUÍ con un
    # mensaje que dice exactamente qué recortar — no con un 413 opaco de Groq.
    prompt_tokens = estimar_tokens(prompt)
    disponible    = GROQ_TPM_LIMIT - GROQ_TPM_SAFETY - prompt_tokens
    max_salida    = min(GROQ_MAX_OUTPUT, disponible)

    # La longitud que se le pide al modelo sale del hueco real, no de una cifra
    # escrita a mano (ver palabras_que_caben). Se sustituye aquí y no en
    # build_prompt porque es aquí donde se sabe cuánto espacio ha quedado tras
    # el recorte progresivo de datos.
    #
    # La sustitución cambia el prompt en unos pocos caracteres, así que se
    # vuelve a medir: si no, el presupuesto se calcularía sobre un texto que ya
    # no es el que se envía.
    if MARCA_LONGITUD in prompt:
        prompt = prompt.replace(MARCA_LONGITUD, instruccion_longitud(max_salida))
        prompt_tokens = estimar_tokens(prompt)
        disponible    = GROQ_TPM_LIMIT - GROQ_TPM_SAFETY - prompt_tokens
        max_salida    = min(GROQ_MAX_OUTPUT, disponible)

    print(f"🧮 Presupuesto Groq: prompt ~{prompt_tokens} tokens · respuesta hasta {max_salida} "
          f"(límite {GROQ_TPM_LIMIT} TPM) · se piden {instruccion_longitud(max_salida)}")
    if max_salida < GROQ_MIN_OUTPUT:
        # Llegar aquí significa que ni el nivel de recorte MÍNIMO ha bastado
        # (main() los prueba todos antes de llamar a esta función), así que ya
        # no es cuestión de datos: el problema está en las instrucciones fijas,
        # que son el 53% del prompt. Por eso el mensaje ya no dice "recorta el
        # historial" -- eso el script lo ha intentado solo.
        raise ValueError(
            f"El prompt (~{prompt_tokens} tokens) deja solo {max_salida} tokens para la respuesta, "
            f"por debajo del mínimo de {GROQ_MIN_OUTPUT}. El recorte progresivo de datos ya se ha "
            f"agotado (ver NIVELES_RECORTE), así que lo que sobra son INSTRUCCIONES fijas: "
            f"hay que comprimir _ESTILO_V2 / las reglas anti-alucinación, o subir el límite de TPM."
        )

    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {GROQ_KEY}",
            "Content-Type":  "application/json",
        },
        json={
            "model":            MODEL,
            "messages":         [{"role": "user", "content": prompt}],
            "max_tokens":       max_salida,
            "temperature":      0.45,
            # Qwen3.6-27B soporta modo "pensador" (reasoning) y modo directo.
            # Esta tarea es sintetizar datos ya dados en prosa fluida en un
            # tono concreto — no resolver un problema lógico complejo — así
            # que no se beneficia de razonamiento paso a paso, y desactivarlo
            # resuelve DOS problemas a la vez en su raíz, en vez de ir
            # ajustando max_tokens a ciegas cada vez que falla algo distinto:
            #   1) El pensamiento interno de este modelo suele salir en
            #      inglés, y aunque se oculte del texto visible con
            #      reasoning_format="hidden", sigue contando dentro del
            #      presupuesto de max_tokens — con un límite bajo, se podía
            #      agotar todo pensando y no dejar nada para la respuesta
            #      real (de ahí un briefing de 0 palabras en un intento).
            #   2) Groq limita a 8000 tokens/minuto (entrada+salida) para
            #      este modelo en el tier gratuito — sin pensamiento interno
            #      de por medio no hay que competir por presupuesto entre
            #      "pensar" y "escribir". (El prompt ha crecido bastante
            #      desde que se escribió esto: el reparto del presupuesto
            #      lo lleva ahora max_salida, calculado arriba.)
            "reasoning_effort": "none",
            "reasoning_format": "hidden",  # inofensivo con reasoning_effort=none, pero no estorba dejarlo
        },
        timeout=120,
    )

    # 413 = el prompt no cabe en el presupuesto de TPM. NO es un error
    # cualquiera: es exactamente la condición que sabemos degradar, así que se
    # distingue del resto para que main() reintente con un recorte más
    # agresivo en vez de morirse.
    #
    # Por qué hace falta esto y no basta con afinar la constante: el 31/07/2026
    # el script calculó ~5744 tokens de prompt y Groq contó 6601 (pidió 8401
    # con los 1800 de respuesta). Un 13% de desvío. Se ha recalibrado
    # CHARS_POR_TOKEN con esa medición, pero CUALQUIER estimación por
    # caracteres se va a desviar del tokenizador real -- la única fuente de
    # verdad es la respuesta de Groq, así que hay que saber reaccionar a ella.
    diag = _diagnostico_ratelimit(r)
    diag["tokens_estimados"] = prompt_tokens
    if diag["tpm_limite_real"]:
        print(f"📉 Groq dice: límite real {diag['tpm_limite_real']} TPM "
              f"(el script asume {GROQ_TPM_LIMIT}) · restante {diag['tpm_restante']}")

    if r.status_code == 413:
        raise PromptDemasiadoGrande(f"Groq 413: {r.text[:200]}")
    if r.status_code != 200:
        raise ValueError(f"Groq error {r.status_code}: {r.text[:200]}")

    if diag["tokens_reales"]:
        desvio = (diag["tokens_reales"] - prompt_tokens) / prompt_tokens * 100
        diag["desvio_estimacion"] = round(desvio, 1)
        # CHARS_POR_TOKEN que habría clavado la cuenta de hoy. Si sale muy
        # distinto del valor vigente varios días seguidos, hay que ajustarlo:
        # estimar de menos provoca 413 y estimar de más recorta datos que sí
        # cabían.
        ideal = len(prompt) / diag["tokens_reales"]
        print(f"🧾 Groq contó {diag['tokens_reales']} tokens de prompt, yo estimé "
              f"{prompt_tokens} ({desvio:+.1f}%) · CHARS_POR_TOKEN exacto de hoy: "
              f"{ideal:.2f} (vigente {CHARS_POR_TOKEN})")

    eleccion = r.json()["choices"][0]
    texto    = eleccion["message"]["content"]
    motivo   = eleccion.get("finish_reason")
    diag["finish_reason"] = motivo

    # `finish_reason == "length"` significa que el modelo se quedó sin espacio
    # y la respuesta está cortada -- normalmente a mitad de frase, y siempre sin
    # la línea "SESGO:" del final, que además hace perder el registro del día.
    #
    # Hasta ahora nadie miraba este campo, así que un briefing truncado se
    # publicaba con la misma cara que uno entero. Es el mismo patrón que este
    # proyecto lleva tiempo quitando: un resultado a medias servido como bueno.
    if motivo == "length" and reintento_de_corte:
        # Ya es el segundo intento: se publica lo que hay (mejor medio briefing
        # que ninguno, que es lo que se decidió en julio) pero queda anotado.
        print(f"⚠️  El briefing SIGUE saliendo cortado tras reintentar con menos "
              f"longitud. Se publica igualmente, pero revisa el presupuesto: "
              f"prompt ~{prompt_tokens} tok, respuesta {max_salida} tok.")
        diag["truncado"] = True
        return texto, diag

    if motivo == "length":
        # Se reintenta pidiendo bastante menos. La espera no es opcional: el
        # límite de Groq es por MINUTO y acabamos de gastar casi todo, así que
        # llamar de inmediato solo daría un 429.
        recorte = int(max_salida * 0.75)
        print(f"⚠️  Respuesta cortada por falta de espacio ({max_salida} tokens). "
              f"Reintentando con un objetivo más corto en 65 s (el límite de Groq "
              f"es por minuto y acabamos de agotarlo).")
        time.sleep(65)
        prompt_corto = prompt
        if MARCA_LONGITUD not in prompt_corto:
            # El prompt ya trae la longitud sustituida del intento anterior: se
            # cambia esa frase por la nueva en vez de volver a construirlo.
            prompt_corto = prompt_corto.replace(instruccion_longitud(max_salida),
                                                instruccion_longitud(recorte))
        return generate_briefing(prompt_corto, reintento_de_corte=True)

    diag["truncado"] = False
    return texto, diag


def extract_bias_tag(text: str) -> tuple:
    """Separa la etiqueta final 'SESGO: ALCISTA/BAJISTA/NEUTRAL' del cuerpo
    del briefing. Devuelve (texto_sin_etiqueta, sesgo). Se pide al modelo en
    un formato fijo en vez de intentar adivinar el sesgo con regex sobre
    texto libre — mucho más fiable para alimentar el registro de sesgo."""
    import re
    match = re.search(r'\n*SESGO:\s*(ALCISTA|BAJISTA|NEUTRAL)\s*$', text.strip(), re.IGNORECASE)
    if not match:
        return text.strip(), None
    bias = match.group(1).upper()
    clean_text = text[:match.start()].strip()
    return clean_text, bias

# ── REGISTRO DE SESGO (memoria ligera de varios días) ─────────────────────────

def get_bias_history() -> list:
    """Lee el registro compacto de sesgo de los últimos días — fecha + sesgo,
    nada de texto completo. Vive en un fichero aparte dentro del mismo Gist."""
    if not GIST_TOKEN:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code != 200:
            return []
        content = r.json()["files"].get(BIAS_HISTORY_FILE, {}).get("content", "")
        if not content:
            return []
        history = json.loads(content)
        return history if isinstance(history, list) else []
    except Exception as e:
        print(f"⚠️  No se pudo leer el registro de sesgo: {e}")
        return []


def get_bias_tracking() -> list:
    """Seguimiento acumulado del sesgo. Vive en el mismo Gist que el briefing,
    en su propio fichero: no se poda nunca."""
    if not GIST_TOKEN:
        return []
    try:
        r = requests.get(
            f"https://api.github.com/gists/{GIST_ID}",
            headers={"Authorization": f"token {GIST_TOKEN}", "Accept": "application/vnd.github+json"},
            timeout=10,
        )
        if r.status_code != 200:
            print(f"⚠️  No se pudo leer el seguimiento del sesgo: HTTP {r.status_code}")
            return []
        contenido = r.json()["files"].get(BIAS_TRACKING_FILE, {}).get("content", "")
        datos = json.loads(contenido) if contenido else []
        return datos if isinstance(datos, list) else []
    except Exception as e:
        print(f"⚠️  No se pudo leer el seguimiento del sesgo: {type(e).__name__}: {e}")
        return []


def _append_bias(history: list, date: str, bias: str) -> list:
    """Añade la entrada de hoy y poda a los últimos BIAS_HISTORY_DAYS — así
    el fichero nunca crece sin límite, siempre son como mucho ~14 líneas."""
    history = [h for h in history if h.get("date") != date]  # evita duplicado si se re-ejecuta el mismo día
    history.append({"date": date, "bias": bias})
    history.sort(key=lambda h: h["date"])
    return history[-BIAS_HISTORY_DAYS:]


def format_bias_history(history: list) -> str:
    if not history:
        return "Sin registro de días anteriores todavía (primera ejecución de esta función)."
    return " | ".join(f"{h['date']}: {h['bias']}" for h in history)

# ── GUARDAR EN GIST ───────────────────────────────────────────────────────────

def evaluar_sesgos(tracking: list, bias_history: list, cierres) -> list:
    """¿Acertó el sesgo de cada día? Devuelve el seguimiento actualizado.

    `cierres` es una serie de cierres del S&P 500 indexada por fecha.

    REGLAS, y todas nacen de lo aprendido midiendo Options Flow:
    - NEUTRAL no se evalúa: no hay dirección que juzgar, y contarlo como
      fallo (o como acierto) inventaría un resultado.
    - Un día al que aún no le han pasado las sesiones del horizonte queda
      PENDIENTE, no cuenta como fallo.
    - Nada se reescribe: un resultado ya calculado no cambia.
    """
    import pandas as pd
    por_fecha = {t["fecha"]: t for t in tracking}
    for h in bias_history:
        f = h.get("fecha") or h.get("date")
        if f and f not in por_fecha:
            por_fecha[f] = {"fecha": f, "sesgo": (h.get("sesgo") or h.get("bias") or "N/D").upper()}

    for t in por_fecha.values():
        if t["sesgo"] not in ("ALCISTA", "BAJISTA"):
            continue
        if cierres is None or len(cierres) == 0:
            continue
        idx = cierres.index
        posteriores = idx[idx >= pd.Timestamp(t["fecha"])]
        if len(posteriores) == 0:
            continue
        pos = idx.get_loc(posteriores[0])
        for dias in (1, 5):
            campo = f"ret_{dias}d"
            if t.get(campo) is not None:
                continue
            if pos + dias >= len(cierres):
                continue          # todavía no ha pasado: pendiente, no fallo
            p0, p1 = float(cierres.iloc[pos]), float(cierres.iloc[pos + dias])
            if p0 <= 0:
                continue
            ret = round((p1 - p0) / p0 * 100, 2)
            t[campo] = ret
            t[f"acierto_{dias}d"] = bool((ret > 0) == (t["sesgo"] == "ALCISTA"))
    return sorted(por_fecha.values(), key=lambda x: x["fecha"])


def construir_datos(market_data: dict, news=None, major_headlines=None) -> dict:
    """El bloque auditable: con que numeros y con que titulares se escribio.

    Los TITULARES tambien, y por el mismo motivo que las barras: el 02/09/2026
    se descubrio que GDELT devolvia prensa local canadiense en el bloque de
    "medios internacionales", y no habia forma de saber desde cuando porque los
    titulares no se guardaban en ningun sitio."""
    def _t(lista):
        return [{"fuente": x.get("source", ""), "hora": x.get("time", ""),
                 "titular": x.get("headline", "")} for x in (lista or [])]
    return {
        "fecha":    market_data.get("date"),
        "sesion":   market_data.get("sesion"),
        "barras":   market_data.get("barras"),
        "indices":  {k: market_data.get(k) for k in
                     ("SPX", "NDX", "RUT", "VIX", "TNX", "TYX", "DXY", "WTI", "GOLD")
                     if isinstance(market_data.get(k), dict)},
        "sectores": market_data.get("sectors"),
        "titulares_mercado": _t(news),
        "titulares_medios":  _t(major_headlines),
    }


def construir_payload(content: str, market_data: dict, bias, nivel_usado, diag,
                       news=None, major_headlines=None) -> dict:
    """Lo que se publica en el Gist. Vive fuera de main() a proposito.

    La primera version construia este diccionario inline, y el test que
    comprobaba que `barras` acaba en el fichero solo podia mirar el TEXTO del
    fuente -- asi que el sabotaje de poner `"barras": None` se le escapo, porque
    la cadena `"barras":` seguia estando. Es la tercera vez en esta semana que
    comprobar una regla contra su propia silueta en el codigo deja pasar el
    sabotaje; una funcion que se puede ejecutar no tiene ese problema."""
    return {
        "text":   content,
        "date":   market_data["date"],
        "time":   market_data["time"],
        "model":  MODEL,
        "source": "Groq + Qwen3.6 27B",
        "bias":   bias,
        # Con que se escribio el briefing de hoy. Hasta ahora esto solo existia
        # en los registros del GitHub Action, que no lee nadie -- y el nivel de
        # recorte importa: en "agresivo" el modelo ve 3 titulares por fuente en
        # vez de 5 y un calendario podado, asi que un briefing mas pobre de lo
        # normal tiene una explicacion registrada en vez de parecer que el
        # modelo tuvo un mal dia.
        "diagnostico": {
            "nivel_recorte":  (nivel_usado or {}).get("nombre"),
            "historial_chars": (nivel_usado or {}).get("historial"),
            "titulares_por_fuente": (nivel_usado or {}).get("titulares"),
            **(diag or {}),
        },
        # CON QUE NUMEROS Y QUE TITULARES SE ESCRIBIO. Sin esto, auditar algo
        # raro al dia siguiente es adivinar: los precios de yfinance ya han
        # cambiado y la ventana de `period="5d"` se ha desplazado. `barras` dice
        # las DOS fechas que se compararon para sacar cada variacion.
        "datos": construir_datos(market_data, news, major_headlines),
    }


def resumen_sesgos(tracking: list) -> dict:
    """Aciertos con la muestra siempre al lado. Por debajo de MIN_MUESTRA_SESGO
    no se presenta como una conclusión: un 70% sobre 7 días no es un 70%."""
    evaluables = [t for t in tracking if t.get("sesgo") in ("ALCISTA", "BAJISTA")]
    out = {"dias_registrados": len(tracking), "horizontes": {}}
    for dias in (1, 5):
        con = [t for t in evaluables if t.get(f"acierto_{dias}d") is not None]
        aciertos = sum(1 for t in con if t[f"acierto_{dias}d"])
        out["horizontes"][str(dias)] = {
            "n": len(con),
            "aciertos_pct": round(aciertos / len(con) * 100, 1) if con else None,
            "suficiente": len(con) >= MIN_MUESTRA_SESGO,
        }
    out["pendientes"] = len(evaluables) - len(
        [t for t in evaluables if t.get("acierto_5d") is not None])
    out["neutrales"] = len(tracking) - len(evaluables)
    return out


def leer_datos_archivados() -> list:
    """El archivo de auditoria que ya hay en el Gist. Si no se puede leer se
    empieza de cero: perder archivo es malo, pero no publicar el briefing por
    ello seria peor."""
    try:
        r = requests.get(f"https://api.github.com/gists/{GIST_ID}", timeout=10,
                         headers={"Authorization": f"token {GIST_TOKEN}"} if GIST_TOKEN else {})
        if r.status_code != 200:
            print(f"⚠️  No se pudo leer el archivo de datos (HTTP {r.status_code}) — se empieza de cero")
            return []
        f = r.json().get("files", {}).get(DATOS_FILE)
        return json.loads(f["content"]) if f else []
    except Exception as e:
        print(f"⚠️  No se pudo leer el archivo de datos: {e} — se empieza de cero")
        return []


def save_to_gist(content: str, market_data: dict, bias: str, bias_history: list, briefing_history: list,
                  nivel_usado: dict = None, diag: dict = None, bias_tracking: list = None,
                  news: list = None, major_headlines: list = None):
    if not GIST_TOKEN:
        raise ValueError("GIST_TOKEN no configurado")

    payload = construir_payload(content, market_data, bias, nivel_usado, diag,
                                news, major_headlines)

    # Archivo de auditoria, podado a los ultimos DATOS_DIAS dias.
    datos_archivo = podar_datos(leer_datos_archivados(), payload["datos"])
    print(f"🗃️  Archivo de datos: {len(datos_archivo)} días guardados ({len(json.dumps(datos_archivo, ensure_ascii=False)) // 1024} KB)")

    updated_history = _append_bias(bias_history, market_data["date"], bias or "N/D")

    # Seguimiento del sesgo: ¿acierta? Se evalúa con los cierres del S&P 500 y
    # se guarda aparte, sin podar. Un fallo aquí no puede tumbar la publicación
    # del briefing, que es lo que la gente lee.
    tracking_actualizado = bias_tracking or []
    try:
        import yfinance as _yf
        hist = _yf.Ticker("^GSPC").history(period="6mo")
        cierres = hist["Close"] if not hist.empty else None
        if cierres is not None and getattr(cierres.index, "tz", None) is not None:
            cierres.index = cierres.index.tz_localize(None)
        tracking_actualizado = evaluar_sesgos(tracking_actualizado, updated_history, cierres)
        r_sesgo = resumen_sesgos(tracking_actualizado)
        payload["sesgo_track"] = r_sesgo
        print(f"📊 Sesgo: {r_sesgo['horizontes']['1']['n']} días evaluados a 1 sesión, "
              f"{r_sesgo['horizontes']['1']['aciertos_pct']}% de aciertos")
    except Exception as e:
        print(f"⚠️  Seguimiento del sesgo no actualizado: {type(e).__name__}: {e}")
    updated_briefing_history = _append_briefing_history(briefing_history, market_data["date"], content, bias)

    r = requests.patch(
        f"https://api.github.com/gists/{GIST_ID}",
        headers={
            "Authorization": f"token {GIST_TOKEN}",
            "Accept":        "application/vnd.github+json",
        },
        json={
            "files": {
                "briefing.json": {
                    "content": json.dumps(payload, ensure_ascii=False, indent=2)
                },
                BIAS_HISTORY_FILE: {
                    "content": json.dumps(updated_history, ensure_ascii=False, indent=2)
                },
                BRIEFING_HISTORY_FILE: {
                    "content": json.dumps(updated_briefing_history, ensure_ascii=False, indent=2)
                },
                BIAS_TRACKING_FILE: {
                    "content": json.dumps(tracking_actualizado, ensure_ascii=False, indent=2)
                },
                DATOS_FILE: {
                    "content": json.dumps(datos_archivo, ensure_ascii=False, indent=2)
                }
            }
        },
        timeout=30,
    )

    if r.status_code not in (200, 201):
        raise ValueError(f"Gist error {r.status_code}: {r.text[:200]}")

    print(f"✅ Briefing guardado en Gist: {r.json()['html_url']}")

# ── MAIN ──────────────────────────────────────────────────────────────────────

def main():
    print(f"🕐 Generando briefing — {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")

    print("📰 Leyendo el historial de los últimos 3 briefings (memoria narrativa)...")
    briefing_history = get_briefing_history()

    print("📊 Leyendo registro de sesgo de los últimos días...")
    bias_history = get_bias_history()

    print("📊 Recopilando datos de mercado...")
    market_data = get_market_data()

    print("📰 Recopilando titulares reales del día...")
    news = get_market_news()

    print("🌍 Recopilando titulares de alto impacto (Reuters/Bloomberg/WSJ/AP/FT vía GDELT)...")
    major_headlines = get_major_outlet_headlines()
    if not major_headlines:
        print("🔁 GDELT no devolvió nada — probando respaldo con RSS directo (BBC/WSJ/Al Jazeera)...")
        major_headlines = get_rss_fallback_headlines()

    print("📅 Recopilando earnings notables (próximas 48h)...")
    earnings = get_notable_earnings()

    print("📈 Leyendo señales de amplitud propias de RSU (Scanner Gist)...")
    breadth = get_rsu_breadth_signals()

    print("🔍 Leyendo clusters de Insider Flow (si el backend está desplegado)...")
    insider_clusters = get_insider_clusters()

    print("🤖 Construyendo prompt...")
    print("📈 Descargando indicadores macro publicados (FRED)...")
    macro_indicators = get_macro_indicators()

    # Recorte progresivo hasta que el prompt quepa DE VERDAD.
    #
    # Dos vueltas de este problema en dos días:
    #   30/07 — el prompt se pasó del techo y el script abortaba sin más, así
    #           que no hubo briefing. De ahí NIVELES_RECORTE.
    #   31/07 — el prompt pasó MI comprobación (~5744 tok estimados) pero Groq
    #           contó 6601 y devolvió 413. Recortar según una estimación por
    #           caracteres no basta: hay que reaccionar también al veredicto
    #           real de la API.
    #
    # Por eso construir y llamar viven en el MISMO bucle: cada nivel se
    # comprueba primero contra la estimación (barato, evita una llamada
    # condenada) y, si pasa, contra Groq. Un 413 baja al siguiente nivel igual
    # que lo haría una estimación por encima del techo.
    raw_briefing, nivel_usado, diag = None, None, {}
    for i, nivel in enumerate(NIVELES_RECORTE):
        prompt = build_prompt(market_data, news, major_headlines, earnings, breadth,
                              insider_clusters, briefing_history, bias_history,
                              macro_indicators, recorte=nivel)
        tokens = estimar_tokens(prompt)
        if tokens > TECHO_PROMPT and i < len(NIVELES_RECORTE) - 1:
            print(f"✂️  Nivel '{nivel['nombre']}': ~{tokens} tok, por encima del techo "
                  f"({TECHO_PROMPT}) — probando el siguiente recorte")
            continue
        print(f"{'✂️ ' if i > 0 else '📏'} Nivel '{nivel['nombre']}' (~{tokens} tok): historial "
              f"{nivel['historial']} chars, {nivel['titulares']} titulares por fuente, "
              f"calendario {nivel['calendario'] or 'completo'}")
        print(f"🧠 Llamando a {MODEL} via Groq...")
        try:
            raw_briefing, diag = generate_briefing(prompt)
            nivel_usado = nivel
            break
        except PromptDemasiadoGrande as e:
            # Groq no está de acuerdo con mi cuenta. Manda Groq.
            if i == len(NIVELES_RECORTE) - 1:
                raise ValueError(
                    f"Groq rechaza el prompt por tamaño incluso en el nivel de recorte más "
                    f"agresivo. Ya no es cuestión de datos: lo que sobra son INSTRUCCIONES "
                    f"fijas (el 53% del prompt, medido el 31/07/2026) — hay que comprimir "
                    f"_ESTILO_V2 / las reglas anti-alucinación, o subir el límite de TPM. {e}"
                ) from e
            print(f"⚠️  Groq devolvió 413 con el nivel '{nivel['nombre']}' pese a que mi "
                  f"estimación decía ~{tokens} tok — bajando un nivel de recorte")

    briefing, bias = extract_bias_tag(raw_briefing)
    print(f"📌 Sesgo detectado hoy: {bias or 'N/D (el modelo no incluyó la etiqueta)'}")

    # Si el modelo se queda sin presupuesto de tokens pensando (ver nota en
    # generate_briefing) puede devolver un texto vacío o casi vacío — mejor
    # que el Action falle con un error claro que guardar un briefing en
    # blanco en el Gist sin que nadie se entere hasta que un usuario lo vea.
    if len(briefing.split()) < 50:
        raise ValueError(
            f"El briefing generado tiene solo {len(briefing.split())} palabras — probablemente "
            f"el modelo agotó el presupuesto de tokens pensando y no llegó a escribir la respuesta. "
            f"No se guarda en el Gist. Respuesta cruda recibida: {raw_briefing[:300]!r}"
        )

    print("💾 Guardando en GitHub Gist...")
    bias_tracking = get_bias_tracking()
    save_to_gist(briefing, market_data, bias, bias_history, briefing_history, nivel_usado, diag,
                 bias_tracking=bias_tracking, news=news, major_headlines=major_headlines)

    print("✅ Briefing completado")
    print(f"📝 Palabras generadas: {len(briefing.split())}")

if __name__ == "__main__":
    main()