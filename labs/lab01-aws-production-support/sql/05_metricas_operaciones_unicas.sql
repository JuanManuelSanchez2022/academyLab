-- LAB 01 - 05: Metricas por operaciones unicas (Athena, solo lectura)
-- Nota: esta consulta asume que cada id_operacion aparece una unica vez en la tabla.
-- Si existen multiples registros por id_operacion, COUNT(DISTINCT id_operacion)
-- cuenta identificadores unicos pero SUM(importe) suma todos los registros,
-- lo que puede duplicar importes. Para evitarlo, deduplicar antes por id_operacion
-- segun una regla explicita (por ejemplo, el ultimo registro por fecha/hora).

SELECT
  estado,
  COUNT(DISTINCT id_operacion) AS operaciones_unicas,
  COUNT(*) AS registros,
  ROUND(SUM(importe), 2) AS importe_total_registros,
  ROUND(AVG(importe), 2) AS importe_promedio
FROM practica_strata.operaciones
WHERE estado IN ('ERROR', 'PENDIENTE')
GROUP BY estado
ORDER BY operaciones_unicas DESC;

-- Alternativa con deduplicacion explicita: estado actual = ultimo evento por id_operacion.
-- Requiere una tabla de EVENTOS con una columna de fecha/hora del evento
-- (aqui practica_strata.eventos_operaciones y fecha_evento, nombres de ejemplo).
-- La tabla practica_strata.operaciones de referencia no tiene esa columna.
-- Se usa ROW_NUMBER() en una subconsulta porque QUALIFY no es SQL estandar
-- y no esta disponible en todos los motores.
--
-- WITH ranked AS (
--   SELECT
--     id_operacion,
--     estado,
--     importe,
--     ROW_NUMBER() OVER (PARTITION BY id_operacion ORDER BY fecha_evento DESC) AS rn
--   FROM practica_strata.eventos_operaciones
-- )
-- SELECT
--   estado,
--   COUNT(*) AS operaciones_unicas,
--   ROUND(SUM(importe), 2) AS importe_total_deduplicado
-- FROM ranked
-- WHERE rn = 1
--   AND estado IN ('ERROR', 'PENDIENTE')
-- GROUP BY estado
-- ORDER BY operaciones_unicas DESC;
