"""Allowlisted, local WSL execution for the Basic Linux course."""

import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from pathlib import Path, PurePosixPath


PROJECT_ROOT = Path(__file__).resolve().parents[1]
COURSE_FIXTURE = PROJECT_ROOT / "labs" / "linux-course" / "fixtures" / "production-support.log"
CAPSTONE_LOG = PROJECT_ROOT / "web" / "course_data" / "basic_capstone_events.log"
DISTRO = "Ubuntu"
_active_distro = None
MAX_OUTPUT = 12000
COMMAND_TIMEOUT = 20
_status_lock = threading.Lock()
_execution_lock = threading.Lock()
_status_cache = None
_status_checked_at = 0.0
_STATUS_TTL = 15
_SUCCESS_MARKER = "__ACADEMY_CHECK_OK__"
_ANSWER_MARKER = "__ACADEMY_ANSWER__"


class LinuxRuntimeError(ValueError):
    """Raised when a fixed Linux exercise cannot run safely."""


# Cada práctica define opciones de ejecución fijas (el alumno elige una por id) y una
# pregunta. La respuesta se valida contra la salida real de answer_script, que se
# ejecuta después de setup + la opción de referencia y nunca se envía al navegador.
# "setup" (opcional) se antepone a cada opción y a la verificación.
_LOG = "fixtures/production-support.log"
_NUMBER = r"[0-9]{1,6}"
_ABSOLUTE_PATH = r"/[A-Za-z0-9._/-]{1,240}"

_EXERCISES = {
    "linux-paths-guided": {
        "commands": ["id -un", "pwd", "ls -la", 'cd "$HOME"'],
        "reference_option": "identificar-entorno",
        "answer_script": 'printf "%s" "$HOME"\n',
        "answer_pattern": _ABSOLUTE_PATH,
        "options": {
            "identificar-entorno": {
                "label": 'id -un, pwd, ls -la y cd "$HOME"',
                "script": (
                    'printf "USER=%s\\n" "$(id -un)"\n'
                    'printf "WORKDIR=%s\\n" "$PWD"\n'
                    "ls -la\n"
                    'cd "$HOME"\n'
                    'test "$PWD" = "$HOME"\n'
                    'printf "HOME=%s\\n" "$PWD"\n'
                ),
            },
        },
    },
    "linux-paths-independent": {
        "commands": ["cd <ruta absoluta>", "cd ../<ruta relativa>", "pwd", "find"],
        "setup": "mkdir -p paths/absolute paths/relative\n",
        "reference_option": "cd-relativa",
        "answer_script": 'cd "$workspace/paths/relative" && pwd\n',
        "answer_pattern": _ABSOLUTE_PATH,
        "options": {
            "pwd-absoluta": {
                "label": "cd <espacio de práctica>/paths/absolute && pwd",
                "script": 'cd "$workspace/paths/absolute"\npwd\n',
            },
            "cd-relativa": {
                "label": "cd <espacio de práctica>/paths/absolute && cd ../relative && pwd",
                "script": 'cd "$workspace/paths/absolute"\ncd ../relative\npwd\n',
            },
            "find-directorios": {
                "label": "find paths -maxdepth 2 -type d",
                "script": "find paths -maxdepth 2 -type d | sort\n",
            },
        },
    },
    "linux-files-guided": {
        "commands": ["mkdir", "touch", "cp", "mv", "cat", "ls -l"],
        "reference_option": "crear-copiar-renombrar",
        "answer_script": 'stat -c "%s" files/renamed.txt\n',
        "answer_pattern": _NUMBER,
        "options": {
            "crear-copiar-renombrar": {
                "label": "mkdir files, touch, cp, mv, cat y ls -l files",
                "script": (
                    "mkdir -p files\n"
                    "rm -f -- files/draft.txt files/copy.txt files/renamed.txt\n"
                    "touch files/draft.txt\n"
                    'printf "operation=OP-4002\\n" > files/draft.txt\n'
                    "cp -- files/draft.txt files/copy.txt\n"
                    "mv -- files/copy.txt files/renamed.txt\n"
                    'test "$(cat files/renamed.txt)" = "operation=OP-4002"\n'
                    "printf 'FILE=%s\\n' files/renamed.txt\n"
                    "cat files/renamed.txt\n"
                    "ls -l files\n"
                ),
            },
        },
    },
    "linux-files-independent": {
        "commands": ["cp", "rm", "cat", "ls -l"],
        # La preparación crea más archivos de los que mencionan las opciones: el alumno
        # solo sabe cuántos quedan si lista el directorio.
        "setup": (
            "mkdir -p files\n"
            "rm -f -- files/*\n"
            'printf "case=LAB-01\\n" > files/incident.txt\n'
            'printf "evidencia=1\\n" > files/evidencia-1.log\n'
            'printf "evidencia=2\\n" > files/evidencia-2.log\n'
        ),
        "reference_option": "copiar-borrar-listar",
        "answer_script": "ls -1 files | wc -l\n",
        "answer_pattern": _NUMBER,
        "options": {
            "copiar-y-borrar": {
                "label": "cp files/incident.txt files/incident-copy.txt && rm files/incident-copy.txt",
                "script": "cp -- files/incident.txt files/incident-copy.txt\nrm -- files/incident-copy.txt\n",
            },
            "copiar-borrar-listar": {
                "label": "cp files/incident.txt files/incident-copy.txt && rm files/incident-copy.txt && ls -l files",
                "script": (
                    "cp -- files/incident.txt files/incident-copy.txt\n"
                    "rm -- files/incident-copy.txt\n"
                    "ls -l files\n"
                ),
            },
            "ver-contenido": {
                "label": "cat files/incident.txt",
                "script": "cat files/incident.txt\n",
            },
        },
    },
    # Piloto de la Fase 3.
    "linux-logs-guided": {
        "commands": ["head", "tail", "less", "grep -n"],
        "reference_option": "inspeccionar-log",
        # -m 1 en lugar de "| head": evita un SIGPIPE que pipefail trataría como fallo.
        "answer_script": 'grep -n -m 1 "ERROR" fixtures/production-support.log | cut -d: -f1\n',
        "answer_pattern": r"[0-9]{1,4}",
        "options": {
            "inspeccionar-log": {
                "label": 'head -n 2, tail -n 2, less y grep -n "ERROR" sobre fixtures/production-support.log',
                "script": (
                    'printf "HEAD\\n"\n'
                    "head -n 2 fixtures/production-support.log\n"
                    'printf "TAIL\\n"\n'
                    "tail -n 2 fixtures/production-support.log\n"
                    'printf "LESS\\n"\n'
                    "LESS=FRX TERM=dumb less -F -X fixtures/production-support.log\n"
                    'printf "ERROR_MATCHES\\n"\n'
                    'grep -n "ERROR" fixtures/production-support.log\n'
                ),
            },
        },
    },
    "linux-logs-independent": {
        "commands": ["find", "grep -n", "grep -c", "tail -n"],
        "reference_option": "grep-n",
        "answer_script": 'grep -n "PENDIENTE" fixtures/production-support.log | tail -n 1 | cut -d: -f1\n',
        "answer_pattern": r"[0-9]{1,4}",
        "options": {
            "find-logs": {
                "label": 'find fixtures -type f -name "*.log"',
                "script": 'find fixtures -type f -name "*.log"\n',
            },
            "grep-c": {
                "label": 'grep -c "PENDIENTE" fixtures/production-support.log',
                "script": 'grep -c "PENDIENTE" fixtures/production-support.log\n',
            },
            "grep-n": {
                "label": 'grep -n "PENDIENTE" fixtures/production-support.log',
                "script": 'grep -n "PENDIENTE" fixtures/production-support.log\n',
            },
            "tail-5": {
                "label": "tail -n 5 fixtures/production-support.log",
                "script": "tail -n 5 fixtures/production-support.log\n",
            },
        },
    },
    "linux-streams-guided": {
        "commands": ["grep ERROR > salida nueva", "grep PENDIENTE >> salida nueva", "cat"],
        "reference_option": "redirigir-y-anexar",
        "answer_script": (
            'grep -m 1 "PENDIENTE" streams/selected.log '
            '| sed -n "s/.*operacion=\\([^ ]*\\).*/\\1/p"\n'
        ),
        "answer_pattern": r"LINUX-[0-9]{4}",
        "options": {
            "redirigir-y-anexar": {
                "label": 'grep "ERROR" log > streams/selected.log, grep "PENDIENTE" log >> streams/selected.log y cat',
                "script": (
                    "mkdir -p streams\n"
                    "rm -f -- streams/selected.log\n"
                    f'grep "ERROR" {_LOG} > streams/selected.log\n'
                    f'grep "PENDIENTE" {_LOG} >> streams/selected.log\n'
                    'printf "SELECTED_LINES=%s\\n" "$(wc -l < streams/selected.log)"\n'
                    "cat streams/selected.log\n"
                ),
            },
        },
    },
    "linux-streams-independent": {
        "commands": ["grep -c", "grep -E", "|", "wc -l", "tail"],
        "reference_option": "tuberia",
        "answer_script": f'grep -c -E "ERROR|PENDIENTE" {_LOG}\n',
        "answer_pattern": _NUMBER,
        "options": {
            "contar-error": {
                "label": f'grep -c "ERROR" {_LOG}',
                "script": f'grep -c "ERROR" {_LOG}\n',
            },
            "contar-lineas": {
                "label": f"wc -l {_LOG}",
                "script": f"wc -l {_LOG}\n",
            },
            "tuberia": {
                "label": f'grep -E "ERROR|PENDIENTE" {_LOG} | wc -l',
                "script": f'grep -E "ERROR|PENDIENTE" {_LOG} | wc -l\n',
            },
            "ultimas-lineas": {
                "label": f"tail -n 3 {_LOG}",
                "script": f"tail -n 3 {_LOG}\n",
            },
        },
    },
    "linux-permissions-guided": {
        "commands": ["ls -l", "chmod 600", "stat"],
        "reference_option": "leer-y-restringir",
        # Los permisos iniciales dependen del umask real del alumno: se recalculan con
        # un archivo nuevo creado de la misma forma que notes.txt.
        "answer_script": (
            "probe=permissions/.probe-umask\n"
            'rm -f -- "$probe"\n'
            'printf "x\\n" > "$probe"\n'
            'stat -c "%A" "$probe"\n'
            'rm -f -- "$probe"\n'
        ),
        "answer_pattern": r"[-dl][rwxsStT-]{9}",
        "options": {
            "leer-y-restringir": {
                "label": "ls -l permissions/notes.txt, chmod 600 permissions/notes.txt y stat",
                "script": (
                    "mkdir -p permissions\n"
                    "rm -f -- permissions/notes.txt\n"
                    'printf "ticket=LAB-01\\n" > permissions/notes.txt\n'
                    "ls -l permissions/notes.txt\n"
                    "chmod 600 permissions/notes.txt\n"
                    'test "$(stat -c "%a" permissions/notes.txt)" = "600"\n'
                    'printf "MODE=%s\\n" "$(stat -c "%A %a" permissions/notes.txt)"\n'
                ),
            },
        },
    },
    "linux-permissions-independent": {
        "commands": ["chmod", "ls -l", "touch"],
        "setup": (
            "mkdir -p permissions\n"
            "rm -f -- permissions/owned-by-learner.txt\n"
            'printf "owner=learner\\n" > permissions/owned-by-learner.txt\n'
            'chown ":$(id -gn)" permissions/owned-by-learner.txt\n'
        ),
        "reference_option": "listar",
        "answer_script": 'stat -c "%U:%G" permissions/owned-by-learner.txt\n',
        "answer_pattern": r"[A-Za-z_][A-Za-z0-9._-]{0,31}:[A-Za-z_][A-Za-z0-9._-]{0,31}",
        "options": {
            "restringir": {
                "label": "chmod 640 permissions/owned-by-learner.txt",
                "script": "chmod 640 permissions/owned-by-learner.txt\n",
            },
            "listar": {
                "label": "ls -l permissions/owned-by-learner.txt",
                "script": "ls -l permissions/owned-by-learner.txt\n",
            },
            "actualizar-fecha": {
                "label": "touch permissions/owned-by-learner.txt",
                "script": "touch permissions/owned-by-learner.txt\n",
            },
        },
    },
    "linux-processes-guided": {
        "commands": ["ps -p $$", "top -b -n1 -w 80"],
        "reference_option": "ps-y-top",
        "answer_script": "ps -p $$ -o comm=\n",
        "answer_pattern": r"[A-Za-z0-9._-]{1,30}",
        "options": {
            "ps-y-top": {
                "label": "ps -p $$ -o pid=,comm= y top -b -n1 -w 80",
                "script": (
                    'printf "CURRENT_PROCESS\\n"\n'
                    "ps -p $$ -o pid=,comm=\n"
                    'printf "PROCESS_SNAPSHOT\\n"\n'
                    "top -b -n1 -w 80\n"
                ),
            },
        },
    },
    "linux-processes-independent": {
        "commands": ["sleep 30 &", "ps -p", "kill", "wait", "echo $?"],
        "reference_option": "terminar",
        # El PID siempre lo crea el propio script; nunca se recibe del navegador.
        "answer_script": (
            "sleep 30 >/dev/null 2>&1 &\n"
            "temporary_pid=$!\n"
            'kill "$temporary_pid"\n'
            "exit_code=0\n"
            'wait "$temporary_pid" 2>/dev/null || exit_code=$?\n'
            'printf "%s" "$exit_code"\n'
        ),
        "answer_pattern": r"[0-9]{1,3}",
        "options": {
            "ver-proceso": {
                "label": "sleep 30 & ps -p $! -o pid=,comm=",
                "script": (
                    "sleep 30 >/dev/null 2>&1 &\n"
                    "temporary_pid=$!\n"
                    'ps -p "$temporary_pid" -o pid=,comm=\n'
                    'kill "$temporary_pid" 2>/dev/null || true\n'
                    'wait "$temporary_pid" 2>/dev/null || true\n'
                ),
            },
            "terminar": {
                "label": 'sleep 30 & kill $! ; wait $! ; echo "codigo=$?"',
                "script": (
                    "sleep 30 >/dev/null 2>&1 &\n"
                    "temporary_pid=$!\n"
                    'kill "$temporary_pid"\n'
                    "exit_code=0\n"
                    'wait "$temporary_pid" 2>/dev/null || exit_code=$?\n'
                    'printf "codigo=%s\\n" "$exit_code"\n'
                ),
            },
            "terminar-normal": {
                "label": 'sleep 1 ; echo "codigo=$?"',
                "script": 'exit_code=0\nsleep 1 || exit_code=$?\nprintf "codigo=%s\\n" "$exit_code"\n',
            },
        },
    },
    "linux-env-guided": {
        "commands": ["printenv HOME", "export ACADEMY_CASE_ID=LAB-01-READONLY", "printenv ACADEMY_CASE_ID", "PATH"],
        "reference_option": "variables",
        # printf con salto final: sin él, wc -l cuenta una entrada menos.
        "answer_script": 'printf "%s\\n" "$PATH" | tr ":" "\\n" | wc -l\n',
        "answer_pattern": _NUMBER,
        "options": {
            "variables": {
                "label": 'printenv HOME, export ACADEMY_CASE_ID, printenv ACADEMY_CASE_ID y conteo de entradas de PATH',
                "script": (
                    'printf "HOME=%s\\n" "$(printenv HOME)"\n'
                    'export ACADEMY_CASE_ID="LAB-01-READONLY"\n'
                    'test "$(printenv ACADEMY_CASE_ID)" = "LAB-01-READONLY"\n'
                    'printf "CASE=%s\\n" "$(printenv ACADEMY_CASE_ID)"\n'
                    'printf "USER=%s PATH_ENTRIES=%s\\n" "$(id -un)" "$(printf "%s\\n" "$PATH" | tr ":" "\\n" | wc -l)"\n'
                ),
            },
        },
    },
    "linux-env-independent": {
        "commands": ["date -u", "id", 'df -h "$HOME"', "grep -n ERROR"],
        "reference_option": "espacio",
        "answer_script": 'df --output=source "$HOME" | tail -n 1\n',
        "answer_pattern": r"[A-Za-z0-9/._:@-]{1,120}",
        "options": {
            "fecha": {
                "label": "date -u +%Y-%m-%dT%H:%M:%SZ",
                "script": "date -u +%Y-%m-%dT%H:%M:%SZ\n",
            },
            "identidad": {
                "label": "id",
                "script": "id\n",
            },
            "espacio": {
                "label": 'df -h "$HOME"',
                "script": 'df -h "$HOME"\n',
            },
            "errores": {
                "label": f'grep -n "ERROR" {_LOG}',
                "script": f'grep -n "ERROR" {_LOG}\n',
            },
        },
    },
}


def exercise_ids():
    return set(_EXERCISES)


def question_exercise_ids():
    """Prácticas que exigen elegir una opción y responder una pregunta."""
    return {exercise_id for exercise_id, item in _EXERCISES.items() if "options" in item}


def exercise_options(exercise_id):
    """Opciones públicas (id y línea de comando) de una práctica con pregunta."""
    options = _EXERCISES.get(exercise_id, {}).get("options", {})
    return [{"id": option_id, "label": option["label"]} for option_id, option in options.items()]


def _wsl_executable():
    executable = shutil.which("wsl.exe")
    if executable:
        return executable
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    candidate = Path(system_root) / "System32" / "wsl.exe"
    return str(candidate) if candidate.is_file() else None


def _decode_output(value):
    if not value:
        return ""
    if b"\x00" in value[:32]:
        return value.decode("utf-16le", errors="replace")
    return value.decode("utf-8", errors="replace")


def _invoke_wsl(arguments, input_bytes=None, timeout=30):
    executable = _wsl_executable()
    if not executable:
        raise LinuxRuntimeError("No se encontró wsl.exe en este equipo.")
    try:
        completed = subprocess.run(
            [executable, *arguments],
            input=input_bytes,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _decode_output(exc.stdout or b"")
        stderr = _decode_output(exc.stderr or b"")
        raise LinuxRuntimeError(
            "La operación WSL excedió el tiempo máximo permitido."
        ) from exc
    except OSError as exc:
        raise LinuxRuntimeError(f"No se pudo iniciar WSL: {exc}") from exc
    return completed.returncode, _decode_output(completed.stdout), _decode_output(completed.stderr)


def _wsl_command(arguments, input_bytes=None, timeout=30):
    return _invoke_wsl(
        ["--distribution", _active_distro or DISTRO, "--exec", *arguments],
        input_bytes=input_bytes,
        timeout=timeout,
    )


def _parse_wsl_list(output):
    distros = {}
    for line in output.splitlines():
        columns = line.strip().lstrip("* ").split()
        if len(columns) >= 3 and columns[-1].isdigit():
            distros[columns[0].casefold()] = int(columns[-1])
    return distros


def _check_status():
    global _active_distro
    if os.name != "nt":
        return {"available": False, "reason": "El entorno Ubuntu/WSL solo se habilita en Windows."}
    try:
        code, stdout, stderr = _invoke_wsl(["--list", "--verbose"])
    except LinuxRuntimeError as exc:
        return {"available": False, "reason": str(exc)}
    if code != 0:
        detail = stderr.strip() or stdout.strip()
        if re.search(r"(?im)^\s*usage:\s*wsl\.exe\b", detail):
            return {
                "available": False,
                "reason": (
                    f"wsl.exe no admite '--list --verbose' (código {code}). "
                    "Actualiza WSL y vuelve a comprobar el entorno."
                ),
            }
        diagnostic = next((line.strip() for line in detail.splitlines() if line.strip()), "")
        if len(diagnostic) > 180:
            diagnostic = diagnostic[:177] + "..."
        return {
            "available": False,
            "reason": (
                f"No se pudieron consultar las distribuciones WSL (código {code}). "
                f"Detalle: {diagnostic or 'sin información adicional.'}"
            ),
        }

    distros = _parse_wsl_list(stdout)
    distro_name = next(
        (
            name
            for name in distros
            if name == DISTRO.casefold() or name.startswith(DISTRO.casefold() + "-")
        ),
        None,
    )
    if distro_name is None:
        _active_distro = None
        return {
            "available": False,
            "reason": f"No se encontró la distribución {DISTRO}; instálala e inicializa su usuario.",
        }
    version = distros[distro_name]
    if version != 2:
        _active_distro = None
        return {
            "available": False,
            "reason": f"{DISTRO} usa WSL {version}; el curso requiere WSL 2.",
        }
    _active_distro = next(
        (line.strip().lstrip("* ").split()[0] for line in stdout.splitlines()
         if line.strip().lstrip("* ").lower().startswith(distro_name)),
        DISTRO,
    )

    try:
        code, uid, stderr = _wsl_command(["/usr/bin/id", "-u"])
        if code != 0:
            return {"available": False, "reason": stderr.strip() or "No se pudo consultar el usuario Linux."}
        if uid.strip() == "0":
            return {"available": False, "reason": "Inicializa un usuario Ubuntu normal; no se ejecutan prácticas como root."}
        code, home, stderr = _wsl_command(["/usr/bin/printenv", "HOME"])
        if code != 0:
            return {"available": False, "reason": stderr.strip() or "No se pudo validar el directorio HOME."}
        home_path = PurePosixPath(home.strip())
        if (
            not home_path.is_absolute()
            or len(home_path.parts) < 3
            or home_path.parts[:2] != ("/", "home")
            or ".." in home_path.parts
        ):
            return {"available": False, "reason": "El HOME de Ubuntu no está dentro de /home."}
        required = "bash cat chmod chown cp date df find grep head id less mkdir mv printenv ps rm sed sleep sort stat tail top touch tr uname wc"
        check_script = (
            f"missing=''; for tool in {required}; do "
            'command -v "$tool" >/dev/null 2>&1 || missing="$missing $tool"; '
            'done; printf "%s" "$missing"'
        )
        code, missing, stderr = _wsl_command(
            ["/usr/bin/bash", "--noprofile", "--norc", "-c", check_script]
        )
        if code != 0:
            return {"available": False, "reason": stderr.strip() or "No se pudieron verificar las herramientas Ubuntu."}
        if missing.strip():
            return {
                "available": False,
                "reason": f"Faltan herramientas requeridas en Ubuntu:{missing.strip()}.",
            }
        code, kernel, stderr = _wsl_command(["/usr/bin/uname", "-r"])
        if code != 0:
            return {"available": False, "reason": stderr.strip() or "No se pudo consultar el kernel WSL 2."}
    except LinuxRuntimeError as exc:
        return {"available": False, "reason": str(exc)}
    return {
        "available": True,
        "distribution": _active_distro,
        "wsl_version": 2,
        "kernel": kernel.strip(),
        "home": str(home_path),
    }


def status(force_refresh=False):
    global _status_cache, _status_checked_at
    with _status_lock:
        now = time.monotonic()
        if not force_refresh and _status_cache is not None and now - _status_checked_at < _STATUS_TTL:
            return dict(_status_cache)
        _status_cache = _check_status()
        _status_checked_at = now
        return dict(_status_cache)


def clear_status_cache():
    global _status_cache, _status_checked_at
    with _status_lock:
        _status_cache = None
        _status_checked_at = 0.0


def _workspace_path(learner_id, exercise_id):
    try:
        normalized_id = str(uuid.UUID(learner_id))
    except (ValueError, TypeError, AttributeError) as exc:
        raise LinuxRuntimeError("Identificador de alumno inválido.") from exc
    if not isinstance(exercise_id, str) or not re.fullmatch(r"[a-z0-9-]{1,60}", exercise_id):
        raise LinuxRuntimeError("El ejercicio Linux solicitado no está permitido.")
    return f"$HOME/academyLab/linux-course/{normalized_id}/{exercise_id}"


def _windows_path_in_wsl(path):
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive or not resolved.is_absolute():
        raise LinuxRuntimeError("No se pudo resolver el fixture local del curso.")
    suffix = resolved.as_posix()[len(resolved.drive.replace("\\", "/")):].lstrip("/")
    return f"/mnt/{drive}/{suffix}"


def _prepare_workspace(learner_id, exercise_id, status_result, fixture):
    workspace = _workspace_path(learner_id, exercise_id)
    home = status_result["home"]
    normalized_id = str(uuid.UUID(learner_id))
    absolute_workspace = f"{home}/academyLab/linux-course/{normalized_id}/{exercise_id}"
    code, _, stderr = _wsl_command(
        ["/usr/bin/mkdir", "-p", absolute_workspace, f"{absolute_workspace}/fixtures"]
    )
    if code != 0:
        raise LinuxRuntimeError(stderr.strip() or "No se pudo preparar el espacio aislado de práctica.")
    fixture_source = _windows_path_in_wsl(fixture)
    code, _, stderr = _wsl_command(
        ["/usr/bin/cp", "--", fixture_source, f"{absolute_workspace}/fixtures/{fixture.name}"]
    )
    if code != 0:
        raise LinuxRuntimeError(stderr.strip() or "No se pudo copiar el fixture al espacio de práctica Ubuntu.")
    return workspace


def _run_script(script, status_result, timeout=COMMAND_TIMEOUT):
    try:
        code, stdout, stderr = _wsl_command(
            [
                "/usr/bin/bash",
                "--noprofile",
                "--norc",
                "-c",
                script,
            ],
            timeout=timeout,
        )
    except LinuxRuntimeError as exc:
        return {
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
            "passed": False,
            "runtime": status_result.get("kernel"),
        }
    output = (
        stdout
        if len(stdout) <= MAX_OUTPUT
        else stdout[: MAX_OUTPUT - 64] + "\n[output truncated]\n" + stdout[-32:]
    )
    error = (
        stderr
        if len(stderr) <= MAX_OUTPUT
        else stderr[: MAX_OUTPUT - 64] + "\n[output truncated]\n" + stderr[-32:]
    )
    passed = code == 0 and _SUCCESS_MARKER in stdout
    return {
        "returncode": code,
        "stdout": output,
        "stderr": error,
        "passed": passed,
        "runtime": status_result.get("kernel"),
    }


def _execute_in_workspace(learner_id, exercise_id, body):
    """Ejecuta un cuerpo de script fijo en el espacio aislado del alumno."""
    with _execution_lock:
        runtime = status()
        if not runtime.get("available"):
            raise LinuxRuntimeError(runtime.get("reason", "Ubuntu no está disponible."))
        workspace = _prepare_workspace(
            learner_id,
            exercise_id,
            runtime,
            COURSE_FIXTURE,
        )
        script = (
            "set -euo pipefail\n"
            "export LC_ALL=C\n"
            f"workspace={workspace}\n"
            'cd "$workspace"\n'
            f"{body}"
            f'printf "\\n{_SUCCESS_MARKER}\\n"\n'
        )
        result = _run_script(script, runtime)
    result["exercise_id"] = exercise_id
    if not result["passed"]:
        result["feedback"] = (
            "La verificación real en Ubuntu no terminó correctamente. "
            "Revisa el error y vuelve a intentar; no se guardó una aprobación."
        )
    return result


def _visible_output(stdout):
    """Quita los marcadores internos de la salida que ve el alumno."""
    lines = [
        line for line in stdout.splitlines()
        if not line.startswith((_SUCCESS_MARKER, _ANSWER_MARKER))
    ]
    return "\n".join(lines).rstrip() + "\n" if lines else ""


def _question_exercise(exercise_id):
    exercise = _EXERCISES.get(exercise_id)
    if exercise is None or "options" not in exercise:
        raise LinuxRuntimeError("El ejercicio Linux solicitado no tiene opciones de ejecución.")
    return exercise


def run_exercise(learner_id, exercise_id):
    """Prácticas sin pregunta: ejecuta el script fijo completo."""
    if exercise_id not in _EXERCISES:
        raise LinuxRuntimeError("El ejercicio Linux solicitado no está permitido.")
    command = _EXERCISES[exercise_id]
    if "options" in command:
        raise LinuxRuntimeError("Esta práctica requiere ejecutar una opción y responder la pregunta.")
    body = command["script"].format(learner_id=str(uuid.UUID(learner_id)))
    result = _execute_in_workspace(learner_id, exercise_id, body)
    result["commands"] = command["commands"]
    return result


def run_option(learner_id, exercise_id, option_id):
    """Ejecuta una opción permitida de una práctica con pregunta (exploración, no evalúa)."""
    exercise = _question_exercise(exercise_id)
    if not isinstance(option_id, str) or option_id not in exercise["options"]:
        raise LinuxRuntimeError("La opción de comando solicitada no está permitida.")
    option = exercise["options"][option_id]
    body = exercise.get("setup", "") + option["script"]
    result = _execute_in_workspace(learner_id, exercise_id, body)
    result["stdout"] = _visible_output(result.get("stdout", ""))
    result["commands"] = [option["label"]]
    result["option_id"] = option_id
    return result


def _answers_match(answer, expected, pattern):
    if not re.fullmatch(pattern, answer) or not re.fullmatch(pattern, expected):
        return False
    if answer.isdigit() and expected.isdigit():
        return int(answer) == int(expected)
    if answer.startswith("/") and expected.startswith("/"):
        # Una barra final no cambia la ruta.
        return answer.rstrip("/") == expected.rstrip("/")
    return answer == expected


def verify_answer(learner_id, exercise_id, answer):
    """Vuelve a ejecutar la opción de referencia y compara la respuesta con su salida real.

    El valor esperado nunca se incluye en el resultado: solo answer_correct.
    """
    exercise = _question_exercise(exercise_id)
    reference = exercise["options"][exercise["reference_option"]]
    body = (
        f'{exercise.get("setup", "")}'
        f'{reference["script"]}'
        f'reference_answer=$({exercise["answer_script"].strip()})\n'
        f'printf "\\n{_ANSWER_MARKER}=%s\\n" "$reference_answer"\n'
    )
    result = _execute_in_workspace(learner_id, exercise_id, body)
    result["commands"] = [reference["label"]]
    match = re.search(rf"^{_ANSWER_MARKER}=(.*?)\r?$", result.get("stdout", ""), re.MULTILINE)
    expected = match.group(1).strip() if match else ""
    result["stdout"] = _visible_output(result.get("stdout", ""))
    if result["passed"] and not re.fullmatch(exercise["answer_pattern"], expected):
        result["passed"] = False
        result["feedback"] = "La ejecución en Ubuntu no produjo un valor de referencia válido; no se guardó una aprobación."
    normalized = answer.strip() if isinstance(answer, str) else ""
    result["answer_correct"] = bool(
        result["passed"] and _answers_match(normalized, expected, exercise["answer_pattern"])
    )
    return result


def run_project_analysis(learner_id):
    with _execution_lock:
        runtime = status()
        if not runtime.get("available"):
            return {
                "passed": False,
                "error": runtime.get("reason", "Ubuntu no está disponible."),
                "stdout": "",
                "stderr": "",
                "runtime": None,
                "error_ids": [],
                "pending_ids": [],
            }
        try:
            workspace = _prepare_workspace(
                learner_id,
                "project-support-basic",
                runtime,
                CAPSTONE_LOG,
            )
        except LinuxRuntimeError as exc:
            return {
                "passed": False,
                "error": str(exc),
                "stdout": "",
                "stderr": "",
                "runtime": runtime.get("kernel"),
                "error_ids": [],
                "pending_ids": [],
            }
        script = (
            "set -euo pipefail\n"
            "export LC_ALL=C\n"
            f"workspace={workspace}\n"
            'cd "$workspace"\n'
            'printf "ERROR_IDS_BEGIN\\n"\n'
            'grep "level=ERROR" fixtures/basic_capstone_events.log '
            '| sed -n "s/.*id_operacion=\\([^ ]*\\).*/\\1/p" | sort -u\n'
            'printf "PENDING_IDS_BEGIN\\n"\n'
            'grep "level=PENDIENTE" fixtures/basic_capstone_events.log '
            '| sed -n "s/.*id_operacion=\\([^ ]*\\).*/\\1/p" | sort -u\n'
            f'printf "\\n{_SUCCESS_MARKER}\\n"\n'
        )
        result = _run_script(script, runtime)
    error_ids = []
    pending_ids = []
    current = None
    for line in result["stdout"].splitlines():
        if line == "ERROR_IDS_BEGIN":
            current = error_ids
        elif line == "PENDING_IDS_BEGIN":
            current = pending_ids
        elif line == _SUCCESS_MARKER:
            current = None
        elif current is not None and re.fullmatch(r"[A-Za-z0-9_-]{1,40}", line):
            current.append(line)
    result["error_ids"] = sorted(set(error_ids))
    result["pending_ids"] = sorted(set(pending_ids))
    result["commands"] = [
        "grep level=ERROR",
        "grep level=PENDIENTE",
        "sed",
        "sort -u",
    ]
    if not result["passed"]:
        result["error"] = "La investigación del log del proyecto no pasó la verificación en Ubuntu."
    return result
