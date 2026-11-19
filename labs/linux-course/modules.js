window.LINUX_COURSE_MODULES = [
  {
    "number": 1,
    "id": "introduccion",
    "title": "Introducción a Linux, distribuciones, terminal y shell",
    "explanation": "Conoce el sistema operativo Linux, las distribuciones, la terminal y Bash. Ubuntu será el entorno real del curso cuando WSL esté habilitado.",
    "concepts": ["Distribución y kernel", "Shell interactiva", "Usuario y directorio de trabajo"],
    "exercises": [
      {
        "title": "Identificar el entorno",
        "task": "Consultar la versión del kernel, la distribución y el usuario actual.",
        "commands": ["uname -a", "cat /etc/os-release", "whoami"],
        "expected": "El verificador confirma que se ejecuta en Ubuntu y devuelve datos reales del sistema; los valores dependen de la instalación.",
        "verification": "Comparar el identificador de distribución con Ubuntu y confirmar que la identidad no corresponde a root."
      }
    ],
  },
  {
    "number": 2,
    "id": "navegacion",
    "title": "Navegación",
    "explanation": "Ubícate en el árbol de directorios y reconoce los archivos visibles dentro del espacio aislado del curso.",
    "concepts": ["pwd", "ls", "cd", "whoami", "clear"],
    "exercises": [
      {
        "title": "Explorar el espacio de prácticas",
        "task": "Consultar el directorio actual, listar su contenido y confirmar el usuario de Ubuntu.",
        "commands": ["pwd", "ls -la", "whoami", "cd <directorio-de-practica>", "clear"],
        "expected": "El directorio actual corresponde al espacio dedicado del curso Linux y el usuario no es root.",
        "verification": "Comprobar que pwd resuelve dentro de ~/academyLab/linux-course y que el usuario no es root."
      }
    ],
  },
  {
    "number": 3,
    "id": "archivos",
    "title": "Archivos y directorios",
    "explanation": "Crear y organizar archivos de práctica dentro de la carpeta aislada del curso.",
    "concepts": ["mkdir", "touch", "cp", "mv", "rm", "cat"],
    "exercises": [
      {
        "title": "Organizar archivos de práctica",
        "task": "Crear un subdirectorio, crear y leer un archivo, copiarlo, mover la copia y eliminar únicamente los archivos de prueba creados.",
        "commands": ["mkdir practica", "touch practica/nota.txt", "cat practica/nota.txt", "cp practica/nota.txt practica/copia.txt", "mv practica/copia.txt practica/renombrada.txt", "rm practica/renombrada.txt"],
        "expected": "Las operaciones quedan limitadas al espacio del curso; la verificación comprueba que la copia y el movimiento se completaron.",
        "verification": "Comprobar rutas bajo el workspace y que solo desaparecen los archivos creados por este ejercicio."
      }
    ]
  },
  {
    "number": 4,
    "id": "lectura-busqueda",
    "title": "Lectura y análisis",
    "explanation": "Inspeccionar archivos de texto y localizar líneas o rutas que cumplan criterios concretos.",
    "concepts": ["head", "tail", "less", "grep", "find"],
    "exercises": [
      {
        "title": "Buscar un evento de log",
        "task": "Usar grep y find sobre los archivos de práctica. less se presentará como lectura paginada cuando la integración permita una sesión interactiva.",
        "commands": ["head -n 5 <archivo>", "tail -n 5 <archivo>", "grep ERROR <archivo>", "find . -type f"],
        "expected": "El verificador encuentra coincidencias reales dentro de los archivos habilitados del curso.",
        "verification": "Comparar las rutas y líneas encontradas por los comandos reales con el criterio del ejercicio."
      }
    ]
  },
  {
    "number": 5,
    "id": "redirecciones",
    "title": "Redirecciones y composición",
    "explanation": "Guardar salidas, anexar resultados y combinar operaciones aprobadas sin entregar una consola de shell libre al navegador.",
    "concepts": [">", ">>", "|", "&&"],
    "exercises": [
      {
        "title": "Crear un resumen filtrado",
        "task": "Guardar y anexar resultados de una búsqueda en archivos del espacio de prácticas; combinar pasos solo mediante flujos de ejercicio previamente definidos.",
        "commands": ["grep ERROR <archivo> > resumen.txt", "grep PENDIENTE <archivo> >> resumen.txt", "cat resumen.txt", "grep ERROR <archivo> | wc -l"],
        "expected": "Los archivos contienen las líneas filtradas esperadas y ningún comando se ejecuta fuera de la lista permitida.",
        "verification": "Comprobar el contenido creado bajo el workspace y el conteo real devuelto por la búsqueda."
      }
    ]
  },
  {
    "number": 6,
    "id": "permisos",
    "title": "Permisos, usuarios y grupos",
    "explanation": "Interpretar permisos y aplicar chmod solamente a archivos de práctica. Las prácticas normales no usarán sudo ni cambiarán usuarios o grupos.",
    "concepts": ["chmod", "id", "groups", "Permisos de lectura, escritura y ejecución"],
    "exercises": [
      {
        "title": "Restringir un archivo de práctica",
        "task": "Consultar identidad y grupos, y cambiar los permisos de un archivo creado dentro del espacio Linux.",
        "commands": ["id", "groups", "chmod 600 practica/nota.txt", "ls -l practica/nota.txt"],
        "expected": "El modo de permisos coincide con el solicitado y el archivo permanece dentro del espacio del curso.",
        "verification": "Consultar los permisos efectivos del archivo y confirmar su ubicación dentro del workspace."
      }
    ]
  },
  {
    "number": 7,
    "id": "procesos",
    "title": "Procesos y servicios",
    "explanation": "Inspeccionar procesos y estados del sistema. top se consultará en modo de una sola captura; kill solo podrá afectar procesos de práctica creados y registrados por el backend.",
    "concepts": ["ps", "top", "kill", "Identificador de proceso (PID)"],
    "exercises": [
      {
        "title": "Inspeccionar un proceso de práctica",
        "task": "Consultar procesos y, cuando se habilite el backend, finalizar únicamente un proceso temporal iniciado por el propio ejercicio.",
        "commands": ["ps", "top -b -n 1", "kill <PID-del-proceso-de-practica>"],
        "expected": "El proceso señalado pertenece al ejercicio y deja de aparecer tras su finalización.",
        "verification": "Aceptar kill solo para el PID temporal registrado por el backend para esta práctica; verificar que terminó."
      }
    ]
  },
  {
    "number": 8,
    "id": "logs-support",
    "title": "Logs y troubleshooting",
    "explanation": "Filtrar registros locales de práctica y relacionar patrones de error con el diagnóstico de Production Support del LAB 01 AWS. No se leerán logs privados de Windows ni logs de sistema fuera del alcance permitido.",
    "concepts": ["grep", "head", "tail", "find", "Correlación temporal"],
    "exercises": [
      {
        "title": "Diagnosticar eventos de Production Support",
        "task": "Buscar eventos ERROR y PENDIENTE en un log sintético del curso y comparar su interpretación con los conceptos del LAB 01.",
        "commands": ["grep ERROR fixtures/production-support.log", "grep PENDIENTE fixtures/production-support.log", "grep ERROR fixtures/production-support.log | wc -l"],
        "expected": "El verificador muestra las coincidencias que realmente devolvió grep y comprueba el conteo del ejercicio contra el archivo de práctica.",
        "verification": "Contar las líneas que realmente coinciden en el fixture y cotejarlas con el registro del ejercicio."
      }
    ]
  }
];
