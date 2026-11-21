-- LAB 01 - 04: Top operaciones por importe en ERROR o PENDIENTE
-- Referencia: región us-east-2, base practica_academylab. Solo lectura.

SELECT
  id_operacion,
  cliente,
  importe,
  estado
FROM practica_academylab.operaciones
WHERE estado IN ('ERROR', 'PENDIENTE')
ORDER BY importe DESC
LIMIT 20;
