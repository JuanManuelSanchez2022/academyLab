@echo off
setlocal
set "URL=http://127.0.0.1:8765"

powershell -NoProfile -NonInteractive -Command "$url = '%URL%/api/platform/shutdown'; try { $result = Invoke-RestMethod -Uri $url -Method Post -Body '{}' -ContentType 'application/json' -TimeoutSec 8; Write-Output $result.message } catch { $response = $_.Exception.Response; if ($response -and $response.StatusCode.value__ -eq 409) { Write-Output 'No se detuvo la plataforma: quedan sesiones del laboratorio activas. Usa primero Detener laboratorio y volver al inicio en cada pestana.'; exit 2 }; if ($response -and $response.StatusCode.value__ -eq 503) { Write-Output 'No se pudo confirmar la detencion del laboratorio. La plataforma sigue activa.'; exit 3 }; if ($_.Exception.Message -match 'Unable to connect|actively refused|timed out') { Write-Output 'El servidor principal no responde; no se finalizaron procesos Python.'; exit 0 }; Write-Error ('No se pudo detener academyLab: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 (
    echo La plataforma no se detuvo. Revisa el mensaje anterior.
    pause
    exit /b 1
)
echo La plataforma principal y el laboratorio administrado se detuvieron.
pause
