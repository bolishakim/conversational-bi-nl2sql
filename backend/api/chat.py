"""
Chat API Endpoint
Real agent workflow integration with LangGraph

Access Control:
- Chatbot is ONLY accessible to:
  - admin: Full access
  - participant_experimental: Experimental group in user study
- participant_control: Control group - NO chatbot access (dashboard only)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import sys
from pathlib import Path
import time

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session as DBSession

from api.auth import get_current_user, get_db
from database.models import User
from database.connection import get_db_session
from utils.logger import logger
from utils.cache import cache
from services.chat_service import get_chat_service
from services.history_service import get_history_service
from services.experiment_service import ExperimentService


def _record_chatbot_interaction(
    db: DBSession,
    participant_id: str,
    user_query: str,
    response: Dict[str, Any],
) -> None:
    """
    Log a completed chatbot query against the participant's currently-active
    task so the per-task counter (experiment_tasks.chatbot_query_count) and
    the fine-grained experiment_interactions log stay in sync with
    query_history.

    Non-fatal: any exception is swallowed and logged, never propagated to the
    caller (we don't want interaction bookkeeping to fail a user's query).
    """
    try:
        service = ExperimentService(db)
        task = service.get_active_task_for_participant(participant_id)
        if not task:
            # No in-progress task (e.g., participant chatting outside a task):
            # query_history still records everything; we just skip the
            # per-task counter + interactions row.
            return

        # Trim the response payload so we don't bloat the log row
        system_response = {
            "execution_status": response.get("execution_status"),
            "sql": (response.get("sql") or "")[:500],
            "row_count": response.get("row_count"),
            "chart_type": response.get("chart_type"),
            "analysis_summary": (response.get("analysis", {}) or {}).get("summary"),
        }

        execution_status = response.get("execution_status")
        total_tokens = response.get("total_tokens") or 0
        total_cost = str(response.get("total_cost_usd") or "0")

        service.log_chatbot_query(
            experiment_id=task.experiment_id,
            participant_id=participant_id,
            task_db_id=task.id,
            user_query=user_query,
            system_response=system_response,
            query_understood=response.get("error_stage") != "orchestrator",
            query_successful=(execution_status == "success"),
            tokens_used=int(total_tokens) if total_tokens else None,
            cost_usd=total_cost,
        )
    except Exception as e:
        logger.error(f"Failed to record chatbot interaction: {e}")


async def get_participant_id_for_user(user: User) -> Optional[str]:
    """
    Get the participant ID for a user.
    Returns None for admin users.
    For participant accounts, returns the linked participant ID.
    """
    # Admin doesn't have a participant ID
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


def require_chatbot_access(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that requires chatbot access permission
    Only admin and participant_experimental roles can access the chatbot
    """
    if not current_user.can_access_chatbot():
        logger.warning(f"User {current_user.email} (role: {current_user.role}) attempted to access chatbot without permission")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chatbot access not available for your account. Please contact the administrator.",
            headers={"X-Access-Denied-Reason": "role_restriction"}
        )
    return current_user


# Rate limit: max queries per experimental participant per minute.
# Controls Prolific abuse (accidental auto-submit loops, scripted spam) and
# keeps LLM costs bounded per participant. Admins bypass.
RATE_LIMIT_QUERIES_PER_MINUTE = 30


def rate_limit_query(current_user: User = Depends(require_chatbot_access)) -> User:
    """
    Enforce a per-user, per-minute quota on chatbot queries. Admin is exempt.
    Returns 429 + Retry-After header when the quota is exceeded.
    """
    if current_user.role == 'admin':
        return current_user
    key = f"ratelimit:chat:{current_user.id}:1m"
    allowed, retry_after = cache.check_rate_limit(
        key, RATE_LIMIT_QUERIES_PER_MINUTE, 60
    )
    if not allowed:
        logger.warning(
            f"Rate limit hit for user {current_user.id} "
            f"(retry in {retry_after}s)"
        )
        raise HTTPException(
            status_code=429,
            detail=(
                f"You're sending queries too quickly. Limit is "
                f"{RATE_LIMIT_QUERIES_PER_MINUTE} per minute. "
                f"Try again in {retry_after} seconds."
            ),
            headers={"Retry-After": str(retry_after)},
        )
    return current_user


# Create router
router = APIRouter(prefix="/api/v1", tags=["chat"])


# ============================================================================
# Pydantic Models
# ============================================================================

class QueryRequest(BaseModel):
    """Query request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language query")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What are the total sales by territory in 2024?"
            }
        }


class AnalysisDetails(BaseModel):
    """Analysis details from Analyst Agent"""
    summary: str
    key_insights: List[str]
    recommendations: List[str]
    data_quality_notes: List[str] = []


class WorkflowDetails(BaseModel):
    """Workflow execution details"""
    orchestrator_action: str
    needs_visualization: bool
    tables_used: List[str]
    is_cross_departmental: bool


class QueryResults(BaseModel):
    """Query results in frontend format"""
    columns: List[str]
    data: List[List[Any]]
    row_count: int


class ChartData(BaseModel):
    """Chart data in Plotly format"""
    data: List[Dict[str, Any]]
    layout: Dict[str, Any]
    config: Optional[Dict[str, Any]] = None


class QueryResponse(BaseModel):
    """Query response model with complete workflow results"""
    # Frontend-expected fields (primary)
    query_id: str
    user_query: str
    sql_query: str
    results: QueryResults
    chart: Optional[ChartData] = None
    analysis: AnalysisDetails
    execution_time_ms: int

    # Additional backend fields (for history/debugging)
    query: str
    domain: str
    retrieved_tables: List[str]
    generated_sql: Optional[str] = None
    sql_explanation: Optional[str] = None
    execution_status: str
    result_data: Optional[Dict[str, Any]] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    processing_time_ms: int
    workflow_details: Optional[WorkflowDetails] = None
    token_usage: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    error_stage: Optional[str] = None
    validation_issues: Optional[List[Dict[str, Any]]] = None
    validation_summary: Optional[str] = None
    execution_error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "query_id": "abc123",
                "user_query": "What are the total sales by territory?",
                "sql_query": "SELECT st.name, SUM(soh.totaldue) as total FROM sales.salesterritory st...",
                "results": {
                    "columns": ["territory", "total"],
                    "data": [["Southwest", 27150594.59]],
                    "row_count": 5
                },
                "chart": {
                    "data": [{"x": ["Southwest"], "y": [27150594.59], "type": "bar"}],
                    "layout": {"title": "Sales by Territory"}
                },
                "analysis": {
                    "summary": "Southwest territory leads with $27M in sales",
                    "key_insights": ["Top territory: Southwest with $27.1M"],
                    "recommendations": ["Focus expansion on high-performing territories"],
                    "data_quality_notes": []
                },
                "execution_time_ms": 45,
                "query": "What are the total sales by territory?",
                "domain": "sales",
                "retrieved_tables": ["sales.salesterritory", "sales.salesorderheader"],
                "generated_sql": "SELECT st.name, SUM(soh.totaldue) as total FROM sales.salesterritory st...",
                "execution_status": "success",
                "result_data": {
                    "rows": [{"territory": "Southwest", "total": 27150594.59}],
                    "row_count": 5,
                    "execution_time_ms": 45
                },
                "chart_type": "bar",
                "processing_time_ms": 2500
            }
        }


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/query", response_model=QueryResponse)
async def process_query(
    request: QueryRequest,
    current_user: User = Depends(rate_limit_query),
    db: DBSession = Depends(get_db),
):
    """
    Process a natural language query through the agent workflow

    Access Control:
    - admin: Full access
    - participant_experimental: Experimental group access
    - participant_control: NO ACCESS (403 Forbidden)

    Workflow:
    1. Orchestrator - Routes query and determines action
    2. Schema Agent - Retrieves relevant tables using RAG
    3. SQL Agent - Generates SQL with chain-of-thought reasoning
    4. Validator Agent - Validates SQL for safety and correctness
    5. Executor Agent - Executes validated SQL
    6. Analyst Agent - Analyzes results and generates insights

    Requires: Bearer token in Authorization header
    """
    logger.info(f"Query from user {current_user.email}: {request.query}")

    # Check cache (simple key based on query)
    cache_key = f"query:{current_user.id}:{request.query}"
    cached_result = cache.get(cache_key)

    if cached_result:
        logger.info("Returning cached result")
        return cached_result

    # Get recent conversation history for context
    conversation_history = []
    try:
        history_service = get_history_service()
        conversation_history = await history_service.get_recent_conversation(
            user_id=str(current_user.id),
            limit=5  # Last 5 query-response pairs
        )
        logger.info(f"Retrieved {len(conversation_history)} conversation messages for context")
    except Exception as e:
        logger.error(f"Failed to retrieve conversation history: {e}")
        # Continue without history - don't fail the query

    # Get participant ID for this user (for query history filtering)
    participant_id = await get_participant_id_for_user(current_user)

    # Get chat service and process query
    # Note: process_query now handles saving to history internally
    chat_service = get_chat_service()
    response = await chat_service.process_query(
        user_query=request.query,
        user_id=str(current_user.id),
        conversation_history=conversation_history,
        participant_id=participant_id
    )

    # Cache successful results for 5 minutes
    if response.get("execution_status") == "success":
        cache.set(cache_key, response, ttl=300)

    # Log the interaction against the participant's active task (no-op for
    # admin, or when no task is in progress).
    if participant_id:
        _record_chatbot_interaction(db, participant_id, request.query, response)

    return response


@router.post("/query/stream")
async def process_query_stream(
    request: QueryRequest,
    current_user: User = Depends(rate_limit_query),
    db: DBSession = Depends(get_db),
):
    """
    Process a natural language query with streaming progress updates

    Access Control:
    - admin: Full access
    - participant_experimental: Experimental group access
    - participant_control: NO ACCESS (403 Forbidden)

    This endpoint streams real-time progress as each agent executes:
    1. Orchestrator - Routes query and determines action
    2. Schema Agent - Retrieves relevant tables using RAG
    3. SQL Agent - Generates SQL with chain-of-thought reasoning
    4. Validator Agent - Validates SQL for safety and correctness
    5. Executor Agent - Executes validated SQL
    6. Analyst Agent - Analyzes results and generates insights

    Returns Server-Sent Events (SSE) with progress updates:
    - type: "start" - Query processing started
    - type: "progress" - Agent stage update (running/completed/failed)
    - type: "result" - Final query result
    - type: "error" - Error occurred

    Requires: Bearer token in Authorization header
    """
    logger.info(f"Streaming query from user {current_user.email}: {request.query}")

    # Get recent conversation history for context
    conversation_history = []
    try:
        history_service = get_history_service()
        conversation_history = await history_service.get_recent_conversation(
            user_id=str(current_user.id),
            limit=5  # Last 5 query-response pairs
        )
        logger.info(f"Retrieved {len(conversation_history)} conversation messages for context")
    except Exception as e:
        logger.error(f"Failed to retrieve conversation history: {e}")
        # Continue without history - don't fail the query

    # Get participant ID for this user (for query history filtering)
    participant_id = await get_participant_id_for_user(current_user)

    # Get chat service
    chat_service = get_chat_service()

    async def stream_and_log():
        """
        Forward SSE events to the client and, after the stream ends, use the
        final "result" payload to log the chatbot interaction against the
        participant's active task. Wrapping at the endpoint layer keeps
        chat_service untouched by experiment concerns.
        """
        import json as _json
        final_payload: Optional[Dict[str, Any]] = None
        async for event_bytes in chat_service.process_query_stream(
            user_query=request.query,
            user_id=str(current_user.id),
            conversation_history=conversation_history,
            participant_id=participant_id,
        ):
            try:
                as_str = event_bytes.decode("utf-8") if isinstance(event_bytes, (bytes, bytearray)) else event_bytes
                for line in as_str.splitlines():
                    if line.startswith("data: "):
                        parsed = _json.loads(line[len("data: "):])
                        if isinstance(parsed, dict) and parsed.get("type") == "result":
                            final_payload = parsed.get("data") or parsed
            except Exception:
                pass
            yield event_bytes

        if participant_id and final_payload is not None:
            _record_chatbot_interaction(db, participant_id, request.query, final_payload)

    # Return streaming response
    return StreamingResponse(
        stream_and_log(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


# Export router
__all__ = ["router"]
