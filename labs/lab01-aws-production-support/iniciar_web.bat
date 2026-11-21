@echo off
setlocal
cd /d "%~dp0"

call "%~dp0buscar_python.bat"
for %%I in ("%~dp0..\..\web\platform_server.py") do set "SERVER=%%~fI"
set "URL=http://127.0.0.1:8765"

if not defined PYTHON (
    echo ERROR: No se encontro Python 3.12 o superior.
    echo Instala Python 3.12 o define ACADEMYLAB_PYTHON con la ruta de python.exe.
    pause
    exit /b 1
)
if not exist "%SERVER%" (
    echo ERROR: No se encontro el servidor principal:
    echo %SERVER%
    pause
    exit /b 1
)

powershell -NoProfile -NonInteractive -Command "$url = '%URL%/api/health'; try { $health = Invoke-RestMethod -Uri $url -TimeoutSec 2; if ($health.status -eq 'ok' -and $health.service -eq 'academylab') { exit 0 } } catch {}; $listener = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue; if ($listener) { exit 2 } else { exit 1 }"
set "CHECK=%ERRORLEVEL%"
if "%CHECK%"=="0" (
    echo academyLab ya esta activa en %URL%.
    start "" "%URL%"
    exit /b 0
)
if not "%CHECK%"=="1" (
    echo ERROR: El puerto 8765 esta ocupado por un servicio que no se pudo identificar.
    echo No se inicio ni detuvo ningun proceso.
    pause
    exit /b 2
)

echo Iniciando academyLab...
start "academyLab - servidor principal" /D "%~dp0" "%PYTHON%" "%SERVER%"

powershell -NoProfile -NonInteractive -Command "$url = '%URL%/api/health'; for ($i = 0; $i -lt 30; $i++) { try { $health = Invoke-RestMethod -Uri $url -TimeoutSec 2; if ($health.status -eq 'ok' -and $health.service -eq 'academylab') { exit 0 } } catch {}; Start-Sleep -Milliseconds 500 }; exit 1"
if errorlevel 1 (
    echo ERROR: El servidor no respondio en el tiempo esperado.
    echo Revisa la ventana del servidor y el puerto 8765.
    pause
    exit /b 1
)

echo Plataforma activa: %URL%
echo El LAB 01 se inicia automaticamente al ingresar al curso AWS.
start "" "%URL%"
exit /b 0
