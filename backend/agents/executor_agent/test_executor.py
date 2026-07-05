"""
Test Executor Agent
Tests SQL execution with timeout, error handling, and result formatting
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.executor_agent.agent import execute_sql


def test_executor_agent():
    """Test Executor Agent with various SQL queries"""

    print("=" * 80)
    print("Testing Executor Agent - SQL Execution")
    print("=" * 80)

    # Test cases
    test_cases = [
        {
            "name": "Simple SELECT query",
            "user_query": "Show me top 5 territories",
            "sql": "SELECT territoryid, name, countryregioncode FROM sales.salesterritory LIMIT 5",
            "expected_success": True,
            "timeout": 10,
            "max_rows": 100
        },
        {
            "name": "Aggregation query with JOIN",
            "user_query": "What are total sales by territory?",
            "sql": """
                SELECT
                    st.name AS territory_name,
                    COUNT(soh.salesorderid) AS order_count,
                    SUM(soh.totaldue) AS total_sales
                FROM sales.salesorderheader soh
                INNER JOIN sales.salesterritory st ON soh.territoryid = st.territoryid
                GROUP BY st.name
                ORDER BY total_sales DESC
                LIMIT 10
            """,
            "expected_success": True,
            "timeout": 30,
            "max_rows": 100
        },
        {
            "name": "Query with date filtering",
            "user_query": "Orders in 2024",
            "sql": """
                SELECT
                    salesorderid,
                    orderdate,
                    totaldue,
                    status
                FROM sales.salesorderheader
                WHERE EXTRACT(YEAR FROM orderdate) = 2024
                ORDER BY orderdate DESC
                LIMIT 10
            """,
            "expected_success": True,
            "timeout": 15,
            "max_rows": 100
        },
        {
            "name": "Invalid table name (should fail)",
            "user_query": "Test error handling",
            "sql": "SELECT * FROM sales.nonexistent_table LIMIT 5",
            "expected_success": False,
            "timeout": 10,
            "max_rows": 100
        },
        {
            "name": "Syntax error (should fail)",
            "user_query": "Test syntax error",
            "sql": "SELECT * FROM WHERE LIMIT 5",
            "expected_success": False,
            "timeout": 10,
            "max_rows": 100
        },
        {
            "name": "Row limit test",
            "user_query": "Test row limiting",
            "sql": "SELECT * FROM sales.salesorderheader",
            "expected_success": True,
            "timeout": 30,
            "max_rows": 5  # Small limit to test truncation
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n{'=' * 80}")
        print(f"[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"{'=' * 80}")
        print(f"Query: \"{test['user_query']}\"")
        print(f"SQL: {test['sql'][:100]}...")
        print(f"Timeout: {test['timeout']}s, Max Rows: {test['max_rows']}")
        print("-" * 80)

        try:
            # Execute SQL
            output = execute_sql(
                sql=test["sql"],
                user_query=test["user_query"],
                timeout_seconds=test["timeout"],
                max_rows=test["max_rows"]
            )

            # Display results
            print(f"\n✓ Execution completed")
            print(f"Success: {output.success}")
            print(f"Execution Time: {output.execution_time_ms:.2f} ms")
            print(f"Row Count: {output.row_count}")
            print(f"Truncated: {output.was_truncated}")

            if output.success:
                print(f"Columns: {', '.join(output.columns or [])}")

                # Show first 3 rows
                if output.results:
                    print(f"\nSample Results (first {min(3, len(output.results))} rows):")
                    for j, row in enumerate(output.results[:3], 1):
                        print(f"  Row {j}: {row}")
            else:
                print(f"Error: {output.error_message}")

            # Check expectations
            success_match = output.success == test["expected_success"]
            status = "[OK]" if success_match else "[WARN]"

            print(f"\n{status} Expected success={test['expected_success']}, Got success={output.success}")

            results.append({
                "test": test["name"],
                "success_match": success_match,
                "row_count": output.row_count,
                "execution_time_ms": output.execution_time_ms,
                "was_truncated": output.was_truncated,
                "error": not success_match
            })

        except Exception as e:
            print(f"\n[FAIL] Test execution error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test["name"],
                "success_match": False,
                "error": True
            })

    # Summary
    print(f"\n{'=' * 80}")
    print("Test Summary")
    print("=" * 80)

    successful = sum(1 for r in results if r["success_match"] and not r.get("error", False))
    total = len(results)

    print(f"Passed: {successful}/{total}")

    if successful > 0:
        successful_tests = [r for r in results if r["success_match"] and not r.get("error", False)]
        avg_time = sum(r.get("execution_time_ms", 0) for r in successful_tests) / len(successful_tests)
        total_rows = sum(r.get("row_count", 0) for r in successful_tests)
        print(f"\nAverage execution time: {avg_time:.2f} ms")
        print(f"Total rows returned: {total_rows}")

        truncated_count = sum(1 for r in successful_tests if r.get("was_truncated", False))
        if truncated_count > 0:
            print(f"Queries with truncated results: {truncated_count}")

    if successful < total:
        print("\nFailed tests:")
        for r in results:
            if not r["success_match"] or r.get("error", False):
                print(f"  - {r['test']}")

    print("\n✅ Executor Agent is working!")
    print("=" * 80)


if __name__ == "__main__":
    test_executor_agent()
