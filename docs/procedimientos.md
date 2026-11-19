# Procedimientos

## Convenciones generales
- Ejecutar comandos desde la raíz del proyecto salvo que se indique lo contrario.
- No modificar ni eliminar recursos AWS existentes.
- No incluir credenciales, `.env`, ni datos sensibles en archivos versionados.
- Separar datos reales, sintéticos y simulaciones.

## Instalación de herramientas (cuando esté autorizada)
Ejemplo con `winget` (requiere privilegios/intervención si Windows lo solicita):
```powershell
winget install -e --id Git.Git --source winget --accept-package-agreements --accept-source-agreements
winget install -e --id Python.Python.3.12 --source winget --accept-package-agreements --accept-source-agreements
```
Verificación breve:
```powershell
git --version
python --version
# o ruta local de usuario:
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" --version
```

## Ejecución de laboratorios
1. Leer el `README.md` del laboratorio en `labs/<lab>/`.
2. Revisar datos de prueba/sintéticos incluidos.
3. Ejecutar scripts Python localmente (sin conexión AWS) según instrucciones.
4. Ejecutar consultas SQL en Athena solo en modo lectura sobre recursos existentes, cuando se cuente con acceso autorizado fuera del repositorio.

## Git (cuando esté disponible)
```powershell
git init                # solo si no existe .git
git status
git add <archivos>
git commit -m "mensaje descriptivo"
```

## Registro de evidencias
- Guardar salidas y resultados en `labs/<lab>/evidence/`.
- Documentar comandos ejecutados y resultados verificables.
