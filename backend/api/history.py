"""
Query History API Endpoints
Provides endpoints to retrieve and manage query history
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from api.auth import get_current_user
from database.models import User
from database.connection import get_db_session
from utils.logger import logger
from services.history_service import get_history_service


async def get_current_participant_id(user: User) -> Optional[str]:
    """
    Get the participant ID for the current user.
    Returns None for admin users (they see all their own queries).
    For participant accounts (user1/user2), returns the linked participant ID.
    """
    # Admin sees all queries for their user_id (no participant filtering)
    if user.role == 'admin':
        return None

    # For participant accounts, get the linked participant
    from database.models import ExperimentParticipant
    from sqlalchemy import select

    async with get_db_session() as session:
        query = select(ExperimentParticipant.id).where(
            ExperimentParticipant.user_id == str(user.id)
        ).order_by(ExperimentParticipant.registered_at.desc()).limit(1)
        result = await session.execute(query)
        participant_id = result.scalar_one_or_none()
        return str(participant_id) if participant_id else None


# Create router
router = APIRouter(prefix="/api/v1/history", tags=["history"])


# ============================================================================
# Pydantic Models
# ============================================================================

class QueryHistoryItem(BaseModel):
    """Single query history entry"""
    id: str
    user_query: str
    domain: Optional[str] = None
    orchestrator_action: Optional[str] = None
    retrieved_tables: List[str] = []
    generated_sql: Optional[str] = None
    sql_explanation: Optional[str] = None
    execution_status: str
    execution_error: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    row_count: Optional[int] = None
    execution_time_ms: Optional[int] = None
    analysis: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    total_duration_ms: Optional[int] = None
    error_occurred: Optional[bool] = None
    created_at: str

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "user_query": "What are the top 5 territories by total sales?",
                "domain": "sales",
                "retrieved_tables": ["sales.salesorderheader", "sales.salesterritory"],
                "generated_sql": "SELECT ...",
                "execution_status": "success",
                "row_count": 5,
                "execution_time_ms": 45,
                "created_at": "2025-12-04T22:30:00Z"
            }
        }


class HistoryListResponse(BaseModel):
    """Response for history list endpoint"""
    total: int
    queries: List[QueryHistoryItem]
    limit: int
    offset: int


class HistoryStatsResponse(BaseModel):
    """Response for history statistics"""
    total_queries: int
    successful_queries: int
    failed_queries: int
    success_rate: float
    domain_breakdown: Dict[str, int]


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=HistoryListResponse)
async def get_history(
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of queries to return"),
    offset: int = Query(default=0, ge=0, description="Number of queries to skip"),
    domain: Optional[str] = Query(default=None, description="Filter by domain (sales, hr, production)"),
    current_user: User = Depends(get_current_user)
):
    """
    Get query history for the current user/participant

    Returns paginated list of previous queries with their results.
    For participant accounts, only shows queries made by the current participant.
    For admin accounts, shows all queries made by the admin.

    Query Parameters:
    - limit: Max number of queries (1-100, default 50)
    - offset: Skip first N queries (for pagination)
    - domain: Filter by domain (optional)

    Requires: Bearer token in Authorization header
    """
    # Get the current participant ID (None for admin)
    participant_id = await get_current_participant_id(current_user)

    logger.info(f"Fetching history for user {current_user.email}, participant_id={participant_id} (limit={limit}, offset={offset}, domain={domain})")

    try:
        history_service = get_history_service()

        # Get queries filtered by user_id and optionally by participant_id
        queries = await history_service.get_user_history(
            user_id=str(current_user.id),
            limit=limit,
            offset=offset,
            domain=domain,
            participant_id=participant_id
        )

        # Get total count (simplified - just return len for now)
        # In production, you'd want a separate count query
        total = len(queries)

        return {
            "total": total,
            "queries": queries,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve query history")


@router.get("/stats", response_model=HistoryStatsResponse)
async def get_history_stats(
    current_user: User = Depends(get_current_user)
):
    """
    Get query history statistics for the current user/participant

    Returns aggregate statistics including:
    - Total number of queries
    - Success/failure counts
    - Success rate percentage
    - Breakdown by domain

    For participant accounts, only counts queries made by the current participant.

    Requires: Bearer token in Authorization header
    """
    # Get the current participant ID (None for admin)
    participant_id = await get_current_participant_id(current_user)

    logger.info(f"Fetching history stats for user {current_user.email}, participant_id={participant_id}")

    try:
        history_service = get_history_service()
        stats = await history_service.get_history_stats(
            user_id=str(current_user.id),
            participant_id=participant_id
        )

        return stats

    except Exception as e:
        logger.error(f"Error fetching history stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@router.get("/{query_id}", response_model=QueryHistoryItem)
async def get_query_by_id(
    query_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific query by ID

    Returns complete details for a single query from history.
    For participant accounts, only returns query if it belongs to the current participant.

    Requires: Bearer token in Authorization header
    """
    # Get the current participant ID (None for admin)
    participant_id = await get_current_participant_id(current_user)

    logger.info(f"Fetching query {query_id} for user {current_user.email}, participant_id={participant_id}")

    try:
        history_service = get_history_service()
        query = await history_service.get_query_by_id(
            query_id=query_id,
            user_id=str(current_user.id),
            participant_id=participant_id
        )

        if not query:
            raise HTTPException(status_code=404, detail="Query not found")

        return query

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching query: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve query")


@router.delete("/{query_id}")
async def delete_query(
    query_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    Delete a query from history

    Permanently removes a query from the user's history.
    For participant accounts, only deletes query if it belongs to the current participant.

    Requires: Bearer token in Authorization header
    """
    # Get the current participant ID (None for admin)
    participant_id = await get_current_participant_id(current_user)

    logger.info(f"Deleting query {query_id} for user {current_user.email}, participant_id={participant_id}")

    try:
        history_service = get_history_service()
        deleted = await history_service.delete_query(
            query_id=query_id,
            user_id=str(current_user.id),
            participant_id=participant_id
        )

        if not deleted:
            raise HTTPException(status_code=404, detail="Query not found")

        return {"message": "Query deleted successfully", "id": query_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting query: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete query")


# Export router
__all__ = ["router"]
