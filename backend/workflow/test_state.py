"""
Test Workflow State Management
Tests state creation, updates, and transitions
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from workflow.state import (
    WorkflowState,
    create_initial_state,
    finalize_state,
    state_summary
)


def test_state_management():
    """Test workflow state creation and updates"""

    print("=" * 80)
    print("Testing Workflow State Management")
    print("=" * 80)

    # Test 1: Create initial state
    print("\n[Test 1] Creating initial state...")
    state = create_initial_state(
        user_query="What are total sales by territory in 2024?",
        conversation_history=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi! How can I help?"}
        ],
        user_id="test-user-123"
    )

    assert state["user_query"] == "What are total sales by territory in 2024?"
    assert len(state["conversation_history"]) == 2
    assert state["user_id"] == "test-user-123"
    assert state["workflow_id"] is not None
    assert state["started_at"] is not None
    assert state["needs_visualization"] == False
    assert state["validation_passed"] == False
    print("[OK] Initial state created with correct defaults")

    # Test 2: Update state through pipeline stages
    print("\n[Test 2] Simulating pipeline updates...")

    # Orchestrator stage
    state["orchestrator_action"] = "FULL_PIPELINE"
    state["orchestrator_reasoning"] = "New SQL query needed for sales data"
    state["needs_visualization"] = True
    print("[OK] Orchestrator state updated")

    # Schema Agent stage
    state["domain"] = "sales"
    state["is_cross_departmental"] = False
    state["retrieved_tables"] = [
        "sales.salesorderheader",
        "sales.salesterritory"
    ]
    state["schema_context"] = "Schema context here..."
    print("[OK] Schema Agent state updated")

    # SQL Agent stage
    state["sql_reasoning_steps"] = [
        "Step 1: Understand intent - User wants sales by territory",
        "Step 2: Identify entities - Need salesorderheader and salesterritory tables"
    ]
    state["generated_sql"] = "SELECT st.name, SUM(soh.totaldue) FROM sales.salesorderheader soh JOIN sales.salesterritory st ON soh.territoryid = st.territoryid WHERE EXTRACT(YEAR FROM soh.orderdate) = 2024 GROUP BY st.name"
    state["sql_explanation"] = "Calculates total sales by territory for 2024"
    state["tables_used"] = ["sales.salesorderheader", "sales.salesterritory"]
    print("[OK] SQL Agent state updated")

    # Validator stage
    state["validation_passed"] = True
    state["validation_severity"] = "safe"
    state["validation_issues"] = []
    state["validated_sql"] = state["generated_sql"]
    print("[OK] Validator state updated")

    # Execution stage
    state["execution_success"] = True
    state["query_results"] = [
        {"name": "Northeast", "sum": 1500000.00},
        {"name": "Southwest", "sum": 1200000.00}
    ]
    state["result_count"] = 2
    state["execution_time_ms"] = 145.3
    print("[OK] Execution state updated")

    # Analyst stage
    state["analysis_reasoning_steps"] = [
        "Step 1: Understand Data - Query returns sales totals by territory",
        "Step 2: Key Patterns - Northeast leads with $1.5M"
    ]
    state["analysis_summary"] = "Northeast territory leads 2024 sales with $1.5M"
    state["key_insights"] = [
        "Northeast territory generated $1.5M in 2024",
        "Southwest territory generated $1.2M, 20% lower than Northeast"
    ]
    state["recommendations"] = [
        "Investigate why Southwest underperforms compared to Northeast"
    ]
    print("[OK] Analyst state updated")

    # Test 3: Finalize state
    print("\n[Test 3] Finalizing state...")
    import time
    time.sleep(0.1)  # Simulate some processing time
    state = finalize_state(state)

    assert state["completed_at"] is not None
    assert state["total_duration_ms"] is not None
    assert state["total_duration_ms"] > 0
    print(f"[OK] State finalized with duration: {state['total_duration_ms']:.2f}ms")

    # Test 4: State summary
    print("\n[Test 4] Generating state summary...")
    summary = state_summary(state)
    print("-" * 80)
    print(summary)
    print("-" * 80)

    assert "Workflow ID:" in summary
    assert "Query:" in summary
    assert "Action: FULL_PIPELINE" in summary
    assert "Domain: sales" in summary
    assert "✓ Passed" in summary
    assert "✓ Success" in summary
    assert "2 rows" in summary
    print("[OK] State summary generated correctly")

    # Test 5: Error state
    print("\n[Test 5] Testing error state...")
    error_state = create_initial_state(
        user_query="Malformed query"
    )
    error_state["error_occurred"] = True
    error_state["error_stage"] = "sql_agent"
    error_state["error_message"] = "Failed to generate SQL"
    error_state["error_details"] = "Invalid table name"
    error_state = finalize_state(error_state)

    error_summary = state_summary(error_state)
    assert "Error:" in error_summary
    assert "Failed to generate SQL" in error_summary
    print("[OK] Error state handled correctly")

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)
    print("All 5 tests passed!")
    print("\nState schema includes:")
    print(f"  - Input fields: user_query, conversation_history, user_id")
    print(f"  - Orchestrator fields: action, reasoning, needs_visualization")
    print(f"  - Schema Agent fields: domain, retrieved_tables, schema_context")
    print(f"  - SQL Agent fields: reasoning_steps, generated_sql, explanation")
    print(f"  - Validator fields: validation_passed, severity, issues")
    print(f"  - Execution fields: execution_success, query_results, result_count")
    print(f"  - Analyst fields: analysis_reasoning, summary, insights, recommendations")
    print(f"  - Error handling: error_occurred, error_stage, error_message")
    print(f"  - Metadata: workflow_id, timestamps, duration")
    print("\nWorkflow state management is ready!")
    print("=" * 80)


if __name__ == "__main__":
    test_state_management()
