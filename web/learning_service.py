"""Content delivery, safe practice validators, and learner evaluation rules."""

import csv
import json
import re
import sqlite3
import time
import uuid
from collections import Counter
from decimal import Decimal, InvalidOperation
from pathlib import Path

import progress_store
import linux_runtime


WEB_DIR = Path(__file__).resolve().parent
CATALOG_PATH = WEB_DIR / "catalog" / "learning_catalog.json"
BASIC_CONTENT_PATH = WEB_DIR / "catalog" / "basic_courses.json"
INTERMEDIATE_CONTENT_PATH = WEB_DIR / "catalog" / "intermediate_courses.json"
ADVANCED_CONTENT_PATH = WEB_DIR / "catalog" / "advanced_courses.json"
LINUX_CONTENT_PATH = WEB_DIR / "catalog" / "linux_basic.json"
COURSE_DATA = WEB_DIR / "course_data"
MINIMUM_SCORE = 80
MAX_QUERY_LENGTH = 4000
MAX_TEXT_LENGTH = 2000


LEVEL_CONTENT_PATHS = {
    "basic": BASIC_CONTENT_PATH,
    "intermediate": INTERMEDIATE_CONTENT_PATH,
    "advanced": ADVANCED_CONTENT_PATH,
}


def _read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def catalog():
    return _read_json(CATALOG_PATH)


def content(level_id: str = "basic"):
    path = LEVEL_CONTENT_PATHS.get(level_id)
    if path is None:
        raise ValueError(f"Nivel desconocido: {level_id}. Niveles válidos: {list(LEVEL_CONTENT_PATHS.keys())}")
    data = _read_json(path)
    if level_id == "basic":
        linux_course = _read_json(LINUX_CONTENT_PATH)
        if any(course["id"] == "linux" for course in data["courses"]):
            raise ValueError("Linux debe definirse únicamente en linux_basic.json.")
        data["courses"].insert(0, linux_course)
    return data


def linux_environment_status():
    status = linux_runtime.status()
    return {
        key: status[key]
        for key in ("available", "reason", "distribution", "wsl_version", "kernel")
        if key in status
    }


def public_catalog():
    data = catalog()
    status = linux_runtime.status()
    availability = "available" if status.get("available") else "pending_environment"
    note = (
        f"Ubuntu {status.get('distribution')} está operativo en WSL 2; "
        "las prácticas ejecutan comandos permitidos en un espacio aislado."
        if status.get("available")
        else status.get("reason", "Requiere Ubuntu operativo y prácticas reales verificadas.")
    )
    for course in data["courses"]:
        if course["id"] == "linux":
            basic = course["contents_by_level"]["basic"]
            basic["availability"] = availability
            basic["availability_note"] = note
            basic["module_ids"] = [
                module["id"] for module in _find_course("linux")["modules"]
            ]
    for route in data["routes"]:
        if route["id"] != "cloud-production-support":
            continue
        basic_level = next(
            (level for level in route["levels"] if level["level_id"] == "basic"),
            None,
        )
        if basic_level and basic_level.get("capstone"):
            basic_level["capstone"]["availability"] = availability
            basic_level["capstone"]["objective"] = (
                "Investigar logs y datos sintéticos, ejecutar comandos Linux en Ubuntu, "
                "usar SQL y Python, interpretar conectividad y documentar el incidente."
                if status.get("available")
                else "Integrar análisis local y completar el criterio Linux cuando Ubuntu esté operativo."
            )
    return data


def _uuid(value):
    if not isinstance(value, str) or len(value) != 36:
        raise ValueError("Identificador de alumno inválido.")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("Identificador de alumno inválido.") from exc
    if str(parsed) != value.lower():
        raise ValueError("Identificador de alumno inválido.")
    return str(parsed)


def _find_course(course_id):
    if not isinstance(course_id, str):
        raise ValueError("Identificador de curso inválido.")
    course = next((item for item in content()["courses"] if item["id"] == course_id), None)
    if course is None:
        raise LookupError("El curso solicitado no está disponible.")
    return course


def _find_module(course, module_id):
    module = next((item for item in course["modules"] if item["id"] == module_id), None)
    if module is None:
        raise LookupError("El módulo solicitado no existe.")
    return module


def _basic_course_metadata(course_id):
    selected = next(
        (item for item in catalog()["courses"] if item["id"] == course_id),
        None,
    )
    if selected is None:
        raise LookupError("El curso solicitado no está disponible.")
    level = selected.get("contents_by_level", {}).get("basic")
    if not isinstance(level, dict):
        raise ValueError(f"El curso {course_id} no tiene configuración Básica.")
    return level


def _assert_basic_prerequisites(learner_id, course_id):
    level = _basic_course_metadata(course_id)
    if level.get("availability") == "blocked_prerequisites":
        raise progress_store.LearningAccessError("El curso está bloqueado por requisitos previos.")
    missing = progress_store.missing_competencies(
        learner_id,
        level.get("prerequisites", []),
    )
    if missing:
        raise progress_store.LearningAccessError(
            "Faltan competencias previas para iniciar este curso."
        )


def _assert_module_access(learner_id, course, module, activity_type):
    _assert_basic_prerequisites(learner_id, course["id"])
    if course["id"] == "linux":
        environment = linux_runtime.status()
        if not environment.get("available"):
            raise progress_store.LearningAccessError(
                environment.get("reason", "Ubuntu/WSL 2 no están disponibles.")
            )
    if not progress_store.course_is_enrolled(learner_id, course["id"]):
        raise progress_store.LearningAccessError("Inicia el curso antes de realizar esta actividad.")

    module_index = course["modules"].index(module)
    completed_modules = progress_store.completed_module_ids(learner_id, course["id"])
    if any(
        item["id"] not in completed_modules
        for item in course["modules"][:module_index]
    ):
        raise progress_store.LearningAccessError(
            "Completa los módulos anteriores antes de continuar."
        )

    if activity_type == "assessment":
        required_exercises = {
            module["guided_practice"]["id"],
            module["independent_practice"]["id"],
        }
        passed_exercises = progress_store.passed_exercise_ids(
            learner_id,
            course["id"],
            module["id"],
        )
        if not required_exercises.issubset(passed_exercises):
            raise progress_store.LearningAccessError(
                "Aprueba las prácticas guiada e independiente antes de rendir la evaluación."
            )


def _project_prerequisites():
    route = next(
        (item for item in catalog()["routes"] if item["id"] == "cloud-production-support"),
        None,
    )
    if route is None:
        raise ValueError("No se encontró la ruta Cloud / Production Support.")
    level = next(
        (item for item in route["levels"] if item["level_id"] == "basic"),
        None,
    )
    if level is None:
        raise ValueError("No se encontró la ruta Básica de Production Support.")
    return level["capstone"].get("prerequisites", [])


def _assert_project_access(learner_id, course):
    _assert_basic_prerequisites(learner_id, course["id"])
    if not progress_store.course_is_enrolled(learner_id, course["id"]):
        raise progress_store.LearningAccessError(
            "Inicia Production Support Básico antes de enviar el proyecto."
        )
    missing = progress_store.missing_competencies(
        learner_id,
        _project_prerequisites(),
    )
    if missing:
        raise progress_store.LearningAccessError(
            "Completa las competencias básicas requeridas antes de enviar el proyecto."
        )


def _public_content(value):
    hidden = {
        "correct_option",
        "feedback_by_option",
        "validator",
        "accepted_answer",
        "answer_field",
        "required_terms",
        "correct_feedback",
        "feedback_by_field",
        "incorrect_feedback",
        "processor",
        "review_topics",
    }
    if isinstance(value, dict):
        return {
            key: _public_content(item)
            for key, item in value.items()
            if key not in hidden
        }
    if isinstance(value, list):
        return [_public_content(item) for item in value]
    return value


def get_course(course_id):
    selected = _find_course(course_id)
    public_course = _public_content(selected)
    public_course["minimum_score_percent"] = MINIMUM_SCORE
    if course_id == "linux":
        environment = linux_environment_status()
        public_course["environment_status"] = environment
        public_course["environment_required"] = not environment["available"]
        public_course["availability"] = (
            "available" if environment["available"] else "pending_environment"
        )
    return public_course


def get_project():
    project = _public_content(content()["project"])
    environment = linux_runtime.status()
    project["availability"] = (
        "available" if environment.get("available") else "pending_environment"
    )
    project["linux_notice"] = (
        "Ubuntu/WSL 2 está verificado. El envío ejecuta grep sobre una copia aislada del log del proyecto; requiere la competencia Linux Básica."
        if environment.get("available")
        else environment.get(
            "reason",
            "Ubuntu/WSL 2 no está disponible; el criterio Linux no puede aprobarse.",
        )
    )
    project["environment_requirement"] = (
        f"Ubuntu en WSL 2 con usuario no root y herramientas del curso; "
        "el servidor ejecuta comandos predefinidos y acotados."
    )
    project["linux_environment_status"] = linux_environment_status()
    competency_titles = {
        item["id"]: item["title"]
        for item in catalog()["competencies"]
    }
    project["prerequisites"] = [
        {"id": competency_id, "title": competency_titles.get(competency_id, competency_id)}
        for competency_id in _project_prerequisites()
    ]
    return project


def start_course(learner_id, course_id):
    learner_id = _uuid(learner_id)
    selected = _find_course(course_id)
    _assert_basic_prerequisites(learner_id, course_id)
    progress_store.start_course(
        learner_id,
        course_id,
        pending_environment=(
            not linux_runtime.status().get("available")
            if course_id == "linux"
            else selected.get("environment_required", False)
        ),
    )
    return progress_store.get_progress(learner_id)


def get_progress(learner_id):
    return progress_store.get_progress(_uuid(learner_id))


def _safe_text(value, field, limit=MAX_TEXT_LENGTH):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"El campo {field} debe ser texto de hasta {limit} caracteres.")
    return value.strip()


def _option_result(exercise, answer):
    valid_ids = {option["id"] for option in exercise.get("options", [])}
    if not isinstance(answer, str) or answer not in valid_ids:
        return False, "Selecciona una de las opciones disponibles."
    correct = answer == exercise["correct_option"]
    feedback = exercise["feedback_by_option"].get(
        answer,
        "Respuesta incorrecta. Revisa los conceptos de este módulo antes de volver a intentarlo.",
    )
    return correct, feedback


def _validate_incident_report(exercise, answer):
    if not isinstance(answer, dict):
        return False, "Completa el informe estructurado con evidencia, impacto y siguiente paso.", {}

    field_specs = {
        field["id"]: field
        for field in exercise.get("fields", [])
        if field.get("type") != "textarea"
    }
    accepted = exercise["accepted_answer"]
    field_results = {}
    for field_id, field in field_specs.items():
        value = answer.get(field_id)
        allowed = {option["id"] for option in field.get("options", [])}
        field_results[field_id] = (
            isinstance(value, str)
            and value in allowed
            and value == accepted[field_id]
        )

    try:
        summary = _safe_text(answer.get("summary"), "resumen", 500)
        summary_ok = len(summary) >= 30 and all(
            term.casefold() in summary.casefold()
            for term in exercise.get("required_terms", [])
        )
    except ValueError:
        summary_ok = False
    field_results["summary"] = summary_ok
    correct = bool(field_results) and all(field_results.values())
    if correct:
        feedback = exercise.get(
            "correct_feedback",
            "Informe aceptado: cita señales observadas, limita el impacto y separa una hipótesis de una causa confirmada.",
        )
    else:
        field_feedback = exercise.get("feedback_by_field", {})
        issues = [
            field_feedback.get(field_id, f"Revisa el campo {field_id}.")
            for field_id, passed in field_results.items()
            if not passed
        ]
        feedback = exercise.get(
            "incorrect_feedback",
            "Revisa el informe: " + " ".join(issues),
        )
    return correct, feedback, {"criteria": field_results}


def _read_operations(path):
    rows = []
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"id_operacion", "cliente", "importe", "estado"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("El conjunto de práctica no contiene las columnas requeridas.")
        for line_number, row in enumerate(reader, start=2):
            if not row or not required.issubset(row) or row["estado"] not in {"OK", "ERROR", "PENDIENTE"}:
                raise ValueError(f"Fila {line_number} inválida en el conjunto local.")
            amount = Decimal(row["importe"])
            rows.append((row["id_operacion"], row["cliente"], float(amount), row["estado"]))
    return rows


def _execute_select(query, data_path, expected_validator):
    query = _safe_text(query, "consulta SQL", MAX_QUERY_LENGTH)
    if not query or not re.match(r"(?is)^select\b", query):
        raise ValueError("Solo se permite una consulta SELECT de solo lectura.")
    if ";" in query.rstrip().rstrip(";"):
        raise ValueError("Envía una sola sentencia SQL.")

    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(
            "CREATE TABLE operations (id_operacion TEXT, cliente TEXT, importe REAL, estado TEXT)"
        )
        connection.executemany(
            "INSERT INTO operations VALUES (?, ?, ?, ?)",
            _read_operations(data_path),
        )

        allowed_functions = {"avg", "count", "max", "min", "round", "sum"}

        def authorize(action, arg1, arg2, database_name, source):
            if action == sqlite3.SQLITE_SELECT:
                return sqlite3.SQLITE_OK
            if action == sqlite3.SQLITE_READ:
                return sqlite3.SQLITE_OK if arg1 == "operations" and database_name == "main" else sqlite3.SQLITE_DENY
            if action == sqlite3.SQLITE_FUNCTION:
                function_name = (arg2 or arg1 or "").lower()
                return sqlite3.SQLITE_OK if function_name in allowed_functions else sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_DENY

        connection.set_authorizer(authorize)
        deadline = time.monotonic() + 0.25
        connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
        cursor = connection.execute(query)
        columns = [column[0] for column in (cursor.description or [])]
        rows = [list(row) for row in cursor.fetchmany(101)]
        if len(rows) > 100:
            raise ValueError("La consulta supera el límite de 100 filas.")
        if not columns:
            raise ValueError("La consulta no devolvió columnas.")
        correct = _validate_sql_result(expected_validator, columns, rows)
        return {"columns": columns, "rows": rows, "row_count": len(rows)}, correct
    except sqlite3.Error as exc:
        raise ValueError(f"Consulta no permitida o inválida: {exc}") from exc
    finally:
        connection.close()


def _validate_sql_result(validator, columns, rows):
    expected = {
        "sql_errors": (
            ["id_operacion", "estado"],
            [["OP-4002", "ERROR"], ["OP-4004", "ERROR"]],
        ),
        "sql_state_counts": (
            ["estado", "cantidad"],
            [["ERROR", 2], ["OK", 2], ["PENDIENTE", 2]],
        ),
        "project_state_counts": (
            ["estado", "cantidad", "importe_total"],
            [["ERROR", 2, 425.0], ["OK", 2, 120.0], ["PENDIENTE", 1, 90.0]],
        ),
    }
    expected_columns, expected_rows = expected[validator]
    normalized_rows = [
        [round(value, 2) if isinstance(value, float) else value for value in row]
        for row in rows
    ]
    return columns == expected_columns and normalized_rows == expected_rows


def _python_processor(processor_id, data_path):
    rows = _read_operations(data_path)
    counts = Counter(row[3] for row in rows)
    if processor_id == "basic_status_counts":
        return {"counts": dict(sorted(counts.items())), "total_rows": len(rows)}
    if processor_id == "pending_amount_sum":
        total = sum((Decimal(str(row[2])) for row in rows if row[3] == "PENDIENTE"), Decimal("0"))
        return {"total": f"{total:.2f}", "matching_rows": counts["PENDIENTE"]}
    if processor_id == "capstone_summary":
        error_total = sum((Decimal(str(row[2])) for row in rows if row[3] == "ERROR"), Decimal("0"))
        return {
            "counts": dict(sorted(counts.items())),
            "error_amount_total": f"{error_total:.2f}",
            "total_rows": len(rows),
        }
    raise ValueError("Procesador de práctica no permitido.")


def _exercise(module, exercise_id):
    for key in ("guided_practice", "independent_practice"):
        exercise = module[key]
        if exercise["id"] == exercise_id:
            return exercise
    raise LookupError("El ejercicio solicitado no existe.")


def _module_metadata(course, module):
    exercises = [
        module["guided_practice"]["id"],
        module["independent_practice"]["id"],
    ]
    return {
        "required_exercise_ids": exercises,
        "assessment_id": module["assessment"]["id"],
        "module_ids": [item["id"] for item in course["modules"]],
        "environment_required": (
            not linux_runtime.status().get("available")
            if course["id"] == "linux"
            else course.get("environment_required", False)
        ),
        "competency_id": course["competency_id"],
    }


def _record_result(
    learner_id,
    course,
    module,
    activity_id,
    activity_type,
    score,
    passed,
    status,
    answers,
    result,
    exercise_id=None,
    evidence_kind=None,
    evidence_summary="",
):
    metadata = _module_metadata(course, module)
    saved = progress_store.record_attempt(
        learner_id=learner_id,
        course_id=course["id"],
        module_id=module["id"],
        activity_id=activity_id,
        activity_type=activity_type,
        score_percent=score,
        passed=passed,
        status=status,
        answers=answers,
        result=result,
        exercise_id=exercise_id,
        required_exercise_ids=metadata["required_exercise_ids"],
        assessment_id=metadata["assessment_id"],
        module_ids=metadata["module_ids"],
        environment_required=metadata["environment_required"],
        competency_id=metadata["competency_id"],
        evidence_kind=evidence_kind,
        evidence_summary=evidence_summary,
    )
    result["attempt_id"] = saved["attempt_id"]
    result["attempt_number"] = saved["attempt_number"]
    result["passed"] = bool(passed)
    result["score_percent"] = float(score)
    result["progress"] = progress_store.get_progress(learner_id)
    return result


def submit_exercise(payload):
    learner_id = _uuid(payload.get("learner_id"))
    course = _find_course(payload.get("course_id"))
    module = _find_module(course, payload.get("module_id"))
    _assert_module_access(learner_id, course, module, "exercise")
    exercise = _exercise(module, payload.get("exercise_id"))
    answer_payload = {}
    execution_result = None

    try:
        if exercise["type"] == "choice":
            answer = payload.get("answer")
            correct, feedback = _option_result(exercise, answer)
            answer_payload = {"answer": answer}
        elif exercise["type"] == "sql_query":
            query = _safe_text(payload.get("query"), "consulta SQL", MAX_QUERY_LENGTH)
            execution_result, correct = _execute_select(
                query,
                COURSE_DATA / "basic_operations.csv",
                exercise["validator"],
            )
            feedback = (
                "Correcto: la consulta devolvió las columnas y filas verificadas."
                if correct
                else "La consulta se ejecutó en el conjunto local, pero el resultado no cumple el criterio. Revisa filtros, columnas y orden."
            )
            answer_payload = {"query": query}
        elif exercise["type"] == "python_result":
            answer = _safe_text(payload.get("answer"), "respuesta", 100)
            execution_result = _python_processor(
                exercise["processor"],
                COURSE_DATA / "basic_operations.csv",
            )
            if exercise["answer_field"] == "ERROR":
                actual_value = str(execution_result["counts"].get("ERROR", 0))
            else:
                actual_value = str(execution_result[exercise["answer_field"]])
            try:
                correct = Decimal(answer) == Decimal(actual_value)
            except InvalidOperation:
                correct = False
            feedback = (
                f"Correcto: el procesador Python devolvió {actual_value}."
                if correct
                else f"El procesador Python devolvió {actual_value}; compara tu respuesta y revisa cómo se filtran las filas."
            )
            answer_payload = {"answer": answer}
        elif exercise["type"] == "incident_report":
            answer = payload.get("answer")
            correct, feedback, execution_result = _validate_incident_report(exercise, answer)
            answer_payload = {"answer": answer}
        elif exercise["type"] == "linux_command":
            if any(
                key in payload
                for key in ("command", "commands", "shell", "script", "cmd", "command_line")
            ):
                raise ValueError("No se aceptan comandos de consola desde el navegador.")
            execution_result = linux_runtime.run_exercise(learner_id, exercise["id"])
            correct = execution_result["passed"]
            feedback = (
                "Verificación aprobada: los comandos se ejecutaron realmente en Ubuntu."
                if correct
                else execution_result.get(
                    "feedback",
                    "La verificación real en Ubuntu falló; revisa la salida y vuelve a intentar.",
                )
            )
            answer_payload = {
                "exercise_id": exercise["id"],
                "commands": execution_result.get("commands", []),
            }
        else:
            raise ValueError("Tipo de ejercicio no permitido.")
    except ValueError as exc:
        correct = False
        feedback = str(exc)
        execution_result = {"error": feedback}
        if exercise["type"] == "sql_query":
            answer_payload = {"query": str(payload.get("query", ""))[:MAX_QUERY_LENGTH]}
        elif exercise["type"] == "linux_command":
            answer_payload = {"exercise_id": exercise["id"]}
        else:
            answer_payload = {"answer": str(payload.get("answer", ""))[:100]}

    result = {
        "exercise_id": exercise["id"],
        "feedback": feedback,
        "execution_result": execution_result,
        "review_recommendations": [] if correct else [module["title"]],
    }
    return _record_result(
        learner_id,
        course,
        module,
        exercise["id"],
        "exercise",
        100 if correct else 0,
        correct,
        "passed" if correct else "needs_review",
        answer_payload,
        result,
        exercise_id=exercise["id"],
        evidence_kind="exercise_result",
        evidence_summary=f"Ejercicio {exercise['id']}: {'aprobado' if correct else 'requiere repaso'}",
    )


def submit_assessment(payload):
    learner_id = _uuid(payload.get("learner_id"))
    course = _find_course(payload.get("course_id"))
    module = _find_module(course, payload.get("module_id"))
    _assert_module_access(learner_id, course, module, "assessment")
    assessment = module["assessment"]
    if payload.get("assessment_id") != assessment["id"]:
        raise LookupError("La evaluación solicitada no existe.")
    answers = payload.get("answers")
    if not isinstance(answers, dict) or len(answers) > 30:
        raise ValueError("Las respuestas de la evaluación no tienen un formato válido.")

    question_ids = {question["id"] for question in assessment["questions"]}
    if set(answers) - question_ids:
        raise ValueError("La evaluación incluye preguntas desconocidas.")
    question_results = []
    correct_count = 0
    review_topics = assessment["review_topics"]
    for question in assessment["questions"]:
        selected = answers.get(question["id"])
        valid_options = {option["id"] for option in question["options"]}
        correct = (
            isinstance(selected, str)
            and selected in valid_options
            and selected == question["correct_option"]
        )
        correct_count += int(correct)
        if not isinstance(selected, str) or selected not in valid_options:
            feedback = "Selecciona una respuesta válida para esta pregunta."
        else:
            feedback = question["feedback_by_option"].get(
                selected,
                "Respuesta incorrecta. Revisa el tema recomendado antes del siguiente intento.",
            )
        question_results.append({
            "question_id": question["id"],
            "correct": correct,
            "feedback": feedback,
            "review_topic": None if correct else review_topics[question["id"]],
        })

    score = round(correct_count * 100 / len(assessment["questions"]), 2)
    passed = score >= MINIMUM_SCORE
    result = {
        "assessment_id": assessment["id"],
        "type": assessment["type"],
        "correct_count": correct_count,
        "question_count": len(assessment["questions"]),
        "question_results": question_results,
        "review_recommendations": list(dict.fromkeys(
            item["review_topic"] for item in question_results if item["review_topic"]
        )),
        "minimum_score_percent": MINIMUM_SCORE,
        "competency_eligible": False,
    }
    metadata = _module_metadata(course, module)
    completed_modules = progress_store.completed_module_ids(learner_id, course["id"])
    result["competency_eligible"] = bool(
        passed
        and not (
            not linux_runtime.status().get("available")
            if course["id"] == "linux"
            else course.get("environment_required", False)
        )
        and set(metadata["module_ids"]).issubset(completed_modules | {module["id"]})
    )
    return _record_result(
        learner_id,
        course,
        module,
        assessment["id"],
        "assessment",
        score,
        passed,
        "approved" if passed else "needs_review",
        answers,
        result,
        evidence_kind="assessment_result",
        evidence_summary=f"Evaluación {assessment['id']}: {score:.0f}%",
    )


def submit_project(payload):
    learner_id = _uuid(payload.get("learner_id"))
    course = _find_course("production-support")
    _assert_project_access(learner_id, course)
    project = content()["project"]
    answers = payload.get("answers")
    if not isinstance(answers, dict) or len(answers) > 30:
        raise ValueError("Las respuestas del proyecto no tienen un formato válido.")

    event_path = COURSE_DATA / "basic_capstone_events.log"
    events = event_path.read_text(encoding="utf-8").splitlines()
    error_ids = sorted({
        re.search(r"id_operacion=(\S+)", line).group(1)
        for line in events
        if "level=ERROR" in line and re.search(r"id_operacion=(\S+)", line)
    })
    pending_ids = sorted({
        re.search(r"id_operacion=(\S+)", line).group(1)
        for line in events
        if "level=PENDIENTE" in line and re.search(r"id_operacion=(\S+)", line)
    })
    submitted_errors = answers.get("error_ids", [])
    submitted_pending = answers.get("pending_ids", [])
    if (
        not isinstance(submitted_errors, list)
        or not isinstance(submitted_pending, list)
        or len(submitted_errors) > 100
        or len(submitted_pending) > 100
        or any(
            not isinstance(item, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", item)
            for item in submitted_errors + submitted_pending
        )
    ):
        raise ValueError("Las selecciones de estados del proyecto no son válidas.")
    log_ok = sorted(set(submitted_errors)) == error_ids and sorted(set(submitted_pending)) == pending_ids

    query_result = None
    query_ok = False
    query_error = None
    query = answers.get("sql_query", "")
    try:
        query_result, query_ok = _execute_select(
            query,
            COURSE_DATA / "basic_capstone_operations.csv",
            "project_state_counts",
        )
    except ValueError as exc:
        query_error = str(exc)

    python_result = _python_processor(
        "capstone_summary",
        COURSE_DATA / "basic_capstone_operations.csv",
    )
    python_answer = answers.get("python_error_amount")
    try:
        python_ok = Decimal(_safe_text(python_answer, "importe ERROR", 20)) == Decimal(
            python_result["error_amount_total"]
        )
    except (InvalidOperation, ValueError):
        python_ok = False
    network_ok = answers.get("network_answer") == "dns"
    aws_ok = answers.get("aws_answer") == "cloudwatch"

    linux_runtime_status = linux_runtime.status()
    linux_analysis = linux_runtime.run_project_analysis(learner_id)
    linux_competency_awarded = not progress_store.missing_competencies(
        learner_id,
        ["linux-basic-operations"],
    )
    linux_ok = (
        linux_competency_awarded
        and linux_analysis.get("passed", False)
        and sorted(set(submitted_errors)) == linux_analysis.get("error_ids", [])
        and sorted(set(submitted_pending)) == linux_analysis.get("pending_ids", [])
    )
    if not linux_runtime_status.get("available"):
        linux_feedback = (
            "Bloqueado por entorno: "
            + linux_runtime_status.get("reason", "Ubuntu/WSL 2 no están disponibles.")
        )
    elif not linux_competency_awarded:
        linux_feedback = "Completa y aprueba el curso Linux con sus prácticas reales en Ubuntu antes de aprobar el proyecto."
    elif not linux_analysis.get("passed", False):
        linux_feedback = linux_analysis.get(
            "error",
            "No se pudo verificar el análisis del log del proyecto en Ubuntu.",
        )
    elif not linux_ok:
        linux_feedback = "Los identificadores informados no coinciden con la salida real de grep en Ubuntu."
    else:
        linux_feedback = "Ubuntu ejecutó grep sobre el log del proyecto y los identificadores coinciden con la evidencia."

    report = answers.get("report", {})
    if not isinstance(report, dict):
        raise ValueError("El informe del proyecto debe ser un objeto JSON.")
    primary_id = _safe_text(report.get("primary_id", ""), "ID principal", 40)
    cause_status = report.get("cause_status")
    next_step = report.get("next_step")
    impact_statement = report.get("impact_statement")
    summary = _safe_text(report.get("summary", ""), "resumen", 500)
    report_ok = (
        primary_id == "PX-510"
        and cause_status == "unknown"
        and next_step == "correlate-provider"
        and impact_statement == "observed-only"
        and len(summary) >= 30
        and any(identifier in summary for identifier in error_ids)
    )

    checks = [
        {"id": "logs", "passed": log_ok, "feedback": "IDs de error y pendiente cotejados con el log sintético." if log_ok else "Revisa las líneas level=ERROR y level=PENDIENTE del log."},
        {"id": "sql", "passed": query_ok, "feedback": "Consulta SELECT verificada." if query_ok else query_error or "El resumen SQL no coincide con los estados del fixture."},
        {"id": "python", "passed": python_ok, "feedback": f"El procesador Python calculó {python_result['error_amount_total']} como importe total ERROR." if python_ok else "Compara tu respuesta con el importe total ERROR que devuelve Python."},
        {"id": "network", "passed": network_ok, "feedback": "La pista indica una falla de resolución DNS." if network_ok else "No hubo IP ni respuesta HTTP; revisa la etapa anterior a HTTP."},
        {"id": "aws", "passed": aws_ok, "feedback": "CloudWatch es una referencia de observabilidad; no se consultó AWS." if aws_ok else "Selecciona la fuente conceptual de logs/métricas, sin operar la cuenta."},
        {"id": "report", "passed": report_ok, "feedback": "El informe distingue evidencia, alcance observado y causa no confirmada." if report_ok else "Revisa el ID, la incertidumbre de la causa, el alcance observado, el siguiente paso y el resumen con evidencia."},
        {"id": "linux", "passed": linux_ok, "feedback": linux_feedback},
    ]
    passed_count = sum(int(check["passed"]) for check in checks)
    score = round(passed_count * 100 / len(checks), 2)
    overall_status = (
        "approved"
        if all(check["passed"] for check in checks) and score >= MINIMUM_SCORE
        else "blocked_environment"
        if (
            all(check["passed"] for check in checks[:-1])
            and score >= MINIMUM_SCORE
            and (
                not linux_runtime_status.get("available")
                or not linux_analysis.get("passed", False)
            )
        )
        else "blocked_prerequisites"
        if all(check["passed"] for check in checks[:-1]) and score >= MINIMUM_SCORE
        else "in_progress"
    )
    result = {
        "project_id": project["id"],
        "status": overall_status,
        "criteria": checks,
        "score_percent": score,
        "passed": overall_status == "approved",
        "python_result": python_result,
        "sql_result": query_result,
        "sql_error": query_error,
        "log_event_count": len(events),
        "linux_runtime_available": linux_runtime_status.get("available", False),
        "linux_analysis": linux_analysis,
        "competency_awarded": False,
        "minimum_score_percent": MINIMUM_SCORE,
    }

    saved = progress_store.record_attempt(
        learner_id=learner_id,
        course_id=course["id"],
        module_id=project["id"],
        activity_id=project["id"],
        activity_type="project",
        score_percent=score,
        passed=overall_status == "approved",
        status=overall_status,
        answers=answers,
        result=result,
        evidence_kind="project_attempt",
        evidence_summary=f"Proyecto integrador: {overall_status}",
    )
    result["attempt_id"] = saved["attempt_id"]
    result["attempt_number"] = saved["attempt_number"]
    result["progress"] = progress_store.get_progress(learner_id)
    return result


def validate_catalog():
    source = catalog()
    learning = content()
    course_ids = {course["id"] for course in learning["courses"]}
    if course_ids != {course["id"] for course in source["courses"]}:
        raise ValueError("El catálogo y los contenidos de cursos no coinciden.")
    competency_ids = {item["id"] for item in source["competencies"]}
    course_assessment_ids = set()
    for course in learning["courses"]:
        if not course["modules"]:
            raise ValueError(f"El curso {course['id']} no tiene módulos.")
        course_metadata = next(
            (item for item in source["courses"] if item["id"] == course["id"]),
            None,
        )
        basic_level = course_metadata.get("contents_by_level", {}).get("basic", {})
        catalog_module_ids = basic_level.get("module_ids", [])
        content_module_ids = [module["id"] for module in course["modules"]]
        if catalog_module_ids != content_module_ids:
            raise ValueError(f"Los módulos Básicos de {course['id']} no coinciden entre catálogo y contenido.")
        if course["competency_id"] not in basic_level.get("competency_ids", []):
            raise ValueError(f"La competencia de {course['id']} no coincide con el catálogo.")
        if not set(basic_level.get("prerequisites", [])).issubset(competency_ids):
            raise ValueError(f"El curso {course['id']} contiene competencias previas desconocidas.")
        for module in course["modules"]:
            if len(module["assessment"]["questions"]) != 5:
                raise ValueError(f"La evaluación de {module['id']} debe tener cinco preguntas.")
            question_ids = {question["id"] for question in module["assessment"]["questions"]}
            if len(question_ids) != len(module["assessment"]["questions"]):
                raise ValueError(f"La evaluación de {module['id']} repite identificadores de pregunta.")
            course_assessment_ids.add(module["assessment"]["id"])
            if set(module["assessment"].get("review_topics", {})) != question_ids:
                raise ValueError(f"La evaluación de {module['id']} debe definir un tema de repaso por pregunta.")
            for question in module["assessment"]["questions"]:
                option_ids = [option["id"] for option in question["options"]]
                if (
                    len(option_ids) != len(set(option_ids))
                    or question["correct_option"] not in option_ids
                    or set(question["feedback_by_option"]) != set(option_ids)
                ):
                    raise ValueError(f"Las opciones y la corrección de {question['id']} son inconsistentes.")
            for key in ("guided_practice", "independent_practice"):
                exercise = module[key]
                if exercise["type"] == "choice":
                    option_ids = [option["id"] for option in exercise["options"]]
                    if (
                        len(option_ids) != len(set(option_ids))
                        or exercise["correct_option"] not in option_ids
                        or set(exercise["feedback_by_option"]) != set(option_ids)
                    ):
                        raise ValueError(f"Las opciones y la corrección de {exercise['id']} son inconsistentes.")
                elif exercise["type"] == "incident_report":
                    fields = {
                        field["id"]: field
                        for field in exercise.get("fields", [])
                        if field.get("type") != "textarea"
                    }
                    accepted = exercise.get("accepted_answer", {})
                    if set(accepted) != set(fields):
                        raise ValueError(f"El informe {exercise['id']} no define todos los campos verificables.")
                    if not exercise.get("required_terms"):
                        raise ValueError(f"El informe {exercise['id']} debe exigir evidencia textual.")
                    feedback_by_field = exercise.get("feedback_by_field")
                    if feedback_by_field is not None and set(feedback_by_field) != set(fields) | {"summary"}:
                        raise ValueError(f"El informe {exercise['id']} debe definir retroalimentación para cada campo.")
                    for field_id, field in fields.items():
                        if accepted[field_id] not in {option["id"] for option in field["options"]}:
                            raise ValueError(f"El informe {exercise['id']} tiene un criterio no disponible para {field_id}.")
                elif exercise["type"] == "linux_command":
                    if (
                        course["id"] != "linux"
                        or exercise["id"] not in linux_runtime.exercise_ids()
                        or not exercise.get("commands")
                        or any(not isinstance(command, str) or not command for command in exercise["commands"])
                    ):
                        raise ValueError(f"El ejercicio Linux {exercise['id']} no está permitido o no tiene comandos documentados.")
                elif exercise["type"] not in {"sql_query", "python_result"}:
                    raise ValueError(f"El ejercicio {exercise['id']} tiene un tipo no permitido.")
    catalog_assessment_ids = {
        item["id"] for item in source["evaluations"] if item.get("type") != "project"
    }
    if course_assessment_ids != catalog_assessment_ids:
        raise ValueError("Las evaluaciones del contenido y del catálogo no coinciden.")
    route = next(item for item in source["routes"] if item["id"] == "cloud-production-support")
    basic_route = next(item for item in route["levels"] if item["level_id"] == "basic")
    if not set(basic_route["capstone"].get("prerequisites", [])).issubset(competency_ids):
        raise ValueError("El proyecto integrador contiene competencias previas desconocidas.")
    if not 0 < MINIMUM_SCORE <= 100:
        raise ValueError("El puntaje mínimo configurado no es válido.")
