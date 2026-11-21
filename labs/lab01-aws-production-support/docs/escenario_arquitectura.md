# Escenario y Arquitectura — LAB 01

## Contexto
Laboratorio de **AWS Production Support** para seguimiento y análisis de operaciones. El escenario combina una vista tabular de operaciones (referencia S3/Athena/Glue) y eventos operativos (referencia CloudWatch Logs).

## Recursos AWS de referencia (existentes, solo lectura)
| Elemento | Valor |
|---|---|
| Región | `us-east-2` |
| Bucket S3 | `practica-athena-sql-2026` |
| Base Glue/Athena | `practica_academylab` |
| Archivo fuente | `datos/operaciones.csv` |
| Columnas | `id_operacion`, `cliente`, `importe`, `estado` |
| Log group CloudWatch | `academylab-operaciones` |

Recursos adicionales existentes (tablas/vistas): operaciones, excepciones, correcciones y seguimiento de errores. **No se modifican ni eliminan.**

## Arquitectura lógica
```text
[S3: practica-athena-sql-2026/datos/operaciones.csv]  (referencia, solo lectura)
        |
        v
[Glue Data Catalog / Athena: practica_academylab.operaciones(+vistas)]
        |
        v
[Consultas SQL] --> detección ERROR/PENDIENTE, conteos, importes

[CloudWatch Logs: academylab-operaciones]  (referencia, solo lectura)
        |
        v
[Export/ejemplos simulados locales] --> data/sample_logs/operaciones.log
        |
        v
[Python: analizar_logs.py] --> ids, estados, causas, resumen automático
```

## Modelo de datos (operaciones)
- `id_operacion`: identificador único de la operación.
- `cliente`: identificador/nombre de cliente.
- `importe`: monto numérico.
- `estado`: estado operativo (p.ej. `OK`, `ERROR`, `PENDIENTE`).

## Objetivos operativos
- Detectar operaciones en `ERROR` y `PENDIENTE`.
- Medir cantidad e importes afectados.
- Identificar causas desde logs y priorizar seguimiento.
- Producir resúmenes reproducibles y verificables.

## Consideraciones de seguridad y costos
- Solo lectura sobre recursos existentes; sin creación de recursos nuevos.
- Sin credenciales en el repositorio.
- Ejecución local del script con datos sintéticos/simulados, sin conexión a AWS.
