@echo off
setlocal
powershell -NoProfile -NonInteractive -Command "$url = 'http://127.0.0.1:8765/api/lab/manual-stop'; try { $result = Invoke-RestMethod -Uri $url -Method Post -Body '{}' -ContentType 'application/json' -TimeoutSec 8; Write-Output $result.message } catch { $response = $_.Exception.Response; if ($response -and $response.StatusCode.value__ -eq 409) { Write-Output 'El laboratorio sigue en uso. Cierra las pestanas con el boton del curso y vuelve a intentarlo.'; exit 2 }; if ($_.Exception.Message -match 'Unable to connect|actively refused|timed out') { Write-Output 'La plataforma principal no responde. No se detuvo ningun proceso; inicia la plataforma y vuelve a intentarlo.'; exit 3 }; Write-Error ('No se pudo detener el laboratorio: ' + $_.Exception.Message); exit 1 }"
if errorlevel 1 (
    pause
    exit /b 1
)
pause
