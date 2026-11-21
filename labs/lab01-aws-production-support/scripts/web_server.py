#!/usr/bin/env python3
"""Servidor web local del LAB 01."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BASE.parent.parent
# ACADEMYLAB_PYTHON o el ejecutable base del proceso actual (mismo criterio que la plataforma).
PY = Path(
    os.environ.get("ACADEMYLAB_PYTHON")
    or getattr(sys, "_base_executable", None)
    or sys.executable
)
SCRIPT_ANALYZER = BASE / "scripts" / "analizar_logs.py"
SCRIPT_TESTS = BASE / "scripts" / "run_tests.py"
TEST_DIR = BASE / "data" / "test"
EVIDENCE_DIR = BASE / "evidence"
EVIDENCE_FILE = EVIDENCE_DIR / "resumen_logs.json"
PORT = int(os.environ.get("AWS_ACADEMY_LAB_PORT", "8766"))
PID_FILE = BASE / (".web_server.pid" if PORT == 8766 else f".web_server-{PORT}.pid")
HOST = "127.0.0.1"
STATIC_FILES = {
    "/": (BASE / "index.html", "text/html; charset=utf-8"),
    "/labs/lab01-aws-production-support/": (BASE / "index.html", "text/html; charset=utf-8"),
    "/styles.css": (BASE / "styles.css", "text/css; charset=utf-8"),
    "/app.js": (BASE / "app.js", "text/javascript; charset=utf-8"),
}
REDIRECTS = {
    "/labs/lab01-aws-production-support": "/labs/lab01-aws-production-support/",
}

_lock = threading.Lock()


def safe_rel(filename):
    """Resolve only an existing, direct-child .log file in data/test."""
    if not isinstance(filename, str) or not filename or Path(filename).name != filename:
        return None
    if "/" in filename or "\\" in filename or Path(filename).suffix.lower() != ".log":
        return None
    root = TEST_DIR.resolve()
    candidate = (root / filename).resolve()
    if candidate.parent != root or not candidate.is_file():
        return None
    return candidate


def run_analyzer(filename):
    path = safe_rel(filename)
    if path is None:
        return {"ok": False, "error": "Archivo no permitido: seleccione un archivo .log de data/test.", "file": filename}

    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=".resumen_logs-", suffix=".json", dir=str(EVIDENCE_DIR))
    os.close(fd)
    temporary_file = Path(temporary_name)
    try:
        proc = subprocess.run(
            [str(PY), str(SCRIPT_ANALYZER), "-i", str(path), "-j", str(temporary_file)],
            capture_output=True, text=True, timeout=120, cwd=str(BASE)
        )
        result = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "file": path.name,
        }
        if proc.returncode != 0:
            return result
        data = json.loads(temporary_file.read_text(encoding="utf-8"))
        os.replace(str(temporary_file), str(EVIDENCE_FILE))
        result["stdout"] = proc.stdout.replace(str(temporary_file), str(EVIDENCE_FILE))
        result["data"] = data
        return result
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": "El análisis superó el límite de 120 segundos.", "stdout": exc.stdout or "", "stderr": exc.stderr or ""}
    except (OSError, json.JSONDecodeError) as exc:
        return {"ok": False, "error": f"No se pudo completar el análisis: {exc}"}
    finally:
        temporary_file.unlink(missing_ok=True)


def run_tests():
    try:
        with tempfile.TemporaryDirectory(prefix="lab01-tests-") as temporary_dir:
            isolated_base = Path(temporary_dir)
            isolated_scripts = isolated_base / "scripts"
            isolated_data = isolated_base / "data"
            isolated_scripts.mkdir()
            isolated_data.mkdir()
            (isolated_base / "evidence").mkdir()
            shutil.copy2(SCRIPT_ANALYZER, isolated_scripts / SCRIPT_ANALYZER.name)
            isolated_tests = isolated_scripts / SCRIPT_TESTS.name
            shutil.copy2(SCRIPT_TESTS, isolated_tests)
            shutil.copytree(TEST_DIR, isolated_data / "test")
            # La prueba de coherencia CSV/log usa los datos de ejemplo del LAB.
            shutil.copytree(BASE / "data" / "sample_logs", isolated_data / "sample_logs")
            shutil.copytree(BASE / "data" / "synthetic", isolated_data / "synthetic")
            proc = subprocess.run(
                [str(PY), str(isolated_tests)],
                capture_output=True, text=True, timeout=300, cwd=str(isolated_base)
            )
        results = []
        for line in proc.stdout.splitlines():
            if line.startswith("PASS:") or line.startswith("FAIL:"):
                status, detail = line.split(":", 1)
                name, separator, message = detail.strip().partition(" -> ")
                results.append({
                    "name": name,
                    "status": status,
                    "detail": message if separator else "",
                })
        passed = sum(1 for result in results if result["status"] == "PASS")
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "results": results,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "error": "Las pruebas superaron el límite de 300 segundos.", "stdout": exc.stdout or "", "stderr": exc.stderr or ""}
    except OSError as exc:
        return {"ok": False, "error": f"No se pudieron ejecutar las pruebas: {exc}"}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, content_type="application/json; charset=utf-8"):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
            pass

    def _read_json(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length < 0 or length > 65536:
                raise ValueError("El cuerpo de la solicitud es demasiado grande.")
            if length == 0:
                return {}, None
            payload = json.loads(self.rfile.read(length))
            if not isinstance(payload, dict):
                raise ValueError("El cuerpo debe ser un objeto JSON.")
            return payload, None
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            return None, str(exc)

    def _local_request(self):
        """Acepta solo clientes locales con un Host local (mitiga DNS rebinding)."""
        if self.client_address[0] != "127.0.0.1":
            return False
        host = self.headers.get("Host", "").split(":", 1)[0].strip("[]").lower()
        return host in {"127.0.0.1", "localhost"}

    def _origin_allowed(self):
        """Un POST de navegador debe venir de la propia página del LAB.

        Las solicitudes sin Origin (scripts locales, curl) se aceptan; los navegadores
        siempre envían Origin en un POST, así que una página externa queda rechazada.
        """
        origin = self.headers.get("Origin")
        if origin is None:
            return True
        return origin in {f"http://127.0.0.1:{PORT}", f"http://localhost:{PORT}"}

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
        elif path == "/favicon.ico":
            self.send_response(204)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif path in STATIC_FILES:
            file_path, content_type = STATIC_FILES[path]
            try:
                body = file_path.read_bytes()
            except OSError as exc:
                self._send(500, {"error": f"No se pudo leer el recurso web: {exc}"})
                return
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionAbortedError, ConnectionResetError):
                pass
        elif path == "/api/health":
            self._send(200, {
                "status": "ok",
                "service": "aws-lab-01",
                "python": str(PY),
                "host": HOST,
                "port": PORT,
            })
        elif path == "/api/files":
            files = []
            if TEST_DIR.exists():
                for file_path in sorted(TEST_DIR.iterdir()):
                    resolved = safe_rel(file_path.name)
                    if resolved is not None:
                        files.append({"name": file_path.name, "size": file_path.stat().st_size})
            self._send(200, {"files": files})
        elif path == "/api/evidence":
            try:
                data = json.loads(EVIDENCE_FILE.read_text(encoding="utf-8"))
                self._send(200, {"ok": True, "data": data})
            except FileNotFoundError:
                self._send(404, {"ok": False, "error": "Evidencia no disponible; ejecute un análisis primero."})
            except (OSError, json.JSONDecodeError) as exc:
                self._send(500, {"ok": False, "error": f"No se pudo leer la evidencia: {exc}"})
        else:
            self._send(404, {"error": "No encontrado"})

    def do_POST(self):
        if not self._local_request():
            self._send(403, {"ok": False, "error": "Solo se permiten solicitudes locales."})
            return
        if not self._origin_allowed():
            self._send(403, {"ok": False, "error": "Origen no permitido."})
            return
        path = urlparse(self.path).path
        payload, error = self._read_json()
        if error:
            self._send(400, {"ok": False, "error": error})
            return
        if path == "/api/analyze":
            if not isinstance(payload.get("file"), str):
                self._send(400, {"ok": False, "error": "Indique el nombre de un archivo .log permitido."})
                return
            with _lock:
                result = run_analyzer(payload["file"])
            self._send(200 if result["ok"] else 400 if "returncode" not in result else 500, result)
        elif path == "/api/tests":
            with _lock:
                result = run_tests()
            self._send(200 if result["ok"] else 500, result)
        else:
            self._send(404, {"error": "No encontrado"})

    def log_message(self, format_string, *args):
        status = args[3] if len(args) > 3 else "-"
        print(f"[lab01] {self.address_string()} {self.command} {urlparse(self.path).path} {status}", flush=True)


def main():
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.daemon_threads = True
    PID_FILE.write_text(str(os.getpid()), encoding="ascii")
    print(f"Servidor web LAB 01 en http://{HOST}:{PORT}", flush=True)
    print(f"Python: {PY}", flush=True)
    print("Detener con Ctrl+C o ejecutar detener_web.bat.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.", flush=True)
    finally:
        server.server_close()
        try:
            if PID_FILE.read_text(encoding="ascii").strip() == str(os.getpid()):
                PID_FILE.unlink()
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    main()