"""Fases 3 y 5: prácticas Linux que exigen ejecutar y responder una pregunta."""
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock


WEB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_DIR))

import learning_service
import linux_runtime
import progress_store


AVAILABLE = {
    "available": True,
    "distribution": "Ubuntu",
    "wsl_version": 2,
    "kernel": "test-kernel",
    "home": "/home/test",
}
PILOT_MODULE = "linux-log-investigation"


def reference_result(answer_correct, passed=True, stdout="22:2026-01-15T10:21:46Z operacion=LINUX-1022 estado=PENDIENTE\n"):
    return {
        "passed": passed,
        "answer_correct": answer_correct,
        "returncode": 0 if passed else 1,
        "stdout": stdout,
        "stderr": "" if passed else "grep: fallo simulado",
        "runtime": "test-kernel",
        "commands": ["grep -n \"PENDIENTE\" fixtures/production-support.log"],
        "exercise_id": "linux-logs-independent",
    }


class LinuxQuestionServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = progress_store.DATABASE
        progress_store.DATABASE = Path(self.temp_dir.name) / "progress.sqlite3"
        progress_store.initialize()
        learning_service.validate_catalog()
        self.learner_id = str(uuid.uuid4())
        self.status = mock.patch.object(learning_service.linux_runtime, "status", return_value=AVAILABLE)
        self.status.start()
        learning_service.start_course(self.learner_id, "linux")

    def tearDown(self):
        self.status.stop()
        progress_store.DATABASE = self.original_database
        self.temp_dir.cleanup()

    def payload(self, exercise_id="linux-logs-independent", **extra):
        return {
            "learner_id": self.learner_id,
            "course_id": "linux",
            "module_id": PILOT_MODULE,
            "exercise_id": exercise_id,
            **extra,
        }

    def linux_attempts(self):
        return [
            item for item in progress_store.get_progress(self.learner_id)["attempts"]
            if item["course_id"] == "linux"
        ]

    def test_every_linux_practice_has_a_question_and_options_come_from_the_runtime(self):
        course = learning_service.get_course("linux")
        exercise_ids = set()
        for module in course["modules"]:
            for key in ("guided_practice", "independent_practice"):
                exercise = module[key]
                exercise_ids.add(exercise["id"])
                self.assertTrue(exercise["question"], exercise["id"])
                self.assertTrue(exercise["answer_hint"], exercise["id"])
                self.assertEqual(exercise["options"], linux_runtime.exercise_options(exercise["id"]))
                serialized = repr(exercise)
                for secret in ("answer_script", "reference_option", "answer_pattern", "setup", "__ACADEMY"):
                    self.assertNotIn(secret, serialized)
                if key == "independent_practice":
                    self.assertGreater(len(exercise["options"]), 2, f"{exercise['id']} debe obligar a elegir.")
        self.assertEqual(len(exercise_ids), 14)
        self.assertEqual(linux_runtime.question_exercise_ids(), exercise_ids)

    def test_pilot_cannot_be_approved_by_just_pressing_the_button(self):
        with (
            mock.patch.object(learning_service, "_assert_module_access"),
            mock.patch.object(learning_service.linux_runtime, "verify_answer") as verify,
            mock.patch.object(learning_service.linux_runtime, "run_exercise") as run_exercise,
        ):
            for payload in (self.payload(), self.payload(answer=""), self.payload(answer="   ")):
                result = learning_service.submit_exercise(payload)
                self.assertFalse(result["passed"])
        verify.assert_not_called()
        run_exercise.assert_not_called()
        self.assertTrue(all(not item["passed"] for item in self.linux_attempts()))

    def test_wrong_answer_is_rejected_without_revealing_the_reference_output(self):
        with (
            mock.patch.object(learning_service, "_assert_module_access"),
            mock.patch.object(
                learning_service.linux_runtime,
                "verify_answer",
                return_value=reference_result(answer_correct=False),
            ),
        ):
            result = learning_service.submit_exercise(self.payload(answer="5"))
        self.assertFalse(result["passed"])
        self.assertNotIn("22", result["feedback"])
        self.assertNotIn("stdout", result["execution_result"])
        self.assertNotIn("22", repr(result["execution_result"]))

    def test_correct_answer_with_a_failed_ubuntu_run_is_not_approved(self):
        with (
            mock.patch.object(learning_service, "_assert_module_access"),
            mock.patch.object(
                learning_service.linux_runtime,
                "verify_answer",
                return_value=reference_result(answer_correct=True, passed=False, stdout=""),
            ),
        ):
            result = learning_service.submit_exercise(self.payload(answer="22"))
        self.assertFalse(result["passed"])

    def test_correct_answer_backed_by_a_real_run_is_approved(self):
        with (
            mock.patch.object(learning_service, "_assert_module_access"),
            mock.patch.object(
                learning_service.linux_runtime,
                "verify_answer",
                return_value=reference_result(answer_correct=True),
            ) as verify,
        ):
            result = learning_service.submit_exercise(self.payload(answer="22"))
        self.assertTrue(result["passed"], result["feedback"])
        verify.assert_called_once_with(self.learner_id, "linux-logs-independent", "22")
        self.assertNotIn("answer_correct", result["execution_result"])

    def test_browser_supplied_shell_text_is_rejected_for_question_practices(self):
        with (
            mock.patch.object(learning_service, "_assert_module_access"),
            mock.patch.object(learning_service.linux_runtime, "verify_answer") as verify,
            mock.patch.object(learning_service.linux_runtime, "run_option") as run_option,
        ):
            result = learning_service.submit_exercise(self.payload(answer="22", command="cat /etc/passwd"))
            self.assertFalse(result["passed"])
            with self.assertRaises(ValueError):
                learning_service.run_linux_option(self.payload(option_id="grep-n", script="rm -rf ~"))
        verify.assert_not_called()
        run_option.assert_not_called()

    def test_running_an_option_does_not_record_an_attempt(self):
        with (
            mock.patch.object(learning_service, "_assert_module_access"),
            mock.patch.object(
                learning_service.linux_runtime,
                "run_option",
                return_value={"passed": True, "stdout": "3\n", "commands": ["grep -c"]},
            ) as run_option,
        ):
            result = learning_service.run_linux_option(self.payload(option_id="grep-c"))
        run_option.assert_called_once_with(self.learner_id, "linux-logs-independent", "grep-c")
        self.assertEqual(result["execution_result"]["stdout"], "3\n")
        self.assertEqual(self.linux_attempts(), [])

    def test_running_options_respects_module_order_and_other_courses(self):
        # El módulo de logs sigue bloqueado hasta aprobar los anteriores.
        with self.assertRaises(progress_store.LearningAccessError):
            learning_service.run_linux_option(self.payload(option_id="grep-n"))
        # Las opciones de una práctica no sirven para otra.
        with mock.patch.object(learning_service, "_assert_module_access"):
            with self.assertRaises(ValueError):
                learning_service.run_linux_option({
                    **self.payload(option_id="grep-n"),
                    "module_id": "linux-foundations",
                    "exercise_id": "linux-paths-guided",
                })
        with self.assertRaises(LookupError):
            learning_service.run_linux_option({**self.payload(option_id="grep-n"), "course_id": "sql"})


class LinuxRuntimeQuestionTests(unittest.TestCase):
    learner_id = str(uuid.uuid4())

    def test_every_runtime_definition_is_consistent(self):
        import re
        for exercise_id, exercise in linux_runtime._EXERCISES.items():
            with self.subTest(exercise_id):
                self.assertIn(exercise["reference_option"], exercise["options"])
                re.compile(exercise["answer_pattern"])
                self.assertTrue(exercise["answer_script"].strip())
                for option_id, option in exercise["options"].items():
                    self.assertRegex(option_id, r"^[a-z0-9-]{1,40}$")
                    self.assertTrue(option["label"] and option["script"].endswith("\n"))
                self.assertTrue(exercise.get("setup", "\n").endswith("\n"))

    def test_setup_runs_before_options_and_before_the_reference(self):
        result = {"passed": True, "returncode": 0, "stdout": "__ACADEMY_ANSWER__=3\n", "stderr": "", "runtime": "k"}
        # side_effect: cada llamada recibe su propio dict (run_option modifica stdout).
        with mock.patch.object(linux_runtime, "_execute_in_workspace", side_effect=lambda *a: dict(result)) as execute:
            linux_runtime.run_option(self.learner_id, "linux-files-independent", "ver-contenido")
            option_body = execute.call_args.args[2]
            output = linux_runtime.verify_answer(self.learner_id, "linux-files-independent", "3")
            verify_body = execute.call_args.args[2]
        setup = linux_runtime._EXERCISES["linux-files-independent"]["setup"]
        self.assertTrue(option_body.startswith(setup))
        self.assertTrue(verify_body.startswith(setup))
        self.assertTrue(output["answer_correct"])

    def test_paths_ignore_a_trailing_slash(self):
        self.assertTrue(linux_runtime._answers_match("/home/a/", "/home/a", r"/[a-z/]+"))
        self.assertFalse(linux_runtime._answers_match("/home/b", "/home/a", r"/[a-z/]+"))

    def test_unknown_options_and_legacy_paths_are_rejected_before_touching_ubuntu(self):
        with mock.patch.object(linux_runtime, "_execute_in_workspace") as execute:
            for option_id in ("grep -n PENDIENTE", "../x", None, "rm"):
                with self.assertRaises(linux_runtime.LinuxRuntimeError):
                    linux_runtime.run_option(self.learner_id, "linux-logs-independent", option_id)
            with self.assertRaises(linux_runtime.LinuxRuntimeError):
                linux_runtime.run_option(self.learner_id, "linux-paths-guided", "grep-n")
            with self.assertRaises(linux_runtime.LinuxRuntimeError):
                linux_runtime.run_exercise(self.learner_id, "linux-logs-independent")
        execute.assert_not_called()

    def run_verify(self, answer, stdout, passed=True):
        result = {"passed": passed, "returncode": 0 if passed else 1, "stdout": stdout, "stderr": "", "runtime": "k"}
        with mock.patch.object(linux_runtime, "_execute_in_workspace", return_value=dict(result)) as execute:
            output = linux_runtime.verify_answer(self.learner_id, "linux-logs-independent", answer)
        return output, execute.call_args.args[2]

    def test_answer_is_compared_with_the_value_extracted_from_the_real_output(self):
        stdout = "22:linea\n\n__ACADEMY_ANSWER__=22\n\n__ACADEMY_CHECK_OK__\n"
        for answer, expected in (("22", True), (" 22 ", True), ("022", True), ("21", False), ("22a", False), ("", False)):
            output, body = self.run_verify(answer, stdout)
            self.assertEqual(output["answer_correct"], expected, answer)
            self.assertNotIn("__ACADEMY_ANSWER__", output["stdout"])
            self.assertNotIn("expected", output)
        self.assertIn('grep -n "PENDIENTE"', body)
        self.assertIn("__ACADEMY_ANSWER__", body)

    def test_missing_or_invalid_reference_value_never_approves(self):
        for stdout in ("sin marcador\n__ACADEMY_CHECK_OK__\n", "__ACADEMY_ANSWER__=\n__ACADEMY_CHECK_OK__\n"):
            output, _ = self.run_verify("22", stdout)
            self.assertFalse(output["passed"])
            self.assertFalse(output["answer_correct"])
        output, _ = self.run_verify("22", "__ACADEMY_ANSWER__=22\n", passed=False)
        self.assertFalse(output["answer_correct"])


if __name__ == "__main__":
    unittest.main()
