import json
import sys
import tempfile
import unittest
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock


WEB_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WEB_DIR))

import learning_service
import progress_store


class LearningServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_database = progress_store.DATABASE
        progress_store.DATABASE = Path(self.temp_dir.name) / "progress.sqlite3"
        progress_store.initialize()
        learning_service.validate_catalog()
        self.learner_id = str(uuid.uuid4())

    def tearDown(self):
        progress_store.DATABASE = self.original_database
        self.temp_dir.cleanup()

    def course_module(self, course_id):
        course = next(
            item for item in learning_service.content()["courses"]
            if item["id"] == course_id
        )
        return course, course["modules"][0]

    @staticmethod
    def assessment_answers(module, incorrect_questions=()):
        answers = {
            question["id"]: question["correct_option"]
            for question in module["assessment"]["questions"]
        }
        for question_id in incorrect_questions:
            answers[question_id] = "__incorrect__"
        return answers

    def submit_correct_exercise(self, learner_id, course, module, exercise):
        payload = {
            "learner_id": learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "exercise_id": exercise["id"],
        }
        if exercise["type"] == "choice":
            payload["answer"] = exercise["correct_option"]
        elif exercise["type"] == "sql_query":
            payload["query"] = exercise["example_query"]
        elif exercise["type"] == "python_result":
            output = learning_service._python_processor(
                exercise["processor"],
                learning_service.COURSE_DATA / "basic_operations.csv",
            )
            field = exercise["answer_field"]
            payload["answer"] = str(
                output["counts"][field] if field == "ERROR" else output[field]
            )
        elif exercise["type"] == "linux_command" and exercise.get("question"):
            # El valor real lo decide la salida de Ubuntu; aquí verify_answer está simulado.
            payload["answer"] = "7"
        elif exercise["type"] == "incident_report":
            payload["answer"] = {
                **exercise["accepted_answer"],
                "summary": "Evidencia observada: "
                + " y ".join(exercise["required_terms"])
                + "; causa no confirmada, solicitar revisión autorizada.",
            }
        result = learning_service.submit_exercise(payload)
        self.assertTrue(result["passed"], result["feedback"])
        return result

    @staticmethod
    def verified_answer(_learner_id, exercise_id, _answer):
        return {
            "passed": True,
            "answer_correct": True,
            "exercise_id": exercise_id,
            "commands": ["allowlisted reference"],
            "stdout": f"{exercise_id} reference-output\n",
            "stderr": "",
            "runtime": "test-kernel",
        }

    def complete_course(self, learner_id, course_id):
        course = next(
            item for item in learning_service.content()["courses"]
            if item["id"] == course_id
        )
        learning_service.start_course(learner_id, course_id)
        for module in course["modules"]:
            for key in ("guided_practice", "independent_practice"):
                self.submit_correct_exercise(learner_id, course, module, module[key])
            result = learning_service.submit_assessment({
                "learner_id": learner_id,
                "course_id": course_id,
                "module_id": module["id"],
                "assessment_id": module["assessment"]["id"],
                "answers": self.assessment_answers(module),
            })
            self.assertTrue(result["passed"])
        return progress_store.get_progress(learner_id)

    def complete_project_prerequisites(self):
        for course_id in ("networking", "sql", "aws", "python", "production-support"):
            self.complete_course(self.learner_id, course_id)

    def wrong_exercise_payload(self, learner_id, course, module, exercise):
        payload = {
            "learner_id": learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "exercise_id": exercise["id"],
        }
        if exercise["type"] == "choice":
            payload["answer"] = next(
                option["id"]
                for option in exercise["options"]
                if option["id"] != exercise["correct_option"]
            )
        elif exercise["type"] == "sql_query":
            payload["query"] = (
                "SELECT id_operacion FROM operations "
                "WHERE estado = 'OK' ORDER BY id_operacion"
            )
        elif exercise["type"] == "python_result":
            payload["answer"] = "0"
        elif exercise["type"] == "incident_report":
            answer = dict(exercise["accepted_answer"])
            field = next(iter(answer))
            field_spec = next(item for item in exercise["fields"] if item["id"] == field)
            answer[field] = next(
                option["id"]
                for option in field_spec["options"]
                if option["id"] != answer[field]
            )
            answer["summary"] = "Evidencia observada: " + " y ".join(exercise["required_terms"])
            payload["answer"] = answer
        return payload

    @staticmethod
    def valid_project_answers():
        return {
            "error_ids": ["PX-510", "PX-513"],
            "pending_ids": ["PX-511"],
            "sql_query": (
                "SELECT estado, COUNT(*) AS cantidad, ROUND(SUM(importe), 2) "
                "AS importe_total FROM operations GROUP BY estado ORDER BY estado;"
            ),
            "python_error_amount": "425.00",
            "network_answer": "dns",
            "aws_answer": "cloudwatch",
            "report": {
                "primary_id": "PX-510",
                "cause_status": "unknown",
                "next_step": "correlate-provider",
                "impact_statement": "observed-only",
                "summary": (
                    "Se observan errores asociados a PX-510; falta "
                    "correlacionar el proveedor."
                ),
            },
        }

    def test_sql_retries_and_practices_gate_competency_award(self):
        course, module = self.course_module("sql")
        learning_service.start_course(self.learner_id, course["id"])
        questions = module["assessment"]["questions"]

        assessment_payload = {
            "learner_id": self.learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "assessment_id": module["assessment"]["id"],
            "answers": self.assessment_answers(module),
        }
        with self.assertRaises(progress_store.LearningAccessError):
            learning_service.submit_assessment(assessment_payload)

        for key in ("guided_practice", "independent_practice"):
            exercise = module[key]
            self.submit_correct_exercise(self.learner_id, course, module, exercise)

        failed = learning_service.submit_assessment({
            **assessment_payload,
            "answers": self.assessment_answers(
                module, [questions[0]["id"], questions[1]["id"]]
            ),
        })
        self.assertEqual(failed["score_percent"], 60)
        self.assertFalse(failed["passed"])
        self.assertTrue(failed["review_recommendations"])
        self.assertEqual(
            failed["review_recommendations"],
            [module["assessment"]["review_topics"][question["id"]] for question in questions[:2]],
        )

        passed_with_practice = learning_service.submit_assessment({
            **assessment_payload,
            "answers": self.assessment_answers(module, [questions[-1]["id"]]),
        })
        self.assertEqual(passed_with_practice["score_percent"], 80)
        self.assertTrue(passed_with_practice["passed"])
        self.assertTrue(passed_with_practice["competency_eligible"])

        completed = learning_service.submit_assessment({
            **assessment_payload,
            "answers": self.assessment_answers(module),
        })
        self.assertTrue(completed["competency_eligible"])
        self.assertEqual(len(completed["progress"]["attempts"]), 5)
        self.assertEqual(
            completed["progress"]["competencies"][0]["competency_id"],
            course["competency_id"],
        )

    def test_answer_keys_are_hidden_and_sql_rejects_non_select(self):
        public_course = learning_service.get_course("sql")
        self.assertEqual(public_course["minimum_score_percent"], 80)
        serialized = str(public_course)
        for key in ("correct_option", "feedback_by_option", "validator", "accepted_answer", "review_topics"):
            self.assertNotIn(key, serialized)
        aws_course = learning_service.get_course("aws")
        self.assertEqual(len(aws_course["modules"]), 6)
        aws_serialized = str(aws_course)
        for key in ("correct_option", "feedback_by_option", "validator", "accepted_answer", "required_terms", "review_topics"):
            self.assertNotIn(key, aws_serialized)
        self.assertEqual(
            len(aws_course["modules"][-1]["assessment"]["questions"]),
            5,
        )

        course, module = self.course_module("sql")
        learning_service.start_course(self.learner_id, course["id"])
        result = learning_service.submit_exercise({
            "learner_id": self.learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "exercise_id": module["guided_practice"]["id"],
            "query": "DROP TABLE operations",
        })
        self.assertFalse(result["passed"])
        self.assertIn("SELECT", result["feedback"])

    def test_public_catalog_reflects_linux_runtime_and_all_basic_modules(self):
        unavailable = {
            "available": False,
            "reason": "Ubuntu no está inicializado.",
        }
        with mock.patch.object(learning_service.linux_runtime, "status", return_value=unavailable):
            pending_catalog = learning_service.public_catalog()
        linux = next(item for item in pending_catalog["courses"] if item["id"] == "linux")
        self.assertEqual(linux["contents_by_level"]["basic"]["availability"], "pending_environment")
        self.assertEqual(
            linux["contents_by_level"]["basic"]["module_ids"],
            [module["id"] for module in self.course_module("linux")[0]["modules"]],
        )
        self.assertIn("Ubuntu", linux["contents_by_level"]["basic"]["availability_note"])
        basic_route = next(
            level for level in pending_catalog["routes"][0]["levels"]
            if level["level_id"] == "basic"
        )
        self.assertEqual(basic_route["capstone"]["availability"], "pending_environment")

        available = {
            "available": True,
            "distribution": "Ubuntu",
            "wsl_version": 2,
            "kernel": "test-kernel",
            "home": "/home/test",
        }
        with mock.patch.object(learning_service.linux_runtime, "status", return_value=available):
            ready_catalog = learning_service.public_catalog()
        ready_linux = next(item for item in ready_catalog["courses"] if item["id"] == "linux")
        self.assertEqual(ready_linux["contents_by_level"]["basic"]["availability"], "available")
        self.assertEqual(
            next(level for level in ready_catalog["routes"][0]["levels"] if level["level_id"] == "basic")["capstone"]["availability"],
            "available",
        )

    def test_available_basic_courses_support_a_complete_learning_flow(self):
        course_ids = ("sql", "aws", "production-support", "networking", "python")
        for course_id in course_ids:
            progress = self.complete_course(self.learner_id, course_id)
            course = next(
                item for item in progress["courses"]
                if item["course_id"] == course_id
            )
            self.assertEqual(course["status"], "approved", course_id)
            course_content = next(
                item for item in learning_service.content()["courses"]
                if item["id"] == course_id
            )
            completed_modules = {
                item["module_id"] for item in progress["modules"]
                if item["course_id"] == course_id and item["status"] == "completed"
            }
            self.assertEqual(
                completed_modules,
                {module["id"] for module in course_content["modules"]},
                course_id,
            )
        self.assertEqual(
            {item["competency_id"] for item in progress_store.get_progress(self.learner_id)["competencies"]},
            {
                "sql-basic-queries",
                "aws-basic-concepts",
                "support-basic-triage",
                "networking-basic-concepts",
                "python-basic-programming",
            },
        )

    def test_wrong_practice_feedback_and_retries_are_recorded_for_each_available_course(self):
        for course_id in ("sql", "aws", "networking", "python", "production-support"):
            course, module = self.course_module(course_id)
            exercise = module["independent_practice"]
            if exercise["type"] != "incident_report":
                exercise = module["guided_practice"]
            learning_service.start_course(self.learner_id, course_id)

            failed = learning_service.submit_exercise(
                self.wrong_exercise_payload(self.learner_id, course, module, exercise)
            )
            self.assertFalse(failed["passed"], course_id)
            self.assertTrue(failed["feedback"], course_id)
            self.assertTrue(failed["review_recommendations"], course_id)
            self.assertEqual(failed["attempt_number"], 1, course_id)

            passed = self.submit_correct_exercise(
                self.learner_id,
                course,
                module,
                exercise,
            )
            self.assertEqual(passed["attempt_number"], 2, course_id)
            self.assertEqual(
                len([
                    attempt for attempt in passed["progress"]["attempts"]
                    if attempt["course_id"] == course_id
                    and attempt["activity_id"] == exercise["id"]
                ]),
                2,
                course_id,
            )

    def test_assessment_feedback_and_retry_history_cover_each_available_course(self):
        for course_id in ("sql", "aws", "networking", "python", "production-support"):
            course, module = self.course_module(course_id)
            learning_service.start_course(self.learner_id, course_id)
            for key in ("guided_practice", "independent_practice"):
                self.submit_correct_exercise(
                    self.learner_id,
                    course,
                    module,
                    module[key],
                )

            answers = self.assessment_answers(module)
            for question in module["assessment"]["questions"][:2]:
                answers[question["id"]] = next(
                    option["id"]
                    for option in question["options"]
                    if option["id"] != question["correct_option"]
                )
            payload = {
                "learner_id": self.learner_id,
                "course_id": course_id,
                "module_id": module["id"],
                "assessment_id": module["assessment"]["id"],
            }
            failed = learning_service.submit_assessment({
                **payload,
                "answers": answers,
            })
            self.assertEqual(failed["score_percent"], 60, course_id)
            self.assertFalse(failed["passed"], course_id)
            self.assertEqual(len(failed["review_recommendations"]), 2, course_id)
            self.assertTrue(
                all(item["feedback"] for item in failed["question_results"]),
                course_id,
            )

            passed = learning_service.submit_assessment({
                **payload,
                "answers": self.assessment_answers(module),
            })
            self.assertTrue(passed["passed"], course_id)
            self.assertEqual(passed["attempt_number"], 2, course_id)

    def test_assessment_and_module_order_require_verified_practice(self):
        course = next(
            item for item in learning_service.content()["courses"]
            if item["id"] == "aws"
        )
        first_module, second_module = course["modules"][:2]
        assessment_payload = {
            "learner_id": self.learner_id,
            "course_id": "aws",
            "module_id": first_module["id"],
            "assessment_id": first_module["assessment"]["id"],
            "answers": self.assessment_answers(first_module),
            "score_percent": 100,
            "passed": True,
            "competency_eligible": True,
        }
        with self.assertRaises(progress_store.LearningAccessError):
            learning_service.submit_assessment(assessment_payload)

        learning_service.start_course(self.learner_id, "aws")
        with self.assertRaises(progress_store.LearningAccessError):
            self.submit_correct_exercise(
                self.learner_id,
                course,
                second_module,
                second_module["guided_practice"],
            )
        with self.assertRaises(progress_store.LearningAccessError):
            learning_service.submit_assessment(assessment_payload)
        self.assertFalse(progress_store.get_progress(self.learner_id)["attempts"])

    def test_assessment_score_is_server_computed_and_unknown_questions_are_rejected(self):
        course, module = self.course_module("sql")
        learning_service.start_course(self.learner_id, course["id"])
        for key in ("guided_practice", "independent_practice"):
            self.submit_correct_exercise(self.learner_id, course, module, module[key])

        payload = {
            "learner_id": self.learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "assessment_id": module["assessment"]["id"],
            "answers": self.assessment_answers(module),
        }
        with self.assertRaises(ValueError):
            learning_service.submit_assessment({
                **payload,
                "answers": {**payload["answers"], "forged-question": "correct"},
            })

        result = learning_service.submit_assessment({
            **payload,
            "score_percent": 0,
            "passed": False,
            "competency_eligible": False,
        })
        self.assertEqual(result["score_percent"], 100)
        self.assertTrue(result["passed"])
        self.assertTrue(result["competency_eligible"])

    def test_concurrent_retries_keep_unique_attempt_numbers(self):
        course, module = self.course_module("production-support")
        learning_service.start_course(self.learner_id, course["id"])
        exercise = module["guided_practice"]

        def submit():
            return learning_service.submit_exercise({
                "learner_id": self.learner_id,
                "course_id": course["id"],
                "module_id": module["id"],
                "exercise_id": exercise["id"],
                "answer": exercise["correct_option"],
            })["attempt_number"]

        with ThreadPoolExecutor(max_workers=8) as executor:
            numbers = list(executor.map(lambda _: submit(), range(8)))
        self.assertEqual(sorted(numbers), list(range(1, 9)))

    def test_python_processor_uses_the_local_fixture(self):
        course, module = self.course_module("python")
        learning_service.start_course(self.learner_id, course["id"])
        exercise = module["guided_practice"]
        result = learning_service.submit_exercise({
            "learner_id": self.learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "exercise_id": exercise["id"],
            "answer": "2",
        })
        self.assertTrue(result["passed"])
        self.assertEqual(result["execution_result"]["counts"]["ERROR"], 2)

    def test_linux_activities_are_blocked_until_ubuntu_is_verified(self):
        course, module = self.course_module("linux")
        unavailable = {
            "available": False,
            "reason": "Ubuntu no está inicializado.",
        }
        with mock.patch.object(learning_service.linux_runtime, "status", return_value=unavailable):
            learning_service.start_course(self.learner_id, course["id"])
            progress = progress_store.get_progress(self.learner_id)
            self.assertEqual(progress["courses"][0]["blocked_reason"], "Ubuntu operativo pendiente.")
            with self.assertRaises(progress_store.LearningAccessError):
                learning_service.submit_exercise({
                    "learner_id": self.learner_id,
                    "course_id": course["id"],
                    "module_id": module["id"],
                    "exercise_id": module["guided_practice"]["id"],
                })
            with self.assertRaises(progress_store.LearningAccessError):
                learning_service.submit_assessment({
                    "learner_id": self.learner_id,
                    "course_id": course["id"],
                    "module_id": module["id"],
                    "assessment_id": module["assessment"]["id"],
                    "answers": self.assessment_answers(module),
                })
        self.assertFalse(progress_store.get_progress(self.learner_id)["attempts"])
        self.assertFalse(progress_store.get_progress(self.learner_id)["competencies"])

    def test_linux_command_api_rejects_browser_supplied_shell_text(self):
        course, module = self.course_module("linux")
        available = {
            "available": True,
            "distribution": "Ubuntu",
            "wsl_version": 2,
            "kernel": "test-kernel",
            "home": "/home/test",
        }
        with (
            mock.patch.object(learning_service.linux_runtime, "status", return_value=available),
            mock.patch.object(learning_service.linux_runtime, "run_exercise") as run_exercise,
        ):
            learning_service.start_course(self.learner_id, course["id"])
            result = learning_service.submit_exercise({
                "learner_id": self.learner_id,
                "course_id": course["id"],
                "module_id": module["id"],
                "exercise_id": module["guided_practice"]["id"],
                "command": "echo browser-command",
            })
        self.assertFalse(result["passed"])
        self.assertIn("No se aceptan comandos", result["feedback"])
        run_exercise.assert_not_called()

    def test_linux_requires_all_real_command_practices_before_competency(self):
        course = next(
            item for item in learning_service.content()["courses"]
            if item["id"] == "linux"
        )
        available = {
            "available": True,
            "distribution": "Ubuntu",
            "wsl_version": 2,
            "kernel": "test-kernel",
            "home": "/home/test",
        }

        def verified_run(_learner_id, exercise_id):
            return {
                "passed": True,
                "exercise_id": exercise_id,
                "commands": ["allowlisted practice"],
                "stdout": f"{exercise_id} real-output\n",
                "stderr": "",
                "runtime": "test-kernel",
            }

        with (
            mock.patch.object(learning_service.linux_runtime, "status", return_value=available),
            mock.patch.object(
                learning_service.linux_runtime,
                "run_exercise",
                side_effect=verified_run,
            ) as run_exercise,
            mock.patch.object(
                learning_service.linux_runtime,
                "verify_answer",
                side_effect=self.verified_answer,
            ) as verify_answer,
        ):
            progress = self.complete_course(self.learner_id, "linux")

        course_progress = next(item for item in progress["courses"] if item["course_id"] == "linux")
        self.assertEqual(course_progress["status"], "approved")
        self.assertIsNone(course_progress["blocked_reason"])
        self.assertEqual(
            len([item for item in progress["modules"] if item["course_id"] == "linux" and item["status"] == "completed"]),
            7,
        )
        self.assertIn(
            "linux-basic-operations",
            {item["competency_id"] for item in progress["competencies"]},
        )
        self.assertEqual(
            len([item for item in progress["attempts"] if item["course_id"] == "linux" and item["activity_type"] == "exercise"]),
            14,
        )
        # Las 14 prácticas se aprueban respondiendo la pregunta; ninguna solo con ejecutar.
        self.assertEqual(verify_answer.call_count, 14)
        run_exercise.assert_not_called()


    def test_project_keeps_six_verified_criteria_blocked_by_linux(self):
        self.complete_project_prerequisites()
        unavailable = {
            "available": False,
            "reason": "Ubuntu no está inicializado.",
        }
        with (
            mock.patch.object(learning_service.linux_runtime, "status", return_value=unavailable),
            mock.patch.object(
                learning_service.linux_runtime,
                "run_project_analysis",
                return_value={
                    "passed": False,
                    "error": unavailable["reason"],
                    "error_ids": [],
                    "pending_ids": [],
                    "stdout": "",
                    "stderr": "",
                },
            ),
        ):
            result = learning_service.submit_project({
                "learner_id": self.learner_id,
                "answers": self.valid_project_answers(),
            })
        self.assertEqual(result["score_percent"], 85.71)
        self.assertEqual(result["status"], "blocked_environment")
        self.assertFalse(result["competency_awarded"])
        self.assertEqual(sum(item["passed"] for item in result["criteria"]), 6)
        self.assertTrue(next(item for item in result["criteria"] if item["id"] == "sql")["passed"])
        self.assertTrue(next(item for item in result["criteria"] if item["id"] == "python")["passed"])

    def test_project_requires_linux_course_and_project_log_execution_before_approval(self):
        self.complete_project_prerequisites()
        available = {
            "available": True,
            "distribution": "Ubuntu",
            "wsl_version": 2,
            "kernel": "test-kernel",
            "home": "/home/test",
        }
        project_analysis = {
            "passed": True,
            "error_ids": ["PX-510", "PX-513"],
            "pending_ids": ["PX-511"],
            "stdout": "grep verified PX-510 PX-513 PX-511\n",
            "stderr": "",
            "runtime": "test-kernel",
            "commands": ["grep level=ERROR", "grep level=PENDIENTE"],
        }

        with (
            mock.patch.object(learning_service.linux_runtime, "status", return_value=available),
            mock.patch.object(
                learning_service.linux_runtime,
                "run_project_analysis",
                return_value=project_analysis,
            ),
        ):
            missing_linux = learning_service.submit_project({
                "learner_id": self.learner_id,
                "answers": self.valid_project_answers(),
            })
        self.assertEqual(missing_linux["status"], "blocked_prerequisites")
        self.assertFalse(next(item for item in missing_linux["criteria"] if item["id"] == "linux")["passed"])

        def verified_run(_learner_id, exercise_id):
            return {
                "passed": True,
                "exercise_id": exercise_id,
                "commands": ["allowlisted practice"],
                "stdout": f"{exercise_id} output\n",
                "stderr": "",
                "runtime": "test-kernel",
            }

        course = next(
            item for item in learning_service.content()["courses"]
            if item["id"] == "linux"
        )
        with (
            mock.patch.object(learning_service.linux_runtime, "status", return_value=available),
            mock.patch.object(
                learning_service.linux_runtime,
                "run_exercise",
                side_effect=verified_run,
            ) as run_exercise,
            mock.patch.object(
                learning_service.linux_runtime,
                "verify_answer",
                side_effect=self.verified_answer,
            ) as verify_answer,
        ):
            self.complete_course(self.learner_id, course["id"])

        with (
            mock.patch.object(learning_service.linux_runtime, "status", return_value=available),
            mock.patch.object(
                learning_service.linux_runtime,
                "run_project_analysis",
                return_value=project_analysis,
            ),
        ):
            approved = learning_service.submit_project({
                "learner_id": self.learner_id,
                "answers": self.valid_project_answers(),
            })
        self.assertEqual(approved["status"], "approved")
        self.assertEqual(approved["score_percent"], 100)
        self.assertTrue(approved["passed"])
        self.assertTrue(next(item for item in approved["criteria"] if item["id"] == "linux")["passed"])
        self.assertEqual(approved["linux_analysis"]["commands"], project_analysis["commands"])

    def test_project_rejects_basic_example_answers_as_final_solution(self):
        self.complete_project_prerequisites()
        result = learning_service.submit_project({
            "learner_id": self.learner_id,
            "answers": {
                "error_ids": ["PX-510", "PX-513"],
                "pending_ids": ["PX-511"],
                "sql_query": (
                    "SELECT estado, COUNT(*) AS cantidad FROM operations "
                    "GROUP BY estado ORDER BY estado;"
                ),
                "python_error_amount": "2",
                "network_answer": "dns",
                "aws_answer": "cloudwatch",
                "report": {
                    "primary_id": "PX-510",
                    "cause_status": "unknown",
                    "next_step": "correlate-provider",
                    "impact_statement": "observed-only",
                    "summary": "Se observan errores asociados a PX-510; falta correlacionar el proveedor.",
                },
            },
        })
        criteria = {item["id"]: item for item in result["criteria"]}
        self.assertFalse(criteria["sql"]["passed"])
        self.assertFalse(criteria["python"]["passed"])

    def test_project_requires_course_enrollment_and_prerequisite_competencies(self):
        with self.assertRaises(progress_store.LearningAccessError):
            learning_service.submit_project({"learner_id": self.learner_id, "answers": {}})

        learning_service.start_course(self.learner_id, "production-support")
        with self.assertRaises(progress_store.LearningAccessError):
            learning_service.submit_project({"learner_id": self.learner_id, "answers": {}})

        progress = progress_store.get_progress(self.learner_id)
        self.assertFalse(progress["attempts"])

    def test_public_sql_course_does_not_expose_example_queries(self):
        raw_course, _ = self.course_module("sql")
        public_course = learning_service.get_course("sql")
        serialized = json.dumps(public_course, ensure_ascii=False)
        self.assertNotIn("example_query", serialized)
        for module in raw_course["modules"]:
            for key in ("guided_practice", "independent_practice"):
                query = module[key].get("example_query")
                if query:
                    self.assertNotIn(query, serialized)

    def test_wrong_python_answer_does_not_reveal_the_expected_value(self):
        course, module = self.course_module("python")
        learning_service.start_course(self.learner_id, course["id"])
        exercise = module["guided_practice"]
        expected = str(learning_service._python_processor(
            exercise["processor"],
            learning_service.COURSE_DATA / "basic_operations.csv",
        )["counts"]["ERROR"])
        result = learning_service.submit_exercise({
            "learner_id": self.learner_id,
            "course_id": course["id"],
            "module_id": module["id"],
            "exercise_id": exercise["id"],
            "answer": "999",
        })
        self.assertFalse(result["passed"])
        self.assertIsNone(result["execution_result"])
        self.assertNotIn(expected, result["feedback"])
        progress = json.dumps(progress_store.get_progress(self.learner_id), ensure_ascii=False)
        self.assertNotIn("counts", progress)


if __name__ == "__main__":
    unittest.main()
