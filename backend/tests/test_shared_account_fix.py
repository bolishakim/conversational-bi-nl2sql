"""
Regression test for the shared-account concurrent-registration fix.

What this verifies (bug that caused the April 2026 Prolific batch data loss):

1. Registering a second participant against the same shared user account
   no longer detaches the first participant's user_id.
2. `get_most_recent_participant_for_user` returns the latest-registered row
   deterministically.
3. `get_participant(id)` still resolves any specific participant by id.
4. `submit_post_study_survey` writes to the specific participant row
   identified by id (not ambiguous by user_id).
5. Cleanup: every row, task, interaction, and query_history created by the
   test is deleted at the end.

Run:
    cd backend && python -m tests.test_shared_account_fix

Exits 0 on success, 1 on any failure. Prints a final VERDICT line.
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Make backend/ importable when run as a script
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Target DB: read from RAILWAY_DB_URL (or DATABASE_URL) env var.
# Example:
#   export RAILWAY_DB_URL=postgresql://user:pass@host:port/db
# The test creates + deletes its own rows with a TESTFIX prefix so it won't
# pollute real participant data.
DB_URL = os.environ.get("RAILWAY_DB_URL") or os.environ.get("DATABASE_URL")
if not DB_URL:
    print(
        "ERROR: set RAILWAY_DB_URL (or DATABASE_URL) to a Postgres connection "
        "string pointing at the DB you want to test against. "
        "Example: export RAILWAY_DB_URL='postgresql://user:pass@host:port/db'"
    )
    sys.exit(2)

# Stop the app settings module from trying to validate required env vars that
# the test doesn't need (OpenAI/Anthropic keys, etc.).
os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_NAME", "test")
os.environ.setdefault("DATABASE_USER", "test")
os.environ.setdefault("DATABASE_PASSWORD", "test")

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import (
    User,
    Experiment,
    ExperimentParticipant,
    ExperimentTask,
    ExperimentInteraction,
    QueryHistory,
)
from services.experiment_service import ExperimentService

TEST_PREFIX = "TESTFIX"


def _build_session():
    """Build a sync SQLAlchemy session against DB_URL."""
    engine = create_engine(DB_URL, echo=False, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    return Session()


class AssertionCounter:
    def __init__(self):
        self.passed = 0
        self.failed = []

    def check(self, label: str, cond: bool, detail: str = ""):
        mark = "\033[32m✓\033[0m" if cond else "\033[31m✗\033[0m"
        print(f"  {mark} {label}{(': ' + detail) if detail else ''}")
        if cond:
            self.passed += 1
        else:
            self.failed.append(f"{label}: {detail}")


def cleanup(db, pid_a: str, pid_b: str):
    """Delete any rows left by a previous/failed run, then the current run."""
    for pid in (pid_a, pid_b):
        row = (
            db.query(ExperimentParticipant)
            .filter(ExperimentParticipant.id == pid)
            .first()
        )
        if not row:
            continue
        db.query(QueryHistory).filter(
            QueryHistory.participant_id == row.id
        ).delete(synchronize_session=False)
        db.query(ExperimentInteraction).filter(
            ExperimentInteraction.participant_id == row.id
        ).delete(synchronize_session=False)
        db.query(ExperimentTask).filter(
            ExperimentTask.participant_id == row.id
        ).delete(synchronize_session=False)
        db.delete(row)
    # Also nuke any TESTFIX participants from aborted prior runs
    leftovers = (
        db.query(ExperimentParticipant)
        .filter(ExperimentParticipant.prolific_pid.like(f"{TEST_PREFIX}%"))
        .all()
    )
    for row in leftovers:
        db.query(QueryHistory).filter(
            QueryHistory.participant_id == row.id
        ).delete(synchronize_session=False)
        db.query(ExperimentInteraction).filter(
            ExperimentInteraction.participant_id == row.id
        ).delete(synchronize_session=False)
        db.query(ExperimentTask).filter(
            ExperimentTask.participant_id == row.id
        ).delete(synchronize_session=False)
        db.delete(row)
    db.commit()


def main() -> int:
    print("=" * 70)
    print(" Shared-account concurrent-registration regression test")
    print("=" * 70)

    db = _build_session()
    svc = ExperimentService(db)
    a = AssertionCounter()

    # Preconditions: need user1 + an active experiment
    user1 = (
        db.query(User).filter(User.email == "user1@adventureworks.com").first()
    )
    if not user1:
        print("FAIL: user1@adventureworks.com not found; cannot run test.")
        return 1

    experiment = (
        db.query(Experiment)
        .filter(Experiment.status.in_(("active", "recruiting", "planning")))
        .order_by(Experiment.created_at.desc())
        .first()
    )
    if not experiment:
        print("FAIL: no active experiment; cannot run test.")
        return 1

    # Capture pre-test state so cleanup can restore the participant code counter
    # and the per-condition group counters (test will register two participants
    # and we don't want those to leak into the live study state).
    initial_next_num = experiment.next_participant_number
    initial_ctrl = experiment.actual_control_participants
    initial_exp = experiment.actual_experimental_participants

    # Pre-clean any leftovers from a prior run before we start
    cleanup(db, "unused-a", "unused-b")

    # ------------------------------------------------------------------
    # Step 1: register participant A via the service method
    # ------------------------------------------------------------------
    print("\n[1] Register participant A ...")
    p_a = svc.register_new_participant_v2(
        experiment_id=experiment.id,
        user_id=user1.id,
        age=25,
        occupation_statuses="employee",
        field_of_work="business",
        field_of_study=None,
        visual_analytics_frequency="daily",
        business_background="both",
        llm_chatbot_experience="regularly",
        bi_tools_experience="advanced",
        consent_given=True,
        forced_condition="experimental",
        prolific_pid=f"{TEST_PREFIX}_A_{uuid.uuid4().hex[:8]}",
        prolific_study_id=f"{TEST_PREFIX}_STUDY",
        prolific_session_id=f"{TEST_PREFIX}_SESS_A",
    )
    a.check("participant A created", p_a is not None, p_a.participant_code)
    a.check("A linked to user1", p_a.user_id == user1.id)

    # ------------------------------------------------------------------
    # Step 2: register participant B (simulates concurrent registration)
    # ------------------------------------------------------------------
    print("\n[2] Register participant B (without any unlink step) ...")
    p_b = svc.register_new_participant_v2(
        experiment_id=experiment.id,
        user_id=user1.id,
        age=30,
        occupation_statuses="student",
        field_of_work=None,
        field_of_study="computer_science",
        visual_analytics_frequency="regularly",
        business_background="education",
        llm_chatbot_experience="occasionally",
        bi_tools_experience="intermediate",
        consent_given=True,
        forced_condition="experimental",
        prolific_pid=f"{TEST_PREFIX}_B_{uuid.uuid4().hex[:8]}",
        prolific_study_id=f"{TEST_PREFIX}_STUDY",
        prolific_session_id=f"{TEST_PREFIX}_SESS_B",
    )
    a.check("participant B created", p_b is not None, p_b.participant_code)
    a.check("B linked to user1", p_b.user_id == user1.id)

    # ------------------------------------------------------------------
    # Step 3: the bug regression — A must still be linked after B registered
    # ------------------------------------------------------------------
    print("\n[3] Regression check: A still linked after B registered ...")
    db.refresh(p_a)
    a.check(
        "A.user_id is still user1 (was NULL under the bug)",
        p_a.user_id == user1.id,
        f"p_a.user_id={p_a.user_id}",
    )

    # ------------------------------------------------------------------
    # Step 4: get_most_recent_participant_for_user returns B
    # ------------------------------------------------------------------
    print("\n[4] get_most_recent_participant_for_user returns B ...")
    latest = svc.get_most_recent_participant_for_user(user1.id)
    a.check(
        "most recent helper returns B",
        latest is not None and latest.id == p_b.id,
        f"returned={getattr(latest, 'participant_code', None)}",
    )

    # ------------------------------------------------------------------
    # Step 5: get_participant(id) resolves both rows independently
    # ------------------------------------------------------------------
    print("\n[5] get_participant(id) resolves both rows ...")
    fetched_a = svc.get_participant(p_a.id)
    fetched_b = svc.get_participant(p_b.id)
    a.check("get_participant(A) returns A", fetched_a and fetched_a.id == p_a.id)
    a.check("get_participant(B) returns B", fetched_b and fetched_b.id == p_b.id)

    # ------------------------------------------------------------------
    # Step 6: survey submissions write to the right rows (not cross-contaminated)
    # The new survey gate requires all real tasks completed first; complete
    # them inline so this test still exercises the cross-attribution check.
    # ------------------------------------------------------------------
    print("\n[6] Submit surveys for both, check attribution ...")
    for participant in (p_a, p_b):
        for task in (
            db.query(ExperimentTask)
            .filter(ExperimentTask.participant_id == participant.id, ExperimentTask.is_tutorial.is_(False))
            .all()
        ):
            svc.start_task(task.id)
            svc.complete_task(task.id, submitted_answer="ok", task_difficulty_rating=3, confidence_in_answer=3)

    resp_a = {"dashboard_usefulness": 5, "chatbot_helpfulness": 4, "_tag": "A"}
    resp_b = {"dashboard_usefulness": 3, "chatbot_helpfulness": 5, "_tag": "B"}
    svc.submit_post_study_survey(p_a.id, resp_a)
    svc.submit_post_study_survey(p_b.id, resp_b)

    db.refresh(p_a)
    db.refresh(p_b)

    a.check("A.session_completed = True", p_a.session_completed is True)
    a.check("B.session_completed = True", p_b.session_completed is True)
    a.check(
        "A survey tag stayed 'A'",
        (p_a.post_study_survey_responses or {}).get("_tag") == "A",
    )
    a.check(
        "B survey tag stayed 'B'",
        (p_b.post_study_survey_responses or {}).get("_tag") == "B",
    )
    a.check("A.status = 'completed'", p_a.status == "completed")
    a.check("B.status = 'completed'", p_b.status == "completed")

    # ------------------------------------------------------------------
    # Step 7: cleanup
    # ------------------------------------------------------------------
    print("\n[7] Cleaning up test rows ...")
    cleanup(db, p_a.id, p_b.id)
    remaining = (
        db.query(ExperimentParticipant)
        .filter(ExperimentParticipant.prolific_pid.like(f"{TEST_PREFIX}%"))
        .count()
    )
    a.check("no TESTFIX rows remain in DB", remaining == 0, f"remaining={remaining}")

    # Restore experiment counter and group counts so the test does not leak
    # state into the live study (the next real participant must still get the
    # code that was queued before the test ran).
    experiment.next_participant_number = initial_next_num
    experiment.actual_control_participants = initial_ctrl
    experiment.actual_experimental_participants = initial_exp
    db.commit()
    db.refresh(experiment)
    a.check(
        "next_participant_number restored",
        experiment.next_participant_number == initial_next_num,
        f"now={experiment.next_participant_number}, initial={initial_next_num}",
    )

    # ------------------------------------------------------------------
    # Verdict
    # ------------------------------------------------------------------
    print("\n" + "=" * 70)
    total = a.passed + len(a.failed)
    print(f" VERDICT: {a.passed}/{total} checks passed")
    if a.failed:
        print("\n Failures:")
        for f in a.failed:
            print(f"   - {f}")
        print("\n RESULT: FAIL")
        return 1
    print("\n RESULT: PASS  (shared-account fix is working)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
