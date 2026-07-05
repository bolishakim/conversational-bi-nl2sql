"""
Domain detection system
Determines which business domain a query belongs to
"""
from typing import Literal, Dict, List
import re


DomainType = Literal["sales", "hr", "production", "purchasing", "general"]


class DomainDetector:
    """Detect the business domain of a natural language query"""

    # Domain-specific keywords (includes plural forms and variations)
    DOMAIN_KEYWORDS = {
        "sales": [
            "sales", "sale", "revenue", "revenues", "order", "orders",
            "customer", "customers", "sold", "purchase", "purchases",
            "buying", "bought", "transaction", "transactions",
            "salesperson", "salespersons", "salespeople", "territory", "territories",
            "quota", "quotas", "deal", "deals", "selling", "sell", "sells",
            "buyer", "buyers", "client", "clients", "account", "accounts"
        ],
        "hr": [
            "employee", "employees", "staff", "workforce", "hire", "hires",
            "hired", "hiring", "new hire", "new hires", "salary", "salaries",
            "pay", "paid", "paying", "payroll", "department", "departments",
            "manager", "managers", "compensation", "turnover", "retention",
            "personnel", "team", "teams", "worker", "workers",
            "job title", "job titles", "resign", "resigned", "resignation", "resignations",
            "headcount", "termination", "onboarding"
        ],
        "production": [
            "product", "products", "inventory", "inventories", "stock", "stocks",
            "manufacturing", "manufacture", "production", "productions",
            "work order", "work orders", "assembly", "assemblies",
            "component", "components", "category", "categories", "SKU", "SKUs",
            "item", "items", "catalog", "catalogs", "goods", "merchandise"
        ],
        "purchasing": [
            "vendor", "vendors", "supplier", "suppliers",
            "purchase order", "purchase orders", "procurement",
            "buying", "bought", "sourcing", "supply chain",
            "shipment", "shipments", "delivery", "deliveries"
        ]
    }

    # Time-related keywords (common to all domains)
    TIME_KEYWORDS = [
        "quarter", "Q1", "Q2", "Q3", "Q4", "monthly", "yearly", "annual",
        "year-over-year", "YoY", "trend", "over time", "historical",
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    # Analytical keywords
    ANALYTICAL_KEYWORDS = [
        "why", "analyze", "compare", "correlation", "impact", "effect",
        "reason", "cause", "factor", "influence", "relationship"
    ]

    def __init__(self):
        # Compile regex patterns for efficiency
        self.domain_patterns = {
            domain: re.compile(
                r'\b(' + '|'.join(re.escape(kw) for kw in keywords) + r')\b',
                re.IGNORECASE
            )
            for domain, keywords in self.DOMAIN_KEYWORDS.items()
        }

    def detect_domain(self, query: str) -> DomainType:
        """
        Detect the primary domain of a query
        Returns: "sales", "hr", "production", "purchasing", or "general"
        """
        # Count matches for each domain
        domain_scores: Dict[str, int] = {
            "sales": 0,
            "hr": 0,
            "production": 0,
            "purchasing": 0
        }

        # Score each domain based on keyword matches
        for domain, pattern in self.domain_patterns.items():
            matches = pattern.findall(query)
            domain_scores[domain] = len(matches)

        # Find domain with highest score
        max_score = max(domain_scores.values())

        if max_score == 0:
            # No clear domain detected
            return "general"

        # Get domain(s) with max score
        top_domains = [d for d, score in domain_scores.items() if score == max_score]

        if len(top_domains) == 1:
            return top_domains[0]

        # If multiple domains tied, apply tie-breaking rules
        # Rule 1: Sales domain takes precedence (most common queries)
        if "sales" in top_domains:
            return "sales"

        # Rule 2: If production and purchasing tied, check for specific keywords
        if "production" in top_domains and "purchasing" in top_domains:
            if "vendor" in query.lower() or "supplier" in query.lower():
                return "purchasing"
            return "production"

        # Default to first domain in tie
        return top_domains[0]

    def detect_multiple_domains(self, query: str) -> List[DomainType]:
        """
        Detect all domains mentioned in query (for cross-departmental queries)
        Returns list of domains, ordered by relevance
        """
        domain_scores: Dict[str, int] = {
            "sales": 0,
            "hr": 0,
            "production": 0,
            "purchasing": 0
        }

        # Score each domain
        for domain, pattern in self.domain_patterns.items():
            matches = pattern.findall(query)
            domain_scores[domain] = len(matches)

        # Return domains with non-zero scores, sorted by score
        domains = [
            domain for domain, score in
            sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
            if score > 0
        ]

        return domains if domains else ["general"]

    def is_time_based_query(self, query: str) -> bool:
        """Check if query is time-based"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.TIME_KEYWORDS)

    def is_analytical_query(self, query: str) -> bool:
        """Check if query requires analytical reasoning (e.g., 'why' questions)"""
        query_lower = query.lower()
        return any(kw in query_lower for kw in self.ANALYTICAL_KEYWORDS)

    def get_query_type(self, query: str) -> str:
        """
        Classify query type
        Returns: "factual", "analytical", "comparison", "trend"
        """
        query_lower = query.lower()

        # Check for analytical queries
        if self.is_analytical_query(query):
            return "analytical"

        # Check for comparison queries
        if any(word in query_lower for word in ["compare", "versus", "vs", "difference"]):
            return "comparison"

        # Check for trend queries
        if self.is_time_based_query(query) and any(word in query_lower for word in ["trend", "over time", "historical"]):
            return "trend"

        # Default to factual
        return "factual"

    def get_domain_info(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """
        Get comprehensive domain information for a query

        Args:
            query: User's natural language query
            conversation_history: Optional list of previous conversation messages
                Format: [{"role": "user/assistant", "content": "..."}]

        Returns:
            Dict with domain information
        """
        primary_domain = self.detect_domain(query)
        all_domains = self.detect_multiple_domains(query)
        is_cross_departmental = len(all_domains) > 1

        # ENHANCEMENT: If domain is "general" and we have conversation history,
        # try to infer domain from the most recent query in history
        if primary_domain == "general" and conversation_history:
            inherited_domain = self._infer_domain_from_history(conversation_history)
            if inherited_domain != "general":
                primary_domain = inherited_domain
                all_domains = [inherited_domain] if inherited_domain not in all_domains else all_domains

        return {
            "primary_domain": primary_domain,
            "all_domains": all_domains,
            "is_cross_departmental": is_cross_departmental,
            "is_time_based": self.is_time_based_query(query),
            "is_analytical": self.is_analytical_query(query),
            "query_type": self.get_query_type(query)
        }

    def _infer_domain_from_history(self, conversation_history: List[Dict]) -> DomainType:
        """
        Infer domain from conversation history for follow-up queries

        Args:
            conversation_history: List of conversation messages

        Returns:
            Inferred domain or "general"
        """
        if not conversation_history:
            return "general"

        # Look for domain hints in recent conversation (last 4 messages = 2 exchanges)
        recent_messages = conversation_history[-4:]

        # Check if assistant's response mentions a domain
        for msg in reversed(recent_messages):
            if msg.get("role") == "assistant":
                content = msg.get("content", "").lower()

                # Look for explicit domain mentions like "Domain: sales"
                if "domain: sales" in content:
                    return "sales"
                elif "domain: hr" in content:
                    return "hr"
                elif "domain: production" in content:
                    return "production"
                elif "domain: purchasing" in content:
                    return "purchasing"

        # Fallback: Try to detect domain from most recent user query
        for msg in reversed(recent_messages):
            if msg.get("role") == "user":
                previous_query = msg.get("content", "")
                detected_domain = self.detect_domain(previous_query)
                if detected_domain != "general":
                    return detected_domain
                break  # Only check the most recent user query

        return "general"


# Global instance
domain_detector = DomainDetector()


__all__ = ["DomainDetector", "DomainType", "domain_detector"]
