# AWS Básico — Cloud / Production Support

## Estado y límites

**Estado: Disponible como curso conceptual local.** No inicia sesión en AWS, no
usa SDK ni credenciales, no crea o consulta recursos y no genera costos. Los
ARN, nombres de objetos, alertas, mensajes y cifras de los ejercicios son
sintéticos.

El curso no pretende formar arquitectos cloud, ingenieros DevOps ni
administradores avanzados. Su objetivo es preparar para reconocer servicios
básicos, interpretar señales iniciales y documentar o escalar consultas de
soporte de producción de forma segura.

## Objetivo de aprendizaje

Al finalizar los seis módulos, el alumno podrá explicar modelos de nube,
identificar servicios y alcance regional, razonar sobre permisos IAM y rutas
S3, distinguir señales de observabilidad y elaborar una actualización técnica
que separe hechos, hipótesis e información pendiente.

## Módulos

1. **Introducción a Cloud Computing:** infraestructura local y nube, IaaS,
   PaaS, SaaS, responsabilidad compartida, regiones, zonas, disponibilidad y
   tolerancia a fallos. Incluye clasificación de escenarios y selección de un
   modelo de servicio.
2. **Fundamentos de AWS:** categorías de servicios, regiones, zonas, consola,
   fuentes posibles de costos y cómo acotar una señal antes de escalar.
3. **IAM y seguridad:** usuarios, grupos, roles, políticas, acción/recurso,
   mínimo privilegio, MFA, credenciales y análisis seguro de AccessDenied.
4. **Amazon S3:** buckets, objetos, claves, prefijos, regiones, clases de
   almacenamiento, acceso, versionado y cifrado.
5. **Introducción a observabilidad:** logs, métricas, eventos, alarmas,
   CloudWatch y CloudWatch Logs; una alarma se trata como señal, no como causa
   raíz.
6. **Integración y soporte:** incidente sintético de acceso denegado a un objeto
   S3 junto con una alerta. El alumno identifica servicios, interpreta la clave,
   considera qué señales aportarían logs/métricas, separa hipótesis de hechos,
   propone un siguiente paso autorizado y redacta un informe.

## Estructura pedagógica y evaluación

Cada módulo incluye objetivo, conceptos, explicación, ejemplo resuelto,
práctica guiada, práctica independiente, verificación, errores frecuentes,
troubleshooting y una evaluación de cinco preguntas.

- Las evaluaciones se corrigen en el servidor; se requiere 80 %.
- Los intentos son ilimitados y se conserva el historial.
- Las respuestas incorrectas incluyen explicación y temas recomendados para
  repasar.
- La evaluación del sexto módulo integra servicios y razonamiento de incidentes;
  no repite literalmente las respuestas de las prácticas.
- La práctica independiente del módulo integrador verifica los campos del
  informe y que el resumen cite el identificador de alarma y la ruta sintética.
- La competencia `aws-basic-concepts` se otorga únicamente al completar todos
  los módulos, las dos prácticas de cada módulo y sus evaluaciones.

## Uso

1. Inicia la plataforma con `labs\lab01-aws-production-support\iniciar_web.bat`.
2. Abre `http://127.0.0.1:8765` en Microsoft Edge.
3. Selecciona **Cloud / Production Support → Básico → AWS**.
4. Completa las prácticas guiada e independiente de cada módulo para habilitar
   su evaluación; avanza en orden.
5. Consulta intentos y competencias en **Mi progreso**.

La persistencia es local en SQLite y el perfil está vinculado a una cookie de
navegador. No hay cuentas ni sincronización multiusuario.

## Validación de desarrollo

El catálogo enlaza los seis módulos y sus seis evaluaciones con el curso AWS.
Las pruebas completan las prácticas y evaluaciones de los cinco cursos
disponibles, comprueban el bloqueo de módulos fuera de orden, verifican que las
claves de respuesta no se exponen y confirman que el puntaje se calcula en el
servidor. No se realizan acciones AWS durante las pruebas.
