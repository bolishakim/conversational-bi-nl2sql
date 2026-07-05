"""
Test Analyst Agent
Tests result analysis with chain-of-thought reasoning
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.analyst_agent.agent import analyze_results


def test_analyst_agent():
    """Test Analyst Agent with various query results"""

    print("=" * 80)
    print("Testing Analyst Agent - Results Analysis")
    print("=" * 80)

    # Test cases with sample results
    test_cases = [
        {
            "name": "Sales by territory analysis",
            "user_query": "What are the top 5 territories by total sales?",
            "sql": "SELECT st.name, SUM(soh.totaldue) AS total_sales FROM sales.salesorderheader soh JOIN sales.salesterritory st ON soh.territoryid = st.territoryid GROUP BY st.name ORDER BY total_sales DESC LIMIT 5",
            "results": [
                {"name": "Southwest", "total_sales": 27150594.59},
                {"name": "Canada", "total_sales": 18398929.19},
                {"name": "Northwest", "total_sales": 18061660.37},
                {"name": "Southeast", "total_sales": 16677431.43},
                {"name": "United Kingdom", "total_sales": 14961076.68}
            ],
            "result_count": 5
        },
        {
            "name": "Employee count by department",
            "user_query": "Show me employee count by department",
            "sql": "SELECT department, COUNT(*) as employee_count FROM humanresources.vemployeedepartment GROUP BY department ORDER BY employee_count DESC",
            "results": [
                {"department": "Production", "employee_count": 148},
                {"department": "Sales", "employee_count": 35},
                {"department": "Engineering", "employee_count": 28},
                {"department": "Information Services", "employee_count": 15},
                {"department": "Marketing", "employee_count": 13}
            ],
            "result_count": 16  # Showing top 5 of 16 total
        },
        {
            "name": "Valid results from current data range",
            "user_query": "Show orders from 2024",
            "sql": "SELECT * FROM sales.salesorderheader WHERE EXTRACT(YEAR FROM orderdate) = 2024 LIMIT 10",
            "results": [
                {"salesorderid": 75123, "orderdate": "2024-06-15", "totaldue": 1234.56},
                {"salesorderid": 75124, "orderdate": "2024-06-16", "totaldue": 2345.67}
            ],
            "result_count": 2
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"{'=' * 80}")
        print(f"Query: \"{test['user_query']}\"")
        print(f"Result Count: {test['result_count']} rows")
        print("-" * 80)

        try:
            # Analyze results
            output = analyze_results(
                user_query=test["user_query"],
                sql=test["sql"],
                results=test["results"],
                result_count=test["result_count"]
            )

            # Display results
            print(f"\n✓ Analysis completed")
            print(f"\n📋 Summary:")
            print(f"  {output.summary}")

            print(f"\n🔍 Chain-of-Thought Reasoning ({len(output.reasoning_steps)} steps):")
            for j, step in enumerate(output.reasoning_steps, 1):
                # Truncate long steps for readability
                step_preview = step[:120] + "..." if len(step) > 120 else step
                print(f"  {j}. {step_preview}")

            print(f"\n💡 Key Insights ({len(output.key_insights)}):")
            for insight in output.key_insights:
                print(f"  • {insight}")

            print(f"\n🎯 Recommendations ({len(output.recommendations)}):")
            for rec in output.recommendations:
                print(f"  • {rec}")

            if output.data_quality_notes:
                print(f"\n⚠️  Data Quality Notes ({len(output.data_quality_notes)}):")
                for note in output.data_quality_notes:
                    print(f"  • {note}")

            # Check quality
            has_reasoning = len(output.reasoning_steps) >= 5
            has_insights = len(output.key_insights) > 0
            has_recommendations = len(output.recommendations) > 0

            status = "[OK]" if (has_reasoning and has_insights) else "[WARN]"
            print(f"\n{status} Reasoning steps: {len(output.reasoning_steps)}/5, Insights: {len(output.key_insights)}, Recommendations: {len(output.recommendations)}")

            results.append({
                "test": test["name"],
                "success": True,
                "reasoning_steps": len(output.reasoning_steps),
                "insights": len(output.key_insights),
                "recommendations": len(output.recommendations),
                "quality_ok": has_reasoning and has_insights
            })

        except Exception as e:
            print(f"\n[FAIL] Analysis error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test["name"],
                "success": False,
                "quality_ok": False
            })

    # Summary
    print(f"\n{'=' * 80}")
    print("Test Summary")
    print("=" * 80)

    successful = sum(1 for r in results if r["success"])
    quality_ok = sum(1 for r in results if r.get("quality_ok", False))
    total = len(results)

    print(f"Passed: {successful}/{total}")
    print(f"Quality OK: {quality_ok}/{total}")

    if successful > 0:
        successful_tests = [r for r in results if r["success"]]
        avg_reasoning = sum(r.get("reasoning_steps", 0) for r in successful_tests) / len(successful_tests)
        avg_insights = sum(r.get("insights", 0) for r in successful_tests) / len(successful_tests)
        avg_recs = sum(r.get("recommendations", 0) for r in successful_tests) / len(successful_tests)

        print(f"\nAverage reasoning steps: {avg_reasoning:.1f}")
        print(f"Average insights: {avg_insights:.1f}")
        print(f"Average recommendations: {avg_recs:.1f}")

    if successful < total:
        print("\nFailed tests:")
        for r in results:
            if not r["success"]:
                print(f"  - {r['test']}")

    print("\n✅ Analyst Agent is working!")
    print("=" * 80)


if __name__ == "__main__":
    test_analyst_agent()
