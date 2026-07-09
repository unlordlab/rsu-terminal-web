import pandas as pd
import re
from datetime import datetime
from config import settings

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVyU3x2DEQVczsqgmUwMSS1SS99Npe8LO-Om5n-VmXKuT-PYxuX65YinMg5XcGZehYE2df6jQuCzTo/pub?output=csv"

REQUIRED_COLS = ['ticker', 'rating', 'fecha']

RATING_CONFIG = {
    "BUY":  {"color": "#00ffad", "label": "BUY"},
    "SELL": {"color": "#f23645", "label": "SELL"},
    "HOLD": {"color": "#ff9800", "label": "HOLD"},
}

def _get_rating_cfg(rating: str) -> dict:
    r = (rating or '').upper()
    if "BUY"  in r: return RATING_CONFIG["BUY"]
    if "SELL" in r: return RATING_CONFIG["SELL"]
    return RATING_CONFIG["HOLD"]

def _safe_str(val) -> str:
    if val is None: return ""
    try:
        if pd.isna(val): return ""
    except Exception: pass
    return str(val).strip()

_DRIVE_FILE_ID_RE = re.compile(r"/file/d/([a-zA-Z0-9_-]+)")
_DRIVE_OPEN_ID_RE = re.compile(r"[?&]id=([a-zA-Z0-9_-]+)")

def _normalize_doc_url(url: str) -> str:
    """Convierte la URL que se pegue en la columna 'urldoc' del Sheet al
    formato que sí funciona embebido en un iframe:
    - Google Docs publicado ('Publicar en la web', URL con /pub) -> añade
      ?embedded=true.
    - Google Drive (PDF u otro archivo subido, URL con /view o /open?id=...,
      lo típico al copiar el enlace de "Compartir") -> se reescribe a
      /file/d/{ID}/preview, que es la única variante de Drive pensada para
      incrustarse en un iframe. Así no hace falta acordarse de cambiar la
      URL a mano cada vez — se pega el enlace de "Compartir" tal cual.
    Si no reconoce el formato, la deja tal cual (por si ya es una URL de
    preview correcta, o cualquier otro visor).
    """
    if not url:
        return url

    if "/pub" in url and "docs.google.com" in url:
        return url.split("?")[0].split("&")[0] + "?embedded=true"

    if "drive.google.com" in url:
        m = _DRIVE_FILE_ID_RE.search(url) or _DRIVE_OPEN_ID_RE.search(url)
        if m:
            return f"https://drive.google.com/file/d/{m.group(1)}/preview"

    return url

def get_tesis_list(search: str = "", rating: str = "", page: int = 1, per_page: int = 9) -> dict:
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [c.strip().lower().replace(" ", "").replace("_", "") for c in df.columns]

        missing = [c for c in REQUIRED_COLS if c not in df.columns]
        if missing:
            return {"ok": False, "error": f"Columnas faltantes: {missing}"}

        df['fecha_dt']    = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
        df['dias_desde']  = (datetime.now() - df['fecha_dt']).dt.days
        df['es_nuevo']    = df['dias_desde'] <= 7

        # Filtros
        if search:
            s = search.lower()
            mask = (
                df.get('ticker', pd.Series(dtype=str)).str.contains(s, case=False, na=False) |
                df.get('nombre', pd.Series(dtype=str)).str.contains(s, case=False, na=False)
            )
            df = df[mask]

        if rating and rating != "Todos":
            df = df[df['rating'].str.upper() == rating.upper()]

        df = df.sort_values('fecha_dt', ascending=False, na_position='last')

        total       = len(df)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page        = max(1, min(page, total_pages))
        start       = (page - 1) * per_page
        df_page     = df.iloc[start:start + per_page]

        items = []
        for _, row in df_page.iterrows():
            rcfg = _get_rating_cfg(_safe_str(row.get('rating', '')))
            items.append({
                "ticker":    _safe_str(row.get('ticker', '')).upper(),
                "nombre":    _safe_str(row.get('nombre', '')),
                "fecha":     _safe_str(row.get('fecha', '')),
                "rating":    _safe_str(row.get('rating', '')).upper(),
                "sector":    _safe_str(row.get('sector', '')),
                "autor":     _safe_str(row.get('autor', '')),
                "resumen":   _safe_str(row.get('resumen', ''))[:300],
                "imagen":    _safe_str(row.get('imagenencabezado', '')),
                "upside":    _safe_str(row.get('upside', '')),
                "riesgo":    _safe_str(row.get('riesgo', '')),
                "es_nuevo":  bool(row.get('es_nuevo', False)),
                "rating_color": rcfg['color'],
                "id":        _safe_str(row.get('ticker', '')) + '_' + _safe_str(row.get('fecha', '')),
            })

        ratings_disponibles = sorted(df['rating'].dropna().str.upper().unique().tolist()) if 'rating' in df.columns else []

        return {
            "ok":       True,
            "items":    items,
            "total":    total,
            "page":     page,
            "per_page": per_page,
            "total_pages": total_pages,
            "ratings":  ["Todos"] + ratings_disponibles,
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}

def get_tesis_detail(ticker: str, fecha: str) -> dict:
    try:
        df = pd.read_csv(CSV_URL)
        df.columns = [c.strip().lower().replace(" ", "").replace("_", "") for c in df.columns]
        df['fecha_dt'] = pd.to_datetime(df['fecha'], dayfirst=True, errors='coerce')
        df['dias_desde'] = (datetime.now() - df['fecha_dt']).dt.days
        df['es_nuevo'] = df['dias_desde'] <= 7

        mask = df['ticker'].str.upper() == ticker.upper()
        if fecha:
            mask = mask & (df['fecha'] == fecha)

        row = df[mask].iloc[0] if len(df[mask]) > 0 else None
        if row is None:
            return {"ok": False, "error": f"Tesis no encontrada: {ticker}"}

        rcfg = _get_rating_cfg(_safe_str(row.get('rating', '')))
        ticker_up = _safe_str(row.get('ticker', '')).upper()

        # Precio objetivo: el único precio que se sigue escribiendo a mano en
        # el Sheet — es una opinión/objetivo, no un dato de mercado.
        precio_objetivo = None
        try:
            precio_objetivo = float(row.get('precioobjetivo', ''))
        except Exception:
            pass

        # Precio actual: se pide en vivo (yfinance, vía cartera_service —
        # mismo caché de 60s que usa Watchlist/Cartera) en vez de depender de
        # que alguien lo escriba a mano en el Sheet y se quede congelado
        # desde el día que se creó la tesis.
        precio_actual = None
        try:
            from services.cartera_service import fetch_live_prices
            live = fetch_live_prices([ticker_up])
            if ticker_up in live and live[ticker_up].get('price'):
                precio_actual = float(live[ticker_up]['price'])
        except Exception:
            pass
        # Fallback: si por lo que sea no hay precio en vivo (ticker raro,
        # yfinance caído...), se usa el valor manual del Sheet si existe,
        # para no dejar el dato completamente vacío.
        if precio_actual is None:
            try:
                precio_actual = float(row.get('precioactual', ''))
            except Exception:
                pass

        # Upside: calculado en vivo a partir de precio objetivo vs precio
        # actual — ya no se lee de una columna "upside" escrita a mano, que
        # además de dar trabajo extra es fácil que se quede sin rellenar
        # (como en la tesis de GE) o desfasada en cuanto el precio se mueve.
        upside = None
        if precio_objetivo is not None and precio_actual not in (None, 0):
            try:
                upside = round((precio_objetivo - precio_actual) / precio_actual * 100, 1)
            except Exception:
                pass
        if upside is None:
            # Último fallback: el valor manual del Sheet, por si la tesis es
            # antigua y no tiene precio objetivo bien formado para calcularlo.
            try:
                upside = round(float(row.get('upside', '')), 1)
            except Exception:
                pass

        url_doc = _safe_str(row.get('urldoc', ''))
        url_doc = _normalize_doc_url(url_doc)

        return {
            "ok":       True,
            "ticker":   ticker_up,
            "nombre":   _safe_str(row.get('nombre', '')),
            "fecha":    _safe_str(row.get('fecha', '')),
            "rating":   _safe_str(row.get('rating', '')).upper(),
            "sector":   _safe_str(row.get('sector', '')),
            "autor":    _safe_str(row.get('autor', '')),
            "resumen":  _safe_str(row.get('resumen', '')),
            "imagen":   _safe_str(row.get('imagenencabezado', '')),
            "upside":   upside,
            "riesgo":   _safe_str(row.get('riesgo', '')).upper(),
            "precio_objetivo": round(precio_objetivo, 2) if precio_objetivo is not None else None,
            "precio_actual":   round(precio_actual, 2) if precio_actual is not None else None,
            "url_doc":  url_doc,
            "es_nuevo": bool(row.get('es_nuevo', False)),
            "rating_color": rcfg['color'],
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}