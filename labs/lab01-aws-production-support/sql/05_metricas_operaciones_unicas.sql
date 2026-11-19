-- LAB 01 - 05: Metricas por operaciones unicas (Athena, solo lectura)
-- Nota: esta consulta asume que cada id_operacion aparece una unica vez en la tabla.
-- Si existen multiples registros por id_operacion, COUNT(DISTINCT id_operacion)
-- cuenta identificadores unicos pero SUM(importe) suma todos los registros,
-- lo que puede duplicar importes. Para evitarlo, usar subconsultas o window functions
-- que dedupliquen previamente por id_operacion segun una regla explicita (por ejemplo,
-- el ultimo registro por fecha/hora). Esta consulta documenta esa limitacion.

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

-- Alternativa con deduplicacion explicita por id_operacion (ejemplo con CTE):
-- WITH latest AS (
--   SELECT id_operacion, estado, importe
--   FROM practica_strata.operaciones
--   QUALIFY ROW_NUMBER() OVER (PARTITION BY id_operacion ORDER BY ts DESC) = 1
-- )
-- SELECT
--   estado,
--   COUNT(*) AS operaciones_unicas,
--   ROUND(SUM(importe), 2) AS importe_total_deduplicado
-- FROM latest
-- WHERE estado IN ('ERROR', 'PENDIENTE')
-- GROUP BY estado
-- ORDER BY operaciones_unicas DESC;