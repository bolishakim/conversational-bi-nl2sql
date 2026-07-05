"""
RAG Retrieval System with Anchor Table Strategy
"""
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from typing import List, Dict, Any
from openai import OpenAI
from config import settings
from config.core_tables import get_anchor_tables_for_domain
from utils.database import db
from utils.domain_detector import domain_detector


class RAGRetriever:
    """Retrieve relevant tables using RAG + anchor table strategy"""

    def __init__(self):
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY not set in .env file")

        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.embedding_model = settings.EMBEDDING_MODEL
        # Don't cache top_k - read dynamically from settings to support runtime changes
        self.enable_anchors = settings.ENABLE_ANCHOR_TABLES

    @property
    def top_k(self) -> int:
        """Read TOP_K_TABLES dynamically from settings"""
        return settings.TOP_K_TABLES

    def generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for user query"""
        try:
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=query,
                encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating query embedding: {e}")
            raise

    def get_anchor_tables(self, domain: str) -> List[str]:
        """Get anchor tables for a specific domain"""
        if not self.enable_anchors:
            return []
        return get_anchor_tables_for_domain(domain)

    def retrieve_similar_tables(
        self,
        query_embedding: List[float],
        exclude_tables: List[str] = None,
        k: int = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar tables using vector similarity search
        """
        k = k or self.top_k
        exclude_tables = exclude_tables or []
        exclude_set = set(exclude_tables)

        # Fetch more results than needed to account for exclusions
        fetch_limit = k + len(exclude_tables) + 5

        # Vector similarity search using pgvector
        query = """
            SELECT
                schema_name,
                table_name,
                full_name,
                description,
                business_terms,
                common_questions,
                key_columns,
                sample_values,
                row_count,
                tier,
                embedding_text,
                1 - (embedding <=> %s::vector) as similarity
            FROM rag.table_embeddings
            ORDER BY embedding <=> %s::vector
            LIMIT %s;
        """

        try:
            results = db.execute_query(
                query,
                (query_embedding, query_embedding, fetch_limit)
            )

            # Filter out excluded tables in Python
            filtered_results = [
                dict(row) for row in results
                if row['full_name'] not in exclude_set
            ]

            # Return only top k after filtering
            return filtered_results[:k]

        except Exception as e:
            print(f"Error retrieving similar tables: {e}")
            return []

    def get_table_details(self, table_names: List[str]) -> List[Dict[str, Any]]:
        """Get full details for specific tables"""
        if not table_names:
            return []

        placeholders = ', '.join(['%s'] * len(table_names))
        query = f"""
            SELECT
                schema_name,
                table_name,
                full_name,
                description,
                business_terms,
                common_questions,
                key_columns,
                sample_values,
                row_count,
                tier,
                embedding_text
            FROM rag.table_embeddings
            WHERE full_name IN ({placeholders});
        """

        try:
            results = db.execute_query(query, tuple(table_names))
            return [dict(row) for row in results]
        except Exception as e:
            print(f"Error getting table details: {e}")
            return []

    def retrieve_relevant_schema(
        self,
        user_query: str,
        include_similarity_scores: bool = False,
        conversation_history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Main retrieval function: Anchor tables + RAG-retrieved tables

        Strategy:
        1. Detect domain from query (with conversation history context)
        2. Get anchor tables for that domain (always included)
        3. Generate query embedding
        4. Retrieve top-k similar tables (excluding anchors)
        5. Combine anchors + retrieved tables

        Args:
            user_query: User's natural language query
            include_similarity_scores: Whether to include similarity scores
            conversation_history: Optional conversation history for domain inference
        """
        # Step 1: Detect domain (with conversation history for follow-up queries)
        domain_info = domain_detector.get_domain_info(user_query, conversation_history)
        primary_domain = domain_info["primary_domain"]
        is_cross_dept = domain_info["is_cross_departmental"]

        # Step 2: Get anchor tables
        anchor_table_names = self.get_anchor_tables(primary_domain)

        # If cross-departmental, add anchors from other domains too
        if is_cross_dept:
            for other_domain in domain_info["all_domains"]:
                if other_domain != primary_domain:
                    other_anchors = self.get_anchor_tables(other_domain)
                    anchor_table_names.extend(other_anchors)

        # Remove duplicates while preserving order
        anchor_table_names = list(dict.fromkeys(anchor_table_names))

        # Get anchor table details
        anchor_tables = self.get_table_details(anchor_table_names)

        # Step 3: Generate query embedding
        query_embedding = self.generate_query_embedding(user_query)

        # Step 4: Retrieve similar tables (excluding anchors)
        rag_retrieved = self.retrieve_similar_tables(
            query_embedding,
            exclude_tables=anchor_table_names,
            k=self.top_k
        )

        # Step 5: Combine results
        all_tables = anchor_tables + rag_retrieved

        # Build result
        result = {
            "query": user_query,
            "domain_info": domain_info,
            "anchor_tables": [t["full_name"] for t in anchor_tables],
            "rag_retrieved_tables": [t["full_name"] for t in rag_retrieved],
            "all_tables": all_tables,
            "total_tables": len(all_tables),
            "strategy": "anchor + rag" if self.enable_anchors else "rag only"
        }

        if include_similarity_scores:
            result["similarity_scores"] = {
                t["full_name"]: t.get("similarity", 1.0)
                for t in rag_retrieved
            }

        return result

    def format_schema_context(self, tables: List[Dict[str, Any]]) -> str:
        """
        Format table metadata into a readable context for LLM
        """
        context_parts = ["# RELEVANT DATABASE SCHEMA\n"]

        for i, table in enumerate(tables, 1):
            context_parts.append(f"\n## Table {i}: {table['full_name']}")
            context_parts.append(f"**Description:** {table['description']}")
            context_parts.append(f"**Row Count:** {table['row_count']:,} rows")

            # Add key columns
            context_parts.append("\n**Key Columns:**")
            import json
            key_columns = json.loads(table['key_columns']) if isinstance(table['key_columns'], str) else table['key_columns']
            for col_name, col_desc in key_columns.items():
                context_parts.append(f"  - `{col_name}`: {col_desc}")

            # Add business terms
            terms = table['business_terms']
            if terms:
                context_parts.append(f"\n**Business Terms:** {', '.join(terms[:5])}")

            # Add sample values if available
            if table.get('sample_values'):
                sample_values = json.loads(table['sample_values']) if isinstance(table['sample_values'], str) else table['sample_values']
                if sample_values:
                    context_parts.append("\n**Sample Values:**")
                    for col, values in list(sample_values.items())[:2]:  # Show max 2 columns
                        context_parts.append(f"  - {col}: {', '.join(str(v) for v in values[:3])}")

        return "\n".join(context_parts)


# Global instance
rag_retriever = RAGRetriever()


__all__ = ["RAGRetriever", "rag_retriever"]
