# Especificación de evaluaciones y progreso

## Alcance actual

La ruta Básica de Cloud / Production Support incluye cursos disponibles de SQL,
AWS, Production Support, Redes y Python. Cada módulo tiene objetivo,
explicación, ejemplo resuelto, práctica guiada e independiente, verificación,
troubleshooting y evaluación. AWS Básico contiene seis módulos y su último
módulo evalúa un incidente integrador. Linux tiene siete módulos y 14 prácticas
de comandos predefinidos; su disponibilidad depende de comprobar Ubuntu en WSL 2,
un usuario no root y las herramientas requeridas. Hasta esa comprobación no se
ejecutan prácticas ni se otorga la competencia operativa.

Intermedio y Avanzado permanecen bloqueados por requisitos previos. El proyecto
integrador Básico exige las cinco competencias disponibles previas. Sus
criterios automáticos pueden verificarse, pero la aprobación total requiere la
competencia Linux Básica y una ejecución real de grep sobre una copia aislada del
log del proyecto en Ubuntu.

## Reglas generales

- Puntaje mínimo de evaluaciones: **80 %**. Cada evaluación de módulo contiene
  cinco preguntas; se requieren al menos cuatro correctas.
- Los intentos son ilimitados y se conserva el historial completo.
- Las opciones se mezclan en la interfaz. Las respuestas correctas, validadores
  y recomendaciones internas no se entregan al navegador.
- El servidor valida identificadores y respuestas, calcula puntajes y registra
  resultados; no acepta un puntaje, estado de aprobado o competencia enviados
  por el cliente.
- Antes de enviar ejercicios se requiere matrícula y prerrequisitos del curso.
  Los módulos se habilitan en orden. Una evaluación requiere aprobar ambas
  prácticas de su módulo.
- La retroalimentación explica respuestas incorrectas y recomienda temas de
  repaso antes de repetir. No se bloquean los intentos posteriores.
- Las competencias solo se otorgan cuando se completan todas las prácticas y
  evaluaciones requeridas de todos los módulos y no falta un entorno obligatorio.
- No se emiten certificaciones profesionales.

## Tipos de evaluación

### Conceptual

Evalúa conceptos aplicados a escenarios, responsabilidades, límites de
servicios y toma de decisiones. AWS Básico incluye evaluaciones conceptuales
para los primeros cinco módulos.

### Ejercicio práctico

Comprueba resultados con condiciones reproducibles. SQL corre en SQLite en
memoria sobre datos sintéticos, en modo de lectura y con una tabla autorizada.
Python llama procesadores predefinidos sobre fixtures locales; no ejecuta código
arbitrario. Los ejercicios AWS verifican elecciones y reportes estructurados
contra reglas del escenario.

### Laboratorio verificable

Debe definir requisitos, acciones permitidas, estado inicial, verificaciones y
limpieza segura. LAB 01 conserva su propio analizador de logs y ocho pruebas
técnicas. Las pruebas del programa no cuentan como evaluación ni otorgan una
competencia del alumno. Linux ejecuta únicamente secuencias allowlisted por el
servidor, dentro de un directorio dedicado por alumno y ejercicio, con límite de
tiempo y salida. No acepta comandos, rutas, PID ni scripts del navegador. La
práctica de kill solo termina el proceso temporal iniciado por el mismo script.

### Resolución de incidentes

Evalúa evidencia citada, alcance, correlación, separación de hechos e hipótesis,
impacto, siguiente paso, escalamiento y documentación. El módulo integrador AWS
usa un AccessDenied y una alarma sintéticos; el servidor comprueba servicio,
señales, alcance y resumen. No acepta una causa inventada ni consulta CloudWatch.

### Proyecto integrador

El proyecto Básico combina eventos, consulta SQL de cantidades e importes,
procesamiento Python, conectividad conceptual, referencia de observabilidad e
informe. Requiere competencias aprobadas de Redes, SQL, AWS, Python y Production
Support antes de aceptar un intento. Los criterios verificables disponibles no
sustituyen el requisito Linux real. También requiere una competencia Linux
otorgada después de los siete módulos y comandos reales. El servidor ejecuta
grep sobre una copia del log del proyecto, compara los identificadores con la
entrega y conserva su salida como evidencia. El proyecto no se aprueba por tener
un puntaje alto si falta cualquiera de esos criterios críticos.

## Seguridad de evaluación y API

- La identidad del alumno se obtiene de una cookie `HttpOnly`, `SameSite=Strict`
  emitida por `GET /api/learning/session`. La base guarda solo el hash del token.
- `learner_id` suministrado en JSON o en la URL no se acepta como identidad.
- Las mutaciones educativas requieren un origen local permitido.
- La API no acepta respuestas de scoring o estados de aprobación del cliente.
- Evaluaciones, prácticas, competencias y proyecto comprueban matrícula y
  prerrequisitos del lado del servidor; la UI deshabilita actividades que aún
  no corresponden.
- El runtime Linux usa ejercicios identificados por una allowlist del servidor;
  la API rechaza campos de comandos o scripts enviados por el cliente.
- Las escrituras SQLite verifican la matrícula en la transacción y mantienen
  números de intento únicos, incluso ante envíos concurrentes.

El token es una sesión anónima de navegador local, no una cuenta autenticada.
Quien tenga acceso a ese navegador o a la base SQLite del equipo puede acceder a
sus datos. No usar este mecanismo para una plataforma multiusuario o expuesta a
Internet.

## Datos y trazabilidad

SQLite conserva perfil anónimo, sesión, cursos y módulos, estado de ejercicios,
intentos, respuestas, puntajes, resultados, competencias y referencias de
evidencia. Cada aprobación queda enlazada al intento que la justifica. La
interfaz **Mi progreso** consulta la sesión activa y presenta su historial.

La base se encuentra en `web/data/learning_progress.sqlite3`. Los fixtures de
las prácticas y del proyecto son sintéticos. No se deben registrar contraseñas,
credenciales AWS ni otros datos sensibles.

## Modelo de datos lógico

Se mantienen separados perfil profesional, ruta, curso reutilizable, nivel,
módulo, evaluación, competencia, sesión anónima, intento y evidencia. La ruta
referencia cursos por identificador y no duplica contenidos. La persistencia
implementa `learner_profile`, `learner_session`, `course_progress`,
`module_progress`, `exercise_progress`, `learning_attempt`,
`competency_award` y `evidence`.

SQLite local no ofrece autenticación, sincronización multiusuario,
administración central, copias de seguridad compartidas ni concurrencia
distribuida. Antes de publicar o ampliar el uso se debe diseñar identidad,
autorización, aislamiento, privacidad, migración y retención.

## Verificación automatizada

Los tests de `web/tests/` comprueban matrícula, orden de módulos, prerrequisitos,
feedback, puntaje calculado en el servidor, bloqueo Linux, acceso a sesiones,
rechazo de sustitución de identidad, persistencia tras reiniciar el servidor y
secuencias de intento bajo concurrencia, además de la política de allowlist y
los criterios críticos del proyecto. Los tests unitarios del runtime no sustituyen
la verificación real en Ubuntu. El recorrido de navegador y las pruebas LAB se
reportan por separado; ninguno se considera una certificación.
