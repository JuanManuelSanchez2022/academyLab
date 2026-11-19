-- LAB 01 - 03: Resumen global de estados (contexto operativo)
-- Referencia: región us-east-2, base practica_strata. Solo lectura.

SELECT
  estado,
  COUNT(*) AS cantidad_operaciones,
  ROUND(SUM(importe), 2) AS importe_total
FROM practica_strata.operaciones
GROUP BY estado
ORDER BY cantidad_operaciones DESC;
