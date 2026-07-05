"""
Test LangGraph Workflow
Tests end-to-end workflow execution with all agents
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from workflow.graph import compile_workflow
from workflow.state import create_initial_state, state_summary


def test_workflow():
    """Test end-to-end workflow execution"""

    print("=" * 80)
    print("Testing LangGraph Workflow - End-to-End Execution")
    print("=" * 80)

    # Test cases
    test_cases = [
        {
            "name": "Full pipeline query (sales)",
            "query": "What are the top 5 territories by total sales in 2024?",
            "expected_action": "FULL_PIPELINE",
            "expected_nodes": ["orchestrator", "schema_agent", "sql_agent", "validator", "end"]
        },
        {
            "name": "Direct answer (greeting)",
            "query": "Hello, how are you?",
            "expected_action": "DIRECT_ANSWER",
            "expected_nodes": ["orchestrator", "end"]
        },
        {
            "name": "Full pipeline query (HR)",
            "query": "Show me the employee count by department",
            "expected_action": "FULL_PIPELINE",
            "expected_nodes": ["orchestrator", "schema_agent", "sql_agent", "validator", "end"]
        }
    ]

    # Compile workflow
    print("\nCompiling workflow graph...")
    try:
        workflow = compile_workflow()
        print("✓ Workflow compiled successfully")
    except Exception as e:
        print(f"✗ Failed to compile workflow: {e}")
        import traceback
        traceback.print_exc()
        return

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"{'=' * 80}")
        print(f"Query: \"{test['query']}\"")
        print(f"Expected Action: {test['expected_action']}")
        print("-" * 80)

        try:
            # Create initial state
            initial_state = create_initial_state(
                user_query=test["query"],
                conversation_history=[]
            )

            print(f"\n📊 Initial State Created:")
            print(f"  Workflow ID: {initial_state['workflow_id']}")
            print(f"  Started At: {initial_state['started_at']}")

            # Execute workflow
            print(f"\n🔄 Executing workflow...")
            final_state = workflow.invoke(initial_state)

            # Display results
            print(f"\n✅ Workflow Completed")
            print(f"\n📋 Final State Summary:")
            print(state_summary(final_state))

            # Detailed breakdown
            print(f"\n🔍 Detailed Results:")

            # Orchestrator
            action = final_state.get("orchestrator_action")
            print(f"\n  [1] Orchestrator:")
            print(f"      Action: {action}")
            print(f"      Reasoning: {final_state.get('orchestrator_reasoning', 'N/A')[:100]}...")
            print(f"      Needs Visualization: {final_state.get('needs_visualization', False)}")

            if action == "DIRECT_ANSWER":
                print(f"      Direct Response: {final_state.get('direct_response', 'N/A')[:100]}...")

            # Schema Agent (if executed)
            if final_state.get("domain"):
                print(f"\n  [2] Schema Agent:")
                print(f"      Domain: {final_state.get('domain')}")
                print(f"      Cross-Departmental: {final_state.get('is_cross_departmental', False)}")
                print(f"      Tables Retrieved: {len(final_state.get('retrieved_tables', []))}")
                print(f"      Tables: {', '.join(final_state.get('retrieved_tables', [])[:5])}...")

            # SQL Agent (if executed)
            if final_state.get("generated_sql"):
                print(f"\n  [3] SQL Agent:")
                reasoning_steps = final_state.get("sql_reasoning_steps", [])
                print(f"      Chain-of-Thought Steps: {len(reasoning_steps)}")
                for j, step in enumerate(reasoning_steps[:3], 1):
                    print(f"        {j}. {step[:80]}...")
                print(f"      SQL Preview: {final_state.get('generated_sql', '')[:100]}...")
                print(f"      Tables Used: {', '.join(final_state.get('tables_used', []))}")
                print(f"      Assumptions: {len(final_state.get('sql_assumptions', []))}")

            # Validator (if executed)
            if final_state.get("validation_severity"):
                print(f"\n  [4] Validator:")
                print(f"      Valid: {final_state.get('validation_passed', False)}")
                print(f"      Severity: {final_state.get('validation_severity', 'N/A')}")
                print(f"      Summary: {final_state.get('validation_summary', 'N/A')[:100]}...")
                issues = final_state.get('validation_issues', [])
                if issues:
                    print(f"      Issues: {len(issues)}")
                    for issue in issues[:2]:
                        print(f"        - [{issue['severity']}] {issue['category']}: {issue['message'][:60]}...")

            # Metadata
            print(f"\n  [5] Metadata:")
            print(f"      Duration: {final_state.get('total_duration_ms', 0):.2f} ms")
            print(f"      Error Occurred: {final_state.get('error_occurred', False)}")

            # Check expectations
            action_match = final_state.get("orchestrator_action") == test["expected_action"]
            status = "[OK]" if action_match else "[WARN]"

            print(f"\n{status} Expected action: {test['expected_action']}, Got: {final_state.get('orchestrator_action')}")

            results.append({
                "test": test["name"],
                "action_match": action_match,
                "domain": final_state.get("domain"),
                "tables_count": len(final_state.get("retrieved_tables", [])),
                "validation_passed": final_state.get("validation_passed", False),
                "duration_ms": final_state.get("total_duration_ms", 0),
                "error": final_state.get("error_occurred", False)
            })

        except Exception as e:
            print(f"\n[FAIL] Workflow execution error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test["name"],
                "action_match": False,
                "error": True
            })

    # Summary
    print(f"\n{'=' * 80}")
    print("Test Summary")
    print("=" * 80)

    successful = sum(1 for r in results if r["action_match"] and not r.get("error", False))
    total = len(results)

    print(f"Passed: {successful}/{total}")

    if successful > 0:
        avg_duration = sum(r.get("duration_ms", 0) for r in results if not r.get("error", False)) / successful
        avg_tables = sum(r.get("tables_count", 0) for r in results if not r.get("error", False)) / successful
        print(f"\nAverage duration: {avg_duration:.2f} ms")
        print(f"Average tables retrieved: {avg_tables:.1f}")

    if successful < total:
        print("\nFailed tests:")
        for r in results:
            if not r["action_match"] or r.get("error", False):
                print(f"  - {r['test']}")

    print("\n✅ LangGraph Workflow is working!")
    print("=" * 80)


if __name__ == "__main__":
    test_workflow()
