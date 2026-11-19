# Arquitectura local de academyLab

## Componentes

- **Plataforma principal:** `web/platform_server.py`, Python estándar, enlazado
  exclusivamente a `127.0.0.1:8765`. Sirve Home, perfiles, rutas, cursos,
  progreso y API educativa.
- **LAB 01:** `labs/lab01-aws-production-support/scripts/web_server.py`,
  enlazado a `127.0.0.1:8766` y arrancado bajo demanda. Sirve su propio
  analizador de logs y ocho pruebas técnicas. La plataforma principal no se
  detiene al salir del LAB.
- **Catálogo y contenidos:** `web/catalog/learning_catalog.json` describe
  perfiles, niveles, rutas, cursos, competencias, evaluaciones y disponibilidad.
  `web/catalog/basic_courses.json` contiene los módulos reutilizables,
  contenidos, prácticas, claves de corrección y escenarios.
- **Interfaz:** HTML estático bajo `web/`; `learning/common.js` inicializa la
  sesión del navegador y los módulos `learning/*.js` envían respuestas a la API.
- **Persistencia:** `web/progress_store.py` usa SQLite local mediante `sqlite3`.

## Identidad y flujo educativo

1. El navegador solicita `GET /api/learning/session`.
2. El servidor genera un token aleatorio, guarda en SQLite solo su hash asociado
   al perfil anónimo y entrega el token en una cookie `HttpOnly`, `SameSite=Strict`.
3. Las solicitudes educativas posteriores obtienen el alumno desde esa cookie.
   El servidor no usa `learner_id` enviado por el cliente ni un parámetro de URL
   como prueba de identidad.
4. El servicio carga el contenido de catálogo, verifica matrícula, competencias
   previas, orden de módulos y prácticas aprobadas antes de aceptar evaluaciones.
5. El servidor calcula puntajes y registra intentos, respuestas, resultados,
   competencias y evidencias en transacciones SQLite.

El origen de las mutaciones educativas se limita a la plataforma local. Los
intentos tienen secuencias únicas en la base y las transacciones de escritura
serializan la asignación del número de intento.

## Persistencia y límites

Las entidades incluyen `learner_profile`, `learner_session`, `course_progress`,
`module_progress`, `exercise_progress`, `learning_attempt`,
`competency_award` y `evidence`. El token de sesión no se guarda en claro.

Este diseño identifica un perfil local por cookie de navegador; no implementa
cuentas, autenticación de personas, recuperación de contraseñas ni
sincronización. Quien tenga acceso al mismo perfil del navegador o al archivo
SQLite local puede acceder a sus datos. No es una arquitectura multiusuario.
Para una plataforma remota se requieren identidad autenticada, autorización,
aislamiento, migraciones, copias de seguridad y política de retención.

## Restricciones de ejecución

- Las consultas de práctica SQL corren en SQLite en memoria, sobre fixtures
  sintéticos, con autorización de lectura limitada a la tabla de práctica.
- Las prácticas Python llaman procesadores predefinidos; no ejecutan código,
  comandos ni rutas enviados por el navegador.
- El curso AWS usa únicamente escenarios sintéticos. No hay SDK, credenciales
  ni llamadas a AWS.
- Linux usa Ubuntu real en WSL 2. El servidor acepta únicamente IDs de prácticas
  allowlisted, prepara directorios aislados por alumno/ejercicio y ejecuta
  scripts fijos con timeout y salida limitada. No existe una terminal que
  reciba comandos libres ni scripts enviados por el navegador.
- LAB 01 usa sus scripts y fixtures propios; las pruebas web se ejecutan en
  aislamiento para no sobrescribir evidencias históricas.

## Disponibilidad

AWS, SQL, Redes, Python y Production Support Básicos están disponibles con
prácticas y evaluaciones locales. AWS Básico contiene seis módulos y sigue siendo
conceptual. Linux está disponible con Ubuntu 24.04 real en WSL 2 y sus prácticas
allowlisted fueron verificadas el 19/11/2026. Intermedio y Avanzado permanecen
bloqueados por competencias previas.

No se ejecutan consultas Athena, operaciones AWS, cambios de IAM, operaciones
de S3, Glue, Lambda o CloudWatch, ni acciones administrativas de Windows/WSL.
