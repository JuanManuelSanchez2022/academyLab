# LAB 01 - AWS Production Support: seguimiento y análisis de operaciones

## Objetivo
Practicar tareas de soporte de producción: identificar operaciones con estado ERROR y PENDIENTE, medir su impacto, analizar logs y generar resúmenes usando datos locales de prueba y consultas SQL compatibles con Athena.

## Escenario de referencia (solo lectura)
- Región: us-east-2
- S3: practica-athena-sql-2026
- Base Athena/Glue: practica_academylab
- Archivo fuente: datos/operaciones.csv
- CloudWatch Log Group: academylab-operaciones

Este laboratorio no se conecta a AWS ni modifica recursos. No requiere credenciales.

## Estructura
- `scripts/analizar_logs.py`: analizador local; mantiene su comportamiento de línea de comandos.
- `scripts/run_tests.py`: nueve pruebas automatizadas, incluida la coherencia entre
  el CSV de operaciones y el estado actual del log. Escribe sus JSON en una carpeta
  temporal; con `--guardar-evidencia` los guarda en `evidence/`.
- `scripts/web_server.py`: servidor HTTP dedicado del LAB 01 en `127.0.0.1:8766`.
- `..\..\web\platform_server.py`: Home en `127.0.0.1:8765`, inicio bajo demanda del LAB y supervisor de sesiones.
- `..\..\web\catalog\learning_catalog.json`: perfiles, niveles, cursos reutilizables, dependencias y estados de disponibilidad.
- `index.html`, `styles.css`, `app.js`: interfaz del LAB 01.
- `data/test/`: logs de prueba permitidos para la interfaz.
- `evidence/`: archivos JSON de evidencia generados.
- `iniciar_web.bat` y `detener_web.bat`: inicio y parada ordenada de la plataforma.
- `iniciar_laboratorio.bat` y `detener_laboratorio.bat`: mecanismos manuales de respaldo para el LAB.
- `sql/`: consultas de referencia para Athena.

## Requisitos
- Windows y Microsoft Edge.
- Python 3.12 o superior. `buscar_python.bat` usa `ACADEMYLAB_PYTHON`, `py -3.12` o `python`.
- No se necesitan paquetes externos ni conexión a AWS.

## Iniciar la web
1. Haz doble clic en `iniciar_web.bat`. Comprueba el servicio principal y evita instancias duplicadas.
2. Abre en Edge la dirección exacta: **http://127.0.0.1:8765**
3. En Home, abre **Cloud / Production Support**, selecciona **Básico** y usa el recurso disponible **LAB 01 — AWS Production Support** dentro de Production Support. El servicio del LAB se inicia automáticamente en `127.0.0.1:8766`.
4. La disponibilidad del LAB no implica que el curso AWS ni toda la ruta estén terminados.
5. Ambos servicios escuchan exclusivamente en `127.0.0.1`. Si un puerto está ocupado por un proceso que no puede identificarse, no se inicia ni se detiene ningún proceso.

También se puede iniciar desde PowerShell, en la carpeta del laboratorio:

```powershell
python ".\..\..\web\platform_server.py"
```

## Usar la interfaz
- El panel muestra el estado del servidor y los resultados de la última ejecución disponible.
- En **Análisis de logs**, selecciona un archivo `.log` de la lista y pulsa **EJECUTAR ANÁLISIS**. La interfaz indica si está en curso, terminó correctamente o falló, y presenta la salida real del analizador Python.
- Pulsa **EJECUTAR TODAS LAS PRUEBAS** para lanzar las nueve pruebas existentes. Se muestran los resultados individuales PASS/FAIL y la salida completa.
- El panel distingue **Con algún evento ERROR** (operaciones que tuvieron al menos un evento ERROR)
  de **En ERROR ahora** (operaciones cuyo último evento es ERROR).
- El servidor solo acepta un Host local; los POST de navegador deben provenir de la propia página del LAB.
- La sección **Evidencia** muestra el JSON de `evidence/resumen_logs.json`. Puedes actualizarlo con **ACTUALIZAR EVIDENCIA**; el estado del servidor y la lista de archivos se actualizan automáticamente cada 30 segundos.
- Los análisis y las pruebas se serializan. Las pruebas se ejecutan en un directorio temporal para no sobrescribir la evidencia existente.
- La señal de sesión se envía por pestaña cada 20 segundos. **Continuar practicando** mantiene la pestaña activa; **Detener laboratorio y volver al inicio** cierra su sesión. Si otras pestañas siguen activas, el servidor continúa funcionando.
- El LAB se detiene al quedar sin sesiones durante 120 segundos. El valor se configura en `web/platform_config.json`.

## API local
- En el servicio del LAB (`127.0.0.1:8766`): `GET /`, `GET /styles.css`, `GET /app.js` y las APIs del analizador.
- En el servicio principal (`127.0.0.1:8765`): Home, página AWS, `/api/health`, `/api/lab/status`, `/api/lab/start` y las rutas de sesión del supervisor.
- `GET /api/health`: estado del servicio al que se consulta.
- `GET /api/files`: lista de archivos `.log` permitidos.
- `POST /api/analyze` con `{"file":"normal.log"}`: analiza un nombre de archivo disponible en `data/test`.
- `POST /api/tests`: ejecuta el conjunto automatizado.
- `GET /api/evidence`: devuelve el JSON generado.

La API no acepta rutas ni comandos proporcionados por el navegador. Solo permite nombres de archivos `.log` directos de `data/test`.

## Detener el servidor
- `detener_laboratorio.bat` detiene solo el LAB y se niega si hay sesiones activas.
- `detener_web.bat` detiene el LAB y el servicio principal, siempre que no haya sesiones activas.
- Alternativamente, pulsa **Ctrl+C** en la consola del servidor.
- Para inicio desde PowerShell, usa **Ctrl+C** en esa misma consola.

## Solución de problemas
- **Python no encontrado:** confirma que `py -3.12` o `python --version` respondan, o define `ACADEMYLAB_PYTHON`.
- **Puerto 8765 ocupado:** comprueba si el servicio principal responde. Si no se identifica, no cierres procesos Python ajenos.
- **Puerto 8766 ocupado:** vuelve al curso AWS e ingresa desde allí si el LAB ya está activo. Un proceso no identificado no se termina automáticamente.
- **Servidor principal no disponible:** inicia la plataforma antes de usar los BAT de parada; si no responde, los BAT no fuerzan la terminación de procesos.
- **No aparecen logs:** verifica que haya archivos `.log` dentro de `data/test`; la lista se actualiza automáticamente.
- **Error al analizar o ejecutar pruebas:** consulta el mensaje de error y la salida de Python en la interfaz o en la consola que inició el servidor.
- **Evidencia no disponible:** ejecuta primero un análisis; luego actualiza la sección Evidencia.
- **No abre la web:** confirma que la consola indica la URL local y que Edge visita exactamente `http://127.0.0.1:8765`.

## Análisis de línea de comandos

```powershell
python ".\scripts\analizar_logs.py" --input ".\data\sample_logs\operaciones.log"
python ".\scripts\analizar_logs.py" --input ".\data\sample_logs\operaciones.log" --json ".\evidence\resumen_logs.json"
python ".\scripts\run_tests.py"
```

## Métricas esperadas del log normal
- Eventos parseados: 10
- Operaciones únicas: 8
- Líneas no parseadas: 0
- Conteo por estado: ERROR=3, OK=4, PENDIENTE=3
- Importes por eventos: ERROR=2740.5, PENDIENTE=1326.25

## Notas del análisis
- Sin una secuencia no se puede deducir el estado actual de una operación que tenga múltiples eventos.
- Operaciones con importes inconsistentes se identifican como conflicto y no se incluyen en el total deduplicado.
- Las consultas SQL son material de referencia; deben ejecutarse solo bajo los permisos y procedimientos de AWS correspondientes.

Ver `docs/INSTRUCTIVO_FUNCIONAMIENTO.txt`, `docs/escenario_arquitectura.md` y `exercises/ejercicios.md` para las instrucciones, el escenario y los ejercicios.
