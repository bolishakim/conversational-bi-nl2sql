"""
Test Orchestrator Agent
Tests routing decisions for different query types
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.orchestrator.agent import analyze_query


def test_orchestrator():
    """Test Orchestrator agent with various query types"""

    print("=" * 80)
    print("Testing Orchestrator Agent - Routing Decisions")
    print("=" * 80)

    # Test cases
    test_cases = [
        {
            "name": "Greeting",
            "query": "Hello, how are you?",
            "history": None,
            "has_results": False,
            "expected_action": "DIRECT_ANSWER"
        },
        {
            "name": "Out of Scope",
            "query": "What's the weather today?",
            "history": None,
            "has_results": False,
            "expected_action": "DIRECT_ANSWER"
        },
        {
            "name": "New SQL Query",
            "query": "What are the total sales by territory in 2024?",
            "history": None,
            "has_results": False,
            "expected_action": "FULL_PIPELINE"
        },
        {
            "name": "Follow-up Question",
            "query": "What does this result mean?",
            "history": [
                {"role": "user", "content": "Show me sales by region"},
                {"role": "assistant", "content": "Here are the sales by region: North: $500K, South: $300K"}
            ],
            "has_results": True,
            "expected_action": "INTERPRET_PREVIOUS"
        },
        {
            "name": "Visualization Change",
            "query": "Show that as a pie chart instead",
            "history": [
                {"role": "user", "content": "Show me sales by territory"},
                {"role": "assistant", "content": "Here's a bar chart showing sales by territory"}
            ],
            "has_results": True,
            "expected_action": "MODIFY_VISUALIZATION"
        },
        {
            "name": "Modified Query",
            "query": "Same but for 2023 instead",
            "history": [
                {"role": "user", "content": "Show sales by territory in 2024"},
                {"role": "assistant", "content": "Here are the 2024 sales results"}
            ],
            "has_results": True,
            "expected_action": "FULL_PIPELINE"
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"Query: \"{test['query']}\"")

        try:
            # Analyze query
            output = analyze_query(
                query=test["query"],
                conversation_history=test["history"],
                has_previous_results=test["has_results"]
            )

            # Display result
            print(f"Action: {output.action}")
            print(f"Reasoning: {output.reasoning}")
            print(f"Needs Visualization: {output.needs_visualization}")

            if output.direct_response:
                print(f"Direct Response: {output.direct_response}")

            if output.context_required:
                print(f"Context Required: {', '.join(output.context_required)}")

            # Check if matches expected
            matches = output.action == test["expected_action"]
            status = "[OK]" if matches else "[WARN]"
            print(f"{status} Expected: {test['expected_action']}, Got: {output.action}")

            results.append({
                "test": test["name"],
                "expected": test["expected_action"],
                "actual": output.action,
                "matches": matches
            })

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            results.append({
                "test": test["name"],
                "expected": test["expected_action"],
                "actual": "ERROR",
                "matches": False
            })

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    passed = sum(1 for r in results if r["matches"])
    total = len(results)

    print(f"Passed: {passed}/{total}")

    if passed < total:
        print("\nWarnings (expected vs actual):")
        for r in results:
            if not r["matches"]:
                print(f"  - {r['test']}: Expected {r['expected']}, Got {r['actual']}")

    print("\nNote: The Orchestrator makes AI-based decisions, so some variation is expected.")
    print("As long as the reasoning is sound, slight differences from expected are OK.")
    print("=" * 80)


if __name__ == "__main__":
    test_orchestrator()
