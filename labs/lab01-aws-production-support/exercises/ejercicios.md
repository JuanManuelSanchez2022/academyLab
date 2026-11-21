# LAB 01 — Ejercicios prácticos

## Datos del laboratorio: eventos y estado actual

El LAB trabaja con dos vistas de las mismas ocho operaciones:

- **Log de eventos** (`data/sample_logs/operaciones.log`): 10 eventos. Una operación puede tener varios eventos. Por ejemplo, OP-1002 pasa de `ERROR` (timeout) a `PENDIENTE` (reintento programado), y OP-1003 pasa de `PENDIENTE` a `OK`.
- **Tabla de operaciones** (`data/synthetic/operaciones_sinteticas.csv`): una fila por operación con su **estado actual**, es decir, el del último evento.

Confundir las dos vistas es un error frecuente de soporte: contar eventos `ERROR` no es contar operaciones que hoy están en `ERROR`.

## Ejercicio 1: Detección de operaciones problemáticas (SQL)
**Consigna:** Usando la tabla de operaciones en `practica_strata` (referencia, solo lectura), identificar todas las operaciones con estado `ERROR` o `PENDIENTE`.
- Ejecutar: `sql/01_detectar_error_pendiente.sql`

**Resultado esperado (estructura):** listado con `id_operacion`, `cliente`, `importe`, `estado` filtrado a `ERROR` y `PENDIENTE`, ordenado por estado e importe.

**Con datos sintéticos locales (CSV):** ERROR → OP-1005 (1200.00), OP-1008 (560.00); PENDIENTE → OP-1002 (980.50), OP-1006 (300.75).

## Ejercicio 2: Medición de impacto (SQL)
**Consigna:** Calcular cantidad de operaciones e importes afectados por estado (`ERROR`, `PENDIENTE`).
- Ejecutar: `sql/02_metricas_error_pendiente.sql`

**Resultado esperado (estructura):** una fila por estado con `cantidad_operaciones`, `importe_total`, `importe_promedio`, `importe_min`, `importe_max`.

**Con datos sintéticos locales (CSV):** ERROR → 2 operaciones, importe 1760.00; PENDIENTE → 2 operaciones, importe 1281.25.

## Ejercicio 3: Análisis de logs y causas (Python, local)
**Consigna:** Analizar `data/sample_logs/operaciones.log` para identificar `id_operacion`, estados y causas. Distinguir lo que ocurrió (eventos) del estado actual de cada operación.
- Ejecutar: `python labs/lab01-aws-production-support/scripts/analizar_logs.py --input labs/lab01-aws-production-support/data/sample_logs/operaciones.log`

**Resultado esperado:**
- Eventos parseados: 10. Operaciones únicas: 8. Líneas no parseadas: 0.
- Conteo de **eventos** por estado: OK=4, ERROR=3, PENDIENTE=3.
- Operaciones con algún evento ERROR: OP-1002, OP-1005, OP-1008 (con causas).
- Operaciones con algún evento PENDIENTE: OP-1002, OP-1003, OP-1006 (con causas).
- Importes de **eventos**: ERROR=2740.5 y PENDIENTE=1326.25. OP-1002 suma 980.50 en ambos porque tiene un evento de cada estado; no son importes de operaciones distintas.
- **Estado actual** (último evento): ERROR → OP-1005, OP-1008 (1760.0); PENDIENTE → OP-1002, OP-1006 (1281.25); OK → OP-1001, OP-1003, OP-1004, OP-1007 (480.25).

**Verificación:** el estado actual del analizador debe coincidir con el CSV del ejercicio 2. Si no coincide, uno de los dos datos está desactualizado.

## Ejercicio 4: Evidencia estructurada
**Consigna:** Generar un resumen JSON reproducible.
- Ejecutar: `python labs/lab01-aws-production-support/scripts/analizar_logs.py --input labs/lab01-aws-production-support/data/sample_logs/operaciones.log --json labs/lab01-aws-production-support/evidence/resumen_logs.json`

**Resultado esperado:** archivo `evidence/resumen_logs.json` con `total_eventos_parseados`, `conteo_por_estado`, `operaciones_error`, `operaciones_pendiente`, importes de eventos, alertas y los campos de estado actual (`estado_actual_por_operacion`, `conteo_operaciones_por_estado_actual`, `importe_operaciones_por_estado_actual`). El campo `archivo` se guarda relativo a la carpeta del LAB, sin rutas personales.

## Ejercicio 5: Priorización (razonamiento)
**Consigna:** Con base en el estado actual y el historial de eventos, proponer un orden de atención.

**Criterio esperado:**
1. Atender primero las operaciones que **siguen** en `ERROR`, por importe: OP-1005 (saldo insuficiente, 1200.00) y OP-1008 (error de formato en datos, 560.00).
2. Después, las `PENDIENTE` según su riesgo: OP-1002 ya tuvo un timeout y tiene un reintento programado, así que hay que verificar el resultado del reintento; OP-1006 requiere revisión manual.
3. OP-1003 no requiere acción: su último evento confirma la operación (`OK`). Citarla como incidente resuelto sería una conclusión basada en eventos y no en el estado actual.
