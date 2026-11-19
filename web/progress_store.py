"""Local SQLite persistence for profiles bound to server-issued browser sessions."""

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path


DATABASE = Path(__file__).resolve().parent / "data" / "learning_progress.sqlite3"
_lock = threading.RLock()


class LearningAccessError(PermissionError):
    """Raised when a learner has not met the server-side access requirements."""


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="microseconds")


def _connect():
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(DATABASE), timeout=5)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


@contextmanager
def _transaction():
    connection = _connect()
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize():
    with _lock, _transaction() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS learner_profile (
                learner_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS learner_session (
                session_hash TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS learner_session_by_learner
                ON learner_session(learner_id);
            CREATE TABLE IF NOT EXISTS course_progress (
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                course_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('in_progress', 'approved')),
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                blocked_reason TEXT,
                PRIMARY KEY (learner_id, course_id)
            );
            CREATE TABLE IF NOT EXISTS module_progress (
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                course_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('in_progress', 'completed', 'pending_environment')),
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                PRIMARY KEY (learner_id, course_id, module_id)
            );
            CREATE TABLE IF NOT EXISTS exercise_progress (
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                course_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                exercise_id TEXT NOT NULL,
                passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
                updated_at TEXT NOT NULL,
                PRIMARY KEY (learner_id, course_id, module_id, exercise_id)
            );
            CREATE TABLE IF NOT EXISTS learning_attempt (
                attempt_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                course_id TEXT NOT NULL,
                module_id TEXT NOT NULL,
                activity_id TEXT NOT NULL,
                activity_type TEXT NOT NULL,
                attempt_number INTEGER NOT NULL,
                score_percent REAL NOT NULL,
                passed INTEGER NOT NULL CHECK(passed IN (0, 1)),
                status TEXT NOT NULL,
                answers_json TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS learning_attempt_history
                ON learning_attempt(learner_id, created_at DESC);
            CREATE UNIQUE INDEX IF NOT EXISTS learning_attempt_sequence
                ON learning_attempt(
                    learner_id, course_id, module_id, activity_id, activity_type, attempt_number
                );
            CREATE TABLE IF NOT EXISTS competency_award (
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                competency_id TEXT NOT NULL,
                course_id TEXT NOT NULL,
                awarded_at TEXT NOT NULL,
                attempt_id TEXT NOT NULL REFERENCES learning_attempt(attempt_id),
                PRIMARY KEY (learner_id, competency_id)
            );
            CREATE TABLE IF NOT EXISTS evidence (
                evidence_id TEXT PRIMARY KEY,
                learner_id TEXT NOT NULL REFERENCES learner_profile(learner_id),
                course_id TEXT NOT NULL,
                attempt_id TEXT NOT NULL REFERENCES learning_attempt(attempt_id),
                kind TEXT NOT NULL,
                summary TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )


def _ensure_learner(connection, learner_id):
    connection.execute(
        "INSERT OR IGNORE INTO learner_profile(learner_id, created_at) VALUES (?, ?)",
        (learner_id, _now()),
    )


def create_learner_session(session_hash):
    learner_id = str(uuid.uuid4())
    now = _now()
    with _lock, _transaction() as connection:
        _ensure_learner(connection, learner_id)
        connection.execute(
            """
            INSERT INTO learner_session(session_hash, learner_id, created_at, last_seen_at)
            VALUES (?, ?, ?, ?)
            """,
            (session_hash, learner_id, now, now),
        )
    return learner_id


def learner_for_session(session_hash):
    with _lock, _transaction() as connection:
        row = connection.execute(
            "SELECT learner_id FROM learner_session WHERE session_hash = ?",
            (session_hash,),
        ).fetchone()
        if row is None:
            return None
        connection.execute(
            "UPDATE learner_session SET last_seen_at = ? WHERE session_hash = ?",
            (_now(), session_hash),
        )
        return row["learner_id"]


def course_is_enrolled(learner_id, course_id):
    with _lock, _transaction() as connection:
        return connection.execute(
            "SELECT 1 FROM course_progress WHERE learner_id = ? AND course_id = ?",
            (learner_id, course_id),
        ).fetchone() is not None


def completed_module_ids(learner_id, course_id):
    with _lock, _transaction() as connection:
        rows = connection.execute(
            """
            SELECT module_id FROM module_progress
            WHERE learner_id = ? AND course_id = ? AND status = 'completed'
            """,
            (learner_id, course_id),
        ).fetchall()
    return {row["module_id"] for row in rows}


def passed_exercise_ids(learner_id, course_id, module_id):
    with _lock, _transaction() as connection:
        rows = connection.execute(
            """
            SELECT exercise_id FROM exercise_progress
            WHERE learner_id = ? AND course_id = ? AND module_id = ? AND passed = 1
            """,
            (learner_id, course_id, module_id),
        ).fetchall()
    return {row["exercise_id"] for row in rows}


def missing_competencies(learner_id, competency_ids):
    required = set(competency_ids)
    if not required:
        return set()
    placeholders = ",".join("?" for _ in required)
    with _lock, _transaction() as connection:
        rows = connection.execute(
            f"""
            SELECT competency_id FROM competency_award
            WHERE learner_id = ? AND competency_id IN ({placeholders})
            """,
            (learner_id, *sorted(required)),
        ).fetchall()
    earned = {row["competency_id"] for row in rows}
    return required - earned


def start_course(learner_id, course_id, pending_environment=False):
    now = _now()
    status = "in_progress"
    blocked_reason = "Ubuntu operativo pendiente." if pending_environment else None
    with _lock, _transaction() as connection:
        _ensure_learner(connection, learner_id)
        connection.execute(
            """
            INSERT INTO course_progress(learner_id, course_id, status, started_at, updated_at, blocked_reason)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(learner_id, course_id) DO UPDATE SET
                updated_at = excluded.updated_at,
                blocked_reason = CASE
                    WHEN excluded.blocked_reason IS NULL THEN NULL
                    ELSE COALESCE(course_progress.blocked_reason, excluded.blocked_reason)
                END
            """,
            (learner_id, course_id, status, now, now, blocked_reason),
        )


def record_attempt(
    learner_id,
    course_id,
    module_id,
    activity_id,
    activity_type,
    score_percent,
    passed,
    status,
    answers,
    result,
    exercise_id=None,
    required_exercise_ids=None,
    assessment_id=None,
    module_ids=None,
    environment_required=False,
    competency_id=None,
    evidence_kind=None,
    evidence_summary="",
):
    now = _now()
    attempt_id = str(uuid.uuid4())
    required_exercise_ids = required_exercise_ids or []
    module_ids = module_ids or []
    with _lock, _transaction() as connection:
        connection.execute("BEGIN IMMEDIATE")
        learner = connection.execute(
            "SELECT 1 FROM learner_profile WHERE learner_id = ?",
            (learner_id,),
        ).fetchone()
        if learner is None:
            raise LearningAccessError("Inicia una sesión local antes de registrar actividades.")
        if activity_type in {"exercise", "assessment", "project"}:
            enrollment = connection.execute(
                "SELECT 1 FROM course_progress WHERE learner_id = ? AND course_id = ?",
                (learner_id, course_id),
            ).fetchone()
            if enrollment is None:
                raise LearningAccessError("Inicia el curso antes de registrar actividades.")
        current_count = connection.execute(
            """
            SELECT COUNT(*) AS count FROM learning_attempt
            WHERE learner_id = ? AND course_id = ? AND module_id = ?
              AND activity_id = ? AND activity_type = ?
            """,
            (learner_id, course_id, module_id, activity_id, activity_type),
        ).fetchone()["count"]
        attempt_number = current_count + 1
        connection.execute(
            """
            INSERT INTO learning_attempt(
                attempt_id, learner_id, course_id, module_id, activity_id, activity_type,
                attempt_number, score_percent, passed, status, answers_json, result_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id, learner_id, course_id, module_id, activity_id, activity_type,
                attempt_number, float(score_percent), int(bool(passed)), status,
                json.dumps(answers, ensure_ascii=False),
                json.dumps(result, ensure_ascii=False),
                now,
            ),
        )
        if exercise_id:
            connection.execute(
                """
                INSERT INTO exercise_progress(learner_id, course_id, module_id, exercise_id, passed, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(learner_id, course_id, module_id, exercise_id) DO UPDATE SET
                    passed = MAX(exercise_progress.passed, excluded.passed),
                    updated_at = excluded.updated_at
                """,
                (learner_id, course_id, module_id, exercise_id, int(bool(passed)), now),
            )

        if activity_type in {"exercise", "assessment"}:
            if activity_type == "assessment" and passed:
                status = "approved"
            exercise_passed = {
                row["exercise_id"]
                for row in connection.execute(
                    """
                    SELECT exercise_id FROM exercise_progress
                    WHERE learner_id = ? AND course_id = ? AND module_id = ? AND passed = 1
                    """,
                    (learner_id, course_id, module_id),
                ).fetchall()
            }
            all_exercises_passed = set(required_exercise_ids).issubset(exercise_passed)
            prior_assessment_passed = connection.execute(
                """
                SELECT 1 FROM learning_attempt
                WHERE learner_id = ? AND course_id = ? AND module_id = ?
                  AND activity_id = ? AND activity_type = 'assessment' AND passed = 1
                LIMIT 1
                """,
                (learner_id, course_id, module_id, assessment_id or ""),
            ).fetchone() is not None
            assessment_passed = prior_assessment_passed or (
                activity_type == "assessment" and passed
            )
            module_complete = (
                all_exercises_passed
                and assessment_passed
                and not environment_required
            )
            module_status = (
                "completed"
                if module_complete
                else "pending_environment"
                if environment_required and all_exercises_passed and assessment_passed
                else "in_progress"
            )
            connection.execute(
                """
                INSERT INTO module_progress(learner_id, course_id, module_id, status, updated_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(learner_id, course_id, module_id) DO UPDATE SET
                    status = CASE
                        WHEN module_progress.status = 'completed' THEN 'completed'
                        WHEN excluded.status = 'completed' THEN 'completed'
                        WHEN excluded.status = 'pending_environment' THEN 'pending_environment'
                        ELSE 'in_progress'
                    END,
                    updated_at = excluded.updated_at,
                    completed_at = COALESCE(module_progress.completed_at, excluded.completed_at)
                """,
                (learner_id, course_id, module_id, module_status, now, now if module_complete else None),
            )
            completed_modules = {
                row["module_id"]
                for row in connection.execute(
                    """
                    SELECT module_id FROM module_progress
                    WHERE learner_id = ? AND course_id = ? AND status = 'completed'
                    """,
                    (learner_id, course_id),
                ).fetchall()
            }
            course_complete = bool(module_ids) and set(module_ids).issubset(completed_modules)
            course_status = "approved" if course_complete else "in_progress"
            course_blocked_reason = "Ubuntu operativo pendiente." if environment_required else None
            connection.execute(
                """
                INSERT INTO course_progress(learner_id, course_id, status, started_at, updated_at, completed_at, blocked_reason)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(learner_id, course_id) DO UPDATE SET
                    status = CASE
                        WHEN course_progress.status = 'approved' THEN 'approved'
                        WHEN excluded.status = 'approved' THEN 'approved'
                        ELSE 'in_progress'
                    END,
                    updated_at = excluded.updated_at,
                    completed_at = COALESCE(course_progress.completed_at, excluded.completed_at),
                    blocked_reason = CASE
                        WHEN excluded.blocked_reason IS NULL THEN NULL
                        ELSE COALESCE(course_progress.blocked_reason, excluded.blocked_reason)
                    END
                """,
                (
                    learner_id, course_id, course_status, now, now,
                    now if course_complete else None, course_blocked_reason,
                ),
            )
            if course_complete and competency_id:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO competency_award(
                        learner_id, competency_id, course_id, awarded_at, attempt_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (learner_id, competency_id, course_id, now, attempt_id),
                )

        if evidence_kind:
            connection.execute(
                """
                INSERT INTO evidence(
                    evidence_id, learner_id, course_id, attempt_id, kind, summary, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()), learner_id, course_id, attempt_id, evidence_kind,
                    evidence_summary[:500], json.dumps(result, ensure_ascii=False), now,
                ),
            )
    return {"attempt_id": attempt_id, "attempt_number": attempt_number}


def get_progress(learner_id):
    with _lock, _transaction() as connection:
        learner = connection.execute(
            "SELECT created_at FROM learner_profile WHERE learner_id = ?", (learner_id,)
        ).fetchone()
        if learner is None:
            return {
                "learner_id": learner_id,
                "courses": [],
                "modules": [],
                "exercises": [],
                "attempts": [],
                "competencies": [],
                "evidence": [],
            }

        def rows(query, params=()):
            return [dict(row) for row in connection.execute(query, params).fetchall()]

        return {
            "learner_id": learner_id,
            "created_at": learner["created_at"],
            "courses": rows(
                "SELECT course_id, status, started_at, updated_at, completed_at, blocked_reason "
                "FROM course_progress WHERE learner_id = ? ORDER BY started_at",
                (learner_id,),
            ),
            "modules": rows(
                "SELECT course_id, module_id, status, updated_at, completed_at "
                "FROM module_progress WHERE learner_id = ? ORDER BY updated_at DESC",
                (learner_id,),
            ),
            "exercises": rows(
                "SELECT course_id, module_id, exercise_id, passed, updated_at "
                "FROM exercise_progress WHERE learner_id = ? ORDER BY updated_at DESC",
                (learner_id,),
            ),
            "attempts": rows(
                """
                SELECT attempt_id, course_id, module_id, activity_id, activity_type,
                       attempt_number, score_percent, passed, status, answers_json, result_json, created_at
                FROM learning_attempt WHERE learner_id = ?
                ORDER BY created_at DESC, attempt_number DESC
                """,
                (learner_id,),
            ),
            "competencies": rows(
                "SELECT competency_id, course_id, awarded_at, attempt_id "
                "FROM competency_award WHERE learner_id = ? ORDER BY awarded_at DESC",
                (learner_id,),
            ),
            "evidence": rows(
                "SELECT evidence_id, course_id, attempt_id, kind, summary, created_at "
                "FROM evidence WHERE learner_id = ? ORDER BY created_at DESC",
                (learner_id,),
            ),
        }
