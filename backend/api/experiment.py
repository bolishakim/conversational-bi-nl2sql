"""
Experiment API Endpoints
Handles experiment management, participant enrollment, and task tracking
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as DBSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings
from database.models import User, ROLE_ADMIN
from services.experiment_service import ExperimentService
from api.auth import get_current_user, get_db


# Create router
router = APIRouter(prefix="/api/v1/experiment", tags=["experiment"])

# Security scheme
security = HTTPBearer()


# ============================================================================
# Pydantic Models
# ============================================================================

class CreateExperimentRequest(BaseModel):
    """Request to create a new experiment"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    research_question: Optional[str] = None
    hypothesis: Optional[str] = None
    target_participants_per_group: int = Field(default=15, ge=1)
    total_tasks: Optional[int] = None
    task_definitions: Optional[List[Dict[str, Any]]] = None


class ExperimentResponse(BaseModel):
    """Experiment response model"""
    id: str
    name: str
    description: Optional[str]
    status: str
    control_participants: int
    experimental_participants: int
    total_tasks: Optional[int]
    created_at: str


class EnrollParticipantRequest(BaseModel):
    """Request to enroll a participant in an experiment"""
    experiment_id: str
    demographics: Optional[Dict[str, Any]] = None
    assignment_method: str = Field(default='random')


class ParticipantResponse(BaseModel):
    """Participant response model"""
    id: str
    participant_code: str
    condition_assigned: str
    status: str
    consent_given: bool
    tasks_completed: int
    tasks_attempted: int


class RecordConsentRequest(BaseModel):
    """Request to record participant consent"""
    participant_id: str


class StartTaskRequest(BaseModel):
    """Request to start a task"""
    task_db_id: str


class CompleteTaskRequest(BaseModel):
    """Request to complete a task"""
    task_db_id: str
    submitted_answer: str
    task_difficulty_rating: Optional[int] = Field(None, ge=1, le=5)
    confidence_in_answer: Optional[int] = Field(None, ge=1, le=5)


class AbandonTaskRequest(BaseModel):
    """Request to abandon a task"""
    task_db_id: str
    reason: Optional[str] = None


class LogInteractionRequest(BaseModel):
    """Request to log an interaction"""
    task_db_id: str
    interaction_type: str
    user_query: Optional[str] = None
    system_response: Optional[Dict[str, Any]] = None
    query_understood: Optional[bool] = None
    query_successful: Optional[bool] = None
    dashboard_action: Optional[str] = None
    dashboard_element: Optional[str] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[str] = None


class SubmitSurveyRequest(BaseModel):
    """Request to submit post-study survey"""
    participant_id: str
    survey_responses: Dict[str, Any]


class RegisterParticipantRequest(BaseModel):
    """
    Request to register a new participant with pre-survey data.

    NOTE: No personally identifiable information (PII) is collected.
    Only anonymous demographic data from the 7-question pre-survey.
    """
    experiment_id: str

    # Pre-Survey Questions (all required unless noted)
    age: int = Field(..., ge=18, le=99, description="Exact age in years (18-99)")
    occupation_statuses: list[str] = Field(..., description="Multi-select: student, employee, self_employed, other")
    field_of_work: Optional[str] = Field(None, description="Required if non-student occupation selected")
    field_of_study: Optional[str] = Field(None, description="Required if student selected")
    visual_analytics_frequency: str = Field(..., description="never, rarely, occasionally, regularly, daily")
    business_background: str = Field(..., description="education, experience, both, none")
    llm_chatbot_experience: str = Field(..., description="never, once_twice, occasionally, regularly")
    bi_tools_experience: str = Field(..., description="none, minimal, basic, intermediate, advanced")

    # Consent (must be True to proceed)
    consent_given: bool = Field(..., description="Must be True to proceed")

    # Prolific identifiers (optional; set when arriving via Prolific URL)
    prolific_pid: Optional[str] = Field(None, description="Prolific participant id, from URL")
    prolific_study_id: Optional[str] = Field(None, description="Prolific study id, from URL")
    prolific_session_id: Optional[str] = Field(None, description="Prolific session id, from URL")
    # Condition forced by Prolific study URL (?condition=control|experimental).
    # Honored only when prolific_pid is also present; ignored otherwise.
    prolific_condition: Optional[str] = Field(None, description="'control' or 'experimental', from URL")


class LookupReturningParticipantRequest(BaseModel):
    """
    Request to find a returning participant.

    NOTE: Since we don't collect personal info, returning participants
    can only be looked up by their participant code.
    """
    participant_code: str = Field(..., description="The participant's unique code (e.g., P001)")


class TaskResponse(BaseModel):
    """Task response model"""
    id: str
    task_id: str
    task_number: int
    task_description: str
    task_type: Optional[str]
    domain: Optional[str]
    complexity_level: Optional[str]
    task_started_at: Optional[str]
    task_completed_at: Optional[str]
    task_duration_seconds: Optional[int]
    submitted_answer: Optional[str]
    # Tutorial fields
    is_tutorial: Optional[bool]
    tutorial_steps: Optional[str]
    tutorial_tips: Optional[str]


# ============================================================================
# Helper Functions
# ============================================================================

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Dependency that requires admin access"""
    if not current_user.can_access_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def get_experiment_service(db: DBSession = Depends(get_db)) -> ExperimentService:
    """Get experiment service instance"""
    return ExperimentService(db)


# ============================================================================
# Experiment Management Endpoints (Admin Only)
# ============================================================================

@router.post("/experiments", response_model=ExperimentResponse)
async def create_experiment(
    request: CreateExperimentRequest,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Create a new experiment (admin only)"""
    experiment = service.create_experiment(
        name=request.name,
        description=request.description,
        research_question=request.research_question,
        hypothesis=request.hypothesis,
        created_by_id=current_user.id,
        target_participants_per_group=request.target_participants_per_group,
        total_tasks=request.total_tasks,
        task_definitions=request.task_definitions,
    )
    return {
        "id": experiment.id,
        "name": experiment.name,
        "description": experiment.description,
        "status": experiment.status,
        "control_participants": experiment.actual_control_participants,
        "experimental_participants": experiment.actual_experimental_participants,
        "total_tasks": experiment.total_tasks,
        "created_at": experiment.created_at.isoformat(),
    }


@router.get("/experiments")
async def list_experiments(
    status: Optional[str] = None,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """List all experiments (admin only)"""
    experiments = service.list_experiments(status=status)
    return [
        {
            "id": e.id,
            "name": e.name,
            "description": e.description,
            "status": e.status,
            "control_participants": e.actual_control_participants,
            "experimental_participants": e.actual_experimental_participants,
            "total_tasks": e.total_tasks,
            "created_at": e.created_at.isoformat(),
        }
        for e in experiments
    ]


@router.get("/experiments/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Get experiment details (admin only)"""
    experiment = service.get_experiment(experiment_id)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {
        "id": experiment.id,
        "name": experiment.name,
        "description": experiment.description,
        "research_question": experiment.research_question,
        "hypothesis": experiment.hypothesis,
        "status": experiment.status,
        "control_participants": experiment.actual_control_participants,
        "experimental_participants": experiment.actual_experimental_participants,
        "target_participants_per_group": experiment.target_participants_per_group,
        "total_tasks": experiment.total_tasks,
        "task_definitions": experiment.task_definitions,
        "created_at": experiment.created_at.isoformat(),
        "actual_start_date": experiment.actual_start_date.isoformat() if experiment.actual_start_date else None,
        "actual_end_date": experiment.actual_end_date.isoformat() if experiment.actual_end_date else None,
    }


@router.patch("/experiments/{experiment_id}/status")
async def update_experiment_status(
    experiment_id: str,
    new_status: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Update experiment status (admin only)"""
    valid_statuses = ['planning', 'recruiting', 'active', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {valid_statuses}"
        )

    experiment = service.update_experiment_status(experiment_id, new_status)
    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return {"message": f"Experiment status updated to {new_status}"}


@router.get("/experiments/{experiment_id}/stats")
async def get_experiment_stats(
    experiment_id: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Get experiment statistics (admin only)"""
    stats = service.get_experiment_stats(experiment_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Experiment not found")
    return stats


# ============================================================================
# Participant Onboarding Endpoints
# ============================================================================

@router.post("/onboarding/register")
async def register_new_participant(
    request: RegisterParticipantRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Register a new participant with pre-survey data.

    NOTE: No personally identifiable information is collected.
    Condition is determined by the logged-in user account:
    - user1@adventureworks.com -> Experimental group
    - user2@adventureworks.com -> Control group
    """
    # Validate consent
    if not request.consent_given:
        raise HTTPException(
            status_code=400,
            detail="Consent is required to participate in the study"
        )

    # Determine condition.
    # Prolific participants: the URL's `condition` param is authoritative (each
    # Prolific study maps to a single condition). University participants:
    # condition comes from the user account (user1=experimental, user2=control).
    if request.prolific_pid:
        if request.prolific_condition not in ('control', 'experimental'):
            raise HTTPException(
                status_code=400,
                detail="Prolific registration requires ?condition=control or ?condition=experimental in the URL"
            )
        forced_condition = request.prolific_condition
        # Sanity check: the Prolific URL should have auto-logged the participant
        # into the shared account that matches the condition. If not, the URL
        # sent them to the wrong study.
        expected_email = (
            'user1@adventureworks.com' if forced_condition == 'experimental'
            else 'user2@adventureworks.com'
        )
        if current_user.email != expected_email:
            raise HTTPException(
                status_code=400,
                detail="Prolific URL condition does not match the logged-in account"
            )
    elif current_user.email == 'user1@adventureworks.com':
        forced_condition = 'experimental'
    elif current_user.email == 'user2@adventureworks.com':
        forced_condition = 'control'
    else:
        raise HTTPException(
            status_code=403,
            detail="Only participant accounts (user1 or user2) can register for the experiment"
        )

    # Shared-account note: multiple Prolific participants log in as the same
    # user. Do NOT unlink previous participants here; that used to cause race
    # conditions where a later registration detached the earlier participant's
    # session, breaking survey submission and /participants/me lookups. Every
    # participant row stays linked to the shared account; the client stores
    # the returned participant_id and sends it explicitly when needed.

    # Validate pre-survey fields
    valid_occupation_statuses = ['student', 'employee', 'self_employed', 'other']
    if not request.occupation_statuses or len(request.occupation_statuses) == 0:
        raise HTTPException(status_code=400, detail="At least one occupation must be selected")
    for occ in request.occupation_statuses:
        if occ not in valid_occupation_statuses:
            raise HTTPException(status_code=400, detail=f"Each occupation must be one of: {valid_occupation_statuses}")

    is_student = 'student' in request.occupation_statuses
    has_non_student = any(o != 'student' for o in request.occupation_statuses)

    if is_student and not request.field_of_study:
        raise HTTPException(status_code=400, detail="field_of_study is required when student is selected")
    if has_non_student and not request.field_of_work:
        raise HTTPException(status_code=400, detail="field_of_work is required when employee/self_employed/other is selected")

    valid_frequencies = ['never', 'rarely', 'occasionally', 'regularly', 'daily']
    if request.visual_analytics_frequency not in valid_frequencies:
        raise HTTPException(status_code=400, detail=f"visual_analytics_frequency must be one of: {valid_frequencies}")

    valid_backgrounds = ['education', 'experience', 'both', 'none']
    if request.business_background not in valid_backgrounds:
        raise HTTPException(status_code=400, detail=f"business_background must be one of: {valid_backgrounds}")

    valid_llm_experience = ['never', 'once_twice', 'occasionally', 'regularly']
    if request.llm_chatbot_experience not in valid_llm_experience:
        raise HTTPException(status_code=400, detail=f"llm_chatbot_experience must be one of: {valid_llm_experience}")

    valid_bi_experience = ['none', 'minimal', 'basic', 'intermediate', 'advanced']
    if request.bi_tools_experience not in valid_bi_experience:
        raise HTTPException(status_code=400, detail=f"bi_tools_experience must be one of: {valid_bi_experience}")

    # Dead-URL guard: reject obviously invalid Prolific IDs. Prolific templates
    # (e.g. {{%PROLIFIC_PID%}}) can leak through when the study URL is
    # misconfigured on the Prolific side; we never want to create a
    # pseudo-Prolific participant from a templated value.
    def _looks_valid_prolific_id(v: Optional[str]) -> bool:
        if not v:
            return False
        if any(ch in v for ch in "{}%"):
            return False
        return 8 <= len(v) <= 64

    if request.prolific_pid and not _looks_valid_prolific_id(request.prolific_pid):
        raise HTTPException(
            status_code=400,
            detail="Invalid Prolific identifier. Please re-enter the study via the Prolific URL."
        )

    # Reject duplicate Prolific submissions before we hit the unique index
    if request.prolific_pid:
        existing = service.find_participant_by_prolific_pid(request.prolific_pid)
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Prolific PID already registered as participant {existing.participant_code}"
            )

    try:
        participant = service.register_new_participant_v2(
            experiment_id=request.experiment_id,
            user_id=current_user.id,
            # Pre-survey data (anonymous)
            age=request.age,
            occupation_statuses=",".join(request.occupation_statuses),
            field_of_work=request.field_of_work,
            field_of_study=request.field_of_study,
            visual_analytics_frequency=request.visual_analytics_frequency,
            business_background=request.business_background,
            llm_chatbot_experience=request.llm_chatbot_experience,
            bi_tools_experience=request.bi_tools_experience,
            # Consent
            consent_given=request.consent_given,
            forced_condition=forced_condition,
            # Prolific (optional; None when participant is from university cohort)
            prolific_pid=request.prolific_pid,
            prolific_study_id=request.prolific_study_id,
            prolific_session_id=request.prolific_session_id,
        )

        # Update user role based on assigned condition
        if participant.condition_assigned == 'control':
            current_user.role = 'participant_control'
        else:
            current_user.role = 'participant_experimental'
        service.db.commit()

        return {
            "success": True,
            "message": "Registration successful",
            "participant_code": participant.participant_code,
            "condition_assigned": participant.condition_assigned,
            "participant_id": participant.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/onboarding/lookup")
async def lookup_returning_participant(
    request: LookupReturningParticipantRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Look up a returning participant by participant code only.
    Used to re-identify returning participants who want to continue their session.

    NOTE: Since we don't collect personal info (name, DOB), participants
    can only be looked up by their participant code.

    IMPORTANT: Participant's condition must match the logged-in user account:
    - user1@adventureworks.com -> Can only look up Experimental participants
    - user2@adventureworks.com -> Can only look up Control participants
    """
    # Determine which condition this user account is for
    if current_user.email == 'user1@adventureworks.com':
        expected_condition = 'experimental'
    elif current_user.email == 'user2@adventureworks.com':
        expected_condition = 'control'
    else:
        raise HTTPException(
            status_code=403,
            detail="Only participant accounts (user1 or user2) can look up participants"
        )

    # Look up participant by code only
    participant = service.find_participant_by_code(request.participant_code)

    if not participant:
        return {
            "found": False,
            "participant": None,
            "message": "No participant found with this ID. Please check your participant code or register as a new participant."
        }

    # Block re-entry for participants who have completed the study
    if participant.session_completed:
        raise HTTPException(
            status_code=400,
            detail="This study session has already been completed. Thank you for your participation!"
        )

    # CRITICAL: Verify participant's condition matches the logged-in user account
    if participant.condition_assigned != expected_condition:
        condition_name = "Experimental" if expected_condition == "experimental" else "Control"
        participant_condition = "Experimental" if participant.condition_assigned == "experimental" else "Control"
        return {
            "found": False,
            "participant": None,
            "message": f"This participant belongs to the {participant_condition} group. Please log in with the correct account for your group."
        }

    # Shared-account note: do NOT unlink other participants (see
    # /onboarding/register comment). We simply link the requested one if it
    # is not already linked. The client stores the returned participant_id
    # explicitly so /participants/me ambiguity doesn't matter.
    participant.user_id = current_user.id
    service.db.commit()
    service.db.refresh(participant)

    # Update user role based on participant's assigned condition
    if participant.condition_assigned == 'control':
        current_user.role = 'participant_control'
    else:
        current_user.role = 'participant_experimental'
    service.db.commit()

    return {
        "found": True,
        "participant": {
            "id": participant.id,
            "participant_code": participant.participant_code,
            "condition_assigned": participant.condition_assigned,
            "status": participant.status,
            "tasks_completed": participant.tasks_completed,
            "tasks_attempted": participant.tasks_attempted,
            "onboarding_completed": participant.onboarding_completed,
        },
        "message": "Participant found"
    }


@router.get("/onboarding/status")
async def get_onboarding_status(
    participant_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Check if the current user has completed onboarding.
    Returns participant info if enrolled, otherwise indicates onboarding is needed.

    Shared-account note: the frontend should pass participant_id (persisted in
    sessionStorage at registration). Without it, a brand-new tab on a shared
    user account could otherwise see another concurrent participant's status.
    """
    participant = service.resolve_participant_for_caller(
        user_id=current_user.id,
        participant_id=participant_id,
        is_admin=current_user.can_access_admin(),
    )

    if not participant:
        return {
            "needs_onboarding": True,
            "participant": None,
            "message": "User is not registered as a participant"
        }

    return {
        "needs_onboarding": not participant.onboarding_completed,
        "participant": {
            "id": participant.id,
            "participant_code": participant.participant_code,
            "condition_assigned": participant.condition_assigned,
            "status": participant.status,
            "tasks_completed": participant.tasks_completed,
            "tasks_attempted": participant.tasks_attempted,
            "onboarding_completed": participant.onboarding_completed,
            # Pre-survey data (anonymous)
            "age_range": participant.age_range,
            "occupation_status": participant.occupation_status,
            "field_of_work": participant.field_of_work,
        },
        "message": "Onboarding completed" if participant.onboarding_completed else "Onboarding required"
    }


@router.get("/onboarding/active-experiment")
async def get_active_experiment(
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get the currently active experiment for participant registration.
    """
    experiment = service.get_active_experiment()

    if not experiment:
        return {
            "has_active_experiment": False,
            "message": "No active experiment available for registration"
        }

    return {
        "has_active_experiment": True,
        "experiment_id": experiment.id,
        "experiment_name": experiment.name,
        "description": experiment.description,
    }


# ============================================================================
# Participant Endpoints
# ============================================================================

@router.post("/participants/enroll", response_model=ParticipantResponse)
async def enroll_participant(
    request: EnrollParticipantRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Enroll current user as a participant in an experiment.

    Legacy direct-enroll path. The Prolific flow uses /onboarding/register
    instead. The shared-account model allows multiple participants per user;
    use the deterministic helper here to avoid the non-deterministic .first().
    """
    existing = service.get_most_recent_participant_for_user(current_user.id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="User is already enrolled in an experiment"
        )

    participant = service.create_participant(
        experiment_id=request.experiment_id,
        user_id=current_user.id,
        email=current_user.email,
        demographics=request.demographics,
        assignment_method=request.assignment_method,
    )

    return {
        "id": participant.id,
        "participant_code": participant.participant_code,
        "condition_assigned": participant.condition_assigned,
        "status": participant.status,
        "consent_given": participant.consent_given,
        "tasks_completed": participant.tasks_completed,
        "tasks_attempted": participant.tasks_attempted,
    }


@router.post("/participants/consent")
async def record_consent(
    request: RecordConsentRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Record participant consent"""
    participant = service.get_participant(request.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Verify the participant belongs to the current user
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    participant = service.record_consent(request.participant_id)
    return {"message": "Consent recorded", "status": participant.status}


@router.get("/participants/me")
async def get_my_participant_info(
    participant_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get current user's participant information.

    Under the shared-account model (multiple Prolific participants log in as
    the same user) the client should pass `participant_id` as a query param
    so we return the correct record. If the caller is admin the participant
    is returned directly. Otherwise the participant must be linked to the
    caller's user account, or must have no link but belong to the caller's
    condition (edge case for pre-bug-fix orphans that we still want to read).

    If no participant_id is given, fall back to the most recent participant
    linked to the caller (most recently registered wins).
    """
    if participant_id:
        participant = service.get_participant(participant_id)
        if not participant:
            return {"enrolled": False}
        if (
            participant.user_id != current_user.id
            and not current_user.can_access_admin()
        ):
            raise HTTPException(status_code=403, detail="Not authorized for that participant")
    else:
        participant = service.get_most_recent_participant_for_user(current_user.id)
        if not participant:
            return {"enrolled": False}

    return {
        "enrolled": True,
        "id": participant.id,
        "participant_code": participant.participant_code,
        "condition_assigned": participant.condition_assigned,
        "status": participant.status,
        "consent_given": participant.consent_given,
        "tasks_completed": participant.tasks_completed,
        "tasks_attempted": participant.tasks_attempted,
        "experiment_id": participant.experiment_id,
        "post_study_survey_responses": participant.post_study_survey_responses,
    }


@router.get("/participants/{participant_id}/summary")
async def get_participant_summary(
    participant_id: str,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Get participant summary (own or admin)"""
    participant = service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Verify authorization
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    return service.get_participant_summary(participant_id)


@router.post("/participants/survey")
async def submit_post_study_survey(
    request: SubmitSurveyRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Submit post-study survey"""
    participant = service.get_participant(request.participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    # Verify authorization
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    try:
        participant = service.submit_post_study_survey(
            request.participant_id,
            request.survey_responses
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"message": "Survey submitted successfully"}


# ============================================================================
# Task Endpoints
# ============================================================================

@router.get("/tasks")
async def get_my_tasks(
    participant_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Get all tasks for current participant.

    Shared-account note: the frontend MUST pass participant_id from
    sessionStorage. Without it, a new participant on a shared user account
    would non-deterministically see another concurrent participant's tasks
    (this is what burned P019 in the v2 run).
    """
    participant = service.resolve_participant_for_caller(
        user_id=current_user.id,
        participant_id=participant_id,
        is_admin=current_user.can_access_admin(),
    )
    if not participant:
        raise HTTPException(status_code=404, detail="Not enrolled as participant")

    tasks = service.get_participant_tasks(participant.id)
    return [
        {
            "id": t.id,
            "task_id": t.task_id,
            "task_number": t.task_number,
            "task_description": t.task_description,
            "task_type": t.task_type,
            "domain": t.domain,
            "complexity_level": t.complexity_level,
            "task_started_at": t.task_started_at.isoformat() if t.task_started_at else None,
            "task_completed_at": t.task_completed_at.isoformat() if t.task_completed_at else None,
            "task_duration_seconds": t.task_duration_seconds,
            "submitted_answer": t.submitted_answer,
            # Tutorial fields
            "is_tutorial": t.is_tutorial if hasattr(t, 'is_tutorial') else False,
            "tutorial_steps": t.tutorial_steps if hasattr(t, 'tutorial_steps') else None,
            "tutorial_tips": t.tutorial_tips if hasattr(t, 'tutorial_tips') else None,
        }
        for t in tasks
    ]


@router.post("/tasks/start")
async def start_task(
    request: StartTaskRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Start a task"""
    task = service.get_task(request.task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify authorization
    participant = service.get_participant(task.participant_id)
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    task = service.start_task(request.task_db_id)
    return {
        "message": "Task started",
        "task_started_at": task.task_started_at.isoformat(),
    }


@router.post("/tasks/complete")
async def complete_task(
    request: CompleteTaskRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Complete a task with answer"""
    task = service.get_task(request.task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify authorization
    participant = service.get_participant(task.participant_id)
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    task = service.complete_task(
        request.task_db_id,
        request.submitted_answer,
        request.task_difficulty_rating,
        request.confidence_in_answer,
    )
    return {
        "message": "Task completed",
        "task_duration_seconds": task.task_duration_seconds,
    }


@router.post("/tasks/abandon")
async def abandon_task(
    request: AbandonTaskRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Abandon a task"""
    task = service.get_task(request.task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify authorization
    participant = service.get_participant(task.participant_id)
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    task = service.abandon_task(request.task_db_id, request.reason)
    return {"message": "Task abandoned"}


# ============================================================================
# Interaction Logging Endpoints
# ============================================================================

@router.post("/interactions/log")
async def log_interaction(
    request: LogInteractionRequest,
    current_user: User = Depends(get_current_user),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Log a user interaction during task completion"""
    task = service.get_task(request.task_db_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Verify authorization
    participant = service.get_participant(task.participant_id)
    if participant.user_id != current_user.id and not current_user.can_access_admin():
        raise HTTPException(status_code=403, detail="Not authorized")

    interaction = service.log_interaction(
        experiment_id=task.experiment_id,
        participant_id=task.participant_id,
        task_db_id=request.task_db_id,
        interaction_type=request.interaction_type,
        user_query=request.user_query,
        system_response=request.system_response,
        query_understood=request.query_understood,
        query_successful=request.query_successful,
        dashboard_action=request.dashboard_action,
        dashboard_element=request.dashboard_element,
        tokens_used=request.tokens_used,
        cost_usd=request.cost_usd,
    )
    return {
        "interaction_id": interaction.id,
        "interaction_sequence": interaction.interaction_sequence,
    }


# ============================================================================
# User Role Check Endpoint
# ============================================================================

@router.get("/access-check")
async def check_access(
    current_user: User = Depends(get_current_user)
):
    """Check user's experiment access permissions"""
    return {
        "user_id": current_user.id,
        "role": current_user.role,
        "can_access_chatbot": current_user.can_access_chatbot(),
        "can_access_dashboards": current_user.can_access_dashboards(),
        "can_access_admin": current_user.can_access_admin(),
    }


# Export router
__all__ = ["router"]
