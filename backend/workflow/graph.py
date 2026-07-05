"""
LangGraph Workflow
Orchestrates the NL2SQL agent pipeline
"""
import sys
from pathlib import Path
from typing import Literal

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from langgraph.graph import StateGraph, END
from workflow.state import WorkflowState
from utils.logger import logger

# Import agents
from agents.orchestrator.agent import create_orchestrator
from agents.schema.agent import create_schema_agent
from agents.sql_agent.agent import create_sql_agent
from agents.validator_agent.agent import create_validator
from agents.executor_agent.agent import create_executor
from agents.analyst_agent.agent import create_analyst
from agents.viz_generator_agent.agent import create_viz_generator


# ============================================================================
# Agent Node Functions
# ============================================================================

def orchestrator_node(state: WorkflowState) -> WorkflowState:
    """
    Orchestrator Agent Node
    Routes the query and decides the workflow path
    """
    logger.info("Executing Orchestrator node...")

    try:
        orchestrator = create_orchestrator()

        # Prepare input
        from agents.orchestrator.agent import OrchestratorInput, ConversationMessage

        messages = [
            ConversationMessage(**msg) for msg in state.get("conversation_history", [])
        ]

        orchestrator_input = OrchestratorInput(
            query=state["user_query"],
            conversation_history=messages,
            has_previous_results=False  # TODO: Check if previous results exist
        )

        # Execute orchestrator
        output = orchestrator.analyze(orchestrator_input)

        # Update state
        state["orchestrator_action"] = output.action
        state["orchestrator_reasoning"] = output.reasoning
        state["needs_visualization"] = output.needs_visualization
        state["direct_response"] = output.direct_response

        # Track token usage
        if output.token_usage:
            if "token_usage" not in state or state["token_usage"] is None:
                state["token_usage"] = []
            state["token_usage"].append(output.token_usage)

        logger.info(f"Orchestrator decided: {output.action}")
        return state

    except Exception as e:
        logger.error(f"Orchestrator node error: {e}")
        state["error_occurred"] = True
        state["error_stage"] = "orchestrator"
        state["error_message"] = f"Failed to route query: {str(e)}"
        return state


def schema_agent_node(state: WorkflowState) -> WorkflowState:
    """
    Schema Agent Node
    Retrieves relevant tables using RAG (with conversation history for domain inference)
    """
    logger.info("Executing Schema Agent node...")

    try:
        schema_agent = create_schema_agent()

        # Prepare input (with conversation history for follow-up queries)
        from agents.schema.agent import SchemaAgentInput

        schema_input = SchemaAgentInput(
            query=state["user_query"],
            conversation_history=state.get("conversation_history", []),
            include_similarity_scores=False
        )

        # Execute schema agent
        output = schema_agent.retrieve_schema(schema_input)

        # Update state
        state["domain"] = output.domain
        state["is_cross_departmental"] = output.is_cross_departmental
        state["retrieved_tables"] = output.anchor_tables + output.rag_retrieved_tables
        state["schema_context"] = output.formatted_schema

        # PHASE 2 OPTIMIZATION: Store raw table metadata for post-SQL filtering
        # This allows validator to use only tables that were actually used in SQL
        state["all_retrieved_table_metadata"] = [
            {
                "full_name": table.full_name,
                "schema_name": table.schema_name,
                "table_name": table.table_name,
                "description": table.description,
                "business_terms": table.business_terms,
                "common_questions": table.common_questions,
                "key_columns": table.key_columns,
                "sample_values": table.sample_values,
                "row_count": table.row_count,
                "tier": table.tier
            }
            for table in output.tables
        ]

        logger.info(f"Schema Agent retrieved {output.total_tables} tables for domain: {output.domain}")
        return state

    except Exception as e:
        logger.error(f"Schema Agent node error: {e}")
        state["error_occurred"] = True
        state["error_stage"] = "schema_agent"
        state["error_message"] = f"Failed to retrieve schema: {str(e)}"
        return state


def sql_agent_node(state: WorkflowState) -> WorkflowState:
    """
    SQL Agent Node
    Generates SQL query with chain-of-thought reasoning
    Supports retry with validation feedback
    """
    # Check if this is a retry (validation_issues exist and validation didn't pass)
    validation_issues = state.get("validation_issues", [])
    validation_passed = state.get("validation_passed", True)  # First run defaults to True (no validation yet)
    is_retry = len(validation_issues) > 0 and not validation_passed

    # Get current retry count
    retry_count = state.get("sql_retry_count", 0)

    # If this is a retry, increment the count
    if is_retry:
        retry_count += 1
        state["sql_retry_count"] = retry_count
        # Set validation feedback for the agent
        state["validation_feedback"] = validation_issues
        logger.info(f"Executing SQL Agent node (RETRY {retry_count} with {len(validation_issues)} validation issues)...")
    else:
        logger.info("Executing SQL Agent node...")

    try:
        sql_agent = create_sql_agent()

        # Prepare input
        from agents.sql_agent.agent import SQLAgentInput

        sql_input = SQLAgentInput(
            query=state["user_query"],
            schema_context=state["schema_context"],
            domain=state["domain"],
            query_type="factual",  # TODO: Determine query type
            conversation_history=state.get("conversation_history", []),
            validation_feedback=state.get("validation_feedback"),
            execution_error=state.get("execution_error"),  # Pass execution error for learning
            previous_sql=state.get("generated_sql") if is_retry else None,
            retry_attempt=retry_count,
            query_iteration=state.get("query_iteration_count", 0),
            max_iterations=state.get("max_query_iterations", 3),
            followup_query_reason=state.get("followup_query_reason")
        )

        # Execute SQL agent
        output = sql_agent.generate_sql(sql_input)

        # Update state
        state["sql_reasoning_steps"] = output.reasoning_steps
        state["generated_sql"] = output.sql
        state["sql_explanation"] = output.explanation
        state["tables_used"] = output.tables_used
        state["sql_assumptions"] = output.key_assumptions

        # Track token usage
        if output.token_usage:
            if "token_usage" not in state or state["token_usage"] is None:
                state["token_usage"] = []
            state["token_usage"].append(output.token_usage)

        logger.info(f"✅ SQL Agent generated query using {len(output.tables_used)} tables")
        return state

    except Exception as e:
        logger.error(f"❌ SQL Agent node error: {e}")
        state["error_occurred"] = True
        state["error_stage"] = "sql_agent"
        state["error_message"] = f"Failed to generate SQL: {str(e)}"
        return state


def validator_node(state: WorkflowState) -> WorkflowState:
    """
    Validator Agent Node
    Validates SQL for safety and correctness

    OPTIMIZATION: Only pass schema for tables actually used in the SQL
    to reduce token usage (Phase 2 optimization)
    """
    logger.info("Executing Validator node...")

    try:
        validator = create_validator()

        # Prepare input
        from agents.validator_agent.agent import ValidatorInput
        from utils.rag_retriever import rag_retriever

        # PHASE 2 OPTIMIZATION: Filter schema to only include tables used in SQL
        # This significantly reduces token usage for validation
        tables_used = state.get("tables_used", [])

        if tables_used:
            # Get all retrieved tables from schema agent
            from agents.schema.agent import SchemaAgentOutput

            # Retrieve only the tables that were actually used
            all_retrieved_tables = state.get("all_retrieved_table_metadata", [])

            if all_retrieved_tables:
                # Filter to only used tables
                used_tables_metadata = [
                    table for table in all_retrieved_tables
                    if table.get("full_name") in tables_used
                ]

                # Format minimal schema context (only used tables)
                schema_summary = rag_retriever.format_schema_context(used_tables_metadata)
                logger.info(f"Validator using filtered schema: {len(used_tables_metadata)} tables (instead of {len(all_retrieved_tables)})")
            else:
                # Fallback to full schema if metadata not available
                schema_summary = state.get("schema_context", "")
                logger.warning("Using full schema for validation (table metadata not available)")
        else:
            # No tables_used info, use full schema
            schema_summary = state.get("schema_context", "")
            logger.warning("Using full schema for validation (no tables_used info)")

        # Fallback to simple list if schema_context is not available
        if not schema_summary:
            schema_summary = f"Available tables: {', '.join(state.get('retrieved_tables', []))}"

        validator_input = ValidatorInput(
            user_query=state["user_query"],
            sql=state["generated_sql"],
            schema_summary=schema_summary
        )

        # Execute validator
        output = validator.validate(validator_input)

        # Update state
        state["validation_passed"] = output.is_valid
        state["validation_severity"] = output.severity
        state["validation_issues"] = [
            {
                "category": issue.category,
                "severity": issue.severity,
                "message": issue.message,
                "suggestion": issue.suggestion
            }
            for issue in output.issues
        ]
        state["validation_summary"] = output.summary
        state["validated_sql"] = output.validated_sql

        # Track token usage
        if output.token_usage:
            if "token_usage" not in state or state["token_usage"] is None:
                state["token_usage"] = []
            state["token_usage"].append(output.token_usage)

        logger.info(f"Validator result: is_valid={output.is_valid}, severity={output.severity}")
        return state

    except Exception as e:
        logger.error(f"Validator node error: {e}")
        state["error_occurred"] = True
        state["error_stage"] = "validator"
        state["error_message"] = f"Failed to validate SQL: {str(e)}"
        return state


def executor_node(state: WorkflowState) -> WorkflowState:
    """
    Executor Agent Node
    Executes validated SQL query
    """
    logger.info("Executing Executor node...")

    try:
        executor = create_executor()

        # Prepare input
        from agents.executor_agent.agent import ExecutorInput

        executor_input = ExecutorInput(
            sql=state["validated_sql"],
            user_query=state["user_query"],
            timeout_seconds=30,
            max_rows=1000
        )

        # Execute SQL
        output = executor.execute(executor_input)

        # Update state
        state["execution_success"] = output.success
        state["query_results"] = output.results
        state["result_count"] = output.row_count
        state["execution_time_ms"] = output.execution_time_ms

        if not output.success:
            state["execution_error"] = output.error_message
            logger.error(f"SQL execution failed: {output.error_message}")
        else:
            logger.info(f"SQL executed successfully: {output.row_count} rows in {output.execution_time_ms:.2f}ms")
            if output.was_truncated:
                logger.warning(f"Results were truncated to {output.row_count} rows")

        return state

    except Exception as e:
        logger.error(f"Executor node error: {e}")
        state["error_occurred"] = True
        state["error_stage"] = "executor"
        state["error_message"] = f"Failed to execute SQL: {str(e)}"
        state["execution_success"] = False
        return state


def viz_generator_node(state: WorkflowState) -> WorkflowState:
    """
    Visualization Generator Node
    Intelligently selects chart type and generates visualization config
    """
    logger.info("Generating visualization configuration...")

    try:
        # Only generate viz if execution succeeded
        if not state.get("execution_success"):
            logger.info("Skipping visualization - execution failed")
            return state

        viz_generator = create_viz_generator()

        # Prepare input
        from agents.viz_generator_agent.agent import VizGeneratorInput

        viz_input = VizGeneratorInput(
            user_query=state["user_query"],
            sql_query=state.get("validated_sql", state.get("generated_sql", "")),
            results=state.get("query_results", []),
            row_count=state.get("result_count", 0)
        )

        # Execute visualization generator
        output = viz_generator.generate_visualization(viz_input)

        # Update state
        state["visualization_type"] = output.chart_type
        state["chart_config"] = output.chart_config

        # Track token usage
        if output.token_usage:
            if "token_usage" not in state or state["token_usage"] is None:
                state["token_usage"] = []
            state["token_usage"].append(output.token_usage)

        logger.info(f"✅ VizGenerator selected chart type: {output.chart_type}")
        return state

    except Exception as e:
        logger.error(f"❌ VizGenerator node error: {e}")
        # Don't fail the whole pipeline if viz generation fails
        state["visualization_type"] = "table"
        state["chart_config"] = {}
        return state


def accumulate_results_node(state: WorkflowState) -> WorkflowState:
    """
    Result Accumulation Node
    Stores current query results for multi-query iteration
    """
    logger.info("Accumulating query results...")

    try:
        # Get current iteration
        current_iteration = state.get("query_iteration_count", 0)

        # Create result entry for this query
        result_entry = {
            "iteration": current_iteration,
            "sql": state.get("validated_sql", ""),
            "results": state.get("query_results", []),
            "row_count": state.get("result_count", 0),
            "execution_time_ms": state.get("execution_time_ms", 0),
            "purpose": f"Query iteration {current_iteration + 1}"
        }

        # Initialize all_query_results if not exists
        if state.get("all_query_results") is None:
            state["all_query_results"] = []

        # Append current results
        state["all_query_results"].append(result_entry)

        logger.info(f"Accumulated results for iteration {current_iteration} ({result_entry['row_count']} rows)")
        return state

    except Exception as e:
        logger.error(f"Result accumulation error: {e}")
        # Don't fail workflow, just log and continue
        return state


def iteration_decision_node(state: WorkflowState) -> WorkflowState:
    """
    Iteration Decision Node
    Determines if follow-up query is needed or if we have final answer
    """
    logger.info("Evaluating if follow-up query is needed...")

    try:
        analyst = create_analyst()

        # Prepare input for iterative analysis
        from agents.analyst_agent.agent import IterativeAnalystInput

        current_iteration = state.get("query_iteration_count", 0)
        max_iterations = state.get("max_query_iterations", 3)

        analyst_input = IterativeAnalystInput(
            user_query=state["user_query"],
            current_iteration=current_iteration,
            max_iterations=max_iterations,
            all_query_results=state.get("all_query_results", [])
        )

        # Execute iterative analysis
        output = analyst.iterative_analyze(analyst_input)

        # Update state with decision
        state["needs_followup_query"] = output.needs_followup_query
        state["followup_query_reason"] = output.followup_query_reason
        state["final_answer_ready"] = output.final_answer_ready

        # If final answer is ready, populate analysis fields
        if output.final_answer_ready:
            state["analysis_reasoning_steps"] = output.reasoning_steps
            state["analysis_summary"] = output.summary
            state["key_insights"] = output.key_insights
            state["recommendations"] = output.recommendations
            state["data_quality_notes"] = output.data_quality_notes
            logger.info(f"Final answer ready with {len(output.key_insights)} insights")
        else:
            logger.info(f"Follow-up query needed: {output.followup_query_reason}")

        # Track token usage
        if output.token_usage:
            if "token_usage" not in state or state["token_usage"] is None:
                state["token_usage"] = []
            state["token_usage"].append(output.token_usage)

        return state

    except Exception as e:
        logger.error(f"Iteration decision node error: {e}")
        # On error, mark as final answer ready to exit iteration loop
        state["final_answer_ready"] = True
        state["needs_followup_query"] = False
        state["error_occurred"] = True
        state["error_stage"] = "iteration_decision"
        state["error_message"] = f"Failed to determine iteration: {str(e)}"
        return state


def prepare_next_iteration_node(state: WorkflowState) -> WorkflowState:
    """
    Prepare Next Iteration Node
    Increments iteration counter and resets state for next query
    """
    logger.info("Preparing next query iteration...")

    try:
        # Increment iteration counter
        current_iteration = state.get("query_iteration_count", 0)
        state["query_iteration_count"] = current_iteration + 1

        # Reset SQL generation state for next iteration
        state["sql_retry_count"] = 0  # Reset retry counter for new query
        state["validation_feedback"] = None  # Clear previous validation feedback

        # Keep generated_sql and validated_sql from previous iteration for context
        # but they will be overwritten in next SQL generation

        logger.info(f"Starting iteration {state['query_iteration_count'] + 1}")
        return state

    except Exception as e:
        logger.error(f"Iteration preparation error: {e}")
        return state


def analyst_node(state: WorkflowState) -> WorkflowState:
    """
    Analyst Agent Node (Legacy - for single-query mode)
    Analyzes query results and generates business insights
    """
    logger.info("Executing Analyst node...")

    try:
        analyst = create_analyst()

        # Prepare input
        from agents.analyst_agent.agent import AnalystInput

        analyst_input = AnalystInput(
            user_query=state["user_query"],
            sql=state["validated_sql"],
            results=state["query_results"] or [],
            result_count=state["result_count"]
        )

        # Execute analyst
        output = analyst.analyze(analyst_input)

        # Update state
        state["analysis_reasoning_steps"] = output.reasoning_steps
        state["analysis_summary"] = output.summary
        state["key_insights"] = output.key_insights
        state["recommendations"] = output.recommendations
        state["data_quality_notes"] = output.data_quality_notes

        logger.info(f"Analyst generated {len(output.key_insights)} insights with {len(output.reasoning_steps)} reasoning steps")
        return state

    except Exception as e:
        logger.error(f"Analyst node error: {e}")
        state["error_occurred"] = True
        state["error_stage"] = "analyst"
        state["error_message"] = f"Failed to analyze results: {str(e)}"
        return state


def end_node(state: WorkflowState) -> WorkflowState:
    """
    End Node
    Finalizes the workflow state
    """
    logger.info("Workflow completed")
    from workflow.state import finalize_state
    return finalize_state(state)


# ============================================================================
# Routing Functions
# ============================================================================

def route_after_orchestrator(state: WorkflowState) -> Literal["schema_agent", "end"]:
    """
    Route after Orchestrator based on action type
    """
    action = state.get("orchestrator_action")

    # If error occurred, end workflow
    if state.get("error_occurred"):
        return "end"

    # If direct answer, end workflow (no SQL needed)
    if action == "DIRECT_ANSWER":
        logger.info("Routing to END (direct answer)")
        return "end"

    # All other actions need SQL generation
    logger.info("Routing to Schema Agent")
    return "schema_agent"


def route_after_validator(state: WorkflowState) -> Literal["sql_agent", "executor", "end"]:
    """
    Route after Validator
    - If validation passed: proceed to executor
    - If validation failed: retry SQL generation (max 3 attempts)
    - If max retries reached: end workflow
    """
    # If error occurred, end workflow
    if state.get("error_occurred"):
        logger.warning("Error occurred, ending workflow")
        return "end"

    # If validation passed, proceed to execution
    if state.get("validation_passed"):
        logger.info("Validation passed, routing to Executor")
        return "executor"

    # Validation failed - check if we can retry
    retry_count = state.get("sql_retry_count", 0)
    max_retries = state.get("max_sql_retries", 3)

    if retry_count < max_retries:
        # IMPORTANT: LangGraph routing functions CANNOT mutate state!
        # State mutations are ignored. We just return routing decision.
        # The SQL Agent node will handle incrementing retry count and reading feedback.
        logger.warning(
            f"Validation failed. Retrying SQL generation "
            f"(attempt {retry_count + 1}/{max_retries})"
        )
        logger.info(f"Sending {len(state.get('validation_issues', []))} validation issues back to SQL Agent")

        return "sql_agent"  # Loop back to SQL Agent with feedback
    else:
        # Max retries reached, end workflow
        logger.error(
            f"Validation failed after {max_retries} attempts. "
            f"Ending workflow with validation failure."
        )
        return "end"


def route_after_iteration_decision(state: WorkflowState) -> Literal["prepare_next_iteration", "end"]:
    """
    Route after Iteration Decision Node
    - If needs_followup_query AND within iteration limit: prepare next iteration
    - Otherwise: end workflow
    """
    # If error occurred, end workflow
    if state.get("error_occurred"):
        logger.warning("Error occurred, ending workflow")
        return "end"

    # Check if we hit iteration limit
    current_iteration = state.get("query_iteration_count", 0)
    max_iterations = state.get("max_query_iterations", 3)

    if current_iteration >= max_iterations:
        logger.info(f"Hit iteration limit ({max_iterations}), ending workflow")
        return "end"

    # Check if follow-up query is needed
    if state.get("needs_followup_query", False) and not state.get("final_answer_ready", False):
        logger.info(f"Follow-up query needed: {state.get('followup_query_reason', 'No reason provided')}")
        return "prepare_next_iteration"
    else:
        logger.info("Final answer ready or no follow-up needed, ending workflow")
        return "end"


# ============================================================================
# Build Workflow Graph
# ============================================================================

def create_workflow() -> StateGraph:
    """
    Create the NL2SQL workflow graph with multi-query iteration support

    Workflow:
    START → Orchestrator → Schema Agent → SQL Agent → Validator → Executor
          → Accumulate Results → Iteration Decision
          → [If needs followup] → Prepare Next Iteration → SQL Agent (loop)
          → [If final answer ready] → END
    """

    # Create graph
    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("schema_agent", schema_agent_node)
    workflow.add_node("sql_agent", sql_agent_node)
    workflow.add_node("validator", validator_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("viz_generator", viz_generator_node)  # NEW - Generates visualization configs
    workflow.add_node("accumulate_results", accumulate_results_node)  # NEW
    workflow.add_node("iteration_decision", iteration_decision_node)  # NEW
    workflow.add_node("prepare_next_iteration", prepare_next_iteration_node)  # NEW
    workflow.add_node("analyst", analyst_node)  # LEGACY - kept for compatibility
    workflow.add_node("end", end_node)

    # Set entry point
    workflow.set_entry_point("orchestrator")

    # Add edges
    workflow.add_conditional_edges(
        "orchestrator",
        route_after_orchestrator,
        {
            "schema_agent": "schema_agent",
            "end": "end"
        }
    )

    workflow.add_edge("schema_agent", "sql_agent")
    workflow.add_edge("sql_agent", "validator")

    workflow.add_conditional_edges(
        "validator",
        route_after_validator,
        {
            "sql_agent": "sql_agent",  # Loop back for validation retry
            "executor": "executor",
            "end": "end"
        }
    )

    # NEW: Multi-query iteration path
    workflow.add_edge("executor", "viz_generator")
    workflow.add_edge("viz_generator", "accumulate_results")
    workflow.add_edge("accumulate_results", "iteration_decision")

    workflow.add_conditional_edges(
        "iteration_decision",
        route_after_iteration_decision,
        {
            "prepare_next_iteration": "prepare_next_iteration",
            "end": "end"
        }
    )

    # Loop back to SQL Agent for next query iteration
    workflow.add_edge("prepare_next_iteration", "sql_agent")

    workflow.add_edge("end", END)

    return workflow


def compile_workflow():
    """
    Compile the workflow graph for execution

    Note: Recursion limit (50) is set when invoking/streaming the workflow,
    not during compilation. See chat_service.py for recursion_limit config.
    """
    workflow = create_workflow()
    return workflow.compile()


__all__ = ["create_workflow", "compile_workflow"]
