-- LAB 01 - 02: Cantidades e importes afectados por estado (foco ERROR/PENDIENTE)
-- Referencia: región us-east-2, base practica_academylab. Solo lectura.

SELECT
  estado,
  COUNT(*) AS cantidad_operaciones,
  ROUND(SUM(importe), 2) AS importe_total,
  ROUND(AVG(importe), 2) AS importe_promedio,
  ROUND(MIN(importe), 2) AS importe_min,
  ROUND(MAX(importe), 2) AS importe_max
FROM practica_academylab.operaciones
WHERE estado IN ('ERROR', 'PENDIENTE')
GROUP BY estado
ORDER BY importe_total DESC;
