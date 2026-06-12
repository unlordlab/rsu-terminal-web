import pandas as pd
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

        rcfg    = _get_rating_cfg(_safe_str(row.get('rating', '')))
        upside  = None
        try:
            v = float(row.get('upside', 0))
            upside = round(v, 1)
        except Exception: pass

        url_doc = _safe_str(row.get('urldoc', ''))
        if url_doc and "/pub" in url_doc:
            url_doc = url_doc.split("?")[0].split("&")[0] + "?embedded=true"

        return {
            "ok":       True,
            "ticker":   _safe_str(row.get('ticker', '')).upper(),
            "nombre":   _safe_str(row.get('nombre', '')),
            "fecha":    _safe_str(row.get('fecha', '')),
            "rating":   _safe_str(row.get('rating', '')).upper(),
            "sector":   _safe_str(row.get('sector', '')),
            "autor":    _safe_str(row.get('autor', '')),
            "resumen":  _safe_str(row.get('resumen', '')),
            "imagen":   _safe_str(row.get('imagenencabezado', '')),
            "upside":   upside,
            "riesgo":   _safe_str(row.get('riesgo', '')).upper(),
            "precio_objetivo": _safe_str(row.get('precioobjetivo', '')),
            "precio_actual":   _safe_str(row.get('precioactual', '')),
            "url_doc":  url_doc,
            "es_nuevo": bool(row.get('es_nuevo', False)),
            "rating_color": rcfg['color'],
            "timestamp": datetime.now().strftime('%H:%M:%S'),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}