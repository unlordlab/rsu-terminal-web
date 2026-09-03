-- Sesiones de amplitud sospechosas en snapshot_mercado.
--
-- El 02/09/2026 el escaneo nocturno publico una sesion con 24 valores de
-- ~2.400 y esta tabla la guardo como normal (ver Scanner #22). Desde el
-- 04/09 el escaner ya no publica sesiones truncadas y el backend las
-- repara solo en cuanto el Gist trae la fecha completa -- esta consulta
-- es para MIRAR que hay, no hace falta borrar nada a mano.
--
--   sqlite3 backend/snapshots.db < scripts/revisar_amplitud_snapshots.sql
--
-- Una fila sospechosa es la que cubre menos de la mitad de la mediana de
-- las 30 sesiones anteriores. Misma regla que shared/cobertura_amplitud.py.
.mode column
.headers on

SELECT
    fecha,
    advances,
    declines,
    advances + declines AS valores,
    CASE
        WHEN advances + declines < 100 THEN '<<< TRUNCADA'
        WHEN advances + declines < (
            SELECT AVG(advances + declines) / 2 FROM snapshot_mercado
        ) THEN '<<< sospechosa'
        ELSE ''
    END AS aviso
FROM snapshot_mercado
ORDER BY fecha DESC
LIMIT 30;
