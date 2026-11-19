# Auditoría del Entorno de Desarrollo

**Proyecto:** academyLab
**Fecha de auditoría:** 2026-11-10 (UTC: 2026-11-11T02:21:28Z)
**Actualización WSL (ETAPA 1):** 2026-11-11 (UTC: 2026-11-11T02:32:43Z)
**Verificación preinstalación (ETAPA 2):** 2026-11-11 (UTC: 2026-11-11T16:31:59Z)
**Etapa:** ETAPA 2 - Verificación preinstalación (finalizada, sin instalaciones)
**Equipo:** DESKTOP-L05N1FK

## 1. Resumen ejecutivo

| Verificación | Resultado | Observación |
|---|---|---|
| Windows 10 22H2 (19045) | **Compatible** | `Windows 10 Pro`, DisplayVersion `22H2`, Build `19045.2965`; compatible con WSL2 y Docker Desktop, sujeto a requisitos adicionales |
| Arquitectura x64 | OK | `64-bit` / `x64-based PC` |
| CPU / virtualización | OK | Intel Core i7-6700HQ 4C/8T; virtualización firmware, SLAT y VM Monitor Mode Extensions habilitadas |
| Espacio en disco | OK (C:) | C: ~378 GB libres; evaluar espacio adicional para Docker/WSL |
| winget | Disponible | `v1.29.380` |
| Python / Git / Docker / Node.js / npm | No instalados | No encontrados en PATH |
| WSL / WSL2 | **No configurado** | `wsl.exe` presente; `--status` reconocido pero sin estado operativo útil; `--version` y `-l -v` no operativos (uso/ayuda); características deshabilitadas (evidencia registro); sin distribuciones |
| Visual Studio Code | Instalado | `1.145.2` (`c4453f8...`) |

**Condición:** Windows 10 Pro 22H2 build 19045.2965 es compatible con el objetivo de preparar WSL2/Docker Desktop, sujeto a habilitación de características, privilegios de administrador y posibles reinicios. No se realizaron instalaciones ni cambios de configuración.

## 2. Sistema operativo

| Campo | Valor |
|---|---|
| Producto | Windows 10 Pro |
| WindowsVersion (registro) | 2009 |
| DisplayVersion | 22H2 |
| ReleaseId | 2009 |
| CurrentBuild | 19045 |
| UBR (parche) | 2965 |
| OS Build (systeminfo) | 10.0.19045 N/A Build 19045 |
| HAL | 10.0.19041.2728 |
| Arquitectura OS | 64-bit |
| Tipo de sistema | x64-based PC |

**Comandos de verificación:**
```powershell
Get-ComputerInfo | Select-Object WindowsProductName, WindowsVersion, OsHardwareAbstractionLayer, OsArchitecture, OsBuildNumber
systeminfo | Select-String "OS Name|OS Version|System Type"
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' | Select-Object ProductName, DisplayVersion, ReleaseId, CurrentBuild, UBR
```

## 3. Hardware

| Componente | Valor |
|---|---|
| Equipo | DESKTOP-L05N1FK |
| Procesador | Intel(R) Core(TM) i7-6700HQ CPU @ 2.60GHz |
| Núcleos físicos | 4 |
| Procesadores lógicos | 8 |
| Virtualización habilitada en firmware | True |
| Second Level Address Translation (SLAT) | True |
| VM Monitor Mode Extensions | True |
| Memoria física total | 8,449,978,368 bytes (~8,059 MB / ~7.87 GiB) |
| Memoria física disponible (referencia inicial) | ~1,357 MB |

**Comandos de verificación:**
```powershell
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, VirtualizationFirmwareEnabled, SecondLevelAddressTranslationExtensions, VMMonitorModeExtensions
systeminfo | Select-String "Total Physical Memory|Available Physical Memory"
```

## 4. Almacenamiento

| Unidad | Usado | Libre | Raíz |
|---:|---:|---:|---|
| C: | 72,699,899,904 B (~67.7 GB) | 406,222,696,448 B (~378.3 GB) | C:\ |
| D: | 32,018,432 B (~30.5 MB) | 20,406,272 B (~19.5 MB) | D:\ |
| E: | 66,146,463,744 B (~61.6 GB) | 208,291,184,640 B (~194.0 GB) | E:\ |

**Comando de verificación:**
```powershell
Get-PSDrive -PSProvider FileSystem | Select-Object Name, Used, Free, Root
```

## 5. Estado de virtualización y WSL (ETAPA 1)

### 5.1 Virtualización (hardware)
| Verificación | Resultado |
|---|---|
| Virtualización en firmware (CPU) | Habilitada (`VirtualizationFirmwareEnabled: True`) |

### 5.2 Comportamiento real de `wsl.exe` (ETAPA 1)
| Comando | Resultado observado |
|---|---|
| `wsl --status` | **Reconocido** (invocable). Devolvió texto de uso/ayuda, sin estado operativo detallado. |
| `wsl --version` | **No reconocido** como opción operativa; devolvió texto de uso/ayuda. |
| `wsl -l -v` | **No reconocido** como opción operativa; devolvió texto de uso/ayuda. |

### 5.3 Características de Windows requeridas para WSL2 (ETAPA 1)
| Característica | Estado reportado |
|---|---|
| `Microsoft-Windows-Subsystem-Linux` | **Disabled** |
| `VirtualMachinePlatform` | **Disabled** |

### 5.4 Distribuciones y estado de WSL2 (ETAPA 1)
| Verificación | Resultado |
|---|---|
| Distribuciones Linux instaladas | **No hay evidencia de distribuciones Linux instaladas** |
| WSL2 | **Pendiente de instalación y configuración** |

## 6. Herramientas requeridas (estado actual)

| Herramienta | Estado | Ubicación / Versión | Evidencia |
|---|---|---|---|
| winget | Disponible | `C:\Users\juan\AppData\Local\Microsoft\WindowsApps\winget.exe` | `winget --version` → `v1.29.380` |
| Python | No instalado | No encontrado en PATH | `Get-Command python` sin resultado |
| Git | No instalado | No encontrado en PATH | `Get-Command git` sin resultado |
| WSL | Presente, no configurado | `C:\WINDOWS\system32\wsl.exe` | Ver secciones 5 y 11 |
| Docker | No instalado | No encontrado en PATH | `Get-Command docker` sin resultado |
| Node.js | No instalado | No encontrado en PATH | `Get-Command node` sin resultado |
| npm | No instalado | No encontrado en PATH | `Get-Command npm` sin resultado |
| Visual Studio Code | Instalado | `C:\Users\juan\AppData\Local\Programs\Microsoft VS Code\bin\code.cmd` | `code --version` → `1.145.2` / commit `c4453f8ea430795f941c1b2ff6c9321135a74a02` |

**Comandos de verificación:**
```powershell
Get-Command winget,python,git,wsl,docker,node,npm,code -ErrorAction SilentlyContinue | Select-Object Name,Source
winget --version
code --version
```

## 7. Estado del directorio del proyecto

| Ruta | Estado |
|---|---|
| `C:\dev\academyLab` | Nombre GitHub/identidad; ruta fisica planeada |
| `C:\dev\aws-cloud-academy` | Ruta fisica vigente mientras VS Code mantiene el workspace abierto |
| `C:\dev\aws-cloud-academy\docs\diagnostico-entorno.md` | Documentacion historica conservada |
| `C:\dev\aws-cloud-academy\docs\auditoria_entorno.md` | Actualizado con el estado academyLab |

## 8. Compatibilidad y decisión (ETAPA 1)
- **Requisito objetivo:** Windows 10 22H2, compilación 19045.
- **Resultado:** `Windows 10 Pro 22H2`, build `19045.2965` — **compatible con el objetivo de preparar WSL2**, sujeto a verificar requisitos adicionales.
- **Acción realizada:** Auditoría y actualización documental únicamente. No se habilitaron características, no se instaló WSL ni Ubuntu.

## 9. Hallazgos y riesgos (acumulados ETAPA 1)
1. **WSL2 pendiente:** características necesarias deshabilitadas; sin distribuciones. Preparación requerirá elevación y posible reinicio.
2. **Comportamiento de `wsl.exe`:** `--status` invocable pero sin estado operativo útil; `--version` y `-l -v` no reconocidos como opciones operativas.
3. **Herramientas base faltantes:** Git, Python 3.12, Docker Desktop, Node.js/npm.
4. **RAM disponible limitada** en auditoría inicial (~1.3 GB libres).

## 10. Cierre de ETAPA 1
**ETAPA 1: AUDITORÍA DEL SISTEMA — FINALIZADA.** Sin instalaciones, sin habilitación de características, sin cambios en otros documentos.

---

## 11. ETAPA 2: Verificación preinstalación (sin cambios en el sistema)

**Fecha/hora:** 2026-11-11 (UTC: 2026-11-11T16:31:59Z)
**Restricciones aplicadas:** No se instalaron programas, no se habilitaron características de Windows, no se instaló Ubuntu, no se modificaron archivos existentes distintos de este informe, no se modificó BIOS, no se crearon recursos AWS, no se avanzó a ETAPA 3.

### 11.1 Sesión de PowerShell y privilegios de administrador

| Verificación | Resultado |
|---|---|
| Usuario actual | `DESKTOP-L05N1FK\juan` |
| Sesión elevada (Administrador) | **No** (`IsAdmin=False`) |

**Comando de verificación:**
```powershell
$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
[Security.Principal.WindowsIdentity]::GetCurrent().Name
```

**Resultado/limitación:** No fue posible abrir una sesión de PowerShell con privilegios de administrador desde este contexto no elevado sin intervención del usuario (UAC). Se realizaron todas las verificaciones no destructivas disponibles sin elevación. La confirmación directa de características mediante `Get-WindowsOptionalFeature -Online`/DISM requiere sesión elevada y queda pendiente para ejecución en PowerShell como Administrador cuando se autorice.

### 11.2 Verificación del estado de características requeridas para WSL2

| Característica | Estado (evidencia no elevada) | Método | Observación |
|---|---|---|---|
| `Microsoft-Windows-Subsystem-Linux` | **Disabled (evidencia: Selection=0)** | Registro CBS Notifications | `HKLM:\...\Component Based Servicing\Notifications\OptionalFeatures\Microsoft-Windows-Subsystem-Linux` → `Selection=0`, `LastModified=2026/11/10/20:11:30` |
| `VirtualMachinePlatform` | **Disabled (evidencia: Selection=0)** | Registro CBS Notifications | `HKLM:\...\Component Based Servicing\Notifications\OptionalFeatures\VirtualMachinePlatform` → `Selection=0`, `LastModified=2026/11/10/20:11:30` |

**Comandos de verificación:**
```powershell
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Notifications\OptionalFeatures\Microsoft-Windows-Subsystem-Linux'
Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\Notifications\OptionalFeatures\VirtualMachinePlatform'
# Confirmación directa (requiere elevación, no ejecutada con éxito en esta sesión):
Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux
Get-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform
```

### 11.3 Virtualización del procesador y estado del hipervisor

| Verificación | Resultado |
|---|---|
| Virtualización habilitada en firmware | **True** |
| SLAT (Second Level Address Translation) | **True** |
| VM Monitor Mode Extensions | **True** |
| Hyper-V Requirements (systeminfo) | `VM Monitor Mode Extensions: Yes` ; `Virtualization Enabled In Firmware: Yes` |

**Comandos de verificación:**
```powershell
Get-CimInstance Win32_Processor | Select-Object Name, VirtualizationFirmwareEnabled, SecondLevelAddressTranslationExtensions, VMMonitorModeExtensions
systeminfo | Select-String "Hyper-V|Virtualization|VM Monitor"
```

**Interpretación:** El procesador/firmware cumplen los prerrequisitos de virtualización necesarios para WSL2 y plataformas de virtualización. Las características de Windows requeridas permanecen deshabilitadas (ver 11.2), por lo que el entorno WSL2 no está operativo.

### 11.4 Distribuciones Linux instaladas (métodos compatibles)

| Método | Resultado |
|---|---|
| Registro `HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss` | **No existe** (`LXSS_NOT_FOUND`) |
| Directorio `%LOCALAPPDATA%\lxss` | **No existe** (`lxss_dir_exists=False`) |
| Paquetes en `%LOCALAPPDATA%\Packages` (Canonical/Ubuntu/Debian/Linux/Alpine/SUSE/Kali/Pengwin) | **Sin coincidencias** |
| `wsl --status` | Invocable; salida de uso/ayuda (sin estado operativo detallado) |
| `wsl --version` | No operativo como opción en este entorno (salida de uso/ayuda) |
| `wsl -l -v` | No operativo como opción en este entorno (salida de uso/ayuda) |

**Comandos de verificación:**
```powershell
Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Lxss'
Test-Path "$env:LOCALAPPDATA\lxss"
Get-ChildItem "$env:LOCALAPPDATA\Packages" -Directory | Where-Object { $_.Name -match 'Canonical|Ubuntu|Debian|Linux|Alpine|SUSE|Kali|Pengwin' }
wsl --status
wsl --version
wsl -l -v
```

**Conclusión:** No hay evidencia de distribuciones Linux instaladas.

### 11.5 Compatibilidad de WSL2 y Docker Desktop con Windows 10 Pro 22H2 build 19045.2965

| Componente | Compatibilidad con este sistema | Requisitos clave y estado |
|---|---|---|
| **WSL2** | **Compatible (condicional)** | Windows 10 1903+ (build 18362+) soporta WSL2; **19045.2965 cumple**. Requisitos: x64 (**OK**), virtualización en firmware y SLAT (**OK**), `Microsoft-Windows-Subsystem-Linux` y `VirtualMachinePlatform` habilitadas (**pendiente**, evidencia de deshabilitadas), componentes/kernel WSL actualizados y distribución Linux (**pendientes**), posible reinicio. |
| **Docker Desktop** | **Compatible (condicional)** | Compatible con Windows 10/11 64-bit moderno; backend WSL2 recomendado. Requisitos: virtualización/SLAT (**OK**), WSL2 operativo (**pendiente**), RAM suficiente (8 GB total en equipo: margen justo, recomendado cerrar carga), características WSL2 habilitadas e integración configurada tras instalación (**pendiente**). |

**Conclusión:** La versión/edición/arquitectura de Windows y las capacidades de virtualización del hardware son compatibles. Los bloqueos actuales son de configuración y componentes no instalados (no de incompatibilidad de SO).

### 11.6 Requisitos adicionales y posibles reinicios identificados

| Requisito / acción futura (identificada, no ejecutada) | Motivo | Reinicio probable |
|---|---|---|
| Abrir PowerShell **como Administrador** | Habilitar características (`Enable-WindowsOptionalFeature`/DISM), verificar con `Get-WindowsOptionalFeature -Online` e instalaciones a nivel sistema | No (abrir sesión) |
| Habilitar `Microsoft-Windows-Subsystem-Linux` | Requisito base WSL | **Sí, probable** |
| Habilitar `VirtualMachinePlatform` | Requisito para WSL2 | **Sí, probable** |
| Reinicio del sistema tras habilitar características | Aplicar cambios de Windows Features | **Sí** |
| Configurar WSL2 por defecto / actualizar componentes/kernel WSL | Operación correcta de WSL2 y compatibilidad Docker | Posible, según método/estado |
| Instalar distribución Linux (Ubuntu 24.04) | Entorno Linux requerido | No habitualmente, tras reinicio previo si aplica |
| Instalar Docker Desktop y configurar backend WSL2 | Contenedores | Posible cierre de sesión/reinicio o relanzamiento |
| Verificar disponibilidad de RAM/disco durante uso | 8 GB RAM y crecimiento de imágenes/contenedores | No |

**Secuencia típica esperada (referencial, sujeta a autorización):** elevar privilegios → habilitar características → reiniciar → configurar WSL2 e instalar Ubuntu → verificar → instalar Docker Desktop → verificar.

### 11.7 Integridad y alcance

| Verificación | Resultado |
|---|---|
| `docs/diagnostico-entorno.md` | **Intacto** (no modificado; SHA256 `9E51D4F2DB3C60EBEB0B4AF0A286E548E9DD3C7B88DBCF3447ACB3DFC13A1C56`, 3479 bytes) |
| Otros documentos | **No modificados** |
| Instalaciones / habilitación de características / Ubuntu / BIOS / AWS / ETAPA 3 | **No realizadas** |

### 11.8 Cierre de ETAPA 2

**ETAPA 2: VERIFICACIÓN PREINSTALACIÓN — FINALIZADA (solo verificación).**
Resultados documentados en `docs/auditoria_entorno.md`. **Se requiere autorización expresa** para instalar herramientas, habilitar características de Windows o avanzar a ETAPA 3.

---
*Informe actualizado a partir de verificaciones reales ejecutadas en PowerShell (sesión no elevada). No se simularon instalaciones ni resultados.*
