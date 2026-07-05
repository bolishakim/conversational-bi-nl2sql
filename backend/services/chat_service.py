"""
Chat Service
Integrates LangGraph workflow with FastAPI endpoints
"""
import sys
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator
import time
import asyncio
import json
from decimal import Decimal

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from workflow.graph import compile_workflow
from workflow.state import WorkflowState, create_initial_state
from utils.logger import logger
from utils.token_tracker import aggregate_usage, TokenUsage


def convert_decimals(obj):
    """Recursively convert Decimal and datetime objects to JSON-serializable types"""
    from datetime import datetime, date

    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, date):
        return obj.isoformat()
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_decimals(item) for item in obj)
    return obj


# ============================================================================
# Chat Service
# ============================================================================

class ChatService:
    """
    Chat Service - Integrates LangGraph workflow with API endpoints

    Features:
    - Executes complete agent workflow
    - Formats results for API responses
    - Handles errors gracefully
    - Provides progress tracking
    """

    def __init__(self):
        """Initialize chat service with compiled workflow"""
        logger.info("Initializing Chat Service...")
        self.workflow = compile_workflow()
        logger.info("Chat Service initialized successfully")

    async def process_query(
        self,
        user_query: str,
        user_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        participant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a natural language query through the agent workflow

        Args:
            user_query: Natural language query from user
            user_id: Optional user ID for tracking
            conversation_history: Optional conversation history for context
            participant_id: Optional participant ID (for shared user accounts history filtering)

        Returns:
            Dict with formatted response for API
        """
        start_time = time.time()
        logger.info(f"Processing query: {user_query[:100]}...")

        if conversation_history:
            logger.info(f"Using conversation history with {len(conversation_history)} messages")

        try:
            # Create initial state with conversation history
            initial_state = create_initial_state(
                user_query,
                conversation_history=conversation_history,
                user_id=user_id
            )

            # Execute workflow in thread pool to avoid blocking the event loop
            logger.info("Executing LangGraph workflow...")
            loop = asyncio.get_event_loop()
            final_state = await loop.run_in_executor(
                None, lambda: self.workflow.invoke(initial_state)
            )

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Format response
            response = self._format_response(final_state, processing_time_ms)

            # Save to history if user_id provided
            if user_id:
                try:
                    from services.history_service import get_history_service
                    history_service = get_history_service()
                    # Create detailed history data from full workflow state
                    history_data = self._format_for_history(final_state, response)
                    await history_service.save_query(
                        user_id=user_id,
                        query_data=history_data,
                        participant_id=participant_id
                    )
                    logger.info(f"Query saved to history for user {user_id}, participant {participant_id}")
                except Exception as e:
                    logger.error(f"Failed to save query to history: {e}")
                    # Don't fail the request if history save fails

            # Debug: Log response chart status
            logger.info(f"RESPONSE DEBUG: has_chart={bool(response.get('chart'))}, chart_type={response.get('chart_type')}")
            if response.get('chart'):
                logger.info(f"CHART DEBUG: keys={list(response['chart'].keys())}, data_length={len(response['chart'].get('data', []))}")

            logger.info(f"Query processed successfully in {processing_time_ms}ms")
            return response

        except Exception as e:
            logger.error(f"Error processing query: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Return error response
            return self._format_error_response(
                user_query,
                str(e),
                processing_time_ms
            )

    async def process_query_stream(
        self,
        user_query: str,
        user_id: Optional[str] = None,
        conversation_history: Optional[list] = None,
        participant_id: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Process a natural language query with streaming progress updates

        Args:
            user_query: Natural language query from user
            user_id: Optional user ID for tracking
            conversation_history: Optional conversation history for context
            participant_id: Optional participant ID (for shared user accounts history filtering)

        Yields:
            Server-Sent Event formatted strings with progress updates
        """
        start_time = time.time()
        logger.info(f"Processing query with streaming: {user_query[:100]}...")

        if conversation_history:
            logger.info(f"Using conversation history with {len(conversation_history)} messages")

        try:
            # Yield initial status
            yield self._format_sse({
                "type": "start",
                "message": "Starting query processing...",
                "query": user_query
            })

            # Create initial state with conversation history
            initial_state = create_initial_state(
                user_query,
                conversation_history=conversation_history,
                user_id=user_id
            )

            # Yield orchestrator start
            yield self._format_sse({
                "type": "progress",
                "stage": "orchestrator",
                "status": "running",
                "message": "Analyzing query and determining workflow..."
            })

            # Execute workflow with streaming
            await asyncio.sleep(0.1)  # Allow event to be sent

            # Request-scoped tracking (NOT instance attributes!)
            stage_tracker = {}

            # Run the blocking workflow.stream() in a thread pool so it doesn't
            # block the async event loop. This allows dashboard API calls to
            # proceed concurrently while the AI pipeline is running.
            event_queue: asyncio.Queue = asyncio.Queue()
            loop = asyncio.get_event_loop()

            def _run_workflow_in_thread():
                """Runs the blocking LangGraph workflow and pushes events to the queue."""
                try:
                    state = initial_state
                    for event in self.workflow.stream(
                        initial_state,
                        config={"recursion_limit": 50}
                    ):
                        for node_name, node_state in event.items():
                            if node_state:
                                state.update(node_state)
                                loop.call_soon_threadsafe(
                                    event_queue.put_nowait,
                                    ("event", node_name, dict(state))
                                )
                    # Signal completion
                    loop.call_soon_threadsafe(
                        event_queue.put_nowait,
                        ("done", None, dict(state))
                    )
                except Exception as exc:
                    loop.call_soon_threadsafe(
                        event_queue.put_nowait,
                        ("error", None, exc)
                    )

            # Start the blocking workflow in a thread
            thread_future = loop.run_in_executor(None, _run_workflow_in_thread)

            final_state = initial_state
            while True:
                msg_type, node_name, payload = await event_queue.get()

                if msg_type == "error":
                    raise payload  # Re-raise exception from thread

                if msg_type == "event":
                    final_state = payload
                    progress_update = self._detect_stage_progress_v2(
                        node_name,
                        final_state,
                        stage_tracker
                    )
                    if progress_update:
                        yield self._format_sse(progress_update)
                        await asyncio.sleep(0.05)

                if msg_type == "done":
                    final_state = payload
                    break

            # Wait for the thread to fully finish
            await thread_future

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Yield completion
            yield self._format_sse({
                "type": "progress",
                "stage": "complete",
                "status": "completed",
                "message": f"Query processed successfully in {processing_time_ms}ms"
            })

            # Format and yield final response
            response = self._format_response(final_state, processing_time_ms)
            yield self._format_sse({
                "type": "result",
                "data": response
            })

            # Save query to history (async operation, don't block streaming)
            if user_id:
                try:
                    from services.history_service import get_history_service
                    history_service = get_history_service()
                    # Create detailed history data from full workflow state
                    history_data = self._format_for_history(final_state, response)
                    await history_service.save_query(
                        user_id=user_id,
                        query_data=history_data,
                        participant_id=participant_id
                    )
                    logger.info(f"Query saved to history for user {user_id}, participant {participant_id}")
                except Exception as e:
                    logger.error(f"Failed to save query to history: {e}")
                    # Don't fail the whole request if history save fails

            logger.info(f"Query streamed successfully in {processing_time_ms}ms")

        except Exception as e:
            logger.error(f"Error in streaming query: {e}")
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Yield error
            yield self._format_sse({
                "type": "error",
                "message": str(e),
                "processing_time_ms": processing_time_ms
            })

    def _format_sse(self, data: Dict[str, Any]) -> str:
        """
        Format data as Server-Sent Event

        Args:
            data: Data to send

        Returns:
            SSE formatted string
        """
        # Custom JSON encoder to handle Decimal, date, and datetime types
        from decimal import Decimal
        from datetime import date, datetime

        def convert_to_json_serializable(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, date):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_to_json_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_json_serializable(item) for item in obj]
            return obj

        cleaned_data = convert_to_json_serializable(data)
        return f"data: {json.dumps(cleaned_data)}\n\n"

    def _detect_stage_progress_v2(
        self,
        node_name: str,
        state: Dict[str, Any],
        tracker: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Detect which workflow stage just completed (V2 - iteration-aware, request-scoped)

        Args:
            node_name: Name of the node that just executed
            state: Current workflow state
            tracker: Request-scoped tracker dict (NOT instance attributes!)

        Returns:
            Progress update dict or None
        """
        # Get iteration and retry counts for context
        iteration = state.get("query_iteration_count", 0)
        retry_count = state.get("sql_retry_count", 0)
        max_iterations = state.get("max_query_iterations", 3)

        # Build unique tracking key (iteration + retry aware)
        tracking_key = f"{node_name}_i{iteration}_r{retry_count}"

        # Skip if already reported
        if tracker.get(tracking_key):
            return None

        # Mark as reported
        tracker[tracking_key] = True

        # Build iteration context for messages
        iteration_context = f" [Iteration {iteration + 1}/{max_iterations}]" if iteration > 0 else ""

        # === Node-specific progress detection ===

        if node_name == "orchestrator":
            if state.get("orchestrator_action"):
                return {
                    "type": "progress",
                    "stage": "orchestrator",
                    "status": "completed",
                    "message": f"Routing decision: {state.get('orchestrator_action')}",
                    "details": {
                        "action": state.get("orchestrator_action"),
                        "needs_visualization": state.get("needs_visualization", False)
                    }
                }

        elif node_name == "schema_agent":
            if state.get("retrieved_tables"):
                return {
                    "type": "progress",
                    "stage": "schema_agent",
                    "status": "completed",
                    "message": f"Retrieved {len(state.get('retrieved_tables', []))} tables from '{state.get('domain', 'unknown')}' domain",
                    "details": {
                        "domain": state.get("domain"),
                        "table_count": len(state.get("retrieved_tables", []))
                    }
                }

        elif node_name == "sql_agent":
            if state.get("generated_sql"):
                retry_suffix = f" (retry {retry_count})" if retry_count > 0 else ""
                return {
                    "type": "progress",
                    "stage": "sql_agent",
                    "status": "completed",
                    "message": f"SQL generated{retry_suffix}{iteration_context} using {len(state.get('tables_used', []))} tables",
                    "details": {
                        "tables_used": state.get("tables_used", []),
                        "reasoning_steps": len(state.get("sql_reasoning_steps", [])),
                        "retry_attempt": retry_count,
                        "iteration": iteration
                    }
                }

        elif node_name == "validator":
            if state.get("validation_passed") is not None:
                # Check if validation failed and we're retrying
                if not state.get("validation_passed") and retry_count < state.get("max_sql_retries", 3):
                    return {
                        "type": "progress",
                        "stage": "validator",
                        "status": "retrying",
                        "message": f"Validation failed{iteration_context} - Retrying SQL generation (attempt {retry_count + 1}/{state.get('max_sql_retries', 3)})",
                        "details": {
                            "is_valid": False,
                            "severity": state.get("validation_severity"),
                            "retry_attempt": retry_count,
                            "iteration": iteration,
                            "issues": state.get("validation_issues", [])
                        }
                    }
                else:
                    return {
                        "type": "progress",
                        "stage": "validator",
                        "status": "completed",
                        "message": f"Validation {'passed' if state.get('validation_passed') else 'failed'}{iteration_context}",
                        "details": {
                            "is_valid": state.get("validation_passed"),
                            "severity": state.get("validation_severity"),
                            "iteration": iteration
                        }
                    }

        elif node_name == "executor":
            if state.get("execution_success") is not None:
                if state.get("execution_success"):
                    return {
                        "type": "progress",
                        "stage": "executor",
                        "status": "completed",
                        "message": f"Query executed{iteration_context}: {state.get('result_count', 0)} rows in {state.get('execution_time_ms', 0):.2f}ms",
                        "details": {
                            "row_count": state.get("result_count"),
                            "execution_time_ms": state.get("execution_time_ms"),
                            "iteration": iteration
                        }
                    }
                else:
                    return {
                        "type": "progress",
                        "stage": "executor",
                        "status": "failed",
                        "message": f"Execution failed{iteration_context}: {state.get('execution_error', 'Unknown error')}",
                        "details": {
                            "iteration": iteration
                        }
                    }

        elif node_name == "viz_generator":
            # Visualization generator node - always report completion
            chart_type = state.get("visualization_type", "table")
            has_chart = chart_type and chart_type != "table"
            return {
                "type": "progress",
                "stage": "viz_generator",
                "status": "completed",
                "message": f"Visualization: {chart_type}" if has_chart else "No chart needed (table view)",
                "details": {
                    "chart_type": chart_type,
                    "has_chart": has_chart,
                    "iteration": iteration
                }
            }

        elif node_name == "accumulate_results":
            # NEW: Multi-query iteration node
            all_results = state.get("all_query_results", [])
            if all_results:
                latest_result = all_results[-1]
                return {
                    "type": "progress",
                    "stage": "accumulate_results",
                    "status": "completed",
                    "message": f"Accumulated results for iteration {iteration + 1}: {latest_result.get('row_count', 0)} rows",
                    "details": {
                        "total_queries": len(all_results),
                        "iteration": iteration,
                        "row_count": latest_result.get("row_count", 0)
                    }
                }

        elif node_name == "iteration_decision":
            # NEW: Multi-query iteration decision node
            needs_followup = state.get("needs_followup_query", False)
            final_ready = state.get("final_answer_ready", False)

            if final_ready:
                return {
                    "type": "progress",
                    "stage": "iteration_decision",
                    "status": "completed",
                    "message": f"Final answer ready after {iteration + 1} iterations",
                    "details": {
                        "needs_followup": False,
                        "final_answer_ready": True,
                        "iteration": iteration,
                        "total_queries": len(state.get("all_query_results", []))
                    }
                }
            elif needs_followup and iteration < max_iterations - 1:
                reason = state.get("followup_query_reason", "No reason provided")
                return {
                    "type": "progress",
                    "stage": "iteration_decision",
                    "status": "needs_followup",
                    "message": f"Follow-up query needed: {reason[:100]}...",
                    "details": {
                        "needs_followup": True,
                        "reason": reason,
                        "iteration": iteration,
                        "max_iterations": max_iterations
                    }
                }
            else:
                return {
                    "type": "progress",
                    "stage": "iteration_decision",
                    "status": "completed",
                    "message": f"Iteration limit reached ({max_iterations}), finalizing answer",
                    "details": {
                        "needs_followup": needs_followup,
                        "iteration": iteration,
                        "hit_limit": True
                    }
                }

        elif node_name == "prepare_next_iteration":
            # NEW: Prepare next iteration node
            next_iteration = state.get("query_iteration_count", 0)
            return {
                "type": "progress",
                "stage": "prepare_next_iteration",
                "status": "completed",
                "message": f"Preparing iteration {next_iteration + 1}/{max_iterations}",
                "details": {
                    "next_iteration": next_iteration,
                    "max_iterations": max_iterations
                }
            }

        elif node_name == "analyst":
            # LEGACY analyst node (kept for compatibility)
            if state.get("key_insights"):
                return {
                    "type": "progress",
                    "stage": "analyst",
                    "status": "completed",
                    "message": f"Analysis complete: {len(state.get('key_insights', []))} insights generated",
                    "details": {
                        "insights_count": len(state.get("key_insights", [])),
                        "recommendations_count": len(state.get("recommendations", []))
                    }
                }

        # No progress update for this node execution
        return None

    def _detect_stage_progress(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        DEPRECATED: Old method using instance attributes (kept for backwards compatibility)
        Use _detect_stage_progress_v2() instead
        """
        # This method is deprecated but kept to avoid breaking existing code
        return None

    def _format_response(
        self,
        state: WorkflowState,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Format workflow state into API response

        Args:
            state: Final workflow state
            processing_time_ms: Total processing time

        Returns:
            Formatted response dict
        """
        # Check if there was an error
        if state.get("error_occurred"):
            error_message = state.get("error_message", "Unknown error")
            # Aggregate token usage even for errors
            token_stats = self._aggregate_token_usage(state)
            return {
                # Frontend-expected fields (required by QueryResponse model)
                "query_id": state.get("query_id", ""),
                "user_query": state["user_query"],
                "sql_query": state.get("generated_sql", ""),
                "results": {
                    "columns": [],
                    "data": [],
                    "row_count": 0
                },
                "chart": None,
                "analysis": {
                    "summary": f"Error: {error_message}",
                    "key_insights": [],
                    "recommendations": [],
                    "data_quality_notes": []
                },
                "execution_time_ms": 0,

                # Backend fields
                "query": state["user_query"],
                "domain": state.get("domain", "unknown"),
                "retrieved_tables": state.get("retrieved_tables", []),
                "generated_sql": state.get("generated_sql", ""),
                "execution_status": "error",
                "error_stage": state.get("error_stage", "unknown"),
                "error_message": error_message,
                "result_data": None,
                "chart_type": None,
                "processing_time_ms": processing_time_ms,
                "token_usage": token_stats
            }

        # Check if it was a direct answer (no SQL needed)
        if state.get("orchestrator_action") == "DIRECT_ANSWER":
            direct_response = state.get("direct_response", "Query answered directly")
            # Aggregate token usage for direct answers too
            token_stats = self._aggregate_token_usage(state)
            return {
                # Frontend-expected fields (required by QueryResponse model)
                "query_id": state.get("query_id", ""),
                "user_query": state["user_query"],
                "sql_query": "",  # No SQL for direct answers
                "results": {
                    "columns": [],
                    "data": [],
                    "row_count": 0
                },
                "chart": None,
                "analysis": {
                    "summary": direct_response,
                    "key_insights": [],
                    "recommendations": [],
                    "data_quality_notes": []
                },
                "execution_time_ms": 0,

                # Backend fields
                "query": state["user_query"],
                "domain": "general",
                "retrieved_tables": [],
                "generated_sql": None,
                "execution_status": "direct_answer",
                "result_data": {
                    "message": direct_response
                },
                "chart_type": None,
                "processing_time_ms": processing_time_ms,
                "token_usage": token_stats
            }

        # Check if validation failed
        if not state.get("validation_passed"):
            validation_summary = state.get("validation_summary", "SQL validation failed")
            # Aggregate token usage for validation failures
            token_stats = self._aggregate_token_usage(state)
            return {
                # Frontend-expected fields
                "query_id": state.get("query_id", ""),
                "user_query": state["user_query"],
                "sql_query": state.get("generated_sql", ""),
                "results": {
                    "columns": [],
                    "data": [],
                    "row_count": 0
                },
                "chart": None,
                "analysis": {
                    "summary": validation_summary,
                    "key_insights": [],
                    "recommendations": [],
                    "data_quality_notes": []
                },
                "execution_time_ms": 0,

                # Backend fields
                "query": state["user_query"],
                "domain": state.get("domain", "unknown"),
                "retrieved_tables": state.get("retrieved_tables", []),
                "generated_sql": state.get("generated_sql", ""),
                "execution_status": "validation_failed",
                "validation_issues": state.get("validation_issues", []),
                "validation_summary": validation_summary,
                "result_data": None,
                "chart_type": None,
                "processing_time_ms": processing_time_ms,
                "token_usage": token_stats
            }

        # Check if execution failed
        if not state.get("execution_success"):
            execution_error = state.get("execution_error", "Query execution failed")
            # Aggregate token usage for execution failures
            token_stats = self._aggregate_token_usage(state)
            return {
                # Frontend-expected fields (required by QueryResponse model)
                "query_id": state.get("query_id", ""),
                "user_query": state["user_query"],
                "sql_query": state.get("validated_sql", ""),
                "results": {
                    "columns": [],
                    "data": [],
                    "row_count": 0
                },
                "chart": None,
                "analysis": {
                    "summary": f"Execution failed: {execution_error}",
                    "key_insights": [],
                    "recommendations": [],
                    "data_quality_notes": []
                },
                "execution_time_ms": 0,

                # Backend fields
                "query": state["user_query"],
                "domain": state.get("domain", "unknown"),
                "retrieved_tables": state.get("retrieved_tables", []),
                "generated_sql": state.get("validated_sql", ""),
                "execution_status": "execution_failed",
                "execution_error": execution_error,
                "result_data": None,
                "chart_type": None,
                "processing_time_ms": processing_time_ms,
                "token_usage": token_stats
            }

        # Aggregate token usage and costs
        token_stats = self._aggregate_token_usage(state)

        # Convert result_data to frontend format (columns + data as 2D array)
        query_results = state.get("query_results", [])
        columns = list(query_results[0].keys()) if query_results else []
        data_rows = [[convert_decimals(row[col]) for col in columns] for row in query_results] if query_results else []

        # Success case - format complete response
        return {
            # Frontend-expected fields (matching QueryResponse interface)
            "query_id": state.get("query_id", ""),
            "user_query": state["user_query"],
            "sql_query": state.get("validated_sql", ""),
            "results": {
                "columns": columns,
                "data": data_rows,
                "row_count": state.get("result_count", 0)
            },
            "chart": self._convert_to_plotly(state),
            "analysis": {
                "summary": state.get("analysis_summary", ""),
                "key_insights": state.get("key_insights", []),
                "recommendations": state.get("recommendations", []),
                "data_quality_notes": state.get("data_quality_notes", [])
            },
            "execution_time_ms": int(state.get("execution_time_ms", 0)),

            # Additional backend fields for history/debugging
            "query": state["user_query"],
            "domain": state.get("domain", "unknown"),
            "retrieved_tables": state.get("retrieved_tables", []),
            "generated_sql": state.get("validated_sql", ""),
            "sql_explanation": state.get("sql_explanation", ""),
            "execution_status": "success",
            "result_data": {
                "rows": convert_decimals(state.get("query_results", [])),
                "row_count": state.get("result_count", 0),
                "execution_time_ms": int(state.get("execution_time_ms", 0))
            },
            "chart_type": state.get("visualization_type") or self._determine_chart_type(state),
            "chart_config": convert_decimals(state.get("chart_config", {})),
            "processing_time_ms": processing_time_ms,
            "workflow_details": {
                "orchestrator_action": state.get("orchestrator_action"),
                "needs_visualization": state.get("needs_visualization", False),
                "tables_used": state.get("tables_used", []),
                "is_cross_departmental": state.get("is_cross_departmental", False)
            },
            "token_usage": token_stats
        }

    def _format_for_history(
        self,
        state: WorkflowState,
        api_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Format full workflow state for history persistence (thesis research data)

        This method extracts ALL detailed workflow information for thesis analysis,
        unlike _format_response which only returns simplified data for the API.

        Args:
            state: Full workflow state with all intermediate results
            api_response: Simplified API response from _format_response

        Returns:
            Complete data dict for history_service.save_query
        """
        # Start with the API response as base
        history_data = api_response.copy()

        # Add all detailed workflow fields from state
        history_data.update({
            # Orchestrator details
            "orchestrator_action": state.get("orchestrator_action"),
            "orchestrator_reasoning": state.get("orchestrator_reasoning"),
            "needs_visualization": state.get("needs_visualization", False),

            # Schema retrieval details
            "anchor_tables": state.get("anchor_tables"),
            "rag_retrieved_tables": state.get("rag_retrieved_tables"),
            "similarity_scores": state.get("similarity_scores"),
            "retrieval_strategy": state.get("retrieval_strategy"),

            # SQL generation details
            "sql_reasoning_steps": state.get("sql_reasoning_steps"),
            "tables_used": state.get("tables_used"),
            "sql_assumptions": state.get("sql_assumptions"),
            "sql_retry_count": state.get("sql_retry_count", 0),

            # Validation details
            "validation_passed": state.get("validation_passed"),
            "validation_severity": state.get("validation_severity"),
            "validation_issues": state.get("validation_issues"),
            "validation_summary": state.get("validation_summary"),

            # Multi-query iteration details
            "query_iteration_count": state.get("query_iteration_count", 0),
            "needs_followup_query": state.get("needs_followup_query", False),
            "followup_query_reason": state.get("followup_query_reason"),
            "all_query_results": state.get("all_query_results"),

            # Analysis details
            "analysis_reasoning_steps": state.get("analysis_reasoning_steps"),
            "analysis_summary": state.get("analysis_summary"),
            "key_insights": state.get("key_insights"),
            "recommendations": state.get("recommendations"),
            "data_quality_notes": state.get("data_quality_notes"),

            # Visualization details
            "chart_reasoning": state.get("chart_reasoning"),
            "visualization_code": state.get("visualization_code"),
            # Override chart_config with Plotly-formatted chart for frontend rendering
            "chart_config": api_response.get("chart"),

            # Cross-departmental flag
            "is_cross_departmental": state.get("is_cross_departmental", False),

            # Token usage summary fields
            "total_input_tokens": api_response.get("token_usage", {}).get("total_input_tokens"),
            "total_output_tokens": api_response.get("token_usage", {}).get("total_output_tokens"),
            "total_tokens": api_response.get("token_usage", {}).get("total_tokens"),
            "total_cost": api_response.get("token_usage", {}).get("total_cost_usd"),
            "llm_calls_count": api_response.get("token_usage", {}).get("total_llm_calls"),
        })

        # Convert all Decimal objects to float for JSON serialization
        return convert_decimals(history_data)

    def _format_error_response(
        self,
        user_query: str,
        error_message: str,
        processing_time_ms: int
    ) -> Dict[str, Any]:
        """
        Format error response

        Args:
            user_query: Original user query
            error_message: Error message
            processing_time_ms: Processing time

        Returns:
            Error response dict
        """
        return {
            # Frontend-expected fields (required by QueryResponse model)
            "query_id": "",
            "user_query": user_query,
            "sql_query": "",
            "results": {
                "columns": [],
                "data": [],
                "row_count": 0
            },
            "chart": None,
            "analysis": {
                "summary": f"Error: {error_message}",
                "key_insights": [],
                "recommendations": [],
                "data_quality_notes": []
            },
            "execution_time_ms": 0,

            # Backend fields
            "query": user_query,
            "domain": "unknown",
            "retrieved_tables": [],
            "generated_sql": None,
            "execution_status": "error",
            "error_message": error_message,
            "result_data": None,
            "chart_type": None,
            "processing_time_ms": processing_time_ms
        }

    def _aggregate_token_usage(self, state: WorkflowState) -> Dict[str, Any]:
        """
        Aggregate token usage across all LLM calls in the workflow

        Args:
            state: Workflow state containing token_usage list

        Returns:
            Dictionary with aggregated token statistics and costs
        """
        token_usage_list = state.get("token_usage", [])

        if not token_usage_list:
            return {
                "total_tokens": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cache_tokens": 0,
                "total_cost_usd": 0.0,
                "total_llm_calls": 0,
                "by_agent": {},
                "by_model": {}
            }

        # Reconstruct TokenUsage objects for aggregation
        usage_objects = []
        for usage_data in token_usage_list:
            usage = TokenUsage(
                agent_name=usage_data.get("agent_name", "unknown"),
                model=usage_data.get("model", "claude-sonnet-4-5"),
                input_tokens=usage_data.get("input_tokens", 0),
                cache_creation_input_tokens=usage_data.get("cache_creation_input_tokens", 0),
                cache_read_input_tokens=usage_data.get("cache_read_input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0)
            )
            usage_objects.append(usage)

        # Aggregate using utility function
        stats = aggregate_usage(usage_objects)

        return {
            "total_tokens": stats["total_tokens"],
            "total_input_tokens": stats["total_input_tokens"],
            "total_output_tokens": stats["total_output_tokens"],
            "total_cache_creation_tokens": stats["total_cache_creation_tokens"],
            "total_cache_read_tokens": stats["total_cache_read_tokens"],
            "total_cost_usd": stats["total_cost"],
            "total_llm_calls": stats["total_llm_calls"],
            "by_agent": stats["by_agent"],
            "by_model": stats["by_model"],
            "details": token_usage_list  # Include raw details for debugging
        }

    def _convert_to_plotly(self, state: WorkflowState) -> Optional[Dict[str, Any]]:
        """
        Convert chart_config to Plotly format expected by frontend

        Args:
            state: Workflow state with chart_config

        Returns:
            Dict with 'data' and 'layout' for Plotly, or None
        """
        chart_type = state.get("visualization_type") or self._determine_chart_type(state)
        chart_config = state.get("chart_config", {})
        results = state.get("query_results", [])

        logger.info(f"Converting to Plotly: chart_type={chart_type}, has_results={bool(results)}, num_results={len(results) if results else 0}")
        logger.info(f"Chart config: {chart_config}")

        if not chart_type or chart_type == "table" or not results:
            logger.info(f"Skipping chart conversion: chart_type={chart_type}, results={bool(results)}")
            return None

        try:
            # Extract data from results
            if not results:
                return None

            # Get column names
            columns = list(results[0].keys())

            # Simple conversion for bar chart (most common case)
            if chart_type == "bar" and len(columns) >= 2:
                from decimal import Decimal

                x_col = chart_config.get("x_axis") or columns[0]
                y_col = chart_config.get("y_axis") or columns[1]

                # Ensure the columns exist in results
                if x_col not in columns or y_col not in columns:
                    logger.warning(f"Chart config columns ({x_col}, {y_col}) not in results. Using smart detection.")
                    # Smart fallback: find the best label column (text/categorical)
                    # and the best value column (numeric, not an ID)
                    numeric_cols = []
                    text_cols = []
                    for col in columns:
                        sample = results[0][col]
                        is_numeric = isinstance(sample, (int, float, Decimal))
                        # Heuristic: columns ending in 'id' are IDs, not values
                        is_id = col.lower().endswith("id") or col.lower() == "id"
                        if is_numeric and not is_id:
                            numeric_cols.append(col)
                        elif not is_numeric or is_id:
                            text_cols.append(col)

                    # Prefer 'name' columns for labels, then any text column
                    label_col = None
                    for col in text_cols:
                        if "name" in col.lower():
                            label_col = col
                            break
                    if not label_col and text_cols:
                        label_col = text_cols[0]

                    # For value, prefer columns with aggregate-like names
                    value_col = None
                    value_keywords = ["total", "sum", "count", "avg", "revenue", "stock", "quantity", "sales", "amount"]
                    for col in numeric_cols:
                        if any(kw in col.lower() for kw in value_keywords):
                            value_col = col
                            break
                    if not value_col and numeric_cols:
                        value_col = numeric_cols[0]

                    x_col = label_col or columns[0]
                    y_col = value_col or columns[1]
                    logger.info(f"Smart detection chose x={x_col}, y={y_col}")

                # Additional check: if y_col is not numeric, swap x and y
                sample_y = results[0].get(y_col)
                sample_x = results[0].get(x_col)
                if not isinstance(sample_y, (int, float, Decimal)) and isinstance(sample_x, (int, float, Decimal)):
                    logger.info(f"Swapping axes: x_col was {x_col} (numeric), y_col was {y_col} (text)")
                    x_col, y_col = y_col, x_col

                x_data = [str(row[x_col]) for row in results]
                y_data = [float(row[y_col]) if isinstance(row[y_col], Decimal) else row[y_col] for row in results]

                # Get colors from chart_config or use default blue
                bar_colors = chart_config.get("colors", ["#3b82f6"] * len(x_data))
                if isinstance(bar_colors, list) and len(bar_colors) != len(x_data):
                    bar_colors = "#3b82f6"  # Fallback to single color if mismatch

                # Decide orientation: use horizontal bars when labels are long
                avg_label_len = sum(len(label) for label in x_data) / max(len(x_data), 1)
                use_horizontal = avg_label_len > 12 and len(x_data) >= 5

                if use_horizontal:
                    # Horizontal bar: categories on Y, values on X
                    # Reverse data so highest value is at top
                    x_data_rev = list(reversed(x_data))
                    y_data_rev = list(reversed(y_data))
                    bar_colors_rev = list(reversed(bar_colors)) if isinstance(bar_colors, list) else bar_colors

                    plotly_data = {
                        "data": [{
                            "x": y_data_rev,
                            "y": x_data_rev,
                            "type": "bar",
                            "orientation": "h",
                            "marker": {"color": bar_colors_rev},
                            "text": y_data_rev,
                            "textposition": "outside",
                            "texttemplate": "%{x:,.0f}",
                            "hovertemplate": "<b>%{y}</b><br>" + y_col + ": %{x:,.2f}<extra></extra>"
                        }],
                        "layout": {
                            "title": {
                                "text": chart_config.get("title", "Results"),
                                "font": {"size": 16, "color": "#1f2937"}
                            },
                            "xaxis": {
                                "title": chart_config.get("y_axis_label", y_col.replace("_", " ").title()),
                                "automargin": True
                            },
                            "yaxis": {
                                "title": "",
                                "automargin": True
                            },
                            "margin": {"l": 160, "r": 60, "t": 60, "b": 60},
                            "showlegend": False,
                            "plot_bgcolor": "#f9fafb",
                            "paper_bgcolor": "#ffffff"
                        }
                    }
                else:
                    # Vertical bar (default): categories on X, values on Y
                    plotly_data = {
                        "data": [{
                            "x": x_data,
                            "y": y_data,
                            "type": "bar",
                            "marker": {"color": bar_colors},
                            "text": y_data,
                            "textposition": "outside",
                            "texttemplate": "%{y:,.0f}",
                            "hovertemplate": "<b>%{x}</b><br>" + y_col + ": %{y:,.2f}<extra></extra>"
                        }],
                        "layout": {
                            "title": {
                                "text": chart_config.get("title", "Results"),
                                "font": {"size": 16, "color": "#1f2937"}
                            },
                            "xaxis": {
                                "title": chart_config.get("x_axis_label", x_col.replace("_", " ").title()),
                                "tickangle": -45 if len(x_data) > 5 else 0,
                                "automargin": True
                            },
                            "yaxis": {
                                "title": chart_config.get("y_axis_label", y_col.replace("_", " ").title()),
                                "automargin": True
                            },
                            "margin": {"l": 80, "r": 20, "t": 60, "b": 100},
                            "showlegend": False,
                            "plot_bgcolor": "#f9fafb",
                            "paper_bgcolor": "#ffffff"
                        }
                    }
                logger.info(f"Created {'horizontal' if use_horizontal else 'vertical'} bar chart with {len(x_data)} data points (labels={x_col}, values={y_col})")
                return plotly_data

            # Line chart
            elif chart_type == "line" and len(columns) >= 2:
                from decimal import Decimal

                x_col = chart_config.get("x_axis") or columns[0]
                y_col = chart_config.get("y_axis") or columns[1]

                if x_col not in columns or y_col not in columns:
                    logger.warning(f"Chart config columns ({x_col}, {y_col}) not in results. Using default.")
                    x_col = columns[0]
                    y_col = columns[1]

                x_data = [str(row[x_col]) for row in results]
                y_data = [float(row[y_col]) if isinstance(row[y_col], Decimal) else row[y_col] for row in results]

                return {
                    "data": [{
                        "x": x_data,
                        "y": y_data,
                        "type": "scatter",
                        "mode": "lines+markers",
                        "line": {"color": "#3b82f6", "width": 2},
                        "marker": {"size": 8, "color": "#3b82f6"},
                        "hovertemplate": "<b>%{x}</b><br>" + y_col + ": %{y:,.2f}<extra></extra>"
                    }],
                    "layout": {
                        "title": {
                            "text": chart_config.get("title", "Trend"),
                            "font": {"size": 16, "color": "#1f2937"}
                        },
                        "xaxis": {
                            "title": chart_config.get("x_axis_label", x_col.replace("_", " ").title()),
                            "automargin": True
                        },
                        "yaxis": {
                            "title": chart_config.get("y_axis_label", y_col.replace("_", " ").title()),
                            "automargin": True
                        },
                        "margin": {"l": 80, "r": 20, "t": 60, "b": 80},
                        "showlegend": False,
                        "plot_bgcolor": "#f9fafb",
                        "paper_bgcolor": "#ffffff"
                    }
                }

            # Pie chart
            elif chart_type == "pie" and len(columns) >= 2:
                from decimal import Decimal

                # For pie charts, use labels/values from chart_config, or fallback to columns
                label_col = chart_config.get("x_axis") or columns[0]
                value_col = chart_config.get("y_axis") or columns[1]

                if label_col not in columns or value_col not in columns:
                    logger.warning(f"Chart config columns ({label_col}, {value_col}) not in results. Using default.")
                    label_col = columns[0]
                    value_col = columns[1]

                labels = [str(row[label_col]) for row in results]
                values = [float(row[value_col]) if isinstance(row[value_col], Decimal) else row[value_col] for row in results]

                # Get colors from chart_config or use default color palette
                pie_colors = chart_config.get("colors", None)

                return {
                    "data": [{
                        "labels": labels,
                        "values": values,
                        "type": "pie",
                        "marker": {"colors": pie_colors} if pie_colors else {},
                        "textposition": "inside",
                        "texttemplate": "%{label}<br>%{percent}",
                        "hovertemplate": "<b>%{label}</b><br>Value: %{value:,.2f}<br>Percentage: %{percent}<extra></extra>"
                    }],
                    "layout": {
                        "title": {
                            "text": chart_config.get("title", "Distribution"),
                            "font": {"size": 16, "color": "#1f2937"}
                        },
                        "margin": {"l": 50, "r": 50, "t": 60, "b": 50},
                        "showlegend": True,
                        "legend": {"orientation": "v", "x": 1.02, "y": 0.5},
                        "paper_bgcolor": "#ffffff"
                    }
                }

            return None

        except Exception as e:
            logger.error(f"Error converting chart to Plotly format: {e}")
            return None

    def _determine_chart_type(self, state: WorkflowState) -> Optional[str]:
        """
        Determine appropriate chart type based on query results

        Args:
            state: Workflow state

        Returns:
            Chart type string or None
        """
        # Simple heuristic based on needs_visualization flag and result structure
        if not state.get("needs_visualization"):
            return None

        results = state.get("query_results", [])
        if not results:
            return None

        # Check number of columns
        if len(results) > 0:
            num_columns = len(results[0].keys())

            # 2 columns (category + value) -> bar chart
            if num_columns == 2:
                return "bar"
            # 3+ columns -> table or line chart
            elif num_columns >= 3:
                # Check if there's a time/date column for line chart
                first_row = results[0]
                for key in first_row.keys():
                    if any(time_word in key.lower() for time_word in ["date", "time", "year", "month"]):
                        return "line"
                return "table"

        return "table"


# ============================================================================
# Factory Function
# ============================================================================

_chat_service_instance = None

def get_chat_service() -> ChatService:
    """
    Get or create chat service singleton

    Returns:
        ChatService instance
    """
    global _chat_service_instance

    if _chat_service_instance is None:
        _chat_service_instance = ChatService()

    return _chat_service_instance


__all__ = ["ChatService", "get_chat_service"]
