"""
Admin API Endpoints
Provides admin-only access to participant tracking, interactions, and analytics
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database.models import User
from services.experiment_service import ExperimentService
from api.auth import get_db
from api.experiment import get_current_user, require_admin


# Create router
router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


# ============================================================================
# Pydantic Models
# ============================================================================

class ParticipantSummary(BaseModel):
    """Summary information for a participant"""
    id: str
    participant_code: str
    condition_assigned: str
    status: str
    tasks_completed: int
    tasks_total: int
    session_duration_minutes: Optional[float]
    avg_task_duration_seconds: Optional[float]
    last_activity: Optional[str]


class ParticipantDetail(ParticipantSummary):
    """Detailed participant information"""
    age: Optional[int]
    age_range: Optional[str]
    occupation_statuses: Optional[str]
    occupation_status: Optional[str]
    field_of_work: Optional[str]
    field_of_study: Optional[str]
    visual_analytics_frequency: Optional[str]
    business_background: Optional[str]
    llm_chatbot_experience: Optional[str]
    bi_tools_experience: Optional[str]
    registered_at: Optional[str]
    first_task_at: Optional[str]
    last_task_at: Optional[str]


class InteractionLog(BaseModel):
    """Single interaction log entry"""
    id: str
    interaction_sequence: int
    interaction_timestamp: str
    interaction_type: str
    task_id: str
    task_number: int
    query_text: Optional[str]
    dashboard_action: Optional[str]
    dashboard_element: Optional[str]
    tokens_used: Optional[int]
    cost_usd: Optional[str]


class TimelineEvent(BaseModel):
    """Timeline event for participant activity"""
    timestamp: str
    event_type: str  # task_started, interaction, task_completed
    task_number: Optional[int]
    details: Dict[str, Any]


class ParticipantAnalytics(BaseModel):
    """Aggregated analytics for a participant"""
    interactions_by_type: List[Dict[str, Any]]
    interactions_over_time: List[Dict[str, Any]]
    dashboard_elements_clicked: List[Dict[str, Any]]
    task_durations: List[Dict[str, Any]]


# ============================================================================
# Helper Functions
# ============================================================================

def get_experiment_service(db: DBSession = Depends(get_db)) -> ExperimentService:
    """Get experiment service instance"""
    return ExperimentService(db)


# ============================================================================
# Admin Endpoints
# ============================================================================

@router.get("/participants")
async def get_all_participants(
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get list of all participants with summary stats (admin only)
    Returns basic info for displaying in a table
    """
    participants = service.get_all_participants_summary()
    return participants


@router.get("/participants/{participant_id}/summary")
async def get_participant_detail(
    participant_id: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get detailed participant information (admin only)
    Includes pre-survey data, task completion, and session info
    """
    participant = service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    detail = service.get_participant_detail_for_admin(participant_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Participant details not found")

    return detail


@router.get("/participants/{participant_id}/interactions")
async def get_participant_interactions(
    participant_id: str,
    task_id: Optional[str] = Query(None, description="Filter by task ID"),
    limit: int = Query(100, ge=1, le=500, description="Number of interactions to return"),
    offset: int = Query(0, ge=0, description="Number of interactions to skip"),
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get paginated interaction logs for a participant (admin only)
    Optionally filter by task
    """
    participant = service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    result = service.get_participant_interactions(
        participant_id=participant_id,
        task_id=task_id,
        limit=limit,
        offset=offset
    )

    return result


@router.get("/participants/{participant_id}/timeline")
async def get_participant_timeline(
    participant_id: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get chronological timeline of all participant activity (admin only)
    Returns events: task_started, interaction, task_completed
    """
    participant = service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    timeline = service.get_participant_timeline(participant_id)
    return timeline


@router.get("/participants/{participant_id}/analytics")
async def get_participant_analytics(
    participant_id: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """
    Get aggregated analytics data for visualization (admin only)
    Returns: interactions by type, over time, dashboard clicks, task durations
    """
    participant = service.get_participant(participant_id)
    if not participant:
        raise HTTPException(status_code=404, detail="Participant not found")

    analytics = service.get_participant_analytics(participant_id)
    return analytics


# ============================================================================
# Study-Wide Analytics Endpoints
# ============================================================================

@router.get("/analytics/overview")
async def get_study_overview(
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Study-wide overview: enrollment timeline, completion funnel"""
    return service.get_study_overview()


@router.get("/analytics/tasks")
async def get_task_comparison(
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Per-task control vs experimental comparison"""
    return service.get_task_comparison()


@router.get("/analytics/surveys")
async def get_survey_analytics(
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Pre-survey demographics + post-survey Likert ratings by condition"""
    return service.get_survey_analytics()


@router.get("/analytics/chatbot")
async def get_chatbot_analytics(
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """NL2SQL usage stats (experimental group only)"""
    return service.get_chatbot_analytics()


# ============================================================================
# Participant Admin Actions (manual exclude / withdraw / reassign / reinstate)
# ============================================================================


class ExcludeParticipantRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class WithdrawParticipantRequest(BaseModel):
    reason: Optional[str] = Field(None, max_length=1000)


class ReassignConditionRequest(BaseModel):
    new_condition: str = Field(..., description="'control' or 'experimental'")
    reason: str = Field(..., min_length=1, max_length=1000)


@router.post("/participants/{participant_id}/actions/exclude")
async def admin_exclude_participant(
    participant_id: str,
    request: ExcludeParticipantRequest,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service),
):
    """
    Exclude a participant from analysis. Keeps data but sets status='excluded'
    and stores the reason in exclusion_reason. Reversible via /reinstate.
    """
    p = service.exclude_participant(participant_id, request.reason)
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"id": p.id, "status": p.status, "exclusion_reason": p.exclusion_reason}


@router.post("/participants/{participant_id}/actions/withdraw")
async def admin_withdraw_participant(
    participant_id: str,
    request: WithdrawParticipantRequest,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service),
):
    """
    Record a participant's withdrawal. Sets status='withdrawn',
    withdrawal_requested=True, withdrawal_timestamp=now. Reversible.
    """
    p = service.withdraw_participant(participant_id, request.reason)
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {
        "id": p.id,
        "status": p.status,
        "withdrawal_requested": p.withdrawal_requested,
        "withdrawal_timestamp": p.withdrawal_timestamp.isoformat() if p.withdrawal_timestamp else None,
    }


@router.post("/participants/{participant_id}/actions/reassign")
async def admin_reassign_participant(
    participant_id: str,
    request: ReassignConditionRequest,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service),
):
    """
    Reassign a participant to a different condition. Sets assignment_method
    to 'manual_override' and appends a timestamped audit line to admin_notes.
    """
    if request.new_condition not in ("control", "experimental"):
        raise HTTPException(
            status_code=400, detail="new_condition must be 'control' or 'experimental'"
        )
    p = service.reassign_participant_condition(
        participant_id, request.new_condition, request.reason
    )
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {
        "id": p.id,
        "condition_assigned": p.condition_assigned,
        "assignment_method": p.assignment_method,
    }


@router.post("/participants/{participant_id}/actions/reinstate")
async def admin_reinstate_participant(
    participant_id: str,
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service),
):
    """
    Undo an exclusion or withdrawal. Status becomes 'completed' if the
    participant's session_completed flag is set, else 'active'.
    """
    p = service.reinstate_participant(participant_id)
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return {"id": p.id, "status": p.status}


@router.get("/analytics/export")
async def get_export_data(
    tables: Optional[str] = Query(None, description="Comma-separated: participants,tasks,interactions,queries"),
    current_user: User = Depends(require_admin),
    service: ExperimentService = Depends(get_experiment_service)
):
    """Raw data dump for thesis analysis"""
    table_list = [t.strip() for t in tables.split(",")] if tables else None
    return service.get_export_data(table_list)


# Export router
__all__ = ["router"]
