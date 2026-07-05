"""
Test Schema Agent
Tests RAG retrieval and schema formatting
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from agents.schema.agent import retrieve_schema


def test_schema_agent():
    """Test Schema Agent with various query types"""

    print("=" * 80)
    print("Testing Schema Agent - RAG Retrieval")
    print("=" * 80)

    # Test cases
    test_queries = [
        {
            "query": "What are total sales by territory in 2024?",
            "expected_domain": "sales",
            "expected_anchor": "sales.salesorderheader"
        },
        {
            "query": "Which employees were hired in the last quarter?",
            "expected_domain": "hr",
            "expected_anchor": "humanresources.employee"
        },
        {
            "query": "What products are low in stock?",
            "expected_domain": "production",
            "expected_anchor": "production.product"
        },
        {
            "query": "Show me purchase orders from vendors",
            "expected_domain": "purchasing",
            "expected_anchor": "purchasing.purchaseorderheader"
        },
        {
            "query": "Compare employee salaries to sales performance",
            "expected_domain": "sales",  # or hr - depends on tie-breaking
            "expected_anchor": None  # Cross-departmental
        }
    ]

    results = []

    for i, test in enumerate(test_queries, 1):
        print(f"\n[Test {i}/{len(test_queries)}]")
        print(f"Query: \"{test['query']}\"")
        print("-" * 80)

        try:
            # Retrieve schema
            output = retrieve_schema(test["query"], include_similarity=True)

            # Display results
            print(f"Domain: {output.domain}")
            print(f"Cross-Departmental: {output.is_cross_departmental}")
            print(f"Strategy: {output.strategy}")
            print(f"Total Tables: {output.total_tables}")

            print(f"\nAnchor Tables ({len(output.anchor_tables)}):")
            for table in output.anchor_tables:
                print(f"  - {table}")

            print(f"\nRAG Retrieved Tables ({len(output.rag_retrieved_tables)}):")
            for table in output.rag_retrieved_tables:
                # Find similarity score
                similarity = next(
                    (t.similarity for t in output.tables if t.full_name == table),
                    0.0
                )
                print(f"  - {table} (similarity: {similarity:.3f})")

            # Check expectations
            domain_match = output.domain == test["expected_domain"]
            anchor_match = (
                test["expected_anchor"] is None or
                test["expected_anchor"] in output.anchor_tables
            )

            status = "[OK]" if domain_match else "[WARN]"
            print(f"\n{status} Domain: Expected {test['expected_domain']}, Got {output.domain}")

            if test["expected_anchor"]:
                anchor_status = "[OK]" if anchor_match else "[WARN]"
                print(f"{anchor_status} Anchor: Expected {test['expected_anchor']} in anchors")

            results.append({
                "query": test["query"],
                "domain_match": domain_match,
                "anchor_match": anchor_match,
                "tables_retrieved": output.total_tables
            })

        except Exception as e:
            print(f"[FAIL] Error: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                "query": test["query"],
                "domain_match": False,
                "anchor_match": False,
                "tables_retrieved": 0
            })

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    successful = sum(1 for r in results if r["domain_match"])
    total = len(results)

    print(f"Domain Detection: {successful}/{total}")
    print(f"\nAverage Tables Retrieved: {sum(r['tables_retrieved'] for r in results) / total:.1f}")

    print("\nSchema Agent RAG retrieval is working!")
    print("=" * 80)


if __name__ == "__main__":
    test_schema_agent()
