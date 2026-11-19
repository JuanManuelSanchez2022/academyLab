#!/usr/bin/env python3
"""Local home server and lifecycle manager for the AWS LAB 01 service."""

import hashlib
import json
import os
import re
import secrets
import signal
import sqlite3
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from http.cookies import CookieError, SimpleCookie
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import learning_service
import progress_store


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = PROJECT_ROOT / "web"
LAB_DIR = PROJECT_ROOT / "labs" / "lab01-aws-production-support"
LAB_SERVER = LAB_DIR / "scripts" / "web_server.py"
PYTHON = Path(r"C:\Users\juan\AppData\Local\Programs\Python\Python312\python.exe")
HOST = "127.0.0.1"
PORT = int(os.environ.get("AWS_ACADEMY_PLATFORM_PORT", "8765"))
LAB_PORT = int(os.environ.get("AWS_ACADEMY_LAB_PORT", "8766"))
CONFIG_FILE = WEB_DIR / "platform_config.json"
LAB_SERVICE_NAME = "aws-lab-01"
LEARNING_SESSION_COOKIE = "academylab_session"
LEARNING_SESSION_MAX_AGE = 31536000
STATIC_FILES = {
    "/": (WEB_DIR / "index.html", "text/html; charset=utf-8"),
    "/profiles/cloud-production-support/": (
        WEB_DIR / "profiles" / "cloud-production-support.html",
        "text/html; charset=utf-8",
    ),
    "/routes/cloud-production-support/basic/": (
        WEB_DIR / "routes" / "level.html",
        "text/html; charset=utf-8",
    ),
    "/routes/cloud-production-support/intermediate/": (
        WEB_DIR / "routes" / "level.html",
        "text/html; charset=utf-8",
    ),
    "/routes/cloud-production-support/advanced/": (
        WEB_DIR / "routes" / "level.html",
        "text/html; charset=utf-8",
    ),
    "/courses/aws-production-support/": (
        WEB_DIR / "courses" / "aws-production-support.html",
        "text/html; charset=utf-8",
    ),
    "/courses/linux/": (WEB_DIR / "courses" / "basic.html", "text/html; charset=utf-8"),
    "/courses/networking/": (WEB_DIR / "courses" / "basic.html", "text/html; charset=utf-8"),
    "/courses/sql/": (WEB_DIR / "courses" / "basic.html", "text/html; charset=utf-8"),
    "/courses/aws/": (WEB_DIR / "courses" / "basic.html", "text/html; charset=utf-8"),
    "/courses/python/": (WEB_DIR / "courses" / "basic.html", "text/html; charset=utf-8"),
    "/courses/production-support/": (WEB_DIR / "courses" / "basic.html", "text/html; charset=utf-8"),
    "/projects/support-basic/": (WEB_DIR / "courses" / "basic-project.html", "text/html; charset=utf-8"),
    "/progress/": (WEB_DIR / "courses" / "progress.html", "text/html; charset=utf-8"),
    "/assets/platform.css": (WEB_DIR / "assets" / "platform.css", "text/css; charset=utf-8"),
    "/catalog/learning_catalog.json": (
        WEB_DIR / "catalog" / "learning_catalog.json",
        "application/json; charset=utf-8",
    ),
    "/profiles/home.js": (WEB_DIR / "profiles" / "home.js", "text/javascript; charset=utf-8"),
    "/profiles/profile.js": (
        WEB_DIR / "profiles" / "profile.js",
        "text/javascript; charset=utf-8",
    ),
    "/routes/route.js": (WEB_DIR / "routes" / "route.js", "text/javascript; charset=utf-8"),
    "/courses/aws-production-support.js": (
        WEB_DIR / "courses" / "aws-production-support.js",
        "text/javascript; charset=utf-8",
    ),
    "/learning/course.js": (WEB_DIR / "learning" / "course.js", "text/javascript; charset=utf-8"),
    "/learning/project.js": (WEB_DIR / "learning" / "project.js", "text/javascript; charset=utf-8"),
    "/learning/progress.js": (WEB_DIR / "learning" / "progress.js", "text/javascript; charset=utf-8"),
    "/learning/common.js": (WEB_DIR / "learning" / "common.js", "text/javascript; charset=utf-8"),
    "/course-data/basic_capstone_operations.csv": (
        WEB_DIR / "course_data" / "basic_capstone_operations.csv",
        "text/csv; charset=utf-8",
    ),
    "/course-data/basic_capstone_events.log": (
        WEB_DIR / "course_data" / "basic_capstone_events.log",
        "text/plain; charset=utf-8",
    ),
}
REDIRECTS = {
    "/courses/aws-production-support": "/courses/aws-production-support/",
    "/profiles/cloud-production-support": "/profiles/cloud-production-support/",
    "/routes/cloud-production-support/basic": "/routes/cloud-production-support/basic/",
    "/routes/cloud-production-support/intermediate": "/routes/cloud-production-support/intermediate/",
    "/routes/cloud-production-support/advanced": "/routes/cloud-production-support/advanced/",
    "/courses/linux": "/courses/linux/",
    "/courses/networking": "/courses/networking/",
    "/courses/sql": "/courses/sql/",
    "/courses/aws": "/courses/aws/",
    "/courses/python": "/courses/python/",
    "/courses/production-support": "/courses/production-support/",
    "/projects/support-basic": "/projects/support-basic/",
    "/progress": "/progress/",
}

_lock = threading.RLock()
_sessions = {}
_pending_sessions = {}
_last_activity = None
_lab_process = None
_verified_lab_pid = None
_stop_supervisor = threading.Event()
_shutdown_requested = threading.Event()


def _configured_idle_timeout():
    override = os.environ.get("AWS_ACADEMY_LAB_IDLE_TIMEOUT_SECONDS")
    if override is not None:
        timeout = int(override)
    elif CONFIG_FILE.exists():
        config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        timeout = config.get("lab_idle_timeout_seconds") if isinstance(config, dict) else None
    else:
        timeout = 120
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1:
        raise ValueError("lab_idle_timeout_seconds debe ser un entero positivo.")
    return timeout


IDLE_TIMEOUT_SECONDS = _configured_idle_timeout()
PLATFORM_PID_FILE = WEB_DIR / (
    ".platform_server.pid" if PORT == 8765 else f".platform_server-{PORT}.pid"
)
LAB_PID_FILE = LAB_DIR / (
    ".web_server.pid" if LAB_PORT == 8766 else f".web_server-{LAB_PORT}.pid"
)


def _json_response(url):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=1.5) as response:
        return json.loads(response.read().decode("utf-8"))


def _lab_health():
    try:
        payload = _json_response(f"http://{HOST}:{LAB_PORT}/api/health")
    except (OSError, ValueError, urllib.error.URLError):
        return None
    if payload.get("status") != "ok" or payload.get("service") != LAB_SERVICE_NAME:
        return None
    return payload


def _port_is_open(port):
    try:
        with socket.create_connection((HOST, port), timeout=0.4):
            return True
    except OSError:
        return False


def _process_status(pid, expected_script):
    if not isinstance(pid, int) or pid <= 0:
        return None
    python_path = str(PYTHON).replace("'", "''")
    script_path = str(expected_script).replace("'", "''")
    command = (
        f"try {{ $p = Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' "
        "-ErrorAction Stop } catch { exit 3 }; "
        "if (-not $p) { exit 2 }; "
        f"if ($p -and $p.ExecutablePath -ieq '{python_path}' "
        f"-and $p.CommandLine -and $p.CommandLine.Contains('{script_path}')) "
        "{ exit 0 }; exit 1"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode == 0:
        return True
    if result.returncode == 2:
        return False
    return None


def _registered_lab_pid(validate_process=True):
    global _verified_lab_pid
    try:
        pid = int(LAB_PID_FILE.read_text(encoding="ascii").strip())
    except (OSError, ValueError):
        _verified_lab_pid = None
        return None
    if _lab_process is not None and _lab_process.pid == pid:
        if _lab_process.poll() is not None:
            return None
        if not validate_process or _process_status(pid, LAB_SERVER) is True:
            return pid
        return None
    if not validate_process and _verified_lab_pid == pid:
        return pid
    if _process_status(pid, LAB_SERVER) is True:
        _verified_lab_pid = pid
        return pid
    if _verified_lab_pid == pid:
        _verified_lab_pid = None
    return None


def _lab_is_managed():
    return _lab_health() is not None and _registered_lab_pid(validate_process=False) is not None


def _start_lab_locked():
    global _lab_process, _last_activity, _verified_lab_pid

    if _lab_is_managed():
        return True, "El laboratorio ya está activo."
    if _port_is_open(LAB_PORT):
        return False, f"El puerto {LAB_PORT} está ocupado por un servicio no identificado."
    if not PYTHON.is_file():
        return False, f"No se encontró Python 3.12 en {PYTHON}."
    if not LAB_SERVER.is_file():
        return False, f"No se encontró el servidor del LAB 01 en {LAB_SERVER}."

    try:
        _lab_process = subprocess.Popen(
            [str(PYTHON), str(LAB_SERVER)],
            cwd=str(LAB_DIR),
            stdin=subprocess.DEVNULL,
        )
    except OSError as exc:
        return False, f"No se pudo iniciar el servidor del LAB 01: {exc}"

    deadline = time.monotonic() + 12
    while time.monotonic() < deadline:
        if _lab_process.poll() is not None:
            return False, f"El servidor del LAB 01 terminó con código {_lab_process.returncode}."
        try:
            pid_matches = LAB_PID_FILE.read_text(encoding="ascii").strip() == str(_lab_process.pid)
        except OSError:
            pid_matches = False
        if _lab_health() is not None and pid_matches:
            _verified_lab_pid = _lab_process.pid
            _last_activity = time.monotonic()
            return True, "Servidor del LAB 01 iniciado."
        time.sleep(0.25)

    if _lab_process.poll() is None:
        try:
            _lab_process.terminate()
            _lab_process.wait(timeout=5)
        except (OSError, subprocess.TimeoutExpired):
            return False, "No se pudo detener el proceso del LAB 01 que no respondió al inicio."
    return False, "El servidor del LAB 01 no respondió dentro del tiempo esperado."


def _stop_lab_locked():
    global _lab_process, _last_activity, _verified_lab_pid

    pid = _registered_lab_pid(validate_process=True)
    if pid is None:
        if _lab_health() is not None:
            return False, "El puerto responde, pero el PID no pudo verificarse; no se detuvo ningún proceso."
        try:
            stale_pid = int(LAB_PID_FILE.read_text(encoding="ascii").strip())
        except (OSError, ValueError):
            _last_activity = None
            return True, "El servidor del LAB 01 ya estaba detenido."
        process_status = _process_status(stale_pid, LAB_SERVER)
        if process_status is False:
            try:
                LAB_PID_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            _last_activity = None
            return True, "El servidor del LAB 01 ya estaba detenido."
        return False, "El PID registrado no pudo verificarse; no se detuvo ningún proceso."

    if _lab_process is not None and _lab_process.pid == pid:
        process = _lab_process
        try:
            process.terminate()
            process.wait(timeout=8)
        except (OSError, subprocess.TimeoutExpired):
            return False, "No se confirmó la detención del proceso del LAB 01."
        if process.poll() is not None:
            try:
                if LAB_PID_FILE.read_text(encoding="ascii").strip() == str(pid):
                    LAB_PID_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            _lab_process = None
            _verified_lab_pid = None
            _last_activity = None
            return True, "Servidor del LAB 01 detenido."
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError as exc:
            return False, f"No se pudo solicitar la detención del LAB 01: {exc}"

    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        process_status = _process_status(pid, LAB_SERVER)
        if process_status is False:
            try:
                if LAB_PID_FILE.read_text(encoding="ascii").strip() == str(pid):
                    LAB_PID_FILE.unlink(missing_ok=True)
            except OSError:
                pass
            _lab_process = None
            _verified_lab_pid = None
            _last_activity = None
            return True, "Servidor del LAB 01 detenido."
        if process_status is None:
            return False, "No se pudo verificar el proceso del LAB 01; no se confirmó su detención."
        time.sleep(0.25)
    return False, "El proceso del LAB 01 continúa activo; no se intentó detener otros procesos."


def _expire_sessions(now):
    expired = [key for key, seen in _sessions.items() if now - seen >= IDLE_TIMEOUT_SECONDS]
    for key in expired:
        del _sessions[key]

    pending_ttl = min(60, IDLE_TIMEOUT_SECONDS)
    expired_pending = [
        session_id for session_id, created in _pending_sessions.items()
        if now - created >= pending_ttl
    ]
    for session_id in expired_pending:
        del _pending_sessions[session_id]


def _active_session_count():
    return len(_sessions)


def _status_payload():
    global _last_activity
    now = time.monotonic()
    _expire_sessions(now)
    running = _lab_is_managed()
    if running and _last_activity is None:
        _last_activity = now
    active_sessions = _active_session_count()
    pending_sessions = len(_pending_sessions)
    if active_sessions:
        idle_seconds = max(0, int(now - max(_sessions.values())))
    elif pending_sessions:
        idle_seconds = 0
    elif _last_activity is not None:
        idle_seconds = max(0, int(now - _last_activity))
    else:
        idle_seconds = None
    remaining = None
    if running and active_sessions == 0 and pending_sessions == 0 and idle_seconds is not None:
        remaining = max(0, IDLE_TIMEOUT_SECONDS - idle_seconds)
    return {
        "ok": True,
        "service": "academylab",
        "status": "ok",
        "host": HOST,
        "port": PORT,
        "lab": {
            "service": LAB_SERVICE_NAME,
            "host": HOST,
            "port": LAB_PORT,
            "running": running,
            "active_sessions": active_sessions,
            "pending_sessions": pending_sessions,
            "idle_timeout_seconds": IDLE_TIMEOUT_SECONDS,
            "idle_seconds": idle_seconds,
            "seconds_until_shutdown": remaining,
        },
    }


def _supervise_lab():
    global _last_activity
    while not _stop_supervisor.wait(2):
        with _lock:
            now = time.monotonic()
            _expire_sessions(now)
            if not _lab_is_managed():
                continue
            if _sessions or _pending_sessions:
                continue
            if _last_activity is None:
                _last_activity = now
            if now - _last_activity >= IDLE_TIMEOUT_SECONDS:
                stopped, message = _stop_lab_locked()
                print(message, flush=True)
                if not stopped:
                    _last_activity = now


class Handler(BaseHTTPRequestHandler):
    def _send(self, status_code, payload, origin=None, set_cookie=None):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-store")
        if origin:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        if set_cookie:
            self.send_header("Set-Cookie", set_cookie)
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _local_request(self):
        if self.client_address[0] != "127.0.0.1":
            return False
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]").lower()
        return host in {"127.0.0.1", "localhost"}

    def _origin(self, allowed_ports):
        origin = self.headers.get("Origin")
        if origin is None:
            return None
        allowed = {
            f"http://{hostname}:{port}"
            for hostname in (HOST, "localhost")
            for port in allowed_ports
        }
        return origin if origin in allowed else False

    def _learner_session(self, create=False):
        cookie = SimpleCookie()
        try:
            cookie.load(self.headers.get("Cookie", ""))
        except CookieError:
            cookie = SimpleCookie()
        session_cookie = cookie.get(LEARNING_SESSION_COOKIE)
        token = session_cookie.value if session_cookie else None
        if token and re.fullmatch(r"[A-Za-z0-9_-]{40,60}", token):
            token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
            learner_id = progress_store.learner_for_session(token_hash)
            if learner_id:
                return learner_id, None
        if not create:
            return None, None

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(token.encode("ascii")).hexdigest()
        learner_id = progress_store.create_learner_session(token_hash)
        set_cookie = (
            f"{LEARNING_SESSION_COOKIE}={token}; Path=/; HttpOnly; "
            f"SameSite=Strict; Max-Age={LEARNING_SESSION_MAX_AGE}"
        )
        return learner_id, set_cookie

    def _read_json(self, limit=8192):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > limit:
                raise ValueError("El cuerpo de la solicitud supera el tamaño permitido.")
            if length == 0:
                return {}, None
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("El cuerpo debe ser un objeto JSON.")
            return payload, None
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            return None, str(exc)

    def do_OPTIONS(self):
        if not self._local_request():
            self._send(403, {"ok": False, "error": "Solo se permiten solicitudes locales."})
            return
        origin = self._origin({PORT, LAB_PORT})
        if origin is False or urlparse(self.path).path not in {"/api/lab/heartbeat", "/api/lab/leave"}:
            self._send(403, {"ok": False, "error": "Origen no permitido."})
            return
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", origin or f"http://{HOST}:{PORT}")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Max-Age", "300")
        self.send_header("Vary", "Origin")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if not self._local_request():
            self._send(403, {"error": "Solo se permiten solicitudes locales."})
            return
        path = urlparse(self.path).path
        if path in REDIRECTS:
            self.send_response(301)
            self.send_header("Location", REDIRECTS[path])
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        if path in STATIC_FILES:
            file_path, content_type = STATIC_FILES[path]
            try:
                body = (
                    json.dumps(
                        learning_service.public_catalog(),
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                    if path == "/catalog/learning_catalog.json"
                    else file_path.read_bytes()
                )
            except OSError as exc:
                self._send(500, {"error": f"No se pudo leer el recurso web: {exc}"})
                return
            except ValueError as exc:
                self._send(500, {"error": f"No se pudo preparar el catálogo educativo: {exc}"})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass
            return
        if path == "/api/health":
            self._send(200, {
                "status": "ok",
                "service": "academylab",
                "host": HOST,
                "port": PORT,
                "lab_port": LAB_PORT,
            })
            return
        if path == "/api/learning/session":
            try:
                _, set_cookie = self._learner_session(create=True)
            except (OSError, sqlite3.Error) as exc:
                print(f"[platform] learning session error: {exc}", flush=True)
                self._send(500, {"ok": False, "error": "No se pudo iniciar el perfil local."})
                return
            self._send(200, {"ok": True}, set_cookie=set_cookie)
            return
        if path == "/api/learning/course":
            course_id = parse_qs(urlparse(self.path).query).get("course_id", [None])[0]
            try:
                self._send(200, {"ok": True, "course": learning_service.get_course(course_id)})
            except LookupError as exc:
                self._send(404, {"ok": False, "error": str(exc)})
            except ValueError as exc:
                self._send(400, {"ok": False, "error": str(exc)})
            return
        if path == "/api/learning/project":
            self._send(200, {"ok": True, "project": learning_service.get_project()})
            return
        if path == "/api/learning/linux-status":
            self._send(200, {
                "ok": True,
                "environment": learning_service.linux_environment_status(),
            })
            return
        if path == "/api/learning/progress":
            learner_id, _ = self._learner_session()
            if not learner_id:
                self._send(401, {"ok": False, "error": "Inicia el perfil local antes de consultar el progreso."})
                return
            try:
                self._send(200, {"ok": True, "progress": learning_service.get_progress(learner_id)})
            except ValueError as exc:
                self._send(400, {"ok": False, "error": str(exc)})
            return
        if path == "/api/lab/status":
            with _lock:
                payload = _status_payload()
            self._send(200, payload)
            return
        self._send(404, {"error": "No encontrado"})

    def do_POST(self):
        if not self._local_request():
            self._send(403, {"ok": False, "error": "Solo se permiten solicitudes locales."})
            return
        path = urlparse(self.path).path
        is_learning_request = path.startswith("/api/learning/")
        allowed_ports = (
            {PORT}
            if is_learning_request or path in {"/api/lab/start", "/api/lab/manual-stop", "/api/platform/shutdown"}
            else {PORT, LAB_PORT}
        )
        origin = self._origin(allowed_ports)
        if origin is False:
            self._send(403, {"ok": False, "error": "Origen no permitido."})
            return
        if is_learning_request and origin is None:
            self._send(403, {"ok": False, "error": "La API de aprendizaje requiere un origen local válido."})
            return
        if is_learning_request and not self.headers.get("Content-Type", "").lower().startswith("application/json"):
            self._send(415, {"ok": False, "error": "La API de aprendizaje requiere Content-Type application/json."})
            return
        payload, error = self._read_json()
        if error:
            self._send(400, {"ok": False, "error": error}, origin if path in {"/api/lab/heartbeat", "/api/lab/leave"} else None)
            return

        if is_learning_request:
            learner_id, _ = self._learner_session()
            if not learner_id:
                self._send(401, {"ok": False, "error": "Inicia el perfil local antes de enviar actividades."}, origin)
                return
            payload.pop("learner_id", None)
            payload["learner_id"] = learner_id
            try:
                if path == "/api/learning/start-course":
                    result = learning_service.start_course(payload.get("learner_id"), payload.get("course_id"))
                elif path == "/api/learning/submit-exercise":
                    result = learning_service.submit_exercise(payload)
                elif path == "/api/learning/submit-assessment":
                    result = learning_service.submit_assessment(payload)
                elif path == "/api/learning/submit-project":
                    result = learning_service.submit_project(payload)
                else:
                    self._send(404, {"ok": False, "error": "Ruta de aprendizaje no encontrada."})
                    return
                self._send(200, {"ok": True, "result": result})
            except progress_store.LearningAccessError as exc:
                self._send(403, {"ok": False, "error": str(exc)}, origin)
            except LookupError as exc:
                self._send(404, {"ok": False, "error": str(exc)})
            except ValueError as exc:
                self._send(400, {"ok": False, "error": str(exc)})
            except (OSError, sqlite3.Error, KeyError) as exc:
                print(f"[platform] learning API error: {exc}", flush=True)
                self._send(500, {"ok": False, "error": "No se pudo completar la operación de aprendizaje."})
            return

        if path == "/api/lab/start":
            with _lock:
                started, message = _start_lab_locked()
                if not started:
                    self._send(503, {"ok": False, "error": message})
                    return
                session_id = str(uuid.uuid4())
                _pending_sessions[session_id] = time.monotonic()
                self._send(200, {
                    "ok": True,
                    "message": message,
                    "url": f"http://{HOST}:{LAB_PORT}/?session={session_id}",
                })
            return

        if path == "/api/lab/heartbeat":
            session_id = payload.get("session_id")
            tab_id = payload.get("tab_id")
            if not _valid_uuid(session_id) or not _valid_uuid(tab_id):
                self._send(400, {"ok": False, "error": "Identificador de sesión o pestaña inválido."}, origin)
                return
            with _lock:
                _expire_sessions(time.monotonic())
                if not _lab_is_managed():
                    self._send(409, {"ok": False, "error": "El servidor del LAB 01 no está activo."}, origin)
                    return
                normalized_session = str(uuid.UUID(session_id))
                if normalized_session not in _pending_sessions and not any(
                    active_session == normalized_session for active_session, _ in _sessions
                ):
                    self._send(404, {"ok": False, "error": "La sesión no fue iniciada desde academyLab."}, origin)
                    return
                _pending_sessions.pop(normalized_session, None)
                _sessions[(normalized_session, str(uuid.UUID(tab_id)))] = time.monotonic()
                self._last_activity = time.monotonic()
                self._send(200, {"ok": True, "idle_timeout_seconds": IDLE_TIMEOUT_SECONDS}, origin)
            return

        if path == "/api/lab/leave":
            session_id = payload.get("session_id")
            tab_id = payload.get("tab_id")
            if not _valid_uuid(session_id) or not _valid_uuid(tab_id):
                self._send(400, {"ok": False, "error": "Identificador de sesión o pestaña inválido."}, origin)
                return
            with _lock:
                key = (str(uuid.UUID(session_id)), str(uuid.UUID(tab_id)))
                if key not in _sessions:
                    self._send(404, {"ok": False, "error": "La sesión de esta pestaña ya no está activa."}, origin)
                    return
                del _sessions[key]
                _expire_sessions(time.monotonic())
                remaining = _active_session_count()
                pending = len(_pending_sessions)
                if remaining or pending:
                    self._send(200, {
                        "ok": True,
                        "stopped": False,
                        "active_sessions": remaining,
                        "pending_sessions": pending,
                        "message": "El laboratorio sigue activo porque hay otras pestañas en uso.",
                    }, origin)
                    return
                stopped, message = _stop_lab_locked()
                self._send(200 if stopped else 503, {
                    "ok": stopped,
                    "stopped": stopped,
                    "active_sessions": 0,
                    "message": message,
                }, origin)
            return

        if path == "/api/lab/manual-stop":
            with _lock:
                _expire_sessions(time.monotonic())
                if _active_session_count() or _pending_sessions:
                    self._send(409, {
                        "ok": False,
                        "error": "Hay pestañas activas o ingresando al laboratorio. Ciérralas desde el botón del curso e inténtalo otra vez.",
                    })
                    return
                stopped, message = _stop_lab_locked()
                self._send(200 if stopped else 503, {"ok": stopped, "message": message})
            return

        if path == "/api/platform/shutdown":
            with _lock:
                _expire_sessions(time.monotonic())
                if _active_session_count() or _pending_sessions:
                    self._send(409, {
                        "ok": False,
                        "error": "El laboratorio tiene pestañas activas. Ciérralas antes de detener toda la plataforma.",
                    })
                    return
                stopped, message = _stop_lab_locked()
                if not stopped:
                    self._send(503, {"ok": False, "error": message})
                    return
                self._send(200, {"ok": True, "message": "La plataforma se está deteniendo."})
                _shutdown_requested.set()
            return

        self._send(404, {"ok": False, "error": "No encontrado"})

    def log_message(self, format_string, *args):
        print(f"[platform] {self.address_string()} - {format_string % args}", flush=True)


def _valid_uuid(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-fA-F-]{36}", value):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def main():
    if IDLE_TIMEOUT_SECONDS < 1:
        raise ValueError("AWS_ACADEMY_LAB_IDLE_TIMEOUT_SECONDS debe ser un entero positivo.")
    if not 1 <= PORT <= 65535 or not 1 <= LAB_PORT <= 65535 or PORT == LAB_PORT:
        raise ValueError("Los puertos configurados deben ser válidos y diferentes.")

    learning_service.validate_catalog()
    progress_store.initialize()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    PLATFORM_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLATFORM_PID_FILE.write_text(str(os.getpid()), encoding="ascii")

    serving = threading.Thread(target=server.serve_forever, name="platform-http", daemon=True)
    supervisor = threading.Thread(target=_supervise_lab, name="lab-supervisor", daemon=True)
    serving.start()
    supervisor.start()
    print(f"academyLab en http://{HOST}:{PORT}", flush=True)
    print(f"LAB 01 bajo demanda en http://{HOST}:{LAB_PORT}; inactividad: {IDLE_TIMEOUT_SECONDS} s.", flush=True)

    try:
        while serving.is_alive() and not _shutdown_requested.wait(0.5):
            pass
    except KeyboardInterrupt:
        print("Detención solicitada desde la consola.", flush=True)
    finally:
        _stop_supervisor.set()
        supervisor.join(timeout=3)
        with _lock:
            if _registered_lab_pid() is not None:
                stopped, message = _stop_lab_locked()
                print(message, flush=True)
                if not stopped:
                    print("No se confirmó la detención del LAB 01.", flush=True)
        server.shutdown()
        server.server_close()
        serving.join(timeout=3)
        try:
            if PLATFORM_PID_FILE.read_text(encoding="ascii").strip() == str(os.getpid()):
                PLATFORM_PID_FILE.unlink()
        except FileNotFoundError:
            pass
        print("academyLab detenido.", flush=True)


if __name__ == "__main__":
    main()
