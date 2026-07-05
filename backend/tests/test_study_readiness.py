"""
Study readiness verification.

Confirms the system is in a clean, correct state to launch the next study run
on the live Railway DB. Combines static DB checks, code-presence checks, and
a live end-to-end test (registers a TESTFIX participant, exercises the fixed
flows, then cleans up so no test data is left behind).

Checks:
  1.  Schema:    public.experiments has next_participant_number column
  2.  Counter:   active experiment's next_participant_number = 16
  3.  No orphaned Prolific rows in experiment_participants
  4.  No orphaned tasks / interactions / query_history rows
  5.  actual_control / actual_experimental match real row counts
  6.  Code:      generate_participant_code uses next_participant_number
  7.  Code:      start_task is idempotent (only stamps if NULL)
  8.  Code:      submit_post_study_survey gates on real tasks complete
  9.  Code:      onboarding/register no longer calls unlink_all_participants_from_user
  10. Live:      register a TESTFIX participant, code is P016
  11. Live:      start_task is idempotent end-to-end (timestamp unchanged on 2nd call)
  12. Live:      survey submission rejected with ValueError when real tasks incomplete
  13. Live:      survey submission accepted when all real tasks complete
  14. Cleanup:   no TESTFIX rows remain

Run:
    export RAILWAY_DB_URL="postgresql://..."
    cd backend && python -m tests.test_study_readiness

Exit 0 on success, 1 on any failure. Final VERDICT line summarizes the run.
"""
from __future__ import annotations

import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DB_URL = os.environ.get("RAILWAY_DB_URL") or os.environ.get("DATABASE_URL")
if not DB_URL:
    print("ERROR: set RAILWAY_DB_URL or DATABASE_URL.")
    sys.exit(2)
# SQLAlchemy 2.x rejects the bare 'postgres://' scheme; normalize.
if DB_URL.startswith("postgres://"):
    DB_URL = "postgresql://" + DB_URL[len("postgres://"):]

os.environ.setdefault("OPENAI_API_KEY", "test")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("JWT_SECRET_KEY", "test")
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_NAME", "test")
os.environ.setdefault("DATABASE_USER", "test")
os.environ.setdefault("DATABASE_PASSWORD", "test")

from sqlalchemy import create_engine, text
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

TEST_PREFIX = "TESTFIX_READY"


class Checks:
    def __init__(self):
        self.passed = 0
        self.failed: list[str] = []

    def check(self, label: str, cond: bool, detail: str = ""):
        mark = "\033[32m✓\033[0m" if cond else "\033[31m✗\033[0m"
        suffix = f": {detail}" if detail else ""
        print(f"  {mark} {label}{suffix}")
        if cond:
            self.passed += 1
        else:
            self.failed.append(f"{label}{suffix}")


def _build_session():
    engine = create_engine(DB_URL, echo=False, future=True)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)()


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def cleanup(db, prefix: str = TEST_PREFIX):
    leftovers = (
        db.query(ExperimentParticipant)
        .filter(ExperimentParticipant.prolific_pid.like(f"{prefix}%"))
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
    print(" Study Readiness Verification")
    print("=" * 70)

    db = _build_session()
    svc = ExperimentService(db)
    c = Checks()

    # Pre-clean any leftovers from prior runs of this script
    cleanup(db)

    # ----------------------------------------------------------------------
    # Section A: Schema + DB state
    # ----------------------------------------------------------------------
    print("\n[A] Schema + DB state")
    has_col = db.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_schema='public' AND table_name='experiments' "
        "AND column_name='next_participant_number'"
    )).scalar()
    c.check("experiments.next_participant_number column exists", bool(has_col))

    exp = db.query(Experiment).filter(Experiment.status == 'active').first()
    if not exp:
        print("FAIL: no active experiment.")
        return 1

    c.check(
        "active experiment next_participant_number == 16",
        exp.next_participant_number == 16,
        f"actual={exp.next_participant_number}",
    )

    prolific_count = (
        db.query(ExperimentParticipant)
        .filter(
            (ExperimentParticipant.recruitment_source == 'prolific')
            | (ExperimentParticipant.prolific_pid.isnot(None))
        )
        .filter(
            ExperimentParticipant.prolific_pid.is_(None)
            | ~ExperimentParticipant.prolific_pid.like(f"{TEST_PREFIX}%")
        )
        .count()
    )
    c.check(
        "no leftover Prolific participants",
        prolific_count == 0,
        f"prolific_count={prolific_count}",
    )

    orphan_tasks = db.execute(text(
        "SELECT COUNT(*) FROM public.experiment_tasks et "
        "LEFT JOIN public.experiment_participants ep ON et.participant_id = ep.id "
        "WHERE ep.id IS NULL"
    )).scalar()
    orphan_inter = db.execute(text(
        "SELECT COUNT(*) FROM public.experiment_interactions ei "
        "LEFT JOIN public.experiment_participants ep ON ei.participant_id = ep.id "
        "WHERE ep.id IS NULL"
    )).scalar()
    orphan_qh = db.execute(text(
        "SELECT COUNT(*) FROM public.query_history qh "
        "WHERE qh.participant_id IS NOT NULL "
        "AND NOT EXISTS (SELECT 1 FROM public.experiment_participants ep WHERE ep.id = qh.participant_id)"
    )).scalar()
    c.check("no orphaned tasks", orphan_tasks == 0, f"orphans={orphan_tasks}")
    c.check("no orphaned interactions", orphan_inter == 0, f"orphans={orphan_inter}")
    c.check("no orphaned query_history", orphan_qh == 0, f"orphans={orphan_qh}")

    not_testfix = (
        ExperimentParticipant.prolific_pid.is_(None)
        | ~ExperimentParticipant.prolific_pid.like(f"{TEST_PREFIX}%")
    )
    real_ctrl = (
        db.query(ExperimentParticipant)
        .filter(
            ExperimentParticipant.experiment_id == exp.id,
            ExperimentParticipant.condition_assigned == 'control',
            not_testfix,
        )
        .count()
    )
    real_exp = (
        db.query(ExperimentParticipant)
        .filter(
            ExperimentParticipant.experiment_id == exp.id,
            ExperimentParticipant.condition_assigned == 'experimental',
            not_testfix,
        )
        .count()
    )
    c.check(
        "actual_control_participants matches real rows",
        exp.actual_control_participants == real_ctrl,
        f"counter={exp.actual_control_participants}, rows={real_ctrl}",
    )
    c.check(
        "actual_experimental_participants matches real rows",
        exp.actual_experimental_participants == real_exp,
        f"counter={exp.actual_experimental_participants}, rows={real_exp}",
    )

    # ----------------------------------------------------------------------
    # Section B: Code presence checks
    # ----------------------------------------------------------------------
    print("\n[B] Code presence")
    svc_src = _read(BACKEND_DIR / "services" / "experiment_service.py")
    api_src = _read(BACKEND_DIR / "api" / "experiment.py")

    c.check(
        "generate_participant_code uses next_participant_number",
        "next_participant_number = next_participant_number + 1" in svc_src,
    )
    c.check(
        "start_task guarded by 'task_started_at is None'",
        "task.task_started_at is None" in svc_src,
    )
    c.check(
        "submit_post_study_survey checks incomplete_real",
        "incomplete_real" in svc_src and "Cannot submit survey" in svc_src,
    )
    c.check(
        "/participants/survey converts ValueError to HTTP 409",
        "status_code=409" in api_src and "submit_post_study_survey" in api_src,
    )
    c.check(
        "register endpoint no longer calls unlink_all_participants_from_user",
        "unlink_all_participants_from_user(current_user.id)" not in api_src,
    )
    c.check(
        "get_most_recent_participant_for_user helper exists",
        "def get_most_recent_participant_for_user" in svc_src,
    )

    # ----------------------------------------------------------------------
    # Section C: Live functional checks (TESTFIX rows, cleaned at end)
    # ----------------------------------------------------------------------
    print("\n[C] Live functional checks")
    user1 = (
        db.query(User).filter(User.email == "user1@adventureworks.com").first()
    )
    if not user1:
        print("FAIL: user1@adventureworks.com missing.")
        return 1

    p = svc.register_new_participant_v2(
        experiment_id=exp.id,
        user_id=user1.id,
        age=27,
        occupation_statuses="employee",
        field_of_work="business",
        field_of_study=None,
        visual_analytics_frequency="regularly",
        business_background="both",
        llm_chatbot_experience="regularly",
        bi_tools_experience="advanced",
        consent_given=True,
        forced_condition="experimental",
        prolific_pid=f"{TEST_PREFIX}_{uuid.uuid4().hex[:8]}",
        prolific_study_id=f"{TEST_PREFIX}_STUDY",
        prolific_session_id=f"{TEST_PREFIX}_SESS",
    )
    c.check(
        "next registered participant code is P016",
        p.participant_code == "P016",
        f"got={p.participant_code}",
    )

    tasks = (
        db.query(ExperimentTask)
        .filter(ExperimentTask.participant_id == p.id)
        .order_by(ExperimentTask.task_number)
        .all()
    )
    c.check(
        "auto-assigned 6 tasks (1 tutorial + 5 real)",
        len(tasks) == 6 and sum(1 for t in tasks if t.is_tutorial) == 1,
        f"total={len(tasks)}",
    )

    real_tasks = [t for t in tasks if not t.is_tutorial]
    first_real = real_tasks[0]

    started = svc.start_task(first_real.id)
    first_started_at = started.task_started_at
    c.check("start_task stamps task_started_at on first call", first_started_at is not None)

    time.sleep(0.5)
    started_again = svc.start_task(first_real.id)
    db.refresh(started_again)
    c.check(
        "start_task is idempotent (timestamp unchanged on 2nd call)",
        started_again.task_started_at == first_started_at,
        f"first={first_started_at}, second={started_again.task_started_at}",
    )

    # Survey gate: real tasks not completed yet, must reject
    rejected = False
    try:
        svc.submit_post_study_survey(p.id, {"_tag": "should_be_rejected"})
    except ValueError:
        rejected = True
    c.check("survey rejected when real tasks incomplete", rejected)

    # Complete all 5 real tasks, then survey should succeed
    for t in real_tasks:
        svc.start_task(t.id)
        svc.complete_task(t.id, submitted_answer="ok", task_difficulty_rating=3, confidence_in_answer=3)

    accepted = False
    try:
        svc.submit_post_study_survey(p.id, {"_tag": "complete"})
        accepted = True
    except ValueError as e:
        print(f"  unexpected ValueError: {e}")
    c.check("survey accepted when all real tasks complete", accepted)

    db.refresh(p)
    c.check("session_completed flipped true", p.session_completed is True)
    c.check("status set to 'completed'", p.status == 'completed')

    # ----------------------------------------------------------------------
    # Section D: Cleanup
    # ----------------------------------------------------------------------
    print("\n[D] Cleanup")
    cleanup(db)
    leftover = (
        db.query(ExperimentParticipant)
        .filter(ExperimentParticipant.prolific_pid.like(f"{TEST_PREFIX}%"))
        .count()
    )
    c.check("no TESTFIX rows remain", leftover == 0, f"remaining={leftover}")

    # The counter advanced because we registered a TESTFIX participant.
    # Restore it to 16 so the next REAL participant still gets P016.
    db.execute(text(
        "UPDATE public.experiments SET next_participant_number = 16 WHERE id = :eid"
    ), {"eid": exp.id})
    # And reconcile group counters again (TESTFIX may have bumped experimental count)
    db.execute(text(
        "UPDATE public.experiments e SET "
        "actual_control_participants = (SELECT COUNT(*) FROM public.experiment_participants "
        "WHERE experiment_id = e.id AND condition_assigned = 'control'), "
        "actual_experimental_participants = (SELECT COUNT(*) FROM public.experiment_participants "
        "WHERE experiment_id = e.id AND condition_assigned = 'experimental') "
        "WHERE e.id = :eid"
    ), {"eid": exp.id})
    db.commit()
    db.refresh(exp)
    c.check(
        "counter restored to 16 after cleanup",
        exp.next_participant_number == 16,
        f"actual={exp.next_participant_number}",
    )

    # Verdict
    print("\n" + "=" * 70)
    total = c.passed + len(c.failed)
    print(f" VERDICT: {c.passed}/{total} checks passed")
    if c.failed:
        print("\n Failures:")
        for f in c.failed:
            print(f"   - {f}")
        print("\n RESULT: FAIL")
        return 1
    print("\n RESULT: PASS  (system is ready for the next study run)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
