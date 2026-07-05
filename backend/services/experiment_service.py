"""
Experiment Service
Handles all experiment-related business logic for the between-subjects user study
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from collections import defaultdict
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func, cast, Date
import random
import hashlib

from database.models import (
    User, Experiment, ExperimentParticipant, ExperimentTask, ExperimentInteraction,
    QueryHistory,
    ROLE_ADMIN, ROLE_PARTICIPANT_CONTROL, ROLE_PARTICIPANT_EXPERIMENTAL
)
from utils.logger import logger


# Participants with these statuses are kept in the DB and shown in the admin
# participant list, but excluded from all analytics aggregates (overview,
# task comparison, survey analytics, chatbot analytics).
ANALYSIS_EXCLUDED_STATUSES = ('excluded', 'withdrawn')


class ExperimentService:
    """Service class for experiment-related operations"""

    def __init__(self, db: DBSession):
        self.db = db

    def _analysis_participants(self) -> List[ExperimentParticipant]:
        """Participants eligible for analytics (excludes 'excluded' / 'withdrawn')."""
        return self.db.query(ExperimentParticipant).filter(
            ~ExperimentParticipant.status.in_(ANALYSIS_EXCLUDED_STATUSES)
        ).all()

    # =========================================================================
    # Experiment Management
    # =========================================================================

    def create_experiment(
        self,
        name: str,
        description: Optional[str] = None,
        research_question: Optional[str] = None,
        hypothesis: Optional[str] = None,
        created_by_id: Optional[str] = None,
        **kwargs
    ) -> Experiment:
        """Create a new experiment"""
        experiment = Experiment(
            name=name,
            description=description,
            research_question=research_question,
            hypothesis=hypothesis,
            created_by=created_by_id,
            **kwargs
        )
        self.db.add(experiment)
        self.db.commit()
        self.db.refresh(experiment)
        logger.info(f"Created experiment: {experiment.id} - {name}")
        return experiment

    def get_experiment(self, experiment_id: str) -> Optional[Experiment]:
        """Get experiment by ID"""
        return self.db.query(Experiment).filter(Experiment.id == experiment_id).first()

    def get_active_experiment(self) -> Optional[Experiment]:
        """Get the currently active experiment"""
        return self.db.query(Experiment).filter(Experiment.status == 'active').first()

    def list_experiments(self, status: Optional[str] = None) -> List[Experiment]:
        """List all experiments, optionally filtered by status"""
        query = self.db.query(Experiment)
        if status:
            query = query.filter(Experiment.status == status)
        return query.order_by(Experiment.created_at.desc()).all()

    def update_experiment_status(self, experiment_id: str, status: str) -> Optional[Experiment]:
        """Update experiment status"""
        experiment = self.get_experiment(experiment_id)
        if experiment:
            experiment.status = status
            if status == 'active' and not experiment.actual_start_date:
                experiment.actual_start_date = datetime.now(timezone.utc)
            elif status == 'completed' and not experiment.actual_end_date:
                experiment.actual_end_date = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(experiment)
            logger.info(f"Updated experiment {experiment_id} status to {status}")
        return experiment

    # =========================================================================
    # Participant Management
    # =========================================================================

    def generate_participant_code(self, experiment_id: str) -> str:
        """
        Generate unique participant code (P001, P002, ...) using a per-experiment
        monotonic counter persisted on the experiments row. Codes are never
        reused, even if participant rows are hard-deleted (this matters for the
        Prolific shared-account model where rows from aborted runs may be
        purged but their codes must not be re-issued).
        """
        from sqlalchemy import text
        next_num = self.db.execute(
            text(
                "UPDATE public.experiments "
                "SET next_participant_number = next_participant_number + 1 "
                "WHERE id = :exp_id "
                "RETURNING next_participant_number - 1"
            ),
            {"exp_id": experiment_id},
        ).scalar()
        if next_num is None:
            raise ValueError(f"Experiment {experiment_id} not found")
        return f"P{str(next_num).zfill(3)}"

    def assign_condition(self, experiment_id: str, method: str = 'random') -> str:
        """
        Assign participant to control or experimental condition
        Uses balanced random assignment to ensure roughly equal groups
        """
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            raise ValueError(f"Experiment {experiment_id} not found")

        control_count = experiment.actual_control_participants
        experimental_count = experiment.actual_experimental_participants

        if method == 'random':
            # Balanced random: prefer the smaller group, with randomness when equal
            if control_count < experimental_count:
                return 'control'
            elif experimental_count < control_count:
                return 'experimental'
            else:
                return random.choice(['control', 'experimental'])
        elif method == 'alternating':
            # Simple alternating assignment
            total = control_count + experimental_count
            return 'control' if total % 2 == 0 else 'experimental'
        else:
            return 'control'  # Default to control

    def create_participant(
        self,
        experiment_id: str,
        user_id: str,
        email: str,
        demographics: Optional[Dict[str, Any]] = None,
        assignment_method: str = 'random'
    ) -> ExperimentParticipant:
        """
        Create a new experiment participant and assign them to a condition
        Also updates the user's role based on assigned condition
        """
        # Generate participant code
        participant_code = self.generate_participant_code(experiment_id)

        # Assign condition
        condition = self.assign_condition(experiment_id, assignment_method)

        # Hash email for privacy
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()

        # Create participant
        participant = ExperimentParticipant(
            experiment_id=experiment_id,
            participant_code=participant_code,
            user_id=user_id,
            email_hash=email_hash,
            condition_assigned=condition,
            assignment_method=assignment_method,
            randomization_seed=random.randint(1, 1000000),
            age_group=demographics.get('age_group') if demographics else None,
            gender=demographics.get('gender') if demographics else None,
            education_level=demographics.get('education_level') if demographics else None,
            occupation=demographics.get('occupation') if demographics else None,
            industry=demographics.get('industry') if demographics else None,
            sql_proficiency=demographics.get('sql_proficiency') if demographics else None,
            bi_tools_experience=demographics.get('bi_tools_experience') if demographics else None,
            data_analysis_experience_years=demographics.get('data_analysis_experience_years') if demographics else None,
        )
        self.db.add(participant)

        # Update experiment participant counts
        experiment = self.get_experiment(experiment_id)
        if condition == 'control':
            experiment.actual_control_participants += 1
        else:
            experiment.actual_experimental_participants += 1

        # Update user role based on condition
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            if condition == 'control':
                user.role = ROLE_PARTICIPANT_CONTROL
            else:
                user.role = ROLE_PARTICIPANT_EXPERIMENTAL
            logger.info(f"Updated user {user_id} role to {user.role}")

        self.db.commit()
        self.db.refresh(participant)
        logger.info(f"Created participant {participant_code} assigned to {condition} condition")
        return participant

    def register_new_participant(
        self,
        experiment_id: str,
        user_id: str,
        email: str,
        full_name: str,
        phone_number: Optional[str],
        date_of_birth: str,  # Format: YYYY-MM-DD
        job_role: str,  # 'employee' or 'student'
        job_title: Optional[str] = None,
        company_name: Optional[str] = None,
        field_of_study: Optional[str] = None,
        university_name: Optional[str] = None,
        assignment_method: str = 'random',
        forced_condition: Optional[str] = None  # If set, forces this condition instead of random
    ) -> ExperimentParticipant:
        """
        Register a new participant with onboarding information
        Creates participant record and assigns to experimental condition

        If forced_condition is provided, uses that instead of random assignment.
        This is used when condition is determined by the user account (user1=experimental, user2=control).
        """
        from datetime import datetime as dt

        # Generate participant code
        participant_code = self.generate_participant_code(experiment_id)

        # Assign condition - use forced_condition if provided, otherwise random
        if forced_condition and forced_condition in ['control', 'experimental']:
            condition = forced_condition
        else:
            condition = self.assign_condition(experiment_id, assignment_method)

        # Hash email for privacy
        email_hash = hashlib.sha256(email.lower().encode()).hexdigest()

        # Parse date of birth
        dob = dt.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None

        # Create participant with onboarding data
        participant = ExperimentParticipant(
            experiment_id=experiment_id,
            participant_code=participant_code,
            user_id=user_id,
            email_hash=email_hash,
            condition_assigned=condition,
            assignment_method=assignment_method,
            randomization_seed=random.randint(1, 1000000),
            # Onboarding fields
            full_name=full_name,
            phone_number=phone_number,
            date_of_birth=dob,
            job_role=job_role,
            job_title=job_title,
            company_name=company_name,
            field_of_study=field_of_study,
            university_name=university_name,
            registered_at=datetime.now(timezone.utc),
            onboarding_completed=True,
            status='active',
        )
        self.db.add(participant)

        # Update experiment participant counts
        experiment = self.get_experiment(experiment_id)
        if condition == 'control':
            experiment.actual_control_participants += 1
        else:
            experiment.actual_experimental_participants += 1

        # Update user role based on condition
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            if condition == 'control':
                user.role = ROLE_PARTICIPANT_CONTROL
            else:
                user.role = ROLE_PARTICIPANT_EXPERIMENTAL
            logger.info(f"Updated user {user_id} role to {user.role}")

        self.db.commit()
        self.db.refresh(participant)
        logger.info(f"Registered participant {participant_code} ({full_name}) assigned to {condition} condition")

        # Auto-assign study tasks to the new participant
        tasks_assigned = self.assign_study_tasks_to_participant(experiment_id, participant.id)
        logger.info(f"Assigned {tasks_assigned} tasks to participant {participant_code}")

        return participant

    def find_participant_by_prolific_pid(self, prolific_pid: str) -> Optional[ExperimentParticipant]:
        """Return the participant row associated with this Prolific PID, or None."""
        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.prolific_pid == prolific_pid
        ).first()

    def register_new_participant_v2(
        self,
        experiment_id: str,
        user_id: str,
        # Pre-survey data (anonymous, no PII)
        age: int,
        occupation_statuses: str,  # comma-separated, e.g. "student,employee"
        field_of_work: Optional[str],
        field_of_study: Optional[str],
        visual_analytics_frequency: str,
        business_background: str,
        llm_chatbot_experience: str,
        bi_tools_experience: str,
        # Consent
        consent_given: bool,
        assignment_method: str = 'random',
        forced_condition: Optional[str] = None,
        # Prolific identifiers (optional, populated when arriving from Prolific URL)
        prolific_pid: Optional[str] = None,
        prolific_study_id: Optional[str] = None,
        prolific_session_id: Optional[str] = None,
    ) -> ExperimentParticipant:
        """
        Register a new participant with pre-survey data (v2 - no PII collected).

        This version collects only anonymous demographic data from the 7-question pre-survey.
        No personally identifiable information (name, email, phone, DOB) is collected.

        If forced_condition is provided, uses that instead of random assignment.
        This is used when condition is determined by the user account (user1=experimental, user2=control).
        """
        # Generate participant code
        participant_code = self.generate_participant_code(experiment_id)

        # Assign condition - use forced_condition if provided, otherwise random
        if forced_condition and forced_condition in ['control', 'experimental']:
            condition = forced_condition
        else:
            condition = self.assign_condition(experiment_id, assignment_method)

        # Recruitment source: Prolific if we have a PID, else university
        recruitment_source = 'prolific' if prolific_pid else 'university'

        # Create participant with pre-survey data (no PII)
        participant = ExperimentParticipant(
            experiment_id=experiment_id,
            participant_code=participant_code,
            user_id=user_id,
            condition_assigned=condition,
            assignment_method=assignment_method,
            randomization_seed=random.randint(1, 1000000),
            # Pre-survey responses
            age=age,
            occupation_statuses=occupation_statuses,
            field_of_work=field_of_work,
            field_of_study=field_of_study,
            visual_analytics_frequency=visual_analytics_frequency,
            business_background=business_background,
            llm_chatbot_experience=llm_chatbot_experience,
            bi_tools_experience=bi_tools_experience,
            # Consent
            consent_given=consent_given,
            consent_timestamp=datetime.now(timezone.utc) if consent_given else None,
            # Recruitment tracking
            recruitment_source=recruitment_source,
            prolific_pid=prolific_pid,
            prolific_study_id=prolific_study_id,
            prolific_session_id=prolific_session_id,
            # Status
            registered_at=datetime.now(timezone.utc),
            onboarding_completed=True,
            status='active',
        )
        self.db.add(participant)

        # Update experiment participant counts
        experiment = self.get_experiment(experiment_id)
        if condition == 'control':
            experiment.actual_control_participants += 1
        else:
            experiment.actual_experimental_participants += 1

        # Update user role based on condition
        user = self.db.query(User).filter(User.id == user_id).first()
        if user:
            if condition == 'control':
                user.role = ROLE_PARTICIPANT_CONTROL
            else:
                user.role = ROLE_PARTICIPANT_EXPERIMENTAL
            logger.info(f"Updated user {user_id} role to {user.role}")

        self.db.commit()
        self.db.refresh(participant)
        logger.info(f"Registered participant {participant_code} (anonymous) assigned to {condition} condition")

        # Auto-assign study tasks to the new participant
        tasks_assigned = self.assign_study_tasks_to_participant(experiment_id, participant.id)
        logger.info(f"Assigned {tasks_assigned} tasks to participant {participant_code}")

        return participant

    def find_participant_by_code(self, participant_code: str) -> Optional[ExperimentParticipant]:
        """
        Find a returning participant by participant code only.
        Used for re-identification of returning participants.

        NOTE: Since we don't collect personal info (name, DOB), this is the only
        way to look up returning participants.
        """
        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.participant_code == participant_code.upper()
        ).first()

    # Legacy methods - kept for backward compatibility
    def find_participant_by_name_and_dob(
        self,
        full_name: str,
        date_of_birth: str  # Format: YYYY-MM-DD
    ) -> Optional[ExperimentParticipant]:
        """
        DEPRECATED: Find a returning participant by name and date of birth.
        This method is no longer used as we don't collect personal info anymore.
        """
        from datetime import datetime as dt
        dob = dt.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None

        return self.db.query(ExperimentParticipant).filter(
            func.lower(ExperimentParticipant.full_name) == full_name.lower(),
            ExperimentParticipant.date_of_birth == dob
        ).first()

    def find_participant_by_code_and_dob(
        self,
        participant_code: str,
        date_of_birth: str  # Format: YYYY-MM-DD
    ) -> Optional[ExperimentParticipant]:
        """
        DEPRECATED: Find a returning participant by participant code and date of birth.
        Use find_participant_by_code instead - we no longer require DOB verification.
        """
        from datetime import datetime as dt
        dob = dt.strptime(date_of_birth, '%Y-%m-%d').date() if date_of_birth else None

        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.participant_code == participant_code,
            ExperimentParticipant.date_of_birth == dob
        ).first()

    def get_participant(self, participant_id: str) -> Optional[ExperimentParticipant]:
        """Get participant by ID"""
        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.id == participant_id
        ).first()

    def get_participant_by_user(self, user_id: str) -> Optional[ExperimentParticipant]:
        """Get participant by user ID (first match — legacy; prefer
        get_most_recent_participant_for_user under the shared-account model)."""
        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.user_id == user_id
        ).first()

    def get_most_recent_participant_for_user(
        self, user_id: str
    ) -> Optional[ExperimentParticipant]:
        """
        Return the most recently registered participant linked to this user.
        Used by /participants/me as a fallback when the client does not pass
        an explicit participant_id. Under the shared-account model multiple
        rows can be linked concurrently; picking the most recent is a
        reasonable default for the returning-participant flow.
        """
        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.user_id == user_id
        ).order_by(ExperimentParticipant.registered_at.desc()).first()

    def resolve_participant_for_caller(
        self,
        user_id: str,
        participant_id: Optional[str],
        is_admin: bool = False,
    ) -> Optional[ExperimentParticipant]:
        """
        Resolve which participant the caller means under the shared-account model.

        Preferred path: caller passes participant_id explicitly (the frontend
        persists it to sessionStorage at registration/lookup time). The
        participant must be linked to the caller's user_id, unless the caller
        is admin.

        Fallback: if no participant_id is given, return the most recently
        registered participant linked to this user. This keeps single-participant
        sessions working but is unsafe when several Prolific participants share
        one login concurrently, so the frontend should send participant_id
        whenever possible.
        """
        if participant_id:
            p = self.get_participant(participant_id)
            if not p:
                return None
            if p.user_id != user_id and not is_admin:
                return None
            return p
        return self.get_most_recent_participant_for_user(user_id)

    def unlink_all_participants_from_user(self, user_id: str, except_participant_id: str = None):
        """Unlink all participants from a user account (except optionally one)"""
        query = self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.user_id == user_id
        )
        if except_participant_id:
            query = query.filter(ExperimentParticipant.id != except_participant_id)
        participants = query.all()
        for p in participants:
            p.user_id = None
        if participants:
            self.db.commit()

    def get_participant_by_code(self, participant_code: str) -> Optional[ExperimentParticipant]:
        """Get participant by code"""
        return self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.participant_code == participant_code
        ).first()

    def record_consent(self, participant_id: str) -> Optional[ExperimentParticipant]:
        """Record participant consent"""
        participant = self.get_participant(participant_id)
        if participant:
            participant.consent_given = True
            participant.consent_timestamp = datetime.now(timezone.utc)
            participant.status = 'active'
            self.db.commit()
            self.db.refresh(participant)
            logger.info(f"Recorded consent for participant {participant.participant_code}")
        return participant

    def _append_admin_note(self, participant: ExperimentParticipant, note: str) -> None:
        """Prepend a timestamped line to admin_notes (most recent first)."""
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        line = f"[{ts}] {note}"
        participant.admin_notes = (
            f"{line}\n{participant.admin_notes}" if participant.admin_notes else line
        )

    def exclude_participant(
        self, participant_id: str, reason: str
    ) -> Optional[ExperimentParticipant]:
        """Mark a participant as excluded from analysis. Data is preserved."""
        p = self.get_participant(participant_id)
        if not p:
            return None
        p.status = 'excluded'
        p.exclusion_reason = reason
        self._append_admin_note(p, f"Excluded. Reason: {reason}")
        self.db.commit()
        self.db.refresh(p)
        logger.info(f"Excluded participant {p.participant_code}: {reason}")
        return p

    def withdraw_participant(
        self, participant_id: str, reason: Optional[str] = None
    ) -> Optional[ExperimentParticipant]:
        """Record a participant's withdrawal request."""
        p = self.get_participant(participant_id)
        if not p:
            return None
        p.status = 'withdrawn'
        p.withdrawal_requested = True
        p.withdrawal_timestamp = datetime.now(timezone.utc)
        if reason:
            p.exclusion_reason = reason
        self._append_admin_note(
            p, f"Withdrawn. Reason: {reason or '(not provided)'}"
        )
        self.db.commit()
        self.db.refresh(p)
        logger.info(f"Withdrew participant {p.participant_code}: {reason}")
        return p

    def reassign_participant_condition(
        self, participant_id: str, new_condition: str, reason: str
    ) -> Optional[ExperimentParticipant]:
        """Change a participant's condition assignment post-hoc."""
        if new_condition not in ('control', 'experimental'):
            raise ValueError("new_condition must be 'control' or 'experimental'")
        p = self.get_participant(participant_id)
        if not p:
            return None
        old = p.condition_assigned
        if old == new_condition:
            return p  # no-op
        p.condition_assigned = new_condition
        p.assignment_method = 'manual_override'
        self._append_admin_note(
            p,
            f"Condition reassigned {old} -> {new_condition}. Reason: {reason}",
        )
        self.db.commit()
        self.db.refresh(p)
        logger.info(
            f"Reassigned {p.participant_code} from {old} to {new_condition}: {reason}"
        )
        return p

    def reinstate_participant(
        self, participant_id: str
    ) -> Optional[ExperimentParticipant]:
        """Undo an exclude / withdraw by restoring status to 'active' or 'completed'."""
        p = self.get_participant(participant_id)
        if not p:
            return None
        # Pick a sensible restored status: 'completed' if session_completed,
        # 'active' otherwise. Keep exclusion_reason / withdrawal fields for
        # audit but clear the ones that gate re-entry.
        p.status = 'completed' if p.session_completed else 'active'
        p.withdrawal_requested = False
        p.withdrawal_timestamp = None
        self._append_admin_note(p, "Reinstated (status restored).")
        self.db.commit()
        self.db.refresh(p)
        logger.info(f"Reinstated participant {p.participant_code}")
        return p

    def update_participant_status(
        self,
        participant_id: str,
        status: str,
        exclusion_reason: Optional[str] = None
    ) -> Optional[ExperimentParticipant]:
        """Update participant status"""
        participant = self.get_participant(participant_id)
        if participant:
            participant.status = status
            if exclusion_reason:
                participant.exclusion_reason = exclusion_reason
            if status == 'completed':
                participant.session_completed = True
                participant.session_completed_at = datetime.now(timezone.utc)
            elif status == 'withdrawn':
                participant.withdrawal_requested = True
                participant.withdrawal_timestamp = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(participant)
        return participant

    def submit_post_study_survey(
        self,
        participant_id: str,
        survey_responses: Dict[str, Any]
    ) -> Optional[ExperimentParticipant]:
        """Submit post-study survey responses.

        Server-side gate: all real (non-tutorial) tasks must be completed
        before the survey is accepted. Without this check, a misbehaving
        client could mark the session complete with tasks still in flight
        (this is what happened to P029 in the April 2026 Prolific run).
        Raises ValueError if the gate fails; the caller surfaces a 409.
        """
        participant = self.get_participant(participant_id)
        if participant:
            incomplete_real = self.db.query(ExperimentTask).filter(
                ExperimentTask.participant_id == participant_id,
                ExperimentTask.is_tutorial.is_(False),
                ExperimentTask.task_completed_at.is_(None),
            ).count()
            if incomplete_real > 0:
                raise ValueError(
                    f"Cannot submit survey: {incomplete_real} real task(s) still incomplete"
                )

            participant.post_study_survey_responses = survey_responses

            # Extract specific metrics if present
            if 'system_usability_scale_score' in survey_responses:
                participant.system_usability_scale_score = survey_responses['system_usability_scale_score']
            if 'chatbot_understanding_rating' in survey_responses:
                participant.chatbot_understanding_rating = survey_responses['chatbot_understanding_rating']
            if 'explanation_helpfulness_rating' in survey_responses:
                participant.explanation_helpfulness_rating = survey_responses['explanation_helpfulness_rating']
            if 'sql_trust_rating' in survey_responses:
                participant.sql_trust_rating = survey_responses['sql_trust_rating']
            if 'overall_satisfaction_rating' in survey_responses:
                participant.overall_satisfaction_rating = survey_responses['overall_satisfaction_rating']
            if 'would_use_at_work' in survey_responses:
                participant.would_use_at_work = survey_responses['would_use_at_work']
            if 'perceived_usefulness' in survey_responses:
                participant.perceived_usefulness = survey_responses['perceived_usefulness']
            if 'perceived_ease_of_use' in survey_responses:
                participant.perceived_ease_of_use = survey_responses['perceived_ease_of_use']
            if 'frustration_level' in survey_responses:
                participant.frustration_level = survey_responses['frustration_level']
            if 'confidence_in_results' in survey_responses:
                participant.confidence_in_results = survey_responses['confidence_in_results']

            # Mark session as completed
            participant.session_completed = True
            participant.session_completed_at = datetime.now(timezone.utc)
            participant.status = 'completed'

            self.db.commit()
            self.db.refresh(participant)
            logger.info(f"Recorded post-study survey for participant {participant.participant_code}")
        return participant

    # =========================================================================
    # Task Management
    # =========================================================================

    # NOTE: Study tasks are defined in the PostgreSQL function assign_6_experiment_tasks()
    # To update tasks, modify the function via: backend/database/seed_tasks.sql

    def assign_study_tasks_to_participant(self, experiment_id: str, participant_id: str) -> int:
        """
        Assign all predefined study tasks to a participant.
        Called automatically when a participant registers.
        Uses the SQL function assign_6_experiment_tasks which creates:
        - 1 tutorial task (Task 0)
        - 5 real tasks (Tasks 1-5)
        Returns the number of tasks assigned.
        """
        from sqlalchemy import text

        # Call the SQL function to create tasks
        result = self.db.execute(
            text("SELECT assign_6_experiment_tasks(:exp_id, :part_id)"),
            {"exp_id": experiment_id, "part_id": participant_id}
        )
        tasks_created = result.scalar()
        self.db.commit()

        logger.info(f"Assigned {tasks_created} tasks (1 tutorial + 5 real) to participant {participant_id}")
        return tasks_created

    def create_task(
        self,
        experiment_id: str,
        participant_id: str,
        task_id: str,
        task_number: int,
        task_description: str,
        task_type: Optional[str] = None,
        domain: Optional[str] = None,
        complexity_level: Optional[str] = None,
        expected_insights: Optional[List[str]] = None,
        success_criteria: Optional[Dict[str, Any]] = None
    ) -> ExperimentTask:
        """Create a new task for a participant"""
        task = ExperimentTask(
            experiment_id=experiment_id,
            participant_id=participant_id,
            task_id=task_id,
            task_number=task_number,
            task_description=task_description,
            task_type=task_type,
            domain=domain,
            complexity_level=complexity_level,
            expected_insights=expected_insights,
            success_criteria=success_criteria,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def get_task(self, task_db_id: str) -> Optional[ExperimentTask]:
        """Get task by database ID"""
        return self.db.query(ExperimentTask).filter(ExperimentTask.id == task_db_id).first()

    def get_participant_tasks(self, participant_id: str) -> List[ExperimentTask]:
        """Get all tasks for a participant"""
        return self.db.query(ExperimentTask).filter(
            ExperimentTask.participant_id == participant_id
        ).order_by(ExperimentTask.task_number).all()

    def start_task(self, task_db_id: str) -> Optional[ExperimentTask]:
        """
        Mark task as started. Idempotent: if task_started_at is already set,
        leave it alone. The frontend may auto-start a task on mount, and the
        same task page can be visited multiple times (back-button, second tab,
        navigation between tasks). Without this guard, every mount would reset
        task_started_at and corrupt task_duration_seconds.
        """
        task = self.get_task(task_db_id)
        if task and task.task_started_at is None:
            task.task_started_at = datetime.now(timezone.utc)

            participant = self.get_participant(task.participant_id)
            if participant and not participant.first_task_at:
                participant.first_task_at = datetime.now(timezone.utc)
                participant.tasks_attempted += 1

            self.db.commit()
            self.db.refresh(task)
            logger.info(f"Started task {task.task_id} for participant {task.participant_id}")
        return task

    def complete_task(
        self,
        task_db_id: str,
        submitted_answer: str,
        task_difficulty_rating: Optional[int] = None,
        confidence_in_answer: Optional[int] = None
    ) -> Optional[ExperimentTask]:
        """Mark task as completed with answer"""
        task = self.get_task(task_db_id)
        if task:
            now = datetime.now(timezone.utc)
            task.task_completed_at = now
            task.submitted_at = now
            task.submitted_answer = submitted_answer
            task.task_difficulty_rating = task_difficulty_rating
            task.confidence_in_answer = confidence_in_answer

            # Calculate duration
            if task.task_started_at:
                duration = (now - task.task_started_at).total_seconds()
                task.task_duration_seconds = int(duration)

            # Update participant
            participant = self.get_participant(task.participant_id)
            if participant:
                participant.tasks_completed += 1
                participant.last_task_at = now

            self.db.commit()
            self.db.refresh(task)
            logger.info(f"Completed task {task.task_id} with duration {task.task_duration_seconds}s")
        return task

    def score_task(
        self,
        task_db_id: str,
        completeness_score: float,
        accuracy_score: float,
        depth_score: float,
        task_successful: bool,
        partial_success: bool = False
    ) -> Optional[ExperimentTask]:
        """Score a completed task (usually done by researcher)"""
        task = self.get_task(task_db_id)
        if task:
            task.answer_completeness_score = completeness_score
            task.answer_accuracy_score = accuracy_score
            task.answer_depth_score = depth_score
            task.overall_answer_quality_score = (completeness_score + accuracy_score + depth_score) / 3
            task.task_successful = task_successful
            task.partial_success = partial_success
            self.db.commit()
            self.db.refresh(task)
            logger.info(f"Scored task {task.task_id}: {task.overall_answer_quality_score:.2f}")
        return task

    def abandon_task(
        self,
        task_db_id: str,
        reason: Optional[str] = None
    ) -> Optional[ExperimentTask]:
        """Mark task as abandoned"""
        task = self.get_task(task_db_id)
        if task:
            task.task_abandoned = True
            task.gave_up_on_task = True
            task.abandonment_reason = reason
            task.task_completed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(task)
            logger.info(f"Task {task.task_id} abandoned: {reason}")
        return task

    # =========================================================================
    # Interaction Tracking
    # =========================================================================

    def get_next_interaction_sequence(self, task_db_id: str) -> int:
        """Get the next interaction sequence number for a task"""
        result = self.db.query(func.max(ExperimentInteraction.interaction_sequence)).filter(
            ExperimentInteraction.task_id == task_db_id
        ).scalar()
        return (result or 0) + 1

    def log_interaction(
        self,
        experiment_id: str,
        participant_id: str,
        task_db_id: str,
        interaction_type: str,
        user_query: Optional[str] = None,
        system_response: Optional[Dict[str, Any]] = None,
        query_understood: Optional[bool] = None,
        query_successful: Optional[bool] = None,
        dashboard_action: Optional[str] = None,
        dashboard_element: Optional[str] = None,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[str] = None
    ) -> ExperimentInteraction:
        """Log a user interaction during task completion"""
        interaction = ExperimentInteraction(
            experiment_id=experiment_id,
            participant_id=participant_id,
            task_id=task_db_id,
            interaction_sequence=self.get_next_interaction_sequence(task_db_id),
            interaction_type=interaction_type,
            user_query=user_query,
            system_response=system_response,
            query_understood=query_understood,
            query_successful=query_successful,
            dashboard_action=dashboard_action,
            dashboard_element=dashboard_element,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )
        self.db.add(interaction)

        # Update task interaction counts
        task = self.get_task(task_db_id)
        if task:
            task.total_interactions += 1
            if interaction_type == 'chatbot_query':
                task.queries_executed += 1
                task.chatbot_query_count += 1
            elif interaction_type.startswith('dashboard_'):
                task.dashboard_interactions += 1

        self.db.commit()
        self.db.refresh(interaction)
        return interaction

    def get_active_task_for_participant(self, participant_id: str) -> Optional[ExperimentTask]:
        """
        Return the participant's currently-in-progress task, if any.

        An "active" task is the most recently started one whose
        task_started_at is set and task_completed_at is not. Used by the
        chatbot endpoint to attribute a query to the right task.
        """
        return self.db.query(ExperimentTask).filter(
            ExperimentTask.participant_id == participant_id,
            ExperimentTask.task_started_at.isnot(None),
            ExperimentTask.task_completed_at.is_(None),
        ).order_by(ExperimentTask.task_started_at.desc()).first()

    def log_chatbot_query(
        self,
        experiment_id: str,
        participant_id: str,
        task_db_id: str,
        user_query: str,
        system_response: Dict[str, Any],
        query_understood: bool = True,
        query_successful: bool = True,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[str] = None
    ) -> ExperimentInteraction:
        """Convenience method for logging chatbot interactions"""
        return self.log_interaction(
            experiment_id=experiment_id,
            participant_id=participant_id,
            task_db_id=task_db_id,
            interaction_type='chatbot_query',
            user_query=user_query,
            system_response=system_response,
            query_understood=query_understood,
            query_successful=query_successful,
            tokens_used=tokens_used,
            cost_usd=cost_usd,
        )

    def log_dashboard_interaction(
        self,
        experiment_id: str,
        participant_id: str,
        task_db_id: str,
        action: str,
        element: str
    ) -> ExperimentInteraction:
        """Convenience method for logging dashboard interactions"""
        return self.log_interaction(
            experiment_id=experiment_id,
            participant_id=participant_id,
            task_db_id=task_db_id,
            interaction_type=f'dashboard_{action}',
            dashboard_action=action,
            dashboard_element=element,
        )

    # =========================================================================
    # Analytics & Reporting
    # =========================================================================

    def get_experiment_stats(self, experiment_id: str) -> Dict[str, Any]:
        """Get summary statistics for an experiment"""
        experiment = self.get_experiment(experiment_id)
        if not experiment:
            return {}

        # Participant counts
        participants = self.db.query(ExperimentParticipant).filter(
            ExperimentParticipant.experiment_id == experiment_id
        ).all()

        control_participants = [p for p in participants if p.condition_assigned == 'control']
        experimental_participants = [p for p in participants if p.condition_assigned == 'experimental']

        # Task completion stats
        tasks = self.db.query(ExperimentTask).filter(
            ExperimentTask.experiment_id == experiment_id
        ).all()

        completed_tasks = [t for t in tasks if t.task_completed_at is not None]
        successful_tasks = [t for t in tasks if t.task_successful]

        # Calculate averages
        avg_duration_control = None
        avg_duration_experimental = None
        avg_quality_control = None
        avg_quality_experimental = None

        control_tasks = [t for t in completed_tasks if any(
            p.condition_assigned == 'control' for p in participants if p.id == t.participant_id
        )]
        experimental_tasks = [t for t in completed_tasks if any(
            p.condition_assigned == 'experimental' for p in participants if p.id == t.participant_id
        )]

        if control_tasks:
            durations = [t.task_duration_seconds for t in control_tasks if t.task_duration_seconds]
            qualities = [t.overall_answer_quality_score for t in control_tasks if t.overall_answer_quality_score]
            if durations:
                avg_duration_control = sum(durations) / len(durations)
            if qualities:
                avg_quality_control = sum(qualities) / len(qualities)

        if experimental_tasks:
            durations = [t.task_duration_seconds for t in experimental_tasks if t.task_duration_seconds]
            qualities = [t.overall_answer_quality_score for t in experimental_tasks if t.overall_answer_quality_score]
            if durations:
                avg_duration_experimental = sum(durations) / len(durations)
            if qualities:
                avg_quality_experimental = sum(qualities) / len(qualities)

        return {
            'experiment_id': experiment_id,
            'experiment_name': experiment.name,
            'status': experiment.status,
            'total_participants': len(participants),
            'control_participants': len(control_participants),
            'experimental_participants': len(experimental_participants),
            'completed_participants': len([p for p in participants if p.session_completed]),
            'total_tasks': len(tasks),
            'completed_tasks': len(completed_tasks),
            'successful_tasks': len(successful_tasks),
            'avg_duration_control_seconds': avg_duration_control,
            'avg_duration_experimental_seconds': avg_duration_experimental,
            'avg_quality_control': avg_quality_control,
            'avg_quality_experimental': avg_quality_experimental,
        }

    def get_participant_summary(self, participant_id: str) -> Dict[str, Any]:
        """Get summary for a specific participant"""
        participant = self.get_participant(participant_id)
        if not participant:
            return {}

        tasks = self.get_participant_tasks(participant_id)
        completed_tasks = [t for t in tasks if t.task_completed_at is not None]

        # Calculate total session duration
        if participant.first_task_at and participant.last_task_at:
            duration = (participant.last_task_at - participant.first_task_at).total_seconds() / 60
        else:
            duration = None

        return {
            'participant_id': participant_id,
            'participant_code': participant.participant_code,
            'condition': participant.condition_assigned,
            'status': participant.status,
            'tasks_completed': len(completed_tasks),
            'tasks_total': len(tasks),
            'session_duration_minutes': duration,
            'avg_task_duration_seconds': (
                sum(t.task_duration_seconds for t in completed_tasks if t.task_duration_seconds) /
                len(completed_tasks) if completed_tasks else None
            ),
            'avg_answer_quality': (
                sum(t.overall_answer_quality_score for t in completed_tasks if t.overall_answer_quality_score) /
                len([t for t in completed_tasks if t.overall_answer_quality_score]) if any(t.overall_answer_quality_score for t in completed_tasks) else None
            ),
        }

    # =========================================================================
    # Admin Analytics Methods
    # =========================================================================

    def get_all_participants_summary(self) -> List[Dict[str, Any]]:
        """Get summary information for all participants (admin only)"""
        participants = self.db.query(ExperimentParticipant).all()

        summaries = []
        for participant in participants:
            tasks = self.get_participant_tasks(participant.id)
            completed_tasks = [t for t in tasks if t.task_completed_at is not None]

            # Calculate session duration
            if participant.first_task_at and participant.last_task_at:
                duration = (participant.last_task_at - participant.first_task_at).total_seconds() / 60
            else:
                duration = None

            # Calculate avg task duration
            if completed_tasks:
                durations = [t.task_duration_seconds for t in completed_tasks if t.task_duration_seconds]
                avg_task_duration = sum(durations) / len(durations) if durations else None
            else:
                avg_task_duration = None

            # Last activity timestamp
            last_activity = None
            if participant.last_task_at:
                last_activity = participant.last_task_at.isoformat()
            elif participant.first_task_at:
                last_activity = participant.first_task_at.isoformat()

            summaries.append({
                'id': participant.id,
                'participant_code': participant.participant_code,
                'condition_assigned': participant.condition_assigned,
                'status': participant.status,
                'tasks_completed': len(completed_tasks),
                'tasks_total': len(tasks),
                'session_duration_minutes': duration,
                'avg_task_duration_seconds': avg_task_duration,
                'last_activity': last_activity,
                'recruitment_source': participant.recruitment_source,
                'prolific_pid': participant.prolific_pid,
            })

        return summaries

    def get_participant_detail_for_admin(self, participant_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed participant information for admin dashboard"""
        participant = self.get_participant(participant_id)
        if not participant:
            return None

        tasks = self.get_participant_tasks(participant_id)
        completed_tasks = [t for t in tasks if t.task_completed_at is not None]

        # Calculate session duration
        if participant.first_task_at and participant.last_task_at:
            duration = (participant.last_task_at - participant.first_task_at).total_seconds() / 60
        else:
            duration = None

        # Calculate avg task duration
        if completed_tasks:
            durations = [t.task_duration_seconds for t in completed_tasks if t.task_duration_seconds]
            avg_task_duration = sum(durations) / len(durations) if durations else None
        else:
            avg_task_duration = None

        # Last activity timestamp
        last_activity = None
        if participant.last_task_at:
            last_activity = participant.last_task_at.isoformat()
        elif participant.first_task_at:
            last_activity = participant.first_task_at.isoformat()

        return {
            'id': participant.id,
            'participant_code': participant.participant_code,
            'condition_assigned': participant.condition_assigned,
            'status': participant.status,
            'tasks_completed': len(completed_tasks),
            'tasks_total': len(tasks),
            'session_duration_minutes': duration,
            'avg_task_duration_seconds': avg_task_duration,
            'last_activity': last_activity,
            # Pre-survey data
            'age': participant.age,
            'age_range': participant.age_range,
            'occupation_statuses': participant.occupation_statuses,
            'occupation_status': participant.occupation_status,
            'field_of_work': participant.field_of_work,
            'field_of_study': participant.field_of_study,
            'visual_analytics_frequency': participant.visual_analytics_frequency,
            'business_background': participant.business_background,
            'llm_chatbot_experience': participant.llm_chatbot_experience,
            'bi_tools_experience': participant.bi_tools_experience,
            # Timestamps
            'registered_at': participant.registered_at.isoformat() if participant.registered_at else None,
            'first_task_at': participant.first_task_at.isoformat() if participant.first_task_at else None,
            'last_task_at': participant.last_task_at.isoformat() if participant.last_task_at else None,
            # Admin audit trail + withdrawal / exclusion surface
            'exclusion_reason': participant.exclusion_reason,
            'admin_notes': participant.admin_notes,
            'withdrawal_requested': participant.withdrawal_requested,
            'withdrawal_timestamp': participant.withdrawal_timestamp.isoformat() if participant.withdrawal_timestamp else None,
            # Recruitment
            'recruitment_source': participant.recruitment_source,
            'prolific_pid': participant.prolific_pid,
        }

    def get_participant_interactions(
        self,
        participant_id: str,
        task_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get paginated interaction logs for a participant"""
        from sqlalchemy import and_

        # Build query
        query = self.db.query(ExperimentInteraction).filter(
            ExperimentInteraction.participant_id == participant_id
        )

        # Filter by task if specified
        if task_id:
            query = query.filter(ExperimentInteraction.task_id == task_id)

        # Get total count
        total = query.count()

        # Get paginated results
        interactions = query.order_by(
            ExperimentInteraction.interaction_timestamp.desc()
        ).limit(limit).offset(offset).all()

        # Format results
        results = []
        for interaction in interactions:
            # Get task info
            task = self.get_task(interaction.task_id)

            results.append({
                'id': interaction.id,
                'interaction_sequence': interaction.interaction_sequence,
                'interaction_timestamp': interaction.interaction_timestamp.isoformat(),
                'interaction_type': interaction.interaction_type,
                'task_id': interaction.task_id,
                'task_number': task.task_number if task else None,
                'query_text': interaction.user_query,
                'dashboard_action': interaction.dashboard_action,
                'dashboard_element': interaction.dashboard_element,
                'tokens_used': interaction.tokens_used,
                'cost_usd': interaction.cost_usd,
            })

        return {
            'interactions': results,
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    def get_participant_timeline(self, participant_id: str) -> List[Dict[str, Any]]:
        """Get chronological timeline of participant activity"""
        tasks = self.get_participant_tasks(participant_id)
        interactions = self.db.query(ExperimentInteraction).filter(
            ExperimentInteraction.participant_id == participant_id
        ).order_by(ExperimentInteraction.interaction_timestamp).all()

        timeline = []

        # Add task start events
        for task in tasks:
            if task.task_started_at:
                timeline.append({
                    'timestamp': task.task_started_at.isoformat(),
                    'event_type': 'task_started',
                    'task_number': task.task_number,
                    'details': {
                        'task_id': task.task_id,
                        'task_description': task.task_description[:100] + '...' if len(task.task_description) > 100 else task.task_description,
                    }
                })

        # Add task completion events
        for task in tasks:
            if task.task_completed_at:
                timeline.append({
                    'timestamp': task.task_completed_at.isoformat(),
                    'event_type': 'task_completed',
                    'task_number': task.task_number,
                    'details': {
                        'task_id': task.task_id,
                        'duration_seconds': task.task_duration_seconds,
                        'answer_submitted': bool(task.submitted_answer),
                    }
                })

        # Add interaction events (sample every 5th to avoid clutter)
        for i, interaction in enumerate(interactions):
            if i % 5 == 0 or interaction.interaction_type == 'chatbot_query':
                task = self.get_task(interaction.task_id)
                timeline.append({
                    'timestamp': interaction.interaction_timestamp.isoformat(),
                    'event_type': 'interaction',
                    'task_number': task.task_number if task else None,
                    'details': {
                        'interaction_type': interaction.interaction_type,
                        'query_text': interaction.user_query[:50] + '...' if interaction.user_query and len(interaction.user_query) > 50 else interaction.user_query,
                        'dashboard_element': interaction.dashboard_element,
                    }
                })

        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x['timestamp'])

        return timeline

    def get_participant_analytics(self, participant_id: str) -> Dict[str, Any]:
        """Get aggregated analytics for visualization"""
        tasks = self.get_participant_tasks(participant_id)
        interactions = self.db.query(ExperimentInteraction).filter(
            ExperimentInteraction.participant_id == participant_id
        ).all()

        # 1. Interactions by type
        interaction_types = {}
        for interaction in interactions:
            itype = interaction.interaction_type
            interaction_types[itype] = interaction_types.get(itype, 0) + 1

        interactions_by_type = [
            {'type': itype, 'count': count}
            for itype, count in interaction_types.items()
        ]

        # 2. Interactions over time (group by 5-minute intervals)
        from collections import defaultdict
        time_buckets = defaultdict(int)

        for interaction in interactions:
            # Round to 5-minute intervals
            timestamp = interaction.interaction_timestamp
            bucket = timestamp.replace(second=0, microsecond=0)
            minute = (bucket.minute // 5) * 5
            bucket = bucket.replace(minute=minute)
            time_buckets[bucket.isoformat()] += 1

        interactions_over_time = [
            {'timestamp': ts, 'count': count}
            for ts, count in sorted(time_buckets.items())
        ]

        # 3. Dashboard elements clicked
        dashboard_clicks = {}
        for interaction in interactions:
            if interaction.dashboard_element:
                elem = interaction.dashboard_element
                dashboard_clicks[elem] = dashboard_clicks.get(elem, 0) + 1

        dashboard_elements_clicked = [
            {'element': elem, 'count': count}
            for elem, count in sorted(dashboard_clicks.items(), key=lambda x: -x[1])
        ]

        # 4. Task durations
        task_durations = []
        for task in tasks:
            if task.task_duration_seconds:
                task_durations.append({
                    'task_number': task.task_number,
                    'duration_seconds': task.task_duration_seconds,
                })

        return {
            'interactions_by_type': interactions_by_type,
            'interactions_over_time': interactions_over_time,
            'dashboard_elements_clicked': dashboard_elements_clicked,
            'task_durations': task_durations,
        }

    # =========================================================================
    # Study-Wide Analytics (Admin Dashboard Tabs)
    # =========================================================================

    def get_study_overview(self) -> Dict[str, Any]:
        """Get study-wide overview: enrollment timeline, completion funnel.

        Excludes participants with status in ANALYSIS_EXCLUDED_STATUSES.
        """
        participants = self._analysis_participants()
        eligible_ids = {p.id for p in participants}
        tasks = [t for t in self.db.query(ExperimentTask).all() if t.participant_id in eligible_ids]

        control = [p for p in participants if p.condition_assigned == 'control']
        experimental = [p for p in participants if p.condition_assigned == 'experimental']
        surveyed = [p for p in participants if p.post_study_survey_responses]

        # Group tasks by participant
        tasks_by_participant = defaultdict(list)
        started_ids = set()
        for t in tasks:
            tasks_by_participant[t.participant_id].append(t)
            if t.task_started_at:
                started_ids.add(t.participant_id)

        # "Completed" = all tasks for this participant are done
        completed = []
        for p in participants:
            p_tasks = tasks_by_participant.get(p.id, [])
            if p_tasks and all(t.task_completed_at is not None for t in p_tasks):
                completed.append(p)

        # Avg session duration
        durations = [p.total_session_duration_minutes for p in participants if p.total_session_duration_minutes]
        avg_session = sum(durations) / len(durations) if durations else None

        # Enrollment over time (by date)
        enrollment_map = defaultdict(lambda: {'control': 0, 'experimental': 0})
        for p in participants:
            date_key = (p.registered_at or p.recruited_at)
            if date_key:
                d = date_key.strftime('%Y-%m-%d')
                enrollment_map[d][p.condition_assigned] += 1

        cumulative = 0
        enrollment_over_time = []
        for d in sorted(enrollment_map.keys()):
            day = enrollment_map[d]
            cumulative += day['control'] + day['experimental']
            enrollment_over_time.append({
                'date': d,
                'control': day['control'],
                'experimental': day['experimental'],
                'cumulative': cumulative,
            })

        # Completion funnel
        completion_funnel = [
            {'stage': 'Registered', 'count': len(participants)},
            {'stage': 'Started Tasks', 'count': len(started_ids)},
            {'stage': 'Completed All Tasks', 'count': len(completed)},
            {'stage': 'Completed Survey', 'count': len(surveyed)},
        ]

        return {
            'total_participants': len(participants),
            'control_count': len(control),
            'experimental_count': len(experimental),
            'completed_count': len(completed),
            'survey_completed_count': len(surveyed),
            'avg_session_duration_minutes': round(avg_session, 1) if avg_session else None,
            'completion_rate_percent': round(len(completed) / len(participants) * 100, 1) if participants else 0,
            'enrollment_over_time': enrollment_over_time,
            'completion_funnel': completion_funnel,
        }

    def get_task_comparison(self) -> Dict[str, Any]:
        """Get per-task control vs experimental comparison.

        Excludes participants with status in ANALYSIS_EXCLUDED_STATUSES
        (tasks from those participants are dropped because their condition
        won't be in participant_condition).
        """
        participants = self._analysis_participants()
        participant_condition = {p.id: p.condition_assigned for p in participants}

        tasks = self.db.query(ExperimentTask).filter(
            ExperimentTask.task_completed_at.isnot(None)
        ).all()

        # Group tasks by task_number and condition
        task_groups = defaultdict(lambda: {'control': [], 'experimental': []})
        for t in tasks:
            cond = participant_condition.get(t.participant_id)
            if cond:
                task_groups[t.task_number][cond].append(t)

        def avg(vals):
            filtered = [v for v in vals if v is not None]
            return round(sum(filtered) / len(filtered), 2) if filtered else None

        result_tasks = []
        all_control_durations = []
        all_exp_durations = []
        all_control_quality = []
        all_exp_quality = []

        for task_num in sorted(task_groups.keys()):
            group = task_groups[task_num]
            ct = group['control']
            et = group['experimental']

            # Get domain/complexity from first task
            sample = ct[0] if ct else (et[0] if et else None)
            domain = sample.domain if sample else None
            complexity = sample.complexity_level if sample else None

            c_durations = [t.task_duration_seconds for t in ct if t.task_duration_seconds]
            e_durations = [t.task_duration_seconds for t in et if t.task_duration_seconds]
            all_control_durations.extend(c_durations)
            all_exp_durations.extend(e_durations)

            c_quality = [t.overall_answer_quality_score for t in ct if t.overall_answer_quality_score]
            e_quality = [t.overall_answer_quality_score for t in et if t.overall_answer_quality_score]
            all_control_quality.extend(c_quality)
            all_exp_quality.extend(e_quality)

            result_tasks.append({
                'task_number': task_num,
                'domain': domain,
                'complexity_level': complexity,
                'control': {
                    'avg_duration': avg(c_durations),
                    'avg_difficulty': avg([t.task_difficulty_rating for t in ct]),
                    'avg_confidence': avg([t.confidence_in_answer for t in ct]),
                    'avg_interactions': avg([t.total_interactions for t in ct]),
                    'avg_quality': avg(c_quality),
                    'completion_count': len(ct),
                },
                'experimental': {
                    'avg_duration': avg(e_durations),
                    'avg_difficulty': avg([t.task_difficulty_rating for t in et]),
                    'avg_confidence': avg([t.confidence_in_answer for t in et]),
                    'avg_interactions': avg([t.total_interactions for t in et]),
                    'avg_quality': avg(e_quality),
                    'avg_chatbot_queries': avg([t.chatbot_query_count for t in et]),
                    'completion_count': len(et),
                },
            })

        return {
            'tasks': result_tasks,
            'overall': {
                'control_avg_duration': avg(all_control_durations),
                'experimental_avg_duration': avg(all_exp_durations),
                'control_avg_quality': avg(all_control_quality),
                'experimental_avg_quality': avg(all_exp_quality),
            },
        }

    def get_survey_analytics(self) -> Dict[str, Any]:
        """Get pre-survey demographics + post-survey Likert ratings by condition.

        Excludes participants with status in ANALYSIS_EXCLUDED_STATUSES.
        """
        participants = self._analysis_participants()
        control = [p for p in participants if p.condition_assigned == 'control']
        experimental = [p for p in participants if p.condition_assigned == 'experimental']

        # Pre-survey: count distribution of each field by condition
        # Simple fields (single value per participant)
        simple_pre_fields = [
            ('age', 'age'),
            ('visual_analytics_frequency', 'visual_analytics_frequency'),
            ('business_background', 'business_background'),
            ('llm_chatbot_experience', 'llm_chatbot_experience'),
            ('bi_tools_experience', 'bi_tools_experience'),
        ]
        # Multi-select field (comma-separated)
        multi_pre_fields = [
            ('occupation_statuses', 'occupation_statuses'),
        ]
        # Conditional fields
        conditional_pre_fields = [
            ('field_of_work', 'field_of_work'),
            ('field_of_study', 'field_of_study'),
        ]

        pre_survey = {}
        for field_name, attr in simple_pre_fields:
            values = set()
            for p in participants:
                v = getattr(p, attr)
                if v is not None:
                    values.add(str(v))
            distribution = []
            for v in sorted(values):
                c_count = sum(1 for p in control if str(getattr(p, attr, '')) == v)
                e_count = sum(1 for p in experimental if str(getattr(p, attr, '')) == v)
                distribution.append({'value': v, 'control': c_count, 'experimental': e_count})
            pre_survey[field_name] = distribution

        for field_name, attr in multi_pre_fields:
            values = set()
            for p in participants:
                v = getattr(p, attr)
                if v:
                    for item in v.split(','):
                        item = item.strip()
                        if item:
                            values.add(item)
            distribution = []
            for v in sorted(values):
                c_count = sum(1 for p in control if getattr(p, attr) and v in [x.strip() for x in getattr(p, attr).split(',')])
                e_count = sum(1 for p in experimental if getattr(p, attr) and v in [x.strip() for x in getattr(p, attr).split(',')])
                distribution.append({'value': v, 'control': c_count, 'experimental': e_count})
            pre_survey[field_name] = distribution

        for field_name, attr in conditional_pre_fields:
            values = set()
            for p in participants:
                v = getattr(p, attr)
                if v:
                    values.add(v)
            distribution = []
            for v in sorted(values):
                c_count = sum(1 for p in control if getattr(p, attr) == v)
                e_count = sum(1 for p in experimental if getattr(p, attr) == v)
                distribution.append({'value': v, 'control': c_count, 'experimental': e_count})
            pre_survey[field_name] = distribution

        # Post-survey Section A: Dashboard Experience (both groups)
        # PU (A1-A4), PEOU (A5-A8), Satisfaction (A9-A10)
        common_fields = [
            'dashboard_usefulness',
            'dashboard_performance',
            'dashboard_effectiveness',
            'dashboard_productivity',
            'dashboard_clear_understandable',
            'dashboard_easy_to_use',
            'dashboard_easy_to_control',
            'dashboard_low_mental_effort',
            'dashboard_satisfaction',
            'dashboard_frustration',
        ]

        def likert_stats(participants_list, field):
            vals = []
            for p in participants_list:
                survey = p.post_study_survey_responses or {}
                v = survey.get(field)
                if v is not None:
                    vals.append(v)
            if not vals:
                return {'avg': None, 'distribution': [0, 0, 0, 0, 0]}
            avg_val = round(sum(vals) / len(vals), 2)
            dist = [vals.count(i) for i in range(1, 6)]
            return {'avg': avg_val, 'distribution': dist}

        common = {}
        for field in common_fields:
            c_stats = likert_stats(control, field)
            e_stats = likert_stats(experimental, field)
            common[field] = {
                'control_avg': c_stats['avg'],
                'experimental_avg': e_stats['avg'],
                'control_dist': c_stats['distribution'],
                'experimental_dist': e_stats['distribution'],
            }

        # Post-survey Section B: AI Chatbot Experience (experimental only)
        # Part 1: Helpfulness (B1-B4), Part 2: Accuracy/Trust (B5-B8), Part 3: Intention (B9-B11)
        exp_fields = [
            'chatbot_helpfulness',
            'chatbot_easy_to_understand',
            'chatbot_suitability',
            'chatbot_visualization_quality',
            'chatbot_accuracy',
            'chatbot_correct_answers',
            'chatbot_reliance',
            'chatbot_verification',
            'chatbot_future_use',
            'chatbot_recommend',
            'chatbot_satisfaction',
        ]
        experimental_only = {}
        for field in exp_fields:
            stats = likert_stats(experimental, field)
            experimental_only[field] = stats

        # Open feedback (C1 for all, C2/C3 for experimental)
        open_feedback = []
        for p in participants:
            survey = p.post_study_survey_responses or {}
            fb = survey.get('open_feedback')
            if fb and fb.strip():
                open_feedback.append({
                    'participant_code': p.participant_code,
                    'condition': p.condition_assigned,
                    'type': 'general',
                    'feedback': fb,
                })
            liked = survey.get('chatbot_liked')
            if liked and liked.strip():
                open_feedback.append({
                    'participant_code': p.participant_code,
                    'condition': p.condition_assigned,
                    'type': 'chatbot_liked',
                    'feedback': liked,
                })
            improvements = survey.get('chatbot_improvements')
            if improvements and improvements.strip():
                open_feedback.append({
                    'participant_code': p.participant_code,
                    'condition': p.condition_assigned,
                    'type': 'chatbot_improvements',
                    'feedback': improvements,
                })

        return {
            'pre_survey': pre_survey,
            'post_survey': {
                'common': common,
                'experimental_only': experimental_only,
                'open_feedback': open_feedback,
            },
        }

    def get_chatbot_analytics(self) -> Dict[str, Any]:
        """Get NL2SQL usage stats from query_history (experimental group only).

        Excludes queries from participants with status in ANALYSIS_EXCLUDED_STATUSES
        and queries that have no participant_id (e.g. admin test queries).
        """
        eligible_ids = {p.id for p in self._analysis_participants()}
        if eligible_ids:
            queries = self.db.query(QueryHistory).filter(
                QueryHistory.participant_id.in_(eligible_ids)
            ).all()
        else:
            queries = []

        if not queries:
            return {
                'total_queries': 0,
                'success_rate_percent': 0,
                'avg_execution_time_ms': None,
                'total_tokens': 0,
                'total_cost_usd': 0.0,
                'avg_queries_per_participant': 0,
                'domain_breakdown': [],
                'queries_over_time': [],
                'token_usage_by_participant': [],
                'error_stages': [],
            }

        total = len(queries)
        successful = sum(1 for q in queries if q.execution_status == 'success')
        exec_times = [q.execution_time_ms for q in queries if q.execution_time_ms]
        total_tokens = sum(q.total_tokens or 0 for q in queries)
        total_cost = sum(float(q.total_cost_usd or 0) for q in queries)

        # Unique participants
        participant_ids = set(q.participant_id for q in queries if q.participant_id)

        # Domain breakdown
        domain_counts = defaultdict(int)
        for q in queries:
            domain_counts[q.domain or 'unknown'] += 1

        # Queries over time (by date)
        date_counts = defaultdict(int)
        for q in queries:
            d = q.created_at.strftime('%Y-%m-%d')
            date_counts[d] += 1

        # Token usage by participant
        participant_tokens = defaultdict(lambda: {'total_tokens': 0, 'total_cost': 0.0, 'query_count': 0})
        for q in queries:
            pid = q.participant_id
            if pid:
                participant_tokens[pid]['total_tokens'] += q.total_tokens or 0
                participant_tokens[pid]['total_cost'] += float(q.total_cost_usd or 0)
                participant_tokens[pid]['query_count'] += 1

        # Resolve participant codes
        participant_map = {}
        if participant_ids:
            parts = self.db.query(ExperimentParticipant).filter(
                ExperimentParticipant.id.in_(participant_ids)
            ).all()
            participant_map = {p.id: p.participant_code for p in parts}

        token_by_participant = []
        for pid, data in participant_tokens.items():
            token_by_participant.append({
                'participant_code': participant_map.get(pid, pid),
                'total_tokens': data['total_tokens'],
                'total_cost': round(data['total_cost'], 4),
                'query_count': data['query_count'],
            })
        token_by_participant.sort(key=lambda x: -x['total_tokens'])

        # Error stages
        error_counts = defaultdict(int)
        for q in queries:
            if q.error_occurred and q.error_stage:
                error_counts[q.error_stage] += 1

        return {
            'total_queries': total,
            'success_rate_percent': round(successful / total * 100, 1) if total else 0,
            'avg_execution_time_ms': round(sum(exec_times) / len(exec_times)) if exec_times else None,
            'total_tokens': total_tokens,
            'total_cost_usd': round(total_cost, 4),
            'avg_queries_per_participant': round(total / len(participant_ids), 1) if participant_ids else 0,
            'domain_breakdown': [{'domain': d, 'count': c} for d, c in sorted(domain_counts.items(), key=lambda x: -x[1])],
            'queries_over_time': [{'date': d, 'count': c} for d, c in sorted(date_counts.items())],
            'token_usage_by_participant': token_by_participant,
            'error_stages': [{'stage': s, 'count': c} for s, c in sorted(error_counts.items(), key=lambda x: -x[1])],
        }

    def get_export_data(self, tables: Optional[List[str]] = None) -> Dict[str, Any]:
        """Get raw data dump for thesis analysis"""
        if not tables:
            tables = ['participants', 'tasks', 'interactions', 'queries']

        result = {'exported_at': datetime.now(timezone.utc).isoformat()}

        if 'participants' in tables:
            participants = self.db.query(ExperimentParticipant).all()
            result['participants'] = [{
                'id': p.id,
                'participant_code': p.participant_code,
                'condition_assigned': p.condition_assigned,
                'status': p.status,
                'registered_at': p.registered_at.isoformat() if p.registered_at else None,
                'age_range': p.age_range,
                'occupation_status': p.occupation_status,
                'field_of_work': p.field_of_work,
                'visual_analytics_frequency': p.visual_analytics_frequency,
                'business_background': p.business_background,
                'llm_chatbot_experience': p.llm_chatbot_experience,
                'bi_tools_experience': p.bi_tools_experience,
                'consent_given': p.consent_given,
                'tasks_completed': p.tasks_completed,
                'tasks_attempted': p.tasks_attempted,
                'session_completed': p.session_completed,
                'session_completed_at': p.session_completed_at.isoformat() if p.session_completed_at else None,
                'total_session_duration_minutes': p.total_session_duration_minutes,
                'first_task_at': p.first_task_at.isoformat() if p.first_task_at else None,
                'last_task_at': p.last_task_at.isoformat() if p.last_task_at else None,
                'post_study_survey_responses': p.post_study_survey_responses,
            } for p in participants]

        if 'tasks' in tables:
            tasks = self.db.query(ExperimentTask).all()
            result['tasks'] = [{
                'id': t.id,
                'participant_id': t.participant_id,
                'task_number': t.task_number,
                'task_id': t.task_id,
                'domain': t.domain,
                'complexity_level': t.complexity_level,
                'task_started_at': t.task_started_at.isoformat() if t.task_started_at else None,
                'task_completed_at': t.task_completed_at.isoformat() if t.task_completed_at else None,
                'task_duration_seconds': t.task_duration_seconds,
                'submitted_answer': t.submitted_answer,
                'task_difficulty_rating': t.task_difficulty_rating,
                'confidence_in_answer': t.confidence_in_answer,
                'overall_answer_quality_score': t.overall_answer_quality_score,
                'total_interactions': t.total_interactions,
                'chatbot_query_count': t.chatbot_query_count,
                'dashboard_interactions': t.dashboard_interactions,
                'task_successful': t.task_successful,
                'task_abandoned': t.task_abandoned,
            } for t in tasks]

        if 'interactions' in tables:
            interactions = self.db.query(ExperimentInteraction).all()
            result['interactions'] = [{
                'id': i.id,
                'participant_id': i.participant_id,
                'task_id': i.task_id,
                'interaction_sequence': i.interaction_sequence,
                'interaction_timestamp': i.interaction_timestamp.isoformat() if i.interaction_timestamp else None,
                'interaction_type': i.interaction_type,
                'user_query': i.user_query,
                'dashboard_action': i.dashboard_action,
                'dashboard_element': i.dashboard_element,
                'tokens_used': i.tokens_used,
                'cost_usd': i.cost_usd,
            } for i in interactions]

        if 'queries' in tables:
            queries = self.db.query(QueryHistory).all()
            result['query_history'] = [{
                'id': q.id,
                'user_id': q.user_id,
                'participant_id': q.participant_id,
                'user_query': q.user_query,
                'domain': q.domain,
                'generated_sql': q.generated_sql,
                'execution_status': q.execution_status,
                'execution_time_ms': q.execution_time_ms,
                'row_count': q.row_count,
                'total_tokens': q.total_tokens,
                'total_cost_usd': q.total_cost_usd,
                'error_occurred': q.error_occurred,
                'error_stage': q.error_stage,
                'chart_type': q.chart_type,
                'created_at': q.created_at.isoformat() if q.created_at else None,
            } for q in queries]

        return result


# Export
__all__ = ["ExperimentService"]
