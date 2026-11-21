import json
import sys
import tempfile
import threading
import unittest
import uuid
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.server import ThreadingHTTPServer
from unittest import mock


WEB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_DIR))

import platform_server
import progress_store


class LearningApiSecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = progress_store.DATABASE
        self.original_port = platform_server.PORT
        progress_store.DATABASE = Path(self.temp_dir.name) / "progress.sqlite3"
        progress_store.initialize()
        self._start_server()
        self.client_a = build_opener(HTTPCookieProcessor(CookieJar()))
        self.client_b = build_opener(HTTPCookieProcessor(CookieJar()))

    def _start_server(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), platform_server.Handler)
        self.server.daemon_threads = True
        platform_server.PORT = self.server.server_address[1]
        self.origin = f"http://127.0.0.1:{platform_server.PORT}"
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def tearDown(self):
        self._stop_server()
        platform_server.PORT = self.original_port
        progress_store.DATABASE = self.original_database
        self.temp_dir.cleanup()

    def _request(self, client, path, payload=None, include_origin=True):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(f"{self.origin}{path}", data=data)
        if data is not None:
            request.add_header("Content-Type", "application/json")
            if include_origin:
                request.add_header("Origin", self.origin)
        with client.open(request, timeout=3) as response:
            return response.status, json.loads(response.read().decode("utf-8")), response.headers

    def _post(self, client, path, payload, include_origin=True):
        try:
            return self._request(client, path, payload, include_origin)
        except HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8")), error.headers

    def test_session_cookie_binds_progress_and_ignores_submitted_learner_ids(self):
        _, _, session_headers = self._request(self.client_a, "/api/learning/session")
        self.assertIn("HttpOnly", session_headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", session_headers["Set-Cookie"])
        self._request(self.client_b, "/api/learning/session")

        _, own_progress, _ = self._request(self.client_a, "/api/learning/progress")
        _, _, _ = self._post(self.client_b, "/api/learning/start-course", {
            "learner_id": own_progress["progress"]["learner_id"],
            "course_id": "sql",
        })
        _, other_progress, _ = self._request(self.client_b, "/api/learning/progress")
        other_id = other_progress["progress"]["learner_id"]
        self.assertNotEqual(own_progress["progress"]["learner_id"], other_id)

        _, forged_read, _ = self._request(
            self.client_a,
            f"/api/learning/progress?learner_id={other_id}",
        )
        self.assertEqual(forged_read["progress"]["courses"], [])

        status, forged_write, _ = self._post(self.client_a, "/api/learning/submit-assessment", {
            "learner_id": other_id,
            "course_id": "sql",
            "module_id": "sql-operational-queries",
            "assessment_id": "sql-basics-assessment",
            "answers": {},
        })
        self.assertEqual(status, 403)
        self.assertIn("Inicia el curso", forged_write["error"])
        _, final_a, _ = self._request(self.client_a, "/api/learning/progress")
        _, final_b, _ = self._request(self.client_b, "/api/learning/progress")
        self.assertEqual(final_a["progress"]["attempts"], [])
        self.assertEqual(len(final_b["progress"]["courses"]), 1)

    def test_learning_mutations_require_a_local_origin(self):
        self._request(self.client_a, "/api/learning/session")
        status, payload, _ = self._post(
            self.client_a,
            "/api/learning/start-course",
            {"course_id": "sql"},
            include_origin=False,
        )
        self.assertEqual(status, 403)
        self.assertIn("origen local", payload["error"])

    def test_navigation_routes_and_planned_profiles_are_consistent(self):
        routes = (
            "/",
            "/profiles/cloud-production-support/",
            "/routes/cloud-production-support/basic/",
            "/routes/cloud-production-support/intermediate/",
            "/routes/cloud-production-support/advanced/",
            "/courses/linux/?level=basic",
            "/projects/support-basic/",
        )
        for path in routes:
            with self.client_a.open(f"{self.origin}{path}", timeout=3) as response:
                body = response.read().decode("utf-8")
                self.assertEqual(response.status, 200, path)
                self.assertIn("text/html", response.headers["Content-Type"], path)
                self.assertTrue(body.strip(), path)

        with mock.patch.object(
            platform_server.learning_service.linux_runtime,
            "status",
            return_value={"available": False, "reason": "Ubuntu no está inicializado."},
        ):
            _, response, _ = self._request(self.client_a, "/catalog/learning_catalog.json")
        catalog = response
        planned = [
            profile for profile in catalog["profiles"]
            if profile["availability"] == "planned"
        ]
        self.assertEqual(len(planned), 6)
        self.assertTrue(all("route_id" not in profile for profile in planned))
        route = next(item for item in catalog["routes"] if item["id"] == "cloud-production-support")
        expected_courses = {"linux", "networking", "sql", "aws", "python", "production-support"}
        for level in route["levels"]:
            self.assertEqual(set(level["course_ids"]), expected_courses)
        basic = next(item for item in catalog["courses"] if item["id"] == "linux")
        self.assertEqual(basic["contents_by_level"]["basic"]["availability"], "pending_environment")

    def test_progress_and_session_survive_server_restart_without_duplicate_attempts(self):
        self._request(self.client_a, "/api/learning/session")
        _, _, _ = self._post(self.client_a, "/api/learning/start-course", {
            "course_id": "production-support",
        })
        _, attempt, _ = self._post(self.client_a, "/api/learning/submit-exercise", {
            "course_id": "production-support",
            "module_id": "support-incident-basics",
            "exercise_id": "support-guided-pending",
            "answer": "track",
        })
        self.assertEqual(attempt["result"]["attempt_number"], 1)

        for _ in range(2):
            _, progress, _ = self._request(self.client_a, "/api/learning/progress")
            self.assertEqual(len(progress["progress"]["attempts"]), 1)

        self._stop_server()
        progress_store.initialize()
        self._start_server()
        _, restored, _ = self._request(self.client_a, "/api/learning/progress")
        self.assertEqual(len(restored["progress"]["attempts"]), 1)
        self.assertEqual(restored["progress"]["attempts"][0]["attempt_number"], 1)

    def test_lab_heartbeat_updates_the_shared_last_activity(self):
        session_id = str(uuid.uuid4())
        tab_id = str(uuid.uuid4())
        original_activity = platform_server._last_activity
        platform_server._last_activity = 0.0
        platform_server._pending_sessions[session_id] = platform_server.time.monotonic()
        try:
            with mock.patch.object(platform_server, "_lab_is_managed", return_value=True):
                status, payload, _ = self._request(
                    self.client_a,
                    "/api/lab/heartbeat",
                    {"session_id": session_id, "tab_id": tab_id},
                )
            self.assertEqual(status, 200)
            self.assertTrue(payload["ok"])
            self.assertGreater(platform_server._last_activity, 0.0)
        finally:
            platform_server._pending_sessions.pop(session_id, None)
            platform_server._sessions.pop((session_id, tab_id), None)
            platform_server._last_activity = original_activity


if __name__ == "__main__":
    unittest.main()
