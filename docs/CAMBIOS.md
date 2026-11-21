# Registro de cambios de academyLab

## 2026-11-20 — Fase 1: portabilidad e integridad de las evaluaciones

Origen: auditoría integral del 2026-11-20 sobre el commit `9ca1656`.

### Portabilidad
- `web/platform_server.py` y `labs/lab01-aws-production-support/scripts/web_server.py`
  ya no usan `C:\Users\juan\...\python.exe`. Usan `ACADEMYLAB_PYTHON` si está definida;
  si no, el ejecutable base del intérprete que los ejecuta. Es el mismo criterio
  en ambos, para que la verificación del PID del LAB siga funcionando.
- `scripts/run_tests.py` usa `ACADEMYLAB_PYTHON` o `sys.executable`.
- Nuevo `labs/lab01-aws-production-support/buscar_python.bat`, usado por
  `iniciar_web.bat` e `iniciar_laboratorio.bat`. Orden de búsqueda:
  `ACADEMYLAB_PYTHON`, `py -3.12`, `python` (3.12 o superior).

### Integridad de las evaluaciones
- La API pública ya no envía `example_query`, que era exactamente la consulta
  aceptada en las prácticas SQL.
- En las prácticas Python, una respuesta incorrecta ya no muestra el valor
  esperado en el feedback ni en `execution_result`.
- Los intentos registrados antes de este cambio pueden conservar el valor
  revelado en el historial de la base local.

### Errores corregidos
- El heartbeat del LAB actualiza la variable global `_last_activity`. Antes
  escribía `self._last_activity` en el objeto de la solicitud y la actividad
  no se registraba.
- `run_tests.py` escribe sus JSON en una carpeta temporal y ya no sobrescribe
  `evidence/normal.json` ni `evidence/multi_event.json`. Con `--guardar-evidencia`
  conserva el comportamiento anterior.

### Verificación
- `python -m unittest discover -s web\tests`: 31/31 OK (28 previas + 3 nuevas).
  Las 3 nuevas fallan con el código anterior.
- `run_tests.py`: 8/8 PASS, sin cambios en `evidence/`.
- Ciclo real: inicio de la plataforma, inicio del LAB desde la API, 8/8 pruebas
  vía web, rechazo del apagado con una sesión pendiente y apagado ordenado
  de la plataforma y del LAB.
- No verificado: prácticas Linux, porque WSL no está instalado en el equipo
  de esta verificación.
