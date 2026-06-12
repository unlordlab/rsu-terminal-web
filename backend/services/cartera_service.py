<<<<<<< HEAD
import pandas as pd
import unicodedata
from datetime import datetime
import pytz
from config import settings

REQUIRED_COLS = {"Ticker", "Estado", "Fecha", "Precio Compra", "Precio Actual", "Inversión", "Valor Actual", "Comisiones"}

def norm_col(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()

def clean_numeric(value):
    if pd.isna(value):
        return 0.0
    val_str = str(value).strip().replace("$", "").replace("%", "").replace(" ", "")
    if "," in val_str:
        val_str = val_str.replace(".", "").replace(",", ".")
    try:
        return float(val_str)
    except Exception:
        return 0.0

def get_market_status():
    ny  = pytz.timezone("America/New_York")
    now = datetime.now(ny)
    wd  = now.weekday()
    h   = now.hour + now.minute / 60
    if wd >= 5:
        return "CLOSED", "#f23645"
    if 9.5 <= h < 16.0:
        return "OPEN", "#00ffad"
    if 4.0 <= h < 9.5 or 16.0 <= h < 20.0:
        return "PRE/POST", "#ff9800"
    return "CLOSED", "#f23645"

def get_cartera():
    try:
        url = settings.url_cartera
        if not url:
            raise ValueError("URL_CARTERA no configurada")

        df_raw = pd.read_csv(url).dropna(how="all")
        df_raw.columns = [c.strip() for c in df_raw.columns]

        col_map      = {norm_col(c): c for c in df_raw.columns}
        required_norm = {norm_col(r): r for r in REQUIRED_COLS}
        missing      = [orig for n, orig in required_norm.items() if n not in col_map]

        if missing:
            raise ValueError(f"Columnas faltantes: {', '.join(missing)}")

        rename = {col_map[n]: orig for n, orig in required_norm.items() if col_map[n] != orig}
        df     = df_raw.rename(columns=rename).copy()

        inv_col = "Inversión" if "Inversión" in df.columns else "Inversion"
        for col in ["Precio Compra", "Precio Actual", inv_col, "Valor Actual", "Comisiones"]:
            if col in df.columns:
                df[col] = df[col].apply(clean_numeric)
        if inv_col != "Inversión":
            df = df.rename(columns={inv_col: "Inversión"})

        df["P&L (%)"] = df.apply(
            lambda x: ((x["Precio Actual"] - x["Precio Compra"]) / x["Precio Compra"] * 100)
            if x["Precio Compra"] != 0 else 0, axis=1
        )
        df["Estado"] = df["Estado"].astype(str).str.strip().str.upper()
        df["Ticker"] = df["Ticker"].astype(str).str.strip()
        df["Fecha"]  = pd.to_datetime(df["Fecha"], errors="coerce")
        df           = df.dropna(subset=["Fecha", "Ticker"])

        abiertas = df[df["Estado"] == "ABIERTA"].copy()
        cerradas = df[df["Estado"] == "CERRADA"].copy()

        if "Inversión" in abiertas.columns and abiertas["Inversión"].sum() > 0:
            abiertas = abiertas[abiertas["Inversión"] > 0]
        if "Inversión" in cerradas.columns and cerradas["Inversión"].sum() > 0:
            cerradas = cerradas[cerradas["Inversión"] > 0]

        # Métricas generales
        metrics = {}
        if not abiertas.empty:
            total_inv   = abiertas["Inversión"].sum()
            total_val   = abiertas["Valor Actual"].sum()
            total_comis = abiertas["Comisiones"].sum()
            pnl_neto    = (total_val - total_inv) - total_comis
            pnl_pct     = (pnl_neto / total_inv * 100) if total_inv != 0 else 0
            val_pct     = ((total_val - total_inv) / total_inv * 100) if total_inv != 0 else 0
            metrics = {
                "total_inv":   round(total_inv, 2),
                "total_val":   round(total_val, 2),
                "pnl_neto":    round(pnl_neto, 2),
                "pnl_pct":     round(pnl_pct, 2),
                "val_pct":     round(val_pct, 2),
                "total_comis": round(total_comis, 2),
            }

        # Stats cerradas
        closed_stats = {}
        if not cerradas.empty:
            ganadas  = len(cerradas[cerradas["P&L (%)"] > 0])
            perdidas = len(cerradas[cerradas["P&L (%)"] <= 0])
            win_rate = ganadas / len(cerradas) * 100 if len(cerradas) > 0 else 0
            avg_pnl  = cerradas["P&L (%)"].sum()
            closed_stats = {
                "total":    len(cerradas),
                "ganadas":  ganadas,
                "perdidas": perdidas,
                "win_rate": round(win_rate, 1),
                "avg_pnl":  round(avg_pnl, 2),
            }

        def df_to_rows(d):
            rows = []
            for _, row in d.sort_values("Fecha", ascending=False).iterrows():
                comment = str(row.get("Comentarios", ""))[:40] if "Comentarios" in row.index else ""
                rows.append({
                    "ticker":  row["Ticker"],
                    "fecha":   row["Fecha"].strftime("%d/%m/%Y"),
                    "compra":  round(row["Precio Compra"], 2),
                    "actual":  round(row["Precio Actual"], 2),
                    "pnl":     round(row["P&L (%)"], 2),
                    "estado":  row["Estado"],
                    "comment": comment,
                })
            return rows

        mkt_status, mkt_color = get_market_status()
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        return {
            "ok":           True,
            "metrics":      metrics,
            "closed_stats": closed_stats,
            "abiertas":     df_to_rows(abiertas),
            "cerradas":     df_to_rows(cerradas),
            "recent":       df_to_rows(df.sort_values("Fecha", ascending=False).head(5)),
            "mkt_status":   mkt_status,
            "mkt_color":    mkt_color,
            "last_update":  now_str,
        }

    except Exception as e:
        return {"ok": False, "error": str(e)}
=======

>>>>>>> 937a93440f767ee6b0c7cb0469a4b2202af036cf
