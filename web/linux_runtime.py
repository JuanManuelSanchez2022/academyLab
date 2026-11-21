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


_EXERCISES = {
    "linux-paths-guided": {
        "commands": ["pwd", "ls -la", "cd"],
        "script": (
            'printf "USER=%s\\n" "$(id -un)"\n'
            'printf "WORKDIR=%s\\n" "$PWD"\n'
            "ls -la\n"
            'cd "$HOME"\n'
            'test "$PWD" = "$HOME"\n'
            'printf "HOME=%s\\n" "$PWD"\n'
        ),
    },
    "linux-paths-independent": {
        "commands": ["mkdir -p", "cd", "pwd", "find"],
        "script": (
            'mkdir -p paths/absolute paths/relative\n'
            'cd "$HOME/academyLab/linux-course/{learner_id}/linux-paths-independent/paths/absolute"\n'
            'test "$PWD" = "$HOME/academyLab/linux-course/{learner_id}/linux-paths-independent/paths/absolute"\n'
            'printf "ABSOLUTE=%s\\n" "$PWD"\n'
            "cd ../relative\n"
            'test "$PWD" = "$HOME/academyLab/linux-course/{learner_id}/linux-paths-independent/paths/relative"\n'
            'printf "RELATIVE=%s\\n" "$PWD"\n'
            'find "$HOME/academyLab/linux-course/{learner_id}/linux-paths-independent/paths" -maxdepth 2 -type d -print | sort\n'
        ),
    },
    "linux-files-guided": {
        "commands": ["mkdir", "touch", "cp", "mv", "cat"],
        "script": (
            "mkdir -p files\n"
            "rm -f -- files/draft.txt files/copy.txt files/renamed.txt\n"
            'touch files/draft.txt\n'
            'printf "operation=OP-4002\\n" > files/draft.txt\n'
            "cp -- files/draft.txt files/copy.txt\n"
            "mv -- files/copy.txt files/renamed.txt\n"
            'test "$(cat files/renamed.txt)" = "operation=OP-4002"\n'
            "printf 'FILE=%s\\n' files/renamed.txt\n"
            "cat files/renamed.txt\n"
        ),
    },
    "linux-files-independent": {
        "commands": ["mkdir", "touch", "cp", "rm"],
        "script": (
            "mkdir -p files\n"
            "rm -f -- files/incident.txt files/incident-copy.txt\n"
            "touch files/incident.txt\n"
            'printf "case=LAB-01\\n" > files/incident.txt\n'
            "cp -- files/incident.txt files/incident-copy.txt\n"
            'test "$(cat files/incident-copy.txt)" = "case=LAB-01"\n'
            "rm -- files/incident-copy.txt\n"
            "test ! -e files/incident-copy.txt\n"
            "printf 'SOURCE=%s\\n' files/incident.txt\n"
            "cat files/incident.txt\n"
            "printf 'COPY_REMOVED=yes\\n'\n"
        ),
    },
    # Piloto de la Fase 3 (prácticas con pregunta): el alumno ejecuta una de las
    # opciones y responde una pregunta. La respuesta se valida contra la salida
    # real de answer_script, que nunca se envía al navegador.
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
        "commands": [">", ">>", "cat"],
        "script": (
            "mkdir -p streams\n"
            "rm -f -- streams/selected.log\n"
            'grep "ERROR" fixtures/production-support.log > streams/selected.log\n'
            'grep "PENDIENTE" fixtures/production-support.log >> streams/selected.log\n'
            'test "$(grep -c "ERROR" streams/selected.log)" -ge 1\n'
            'test "$(grep -c "PENDIENTE" streams/selected.log)" -ge 1\n'
            'printf "SELECTED_LINES=%s\\n" "$(wc -l < streams/selected.log)"\n'
            "cat streams/selected.log\n"
        ),
    },
    "linux-streams-independent": {
        "commands": ["grep", "|", "wc -l"],
        "script": (
            'error_count=$(grep -c "ERROR" fixtures/production-support.log)\n'
            'pending_count=$(grep -c "PENDIENTE" fixtures/production-support.log)\n'
            'total_count=$(grep -E "ERROR|PENDIENTE" fixtures/production-support.log | wc -l)\n'
            'test "$total_count" -eq "$((error_count + pending_count))"\n'
            'printf "ERROR=%s PENDIENTE=%s TOTAL=%s\\n" "$error_count" "$pending_count" "$total_count"\n'
        ),
    },
    "linux-permissions-guided": {
        "commands": ["ls -l", "chmod 600", "stat"],
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
    "linux-permissions-independent": {
        "commands": ["id -gn", "chown :group", "stat"],
        "script": (
            "mkdir -p permissions\n"
            "rm -f -- permissions/owned-by-learner.txt\n"
            'printf "owner=learner\\n" > permissions/owned-by-learner.txt\n'
            'group=$(id -gn)\n'
            'chown ":$group" permissions/owned-by-learner.txt\n'
            'test "$(stat -c "%G" permissions/owned-by-learner.txt)" = "$group"\n'
            'printf "OWNER_GROUP=%s:%s\\n" "$(stat -c "%U" permissions/owned-by-learner.txt)" "$group"\n'
        ),
    },
    "linux-processes-guided": {
        "commands": ["ps", "top -b -n1"],
        "script": (
            'printf "CURRENT_PROCESS\\n"\n'
            "ps -p $$ -o pid=,comm=\n"
            'printf "PROCESS_SNAPSHOT\\n"\n'
            "top -b -n1 -w 80\n"
        ),
    },
    "linux-processes-independent": {
        "commands": ["sleep", "ps", "kill"],
        "script": (
            "sleep 30 &\n"
            "pid=$!\n"
            'ps -p "$pid" -o pid=,comm=\n'
            'kill "$pid"\n'
            'if wait "$pid" 2>/dev/null; then printf "ERROR: process unexpectedly succeeded\\n"; exit 1; fi\n'
            'printf "PROCESS_TERMINATED=yes\\n"\n'
        ),
    },
    "linux-env-guided": {
        "commands": ["printenv HOME", "export", "printenv"],
        "script": (
            'printf "HOME=%s\\n" "$(printenv HOME)"\n'
            'export ACADEMY_CASE_ID="LAB-01-READONLY"\n'
            'test "$(printenv ACADEMY_CASE_ID)" = "LAB-01-READONLY"\n'
            'printf "CASE=%s\\n" "$(printenv ACADEMY_CASE_ID)"\n'
            'printf "USER=%s PATH_ENTRIES=%s\\n" "$(id -un)" "$(printf "%s" "$PATH" | tr ":" "\\n" | wc -l)"\n'
        ),
    },
    "linux-env-independent": {
        "commands": ["date -u", "df -h", "id", "grep"],
        "script": (
            'printf "UTC=%s\\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"\n'
            "id\n"
            'df -h "$HOME"\n'
            'grep -n "ERROR" fixtures/production-support.log\n'
            'printf "EVIDENCE_SOURCE=%s\\n" "fixtures/production-support.log"\n'
        ),
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
    result = _execute_in_workspace(learner_id, exercise_id, option["script"])
    result["stdout"] = _visible_output(result.get("stdout", ""))
    result["commands"] = [option["label"]]
    result["option_id"] = option_id
    return result


def _answers_match(answer, expected, pattern):
    if not re.fullmatch(pattern, answer) or not re.fullmatch(pattern, expected):
        return False
    if answer.isdigit() and expected.isdigit():
        return int(answer) == int(expected)
    return answer == expected


def verify_answer(learner_id, exercise_id, answer):
    """Vuelve a ejecutar la opción de referencia y compara la respuesta con su salida real.

    El valor esperado nunca se incluye en el resultado: solo answer_correct.
    """
    exercise = _question_exercise(exercise_id)
    reference = exercise["options"][exercise["reference_option"]]
    body = (
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
