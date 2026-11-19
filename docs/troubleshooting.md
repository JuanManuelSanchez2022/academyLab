# Troubleshooting

## Instalación y herramientas
- **`winget` solicita acuerdos o región / error interactivo:** usar `--accept-source-agreements --accept-package-agreements --source winget --disable-interactivity` en sesión con permisos adecuados; si falla, aceptar acuerdos manualmente o ejecutar como Administrador.
- **Instalación requiere privilegios/UAC:** detener la operación y solicitar autorización/acción del usuario; no omitir controles de seguridad.
- **`python` apunta al alias de Microsoft Store:** usar la ruta real (`$env:LOCALAPPDATA\Programs\Python\Python312\python.exe`) o ajustar App execution aliases; verificar con `python --version`.
- **`git` no reconocido tras instalar:** cerrar y reabrir terminal para refrescar PATH; verificar `C:\Program Files\Git\cmd\git.exe`.

## WSL2 / Docker (pendientes, no instalados en esta etapa)
- `Microsoft-Windows-Subsystem-Linux` y `VirtualMachinePlatform` deshabilitadas: requieren habilitación con privilegios de Administrador y reinicio probable (no realizado).
- `wsl --version` / `wsl -l -v` no operativos en este estado: esperado sin configuración completa.

## Ejecución de scripts del laboratorio
- Ejecutar desde la raíz del proyecto o según rutas indicadas en el README del lab.
- Si hay errores de codificación en Windows, usar UTF-8 (`python -X utf8 ...` o asegurar lectura con `encoding="utf-8"`).
- Los scripts LAB 01 funcionan con datos de prueba locales; no requieren credenciales ni conexión AWS.

## AWS (solo lectura)
- No modificar tablas, buckets, archivos, logs ni configuraciones existentes.
- No crear recursos nuevos ni ejecutar servicios que generen costos.
- No almacenar credenciales en el repositorio.
