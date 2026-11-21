# Registro de cambios de academyLab

## 2026-11-21 — Fase 3 (piloto): prácticas Linux que exigen demostrar comprensión

### Problema
Las 14 prácticas Linux se aprobaban con solo pulsar «Ejecutar en Ubuntu»: el alumno no
tenía que interpretar nada. Este piloto cambia **solo** el módulo `linux-log-investigation`
(`linux-logs-guided` y `linux-logs-independent`). Las otras 12 prácticas no cambian.

### Nuevo flujo (dos pasos)
1. **Ejecutar.** El alumno elige una opción de comando de una lista fija y la ejecuta
   en Ubuntu (`POST /api/learning/run-linux-option`).
   - La guiada tiene 1 opción y la independiente 4 (`find`, `grep -c`, `grep -n`, `tail -n 5`).
   - Ejecutar no registra intentos ni aprueba nada.
   - Sigue sin aceptarse texto de consola desde el navegador.
2. **Responder.** El alumno responde una pregunta (número de línea del primer ERROR o del
   último PENDIENTE). Para validarla, el servidor vuelve a ejecutar en Ubuntu la opción de
   referencia y extrae el valor de su salida real con un marcador interno.
   - Se aprueba solo si la ejecución terminó bien **y** la respuesta coincide.
   - Una respuesta incorrecta no muestra la salida de referencia ni el valor esperado.

### Archivos
- `web/linux_runtime.py`:
  - Opciones, opción de referencia, `answer_script` y patrón de respuesta para las dos prácticas.
  - Nuevas funciones `run_option`, `verify_answer`, `question_exercise_ids` y `exercise_options`.
  - `run_exercise` rechaza las prácticas con pregunta.
- `web/learning_service.py`:
  - `run_linux_option`.
  - Rama `linux_command` con pregunta.
  - `get_course` agrega las opciones desde el runtime, que es la única fuente.
  - `validate_catalog` exige pregunta y pista solo donde el runtime define opciones.
- `web/platform_server.py`: ruta `/api/learning/run-linux-option`.
- `web/catalog/linux_basic.json`: preguntas, pistas e instrucciones del piloto.
- `web/learning/course.js`: formulario de dos pasos; las demás prácticas Linux no cambian.
- `labs/linux-course/fixtures/production-support.log`: pasa de 5 a 30 líneas sintéticas.
  - Primer ERROR en la línea 7 y último PENDIENTE en la 22, fuera de lo que muestran `head`/`tail`.
  - Las prácticas existentes que leen este log siguen siendo válidas: buscan "al menos una" coincidencia.
- `web/assets/platform.css`: corrige un defecto previo. En todas las evaluaciones, los botones
  de opción ocupaban todo el ancho (`.learning-form input { width: 100% }`) y el texto quedaba
  desplazado a la derecha.

### Pruebas
- Nueva `web/tests/test_linux_questions.py`, con 11 pruebas:
  - Sin respuesta no se aprueba.
  - Respuesta incorrecta: no se aprueba y no se revela el valor.
  - Respuesta correcta con una ejecución fallida: no se aprueba.
  - Se rechazan las opciones desconocidas y el texto de consola.
  - Ejecutar no registra intentos.
  - Se respeta el orden de los módulos.
  - La extracción y la comparación usan el marcador.
  - El catálogo público no expone el script de la respuesta.
- `test_learning_service.py`: completar el curso Linux exige responder en el piloto (2 respuestas
  verificadas + 12 ejecuciones).
- Suite web: 46/46. LAB 01: 9/9.

### Verificación y límites
- Los scripts exactos del piloto se ejecutaron con Git Bash (herramientas GNU) sobre una copia
  del log con fin de línea CRLF, como se copia hoy a Ubuntu:
  - Las 5 opciones terminan bien.
  - Las respuestas esperadas son 7 y 22, y se rechazan otros valores.
  - El marcador no aparece en la salida visible.
- Navegador: plataforma con Ubuntu **simulado**, porque los scripts corrieron en Git Bash.
  - Se probó `grep -c`, una respuesta incorrecta (rechazada, sin revelar el valor) y
    `grep -n` → 22 (aprobada en el intento 2).
  - Para llegar al módulo 3 sin aprobar los anteriores, la demo omitió el control de orden.
- **No verificado:** ejecución en Ubuntu/WSL real. Esta PC no tiene WSL. Antes de extender el
  piloto, hay que probar ambas prácticas en Ubuntu 24.04.
- Las aprobaciones Linux ya registradas con el criterio anterior se conservan.

## 2026-11-21 — Fase 2: coherencia de datos del LAB 01 y seguridad del servidor del LAB

### Datos y ejercicios
- `data/synthetic/operaciones_sinteticas.csv` pasa a ser la tabla de **estado actual**
  (último evento de cada operación): OP-1002 → PENDIENTE y OP-1003 → OK. Antes conservaba el
  primer estado y contradecía el log.
- `exercises/ejercicios.md`:
  - Explica la diferencia entre eventos y estado actual.
  - Corrige "INFO=4" (es OK=4).
  - Cifras del ejercicio 2: ERROR 2 operaciones, 1760.00; PENDIENTE 2 operaciones, 1281.25.
  - Agrega resultados esperados locales al ejercicio 1.
  - Rehace la priorización del ejercicio 5 según el estado actual.
- `sql/05_metricas_operaciones_unicas.sql`: la alternativa deduplicada usa `ROW_NUMBER()` en una
  subconsulta, en lugar de `QUALIFY` y de una columna `ts` inexistente. También documenta que
  requiere una tabla de eventos con fecha.

### Analizador (cambio aditivo)
- `analizar_logs.py` agrega `estado_actual_por_operacion`, `conteo_operaciones_por_estado_actual`
  e `importe_operaciones_por_estado_actual`. Los campos existentes no cambian.
- `archivo` se guarda relativo a la carpeta del LAB, sin rutas personales. Se regeneraron las tres
  evidencias versionadas.

### Interfaz del LAB
- La tarjeta "Errores" pasa a llamarse "Con algun evento ERROR".
- Nueva tarjeta "En ERROR ahora".

### Seguridad del servidor del LAB
- `web_server.py` rechaza con 403 las solicitudes con Host no local (mitiga DNS rebinding).
- Rechaza con 403 los POST con un Origin distinto de la propia página del LAB.
- Las solicitudes sin Origin, como scripts locales, siguen aceptándose.

### Pruebas
- LAB: 9 pruebas (antes 8).
  - `normal` y `multi_event` verifican también el estado actual.
  - Nueva `csv_matches_log_current_state`: falla si el CSV y el log vuelven a divergir.
  - El runner web copia `data/sample_logs` y `data/synthetic` a su carpeta temporal.
- Nueva `web/tests/test_lab_web_server.py` (4 pruebas de Host y Origin). Suite web: 35/35.
- Las pruebas nuevas fallan con el código de la Fase 1.
- Verificado en el navegador:
  - Análisis de `normal.log` con las tarjetas 3 / 2.
  - 9/9 pruebas desde la interfaz.
  - Al cerrar la pestaña se cierra la sesión y el apagado ordenado procede.
- Las consultas `sql/01` y `sql/02` y la alternativa de `sql/05` se ejecutaron en SQLite sobre el
  CSV y coinciden con las cifras de los ejercicios.

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
