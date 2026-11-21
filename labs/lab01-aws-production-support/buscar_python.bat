@echo off
rem Define PYTHON con un interprete Python 3.12 o superior.
rem Orden: variable ACADEMYLAB_PYTHON, lanzador "py -3.12", "python" del PATH.
rem Uso: call "%~dp0buscar_python.bat"  (deja PYTHON vacio si no encuentra uno valido)
set "PYTHON="
if defined ACADEMYLAB_PYTHON (
    if exist "%ACADEMYLAB_PYTHON%" set "PYTHON=%ACADEMYLAB_PYTHON%"
    goto :eof
)
for /f "usebackq delims=" %%P in (`py -3.12 -c "import sys;print(sys.executable)" 2^>nul`) do set "PYTHON=%%P"
if defined PYTHON goto :eof
for /f "usebackq delims=" %%P in (`python -c "import sys;assert sys.version_info>=(3,12);print(sys.executable)" 2^>nul`) do set "PYTHON=%%P"
goto :eof
