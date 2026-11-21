# academyLab

Plataforma local de aprendizaje organizada por perfiles, rutas, niveles, cursos y
competencias para Cloud / Production Support. El contenido se practica con
escenarios y datos sintéticos; no se conecta a cuentas AWS.

## Iniciar la plataforma

1. Ejecuta con doble clic `labs\lab01-aws-production-support\iniciar_web.bat`.
2. Abre Microsoft Edge en `http://127.0.0.1:8765`.
3. Selecciona **Cloud / Production Support** y luego un nivel.

Requisitos: Windows, Python 3.12 o superior y Ubuntu
24.04 en WSL 2 para las prácticas Linux. No se requieren paquetes Python
adicionales, Docker ni credenciales AWS.

## Estado de la ruta Básica

- **SQL, AWS, Production Support, Redes y Python:** disponibles con módulos,
  prácticas verificables y evaluaciones corregidas por el servidor.
- **AWS Básico:** seis módulos, desde Cloud Computing hasta un escenario
  integrador de S3, IAM y observabilidad. Es formación conceptual con fixtures
  sintéticos; no accede a AWS ni modifica recursos.
- **Linux:** verificado con Ubuntu 24.04 en WSL 2 el 19/11/2026. Tiene siete
  módulos y 14 prácticas ejecutadas en Ubuntu real mediante una allowlist fija;
  no se aceptan comandos libres del navegador. Piloto de la Fase 3: las dos
  prácticas del módulo de logs exigen responder una pregunta a partir de la salida
  real; sus scripts nuevos todavía no se verificaron en Ubuntu (ver `docs/CAMBIOS.md`).
- **Proyecto integrador Básico:** exige las competencias disponibles previas.
  Se verificó el análisis Linux real con grep; su aprobación definitiva depende
  de completar las competencias y prácticas desde el progreso del alumno.
- **Intermedio y Avanzado:** bloqueados por requisitos previos.
- Otros perfiles profesionales se muestran como planificados.

La ruta no se considera aprobada mientras falten competencias obligatorias. No
se emiten certificaciones.

## Laboratorio LAB 01

LAB 01 — AWS Production Support es un recurso independiente para analizar logs y
ejecutar nueve pruebas automatizadas del analizador. Se inicia bajo demanda desde
la plataforma en `127.0.0.1:8766`; el servidor principal permanece en
`127.0.0.1:8765`.

El LAB usa datos locales de prueba y no ejecuta consultas Athena ni operaciones
AWS. Sus pruebas técnicas no otorgan competencias del alumno.

## Progreso y seguridad

Las prácticas y evaluaciones se corrigen en el servidor local. Las respuestas
correctas no se envían al navegador; el servidor calcula puntajes y comprueba
prerrequisitos antes de registrar actividades o competencias. La identidad
local se vincula mediante una cookie `HttpOnly` emitida por el servidor, no a
un identificador enviado en el cuerpo de la solicitud.

SQLite conserva el historial en `web\data\learning_progress.sqlite3`. Es una
persistencia local por navegador/equipo, sin cuentas, autenticación de
usuarios ni sincronización multiusuario. No compartas el perfil del navegador
ni el archivo de la base como si fuera un sistema multiusuario.

## Pruebas y documentación

Pruebas del servicio educativo y de la API:

```powershell
python -m unittest discover -s web\tests -v
python labs\lab01-aws-production-support\scripts\run_tests.py
```

Consulta:

- `docs\aws-basico.md` — objetivos y alcance del curso AWS.
- `docs\especificacion-evaluaciones.md` — puntajes, criterios y progreso.
- `docs\arquitectura.md` — servicios, persistencia y límites de seguridad.
- `docs\INSTRUCTIVO_FUNCIONAMIENTO.txt` — inicio, navegación, detención y
  solución de problemas.

## Detener servicios

- `labs\lab01-aws-production-support\detener_laboratorio.bat`: detiene solo el
  LAB si no quedan sesiones activas.
- `labs\lab01-aws-production-support\detener_web.bat`: solicita detener la
  plataforma local de forma ordenada.

Los servidores enlazan a `127.0.0.1`; los scripts no finalizan procesos Python
ajenos ni administran recursos AWS.
