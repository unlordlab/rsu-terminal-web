"""
migrate_tesis_from_sheet.py — migración de una sola vez, 17/07/2026.

Trae todas las tesis del Google Sheet publicado como CSV (el sistema
antiguo) a la nueva tabla `tesis` en tesis.db, marcándolas como
'approved' (ya estaban publicadas, no necesitan revisión de nuevo).

Ejecutar UNA VEZ en el VPS, antes de desplegar el nuevo tesis_service.py
en producción, para no perder las tesis ya publicadas:

    cd backend
    python3 ../scripts/migrate_tesis_from_sheet.py

Es seguro ejecutarlo más de una vez por accidente: comprueba si una tesis
con el mismo ticker+fecha ya existe antes de insertarla, para no duplicar.
"""
import sys
import os
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from services.tesis_service import _conn, _init_db  # noqa: E402

CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vQVyU3x2DEQVczsqgmUwMSS1SS99Npe8LO-Om5n-VmXKuT-PYxuX65YinMg5XcGZehYE2df6jQuCzTo/pub?output=csv"


def main():
    _init_db()
    print(f"Descargando CSV desde el Google Sheet...")
    df = pd.read_csv(CSV_URL)
    print(f"  {len(df)} filas encontradas.")

    required = {'ticker', 'rating', 'fecha'}
    missing = required - set(c.lower() for c in df.columns)
    if missing:
        print(f"✗ Faltan columnas esperadas en el CSV: {missing}. Revisa el Sheet a mano.")
        return

    # Normalizar nombres de columna: minúsculas, sin espacios NI guiones
    # bajos — mismo criterio que usaba el tesis_service.py antiguo
    # (c.lower().replace(" ", "").replace("_", "")), para que columnas
    # como "URL_Doc" o "Precio_Objetivo" se reconozcan igual.
    df.columns = [c.lower().strip().replace(" ", "").replace("_", "") for c in df.columns]

    conn = _conn()
    insertados = 0
    saltados = 0

    for _, row in df.iterrows():
        ticker = str(row.get('ticker', '')).strip().upper()
        fecha_raw = str(row.get('fecha', '')).strip()
        # El Sheet usa DD/MM/YYYY; el resto del sistema usa YYYY-MM-DD para
        # que el orden cronológico (ORDER BY fecha) funcione bien como texto.
        try:
            fecha = pd.to_datetime(fecha_raw, dayfirst=True).strftime("%Y-%m-%d")
        except Exception:
            fecha = fecha_raw
        rating = str(row.get('rating', 'HOLD')).strip().upper() or 'HOLD'
        nombre = str(row.get('nombre', '') or '').strip()
        sector = str(row.get('sector', '') or '').strip()
        autor = str(row.get('autor', '') or '').strip()
        resumen = str(row.get('resumen', '') or '').strip()
        imagen = str(row.get('imagenencabezado', '') or row.get('imagen', '') or '').strip()
        riesgo = str(row.get('riesgo', '') or '').strip()
        titulo = str(row.get('titulo', '') or row.get('título', '') or '').strip()
        doc_url = str(row.get('urldoc', '') or row.get('url', '') or '').strip()
        try:
            precio_objetivo = float(row.get('precioobjetivo', ''))
        except Exception:
            precio_objetivo = None

        if not ticker or not fecha or ticker == 'NAN':
            print(f"  SALTADA (sin ticker/fecha válidos): ticker={ticker!r} fecha={fecha!r}")
            saltados += 1
            continue

        existe = conn.execute(
            "SELECT id FROM tesis WHERE ticker = ? AND fecha = ?", (ticker, fecha)
        ).fetchone()
        if existe:
            print(f"  SALTADA (ya existe): {ticker} {fecha}")
            saltados += 1
            continue

        # El contenido real vivía en el documento externo (doc_url), no en
        # el propio Sheet — lo guardamos como referencia, no como texto
        # completo. Si se quiere el contenido íntegro migrado también,
        # habría que descargarlo aparte (fuera del alcance de este script).
        contenido = (
            f"*(Tesis migrada del Google Sheet original — el contenido completo "
            f"vive en el documento enlazado.)*\n\n"
            + (f"Documento original: {doc_url}" if doc_url else "*(Sin documento enlazado en el Sheet.)*")
        )

        conn.execute(
            """INSERT INTO tesis (ticker, nombre, fecha, rating, sector, autor, titulo, resumen,
                                   imagen, riesgo, precio_objetivo, contenido, status, fuente, doc_url, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'approved', 'migracion_sheet', ?, strftime('%s','now'))""",
            (ticker, nombre, fecha, rating, sector, autor, titulo, resumen, imagen, riesgo,
             precio_objetivo, contenido, doc_url or None)
        )
        insertados += 1

    conn.commit()
    conn.close()
    print(f"✓ Migración completada: {insertados} tesis insertadas, {saltados} saltadas (duplicadas o sin datos).")


if __name__ == "__main__":
    main()