"""Controles de Host y Origin del servidor del LAB 01."""
import importlib.util
import json
import threading
import unittest
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path


LAB_SERVER = (
    Path(__file__).resolve().parents[2]
    / "labs" / "lab01-aws-production-support" / "scripts" / "web_server.py"
)
_spec = importlib.util.spec_from_file_location("lab01_web_server", LAB_SERVER)
lab_server = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lab_server)


class LabWebServerSecurityTests(unittest.TestCase):
    def setUp(self):
        self.original_port = lab_server.PORT
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), lab_server.Handler)
        self.server.daemon_threads = True
        lab_server.PORT = self.server.server_address[1]
        self.origin = f"http://127.0.0.1:{lab_server.PORT}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        lab_server.PORT = self.original_port

    def _request(self, method, path, body=None, headers=None):
        connection = HTTPConnection("127.0.0.1", lab_server.PORT, timeout=5)
        try:
            data = None if body is None else json.dumps(body).encode("utf-8")
            connection.request(method, path, body=data, headers=headers or {})
            response = connection.getresponse()
            return response.status, json.loads(response.read().decode("utf-8") or "{}")
        finally:
            connection.close()

    def test_local_host_is_served(self):
        status, payload = self._request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(payload["service"], "aws-lab-01")

    def test_foreign_host_header_is_rejected(self):
        status, _ = self._request("GET", "/api/files", headers={"Host": "evil.example"})
        self.assertEqual(status, 403)
        status, _ = self._request(
            "POST", "/api/analyze", {"file": "normal.log"}, headers={"Host": "evil.example"}
        )
        self.assertEqual(status, 403)

    def test_cross_origin_post_is_rejected_before_running_anything(self):
        for path in ("/api/analyze", "/api/tests"):
            status, payload = self._request(
                "POST",
                path,
                {"file": "normal.log"},
                headers={"Origin": "http://evil.example", "Content-Type": "text/plain"},
            )
            self.assertEqual(status, 403, path)
            self.assertEqual(payload["error"], "Origen no permitido.")

    def test_lab_page_origin_reaches_the_file_validation(self):
        # Un archivo fuera de data/test se rechaza con 400 sin ejecutar el analizador.
        status, payload = self._request(
            "POST",
            "/api/analyze",
            {"file": "../../../web/platform_server.py"},
            headers={"Origin": self.origin, "Content-Type": "application/json"},
        )
        self.assertEqual(status, 400)
        self.assertIn("Archivo no permitido", payload["error"])


if __name__ == "__main__":
    unittest.main()
