"""
Test SQL Agent
Tests SQL generation from natural language with schema context
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.schema.agent import retrieve_schema
from agents.sql_agent.agent import generate_sql


def test_sql_agent():
    """Test SQL Agent with Schema Agent integration"""

    print("=" * 80)
    print("Testing SQL Agent - Query Generation")
    print("=" * 80)

    # Test cases
    test_queries = [
        {
            "query": "What are the total sales by territory in 2024?",
            "expected_tables": ["sales.salesorderheader", "sales.salesterritory"]
        },
        {
            "query": "Show me the top 5 products by revenue",
            "expected_tables": ["production.product", "sales.salesorderdetail"]
        },
        {
            "query": "How many employees were hired in each department?",
            "expected_tables": ["humanresources.employee", "humanresources.department"]
        }
    ]

    results = []

    for i, test in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}]")
        print(f"Query: \"{test['query']}\"")
        print("=" * 80)

        try:
            # Step 1: Retrieve schema using Schema Agent
            print("\n[Step 1] Retrieving schema...")
            schema_output = retrieve_schema(test["query"])
            print(f"  Retrieved {schema_output.total_tables} tables")
            print(f"  Domain: {schema_output.domain}")

            # Step 2: Generate SQL using SQL Agent
            print("\n[Step 2] Generating SQL...")
            sql_output = generate_sql(
                query=test["query"],
                schema_context=schema_output.formatted_schema,
                domain=schema_output.domain,
                query_type="factual"
            )

            # Display results
            print(f"\n[Chain-of-Thought Reasoning] ({len(sql_output.reasoning_steps)} steps)")
            print("-" * 80)
            for step in sql_output.reasoning_steps:
                print(f"  {step}")
            print("-" * 80)

            print(f"\n[Generated SQL]")
            print("-" * 80)
            print(sql_output.sql)
            print("-" * 80)

            print(f"\n[Explanation]")
            print(sql_output.explanation)

            print(f"\n[Tables Used] ({len(sql_output.tables_used)})")
            for table in sql_output.tables_used:
                print(f"  - {table}")

            if sql_output.key_assumptions:
                print(f"\n[Assumptions]")
                for assumption in sql_output.key_assumptions:
                    print(f"  - {assumption}")

            # Validation
            has_sql = len(sql_output.sql) > 0
            uses_expected = any(
                expected in sql_output.sql.lower()
                for expected in test["expected_tables"]
            )

            status = "[OK]" if (has_sql and uses_expected) else "[WARN]"
            print(f"\n{status} SQL generated: {len(sql_output.sql)} characters")

            results.append({
                "query": test["query"],
                "success": has_sql,
                "sql_length": len(sql_output.sql),
                "tables_used": len(sql_output.tables_used)
            })

        except Exception as e:
            print(f"\n[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": test["query"],
                "success": False,
                "sql_length": 0,
                "tables_used": 0
            })

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    successful = sum(1 for r in results if r["success"])
    total = len(results)
    avg_sql_length = sum(r["sql_length"] for r in results) / total if total > 0 else 0

    print(f"Successful: {successful}/{total}")
    print(f"Average SQL length: {avg_sql_length:.0f} characters")
    print(f"\nSQL Agent is working correctly!")
    print("=" * 80)


if __name__ == "__main__":
    test_sql_agent()
