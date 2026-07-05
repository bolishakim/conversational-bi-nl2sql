"""
Regression test for the participant-resolution bug that surfaced in the v2
Prolific run.

The original shared-account fix only patched /participants/me to accept an
explicit participant_id. Other endpoints (/tasks, /onboarding/status) still
called get_participant_by_user(user_id).first() — non-deterministic when
multiple Prolific participants share user1@adventureworks.com. P019 hit
/tasks during P016's session and was shown P016's task list, then P016's
"all complete -> survey" flip when P016 finished.

This test verifies resolve_participant_for_caller routes correctly:
  1. Two TESTFIX participants A and B on user1.
  2. resolve(user1, A.id) returns A.
  3. resolve(user1, B.id) returns B.
  4. resolve(user1, None) returns B (most recent, deterministic).
  5. resolve(user1, "non-existent-id") returns None.
  6. resolve(user2, A.id) returns None (A is linked to user1, caller is user2).
  7. resolve(user2, A.id, is_admin=True) returns A (admin escape hatch).

Run:
    export RAILWAY_DB_URL=postgresql://...
    cd backend && python -m tests.test_concurrent_resolution
"""
from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DB_URL = os.environ.get("RAILWAY_DB_URL") or os.environ.get("DATABASE_URL")
if not DB_URL:
    print("ERROR: set RAILWAY_DB_URL.")
    sys.exit(2)
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
    User, Experiment, ExperimentParticipant, ExperimentTask,
    ExperimentInteraction, QueryHistory,
)
from services.experiment_service import ExperimentService

PREFIX = "TESTFIX_RESOLVE"


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


def cleanup(db):
    leftovers = (
        db.query(ExperimentParticipant)
        .filter(ExperimentParticipant.prolific_pid.like(f"{PREFIX}%"))
        .all()
    )
    for row in leftovers:
        db.query(QueryHistory).filter(QueryHistory.participant_id == row.id).delete(synchronize_session=False)
        db.query(ExperimentInteraction).filter(ExperimentInteraction.participant_id == row.id).delete(synchronize_session=False)
        db.query(ExperimentTask).filter(ExperimentTask.participant_id == row.id).delete(synchronize_session=False)
        db.delete(row)
    db.commit()


def main() -> int:
    print("=" * 70)
    print(" Concurrent participant-resolution regression test")
    print("=" * 70)

    engine = create_engine(DB_URL, future=True)
    db = sessionmaker(bind=engine, autoflush=False, future=True)()
    svc = ExperimentService(db)
    c = Checks()

    user1 = db.query(User).filter(User.email == "user1@adventureworks.com").first()
    user2 = db.query(User).filter(User.email == "user2@adventureworks.com").first()
    exp = db.query(Experiment).filter(Experiment.status == "active").first()
    if not (user1 and user2 and exp):
        print("FAIL: missing user1, user2, or active experiment.")
        return 1

    # Capture experiment counter to restore at the end (test will register 2)
    initial_next_num = exp.next_participant_number
    initial_ctrl = exp.actual_control_participants
    initial_exp = exp.actual_experimental_participants

    cleanup(db)

    print("\n[1] Register two TESTFIX participants on user1 ...")
    a = svc.register_new_participant_v2(
        experiment_id=exp.id, user_id=user1.id,
        age=25, occupation_statuses="employee", field_of_work="business",
        field_of_study=None, visual_analytics_frequency="daily",
        business_background="both", llm_chatbot_experience="regularly",
        bi_tools_experience="advanced", consent_given=True,
        forced_condition="experimental",
        prolific_pid=f"{PREFIX}_A_{uuid.uuid4().hex[:8]}",
        prolific_study_id=f"{PREFIX}_STUDY",
        prolific_session_id=f"{PREFIX}_SESS_A",
    )
    b = svc.register_new_participant_v2(
        experiment_id=exp.id, user_id=user1.id,
        age=30, occupation_statuses="student", field_of_work=None,
        field_of_study="cs", visual_analytics_frequency="regularly",
        business_background="education", llm_chatbot_experience="occasionally",
        bi_tools_experience="intermediate", consent_given=True,
        forced_condition="experimental",
        prolific_pid=f"{PREFIX}_B_{uuid.uuid4().hex[:8]}",
        prolific_study_id=f"{PREFIX}_STUDY",
        prolific_session_id=f"{PREFIX}_SESS_B",
    )
    c.check("A and B both linked to user1", a.user_id == user1.id and b.user_id == user1.id)
    c.check("A and B have distinct codes", a.participant_code != b.participant_code,
            f"a={a.participant_code}, b={b.participant_code}")

    print("\n[2] resolve_participant_for_caller routes by participant_id ...")
    r_a = svc.resolve_participant_for_caller(user1.id, a.id)
    r_b = svc.resolve_participant_for_caller(user1.id, b.id)
    c.check("resolve(user1, A.id) -> A", r_a is not None and r_a.id == a.id,
            f"got={getattr(r_a, 'participant_code', None)}")
    c.check("resolve(user1, B.id) -> B", r_b is not None and r_b.id == b.id,
            f"got={getattr(r_b, 'participant_code', None)}")

    print("\n[3] resolve with no participant_id returns most recent ...")
    r_default = svc.resolve_participant_for_caller(user1.id, None)
    c.check("resolve(user1, None) -> most recent (B)",
            r_default is not None and r_default.id == b.id,
            f"got={getattr(r_default, 'participant_code', None)}")

    print("\n[4] resolve with bogus participant_id returns None ...")
    r_bogus = svc.resolve_participant_for_caller(user1.id, "non-existent-uuid")
    c.check("resolve(user1, bogus-id) -> None", r_bogus is None)

    print("\n[5] resolve cross-account is denied ...")
    r_xacc = svc.resolve_participant_for_caller(user2.id, a.id)
    c.check("resolve(user2, A.id) -> None (cross-account, not admin)", r_xacc is None)

    r_admin = svc.resolve_participant_for_caller(user2.id, a.id, is_admin=True)
    c.check("resolve(user2, A.id, is_admin=True) -> A (admin escape)",
            r_admin is not None and r_admin.id == a.id)

    print("\n[6] Each participant's task list resolves to its own rows ...")
    a_tasks = svc.get_participant_tasks(a.id)
    b_tasks = svc.get_participant_tasks(b.id)
    c.check("A has its own 6 tasks", len(a_tasks) == 6, f"len={len(a_tasks)}")
    c.check("B has its own 6 tasks", len(b_tasks) == 6, f"len={len(b_tasks)}")
    c.check("A's tasks all FK to A only",
            all(t.participant_id == a.id for t in a_tasks))
    c.check("B's tasks all FK to B only",
            all(t.participant_id == b.id for t in b_tasks))
    c.check("A and B share no task rows",
            len({t.id for t in a_tasks} & {t.id for t in b_tasks}) == 0)

    print("\n[7] Cleanup and restore counter ...")
    cleanup(db)
    leftover = (
        db.query(ExperimentParticipant)
        .filter(ExperimentParticipant.prolific_pid.like(f"{PREFIX}%"))
        .count()
    )
    c.check("no TESTFIX rows remain", leftover == 0, f"remaining={leftover}")

    db.execute(text(
        "UPDATE public.experiments SET "
        "next_participant_number = :n, "
        "actual_control_participants = :c, "
        "actual_experimental_participants = :e "
        "WHERE id = :eid"
    ), {"n": initial_next_num, "c": initial_ctrl, "e": initial_exp, "eid": exp.id})
    db.commit()
    db.refresh(exp)
    c.check("counter restored", exp.next_participant_number == initial_next_num,
            f"now={exp.next_participant_number}, initial={initial_next_num}")

    print("\n" + "=" * 70)
    total = c.passed + len(c.failed)
    print(f" VERDICT: {c.passed}/{total} checks passed")
    if c.failed:
        print("\n Failures:")
        for f in c.failed:
            print(f"   - {f}")
        print("\n RESULT: FAIL")
        return 1
    print("\n RESULT: PASS  (concurrent participant resolution works)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
