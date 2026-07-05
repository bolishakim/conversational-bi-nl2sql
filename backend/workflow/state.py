"""
Workflow State Management
Defines the shared state that flows through the NL2SQL agent pipeline
"""
from typing import TypedDict, List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# State Type Definitions
# ============================================================================

class WorkflowState(TypedDict, total=False):
    """
    Shared state that flows through the NL2SQL agent workflow

    This state is passed through all agents and accumulates information
    as it progresses through the pipeline.
    """

    # ========================================================================
    # Input (from user)
    # ========================================================================
    user_query: str
    """Original user query in natural language"""

    conversation_history: List[Dict[str, str]]
    """Previous conversation messages for context"""

    user_id: Optional[str]
    """User ID for session tracking"""

    # ========================================================================
    # Orchestrator Output
    # ========================================================================
    orchestrator_action: Optional[Literal["DIRECT_ANSWER", "INTERPRET_PREVIOUS", "MODIFY_VISUALIZATION", "FULL_PIPELINE"]]
    """Action type determined by Orchestrator"""

    orchestrator_reasoning: Optional[str]
    """Orchestrator's reasoning for the routing decision"""

    needs_visualization: bool
    """Whether the query needs visualization"""

    direct_response: Optional[str]
    """Direct response for DIRECT_ANSWER action"""

    # ========================================================================
    # Schema Agent Output
    # ========================================================================
    domain: Optional[str]
    """Detected domain (sales, hr, production, purchasing, general)"""

    is_cross_departmental: bool
    """Whether query spans multiple domains"""

    retrieved_tables: Optional[List[str]]
    """List of table names retrieved via RAG"""

    schema_context: Optional[str]
    """Formatted schema context for SQL generation"""

    all_retrieved_table_metadata: Optional[List[Dict[str, Any]]]
    """Raw table metadata for all retrieved tables (Phase 2 optimization)"""

    # ========================================================================
    # SQL Agent Output
    # ========================================================================
    sql_reasoning_steps: Optional[List[str]]
    """Chain-of-thought reasoning steps for SQL generation"""

    generated_sql: Optional[str]
    """Generated SQL query"""

    sql_explanation: Optional[str]
    """Explanation of what the SQL does"""

    tables_used: Optional[List[str]]
    """Tables actually used in the SQL query"""

    sql_assumptions: Optional[List[str]]
    """Assumptions made during SQL generation"""

    # ========================================================================
    # SQL Retry & Feedback Loop
    # ========================================================================
    sql_retry_count: int
    """Number of SQL generation attempts (starts at 0)"""

    max_sql_retries: int
    """Maximum number of SQL retry attempts (default 3)"""

    validation_feedback: Optional[List[Dict[str, str]]]
    """Previous validation issues to help SQL Agent fix problems"""

    # ========================================================================
    # Validator Output
    # ========================================================================
    validation_passed: bool
    """Whether SQL validation passed"""

    validation_severity: Optional[str]
    """Validation severity: safe, warning, error, critical"""

    validation_issues: Optional[List[Dict[str, str]]]
    """List of validation issues found"""

    validation_summary: Optional[str]
    """Brief validation summary"""

    validated_sql: Optional[str]
    """SQL after validation (may be modified)"""

    # ========================================================================
    # Execution Results
    # ========================================================================
    execution_success: bool
    """Whether SQL execution succeeded"""

    query_results: Optional[List[Dict[str, Any]]]
    """Query results as list of row dictionaries"""

    result_count: Optional[int]
    """Number of rows returned"""

    execution_time_ms: Optional[float]
    """Query execution time in milliseconds"""

    execution_error: Optional[str]
    """Error message if execution failed"""

    # ========================================================================
    # Analyst Output
    # ========================================================================
    analysis_reasoning_steps: Optional[List[str]]
    """Chain-of-thought reasoning for analysis"""

    analysis_summary: Optional[str]
    """One-sentence summary of key finding"""

    key_insights: Optional[List[str]]
    """Bulleted insights with specific numbers"""

    recommendations: Optional[List[str]]
    """Actionable recommendations and follow-ups"""

    data_quality_notes: Optional[List[str]]
    """Caveats and limitations"""

    # ========================================================================
    # Multi-Query Iteration Support
    # ========================================================================
    query_iteration_count: int
    """Number of SQL queries executed so far (0-based)"""

    max_query_iterations: int
    """Maximum number of SQL queries allowed (default 3)"""

    needs_followup_query: bool
    """Whether analyst determined more data is needed"""

    followup_query_reason: Optional[str]
    """Why a follow-up query is needed"""

    all_query_results: Optional[List[Dict[str, Any]]]
    """Accumulated results from all queries executed
    Format: [
        {
            "iteration": 0,
            "sql": "SELECT ...",
            "results": [...],
            "row_count": 10,
            "purpose": "Get raw quarterly data"
        },
        ...
    ]
    """

    final_answer_ready: bool
    """Whether we have enough data to provide final answer"""

    # ========================================================================
    # Visualization Output (optional)
    # ========================================================================
    visualization_type: Optional[str]
    """Type of visualization (bar, line, pie, scatter, etc.)"""

    chart_config: Optional[Dict[str, Any]]
    """Chart configuration for frontend"""

    # ========================================================================
    # Error Handling
    # ========================================================================
    error_occurred: bool
    """Whether an error occurred in the pipeline"""

    error_stage: Optional[str]
    """Which agent stage had the error"""

    error_message: Optional[str]
    """Error message for user"""

    error_details: Optional[str]
    """Detailed error for debugging"""

    # ========================================================================
    # Token Usage & Cost Tracking
    # ========================================================================
    token_usage: Optional[List[Dict[str, Any]]]
    """List of token usage records from each LLM call"""

    total_tokens: Optional[int]
    """Total tokens used across all LLM calls"""

    total_cost: Optional[float]
    """Total cost in USD for all LLM calls"""

    # ========================================================================
    # Metadata
    # ========================================================================
    workflow_id: Optional[str]
    """Unique ID for this workflow execution"""

    started_at: Optional[str]
    """Workflow start timestamp"""

    completed_at: Optional[str]
    """Workflow completion timestamp"""

    total_duration_ms: Optional[float]
    """Total workflow duration in milliseconds"""


# ============================================================================
# Helper Functions
# ============================================================================

def create_initial_state(
    user_query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_id: Optional[str] = None
) -> WorkflowState:
    """
    Create initial workflow state from user input

    Args:
        user_query: User's natural language query
        conversation_history: Optional conversation history
        user_id: Optional user ID

    Returns:
        Initialized WorkflowState
    """
    import uuid
    from datetime import datetime

    return WorkflowState(
        # Input
        user_query=user_query,
        conversation_history=conversation_history or [],
        user_id=user_id,

        # Default flags
        needs_visualization=False,
        is_cross_departmental=False,
        validation_passed=False,
        execution_success=False,
        error_occurred=False,

        # SQL Retry tracking
        sql_retry_count=0,
        max_sql_retries=3,
        validation_feedback=None,

        # Multi-query iteration tracking
        query_iteration_count=0,
        max_query_iterations=3,
        needs_followup_query=False,
        all_query_results=[],
        final_answer_ready=False,

        # Metadata
        workflow_id=str(uuid.uuid4()),
        started_at=datetime.utcnow().isoformat()
    )


def finalize_state(state: WorkflowState) -> WorkflowState:
    """
    Finalize workflow state by adding completion timestamp and duration

    Args:
        state: Current workflow state

    Returns:
        Updated state with completion info
    """
    from datetime import datetime

    state["completed_at"] = datetime.utcnow().isoformat()

    # Calculate duration if both timestamps exist
    if state.get("started_at") and state.get("completed_at"):
        try:
            start = datetime.fromisoformat(state["started_at"])
            end = datetime.fromisoformat(state["completed_at"])
            state["total_duration_ms"] = (end - start).total_seconds() * 1000
        except:
            pass

    return state


def state_summary(state: WorkflowState) -> str:
    """
    Generate a human-readable summary of the workflow state

    Args:
        state: Workflow state to summarize

    Returns:
        String summary
    """
    lines = [
        f"Workflow ID: {state.get('workflow_id', 'N/A')}",
        f"Query: {state.get('user_query', 'N/A')}",
        f"Action: {state.get('orchestrator_action', 'N/A')}",
        f"Domain: {state.get('domain', 'N/A')}",
        f"Validation: {'✓ Passed' if state.get('validation_passed') else '✗ Failed'}",
        f"Execution: {'✓ Success' if state.get('execution_success') else '✗ Failed'}",
        f"Results: {state.get('result_count', 0)} rows",
    ]

    if state.get("error_occurred"):
        lines.append(f"Error: {state.get('error_message', 'Unknown error')}")

    return "\n".join(lines)


__all__ = [
    "WorkflowState",
    "create_initial_state",
    "finalize_state",
    "state_summary"
]
