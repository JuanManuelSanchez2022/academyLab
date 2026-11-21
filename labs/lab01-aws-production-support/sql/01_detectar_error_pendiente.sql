-- LAB 01 - 01: Detectar operaciones con estado ERROR o PENDIENTE
-- Referencia: región us-east-2, base practica_academylab. Solo lectura.
-- Ajustar nombre de tabla/vista si corresponde (operaciones).

SELECT
  id_operacion,
  cliente,
  importe,
  estado
FROM practica_academylab.operaciones
WHERE estado IN ('ERROR', 'PENDIENTE')
ORDER BY estado, importe DESC, id_operacion;
