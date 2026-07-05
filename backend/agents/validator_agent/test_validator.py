"""
Test Validator Agent
Tests SQL validation for safety, syntax, and schema correctness
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.validator_agent.agent import validate_sql


def test_validator_agent():
    """Test Validator Agent with various SQL queries"""

    print("=" * 80)
    print("Testing Validator Agent - SQL Validation")
    print("=" * 80)

    # Mock schema summary
    schema_summary = """
    Available tables:
    - sales.salesorderheader (salesorderid, orderdate, totaldue, territoryid)
    - sales.salesterritory (territoryid, name, group)
    - production.product (productid, name, listprice)
    - sales.salesorderdetail (salesorderdetailid, salesorderid, productid, orderqty, unitprice)
    """

    # Test cases
    test_cases = [
        {
            "name": "Valid SELECT query",
            "user_query": "What are sales by territory?",
            "sql": "SELECT st.name, SUM(soh.totaldue) FROM sales.salesorderheader soh JOIN sales.salesterritory st ON soh.territoryid = st.territoryid GROUP BY st.name",
            "expected_valid": True,
            "expected_severity": "safe"
        },
        {
            "name": "Dangerous DELETE query",
            "user_query": "Delete all records",
            "sql": "DELETE FROM sales.salesorderheader WHERE orderdate < '2020-01-01'",
            "expected_valid": False,
            "expected_severity": "critical"
        },
        {
            "name": "Dangerous DROP query",
            "user_query": "Drop the table",
            "sql": "DROP TABLE sales.salesorderheader",
            "expected_valid": False,
            "expected_severity": "critical"
        },
        {
            "name": "Dangerous UPDATE query",
            "user_query": "Update prices",
            "sql": "UPDATE production.product SET listprice = 100 WHERE productid = 1",
            "expected_valid": False,
            "expected_severity": "critical"
        },
        {
            "name": "Valid CTE query",
            "user_query": "Show top products",
            "sql": "WITH product_sales AS (SELECT productid, SUM(orderqty) as total FROM sales.salesorderdetail GROUP BY productid) SELECT * FROM product_sales ORDER BY total DESC LIMIT 5",
            "expected_valid": True,
            "expected_severity": "safe"
        },
        {
            "name": "Query with potential table name error",
            "user_query": "Show orders",
            "sql": "SELECT * FROM sales.orders WHERE orderdate > '2024-01-01'",
            "expected_valid": False,  # Table 'orders' doesn't exist
            "expected_severity": "error"
        }
    ]

    results = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n[Test {i}/{len(test_cases)}] {test['name']}")
        print(f"Query: \"{test['user_query']}\"")
        print(f"SQL: {test['sql'][:80]}...")
        print("-" * 80)

        try:
            # Validate SQL
            output = validate_sql(
                user_query=test["user_query"],
                sql=test["sql"],
                schema_summary=schema_summary
            )

            # Display results
            print(f"Valid: {output.is_valid}")
            print(f"Severity: {output.severity}")
            print(f"Summary: {output.summary}")

            if output.issues:
                print(f"\nIssues ({len(output.issues)}):")
                for issue in output.issues:
                    print(f"  [{issue.severity.upper()}] {issue.category}: {issue.message}")
                    if issue.suggestion:
                        print(f"    Suggestion: {issue.suggestion}")

            # Check expectations
            valid_match = output.is_valid == test["expected_valid"]
            severity_match = output.severity == test["expected_severity"]

            status = "[OK]" if (valid_match and severity_match) else "[WARN]"
            print(f"\n{status} Expected valid={test['expected_valid']}, Got valid={output.is_valid}")
            print(f"{status} Expected severity={test['expected_severity']}, Got severity={output.severity}")

            results.append({
                "test": test["name"],
                "valid_match": valid_match,
                "severity_match": severity_match,
                "issues_count": len(output.issues)
            })

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "test": test["name"],
                "valid_match": False,
                "severity_match": False,
                "issues_count": 0
            })

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    successful = sum(1 for r in results if r["valid_match"] and r["severity_match"])
    total = len(results)

    print(f"Passed: {successful}/{total}")
    print(f"\nAverage issues per query: {sum(r['issues_count'] for r in results) / total:.1f}")

    if successful < total:
        print("\nFailed tests:")
        for r in results:
            if not (r["valid_match"] and r["severity_match"]):
                print(f"  - {r['test']}")

    print("\nValidator Agent is working!")
    print("=" * 80)


if __name__ == "__main__":
    test_validator_agent()
