@echo off
setlocal
cd /d "%~dp0"

set "PYTHON=C:\Users\juan\AppData\Local\Programs\Python\Python312\python.exe"
set "SERVER=%~dp0scripts\web_server.py"

if not exist "%PYTHON%" (
    echo ERROR: No se encontro Python 3.12 en:
    echo %PYTHON%
    pause
    exit /b 1
)

powershell -NoProfile -NonInteractive -Command "try { $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8766/api/health' -TimeoutSec 2; if ($health.status -eq 'ok' -and $health.service -eq 'aws-lab-01') { exit 0 } } catch {}; $listener = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue; if ($listener) { exit 2 } else { exit 1 }"
set "CHECK=%ERRORLEVEL%"
if "%CHECK%"=="0" (
    echo El servidor del LAB 01 ya esta activo.
    echo Ingresa desde academyLab para crear una sesion supervisada.
    pause
    exit /b 0
)
if not "%CHECK%"=="1" (
    echo ERROR: El puerto 8766 esta ocupado por un proceso no identificado.
    echo No se inicio ni detuvo ningun proceso.
    pause
    exit /b 2
)

echo Iniciando el servidor de respaldo del LAB 01 en 127.0.0.1:8766.
echo Para abrir una sesion supervisada, inicia la plataforma principal e ingresa desde academyLab.
"%PYTHON%" "%SERVER%"
if errorlevel 1 echo ERROR: El servidor del LAB 01 termino con un error.
pause
