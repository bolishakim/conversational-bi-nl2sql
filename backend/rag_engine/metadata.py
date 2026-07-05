"""
RAG System Metadata Configuration
Extracted from research prototype: rag_nl2sql_system/config/core_tables.py
"""
from typing import List, Dict

# ============================================================================
# ANCHOR TABLES (Always included in RAG context)
# ============================================================================
# These tables are domain-specific and always included regardless of similarity score
# Based on analysis from research prototype showing these cover 70%+ of queries

ANCHOR_TABLES = {
    "sales": [
        "sales.salesorderheader",
        "sales.customer",
        "production.product"
    ],
    "hr": [
        "humanresources.employee",
        "person.person",
        "humanresources.department",
        "humanresources.employeepayhistory"
    ],
    "production": [
        "production.product",
        "production.productcategory",
        "production.workorder"
    ],
    "purchasing": [
        "purchasing.purchaseorderheader",
        "purchasing.vendor",
        "production.product"
    ],
    "general": [
        "sales.salesorderheader",
        "production.product",
        "humanresources.employee",
        "person.person"
    ]
}


def get_anchor_tables_for_domain(domain: str) -> List[str]:
    """Get anchor tables for a specific domain"""
    return ANCHOR_TABLES.get(domain, ANCHOR_TABLES["general"])


def get_all_anchor_tables() -> Dict[str, List[str]]:
    """Get all anchor tables configuration"""
    return ANCHOR_TABLES
