# LAB 01 — Ejercicios prácticos

## Ejercicio 1: Detección de operaciones problemáticas (SQL)
**Consigna:** Usando la tabla de operaciones en `practica_strata` (referencia, solo lectura), identificar todas las operaciones con estado `ERROR` o `PENDIENTE`.
- Ejecutar: `sql/01_detectar_error_pendiente.sql`
**Resultado esperado (estructura):** listado con `id_operacion`, `cliente`, `importe`, `estado` filtrado a `ERROR` y `PENDIENTE`, ordenado por estado e importe.

## Ejercicio 2: Medición de impacto (SQL)
**Consigna:** Calcular cantidad de operaciones e importes afectados por estado (`ERROR`, `PENDIENTE`).
- Ejecutar: `sql/02_metricas_error_pendiente.sql`
**Resultado esperado (estructura):** una fila por estado con `cantidad_operaciones`, `importe_total`, `importe_promedio`, `importe_min`, `importe_max`.
**Con datos sintéticos locales (`data/synthetic/operaciones_sinteticas.csv`):** ERROR → 3 ops, importe 2740.50; PENDIENTE → 2 ops, importe 345.75.

## Ejercicio 3: Análisis de logs y causas (Python, local)
**Consigna:** Analizar `data/sample_logs/operaciones.log` para identificar `id_operacion`, estados y causas; generar resumen de errores y pendientes.
- Ejecutar: `python labs/lab01-aws-production-support/scripts/analizar_logs.py --input labs/lab01-aws-production-support/data/sample_logs/operaciones.log`
**Resultado esperado:**
- Eventos parseados: 10, líneas no parseadas: 0.
- Conteo por estado: ERROR=3, INFO=4, OK (eventos INFO con estado OK) según log, PENDIENTE=3 (ver salida exacta en `evidence/`).
- Operaciones en ERROR detectadas: OP-1002, OP-1005, OP-1008 (con causas).
- Operaciones en PENDIENTE detectadas: OP-1002, OP-1003, OP-1006 (con causas).
- Importes totales de eventos ERROR=2740.5, PENDIENTE=1326.25.

## Ejercicio 4: Evidencia estructurada
**Consigna:** Generar un resumen JSON reproducible.
- Ejecutar: `python labs/lab01-aws-production-support/scripts/analizar_logs.py --input labs/lab01-aws-production-support/data/sample_logs/operaciones.log --json labs/lab01-aws-production-support/evidence/resumen_logs.json`
**Resultado esperado:** archivo `evidence/resumen_logs.json` con `total_eventos_parseados`, `conteo_por_estado`, `operaciones_error`, `operaciones_pendiente`, importes y alertas.

## Ejercicio 5: Priorización (razonamiento)
**Consigna:** Con base en el resumen, proponer orden de atención.
**Criterio esperado:** priorizar `ERROR` por impacto de importe y recurrencia de causa (p.ej. timeout/reintento en OP-1002, saldo insuficiente en OP-1005, formato en OP-1008), luego `PENDIENTE` por antigüedad/bloqueo.
