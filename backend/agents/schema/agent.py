"""
Schema Agent
Retrieves relevant database schema using RAG
"""
import sys
from pathlib import Path
from typing import Dict, Any, List
from pydantic import BaseModel, Field

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.logger import logger
from utils.rag_retriever import rag_retriever
from agents.schema.prompts import SCHEMA_AGENT_SYSTEM_PROMPT


# ============================================================================
# Input/Output Schemas
# ============================================================================

class SchemaAgentInput(BaseModel):
    """Input to Schema Agent"""
    query: str = Field(..., description="User's natural language query")
    conversation_history: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Previous conversation messages for context"
    )
    include_similarity_scores: bool = Field(
        default=False,
        description="Whether to include similarity scores in output"
    )


class TableMetadata(BaseModel):
    """Metadata for a single table"""
    schema_name: str = Field(..., description="Database schema name")
    table_name: str = Field(..., description="Table name")
    full_name: str = Field(..., description="Fully qualified table name (schema.table)")
    description: str = Field(..., description="Table description")
    business_terms: List[str] = Field(..., description="Business terminology")
    common_questions: List[str] = Field(..., description="Common questions this table answers")
    key_columns: Dict[str, str] = Field(..., description="Key column names and descriptions")
    sample_values: Dict[str, List[str]] = Field(default_factory=dict, description="Sample values for columns")
    row_count: int = Field(..., description="Number of rows in table")
    tier: int = Field(..., description="Table tier (1=Essential, 2=Important)")
    similarity: float = Field(default=1.0, description="Similarity score (1.0 for anchor tables)")


class SchemaAgentOutput(BaseModel):
    """Output from Schema Agent"""
    query: str = Field(..., description="Original user query")
    domain: str = Field(..., description="Detected domain (sales, hr, production, purchasing, general)")
    is_cross_departmental: bool = Field(..., description="Whether query spans multiple departments")
    strategy: str = Field(..., description="Retrieval strategy used (anchor + rag, rag only)")
    anchor_tables: List[str] = Field(..., description="Anchor tables included")
    rag_retrieved_tables: List[str] = Field(..., description="Tables retrieved via RAG")
    total_tables: int = Field(..., description="Total number of tables retrieved")
    tables: List[TableMetadata] = Field(..., description="Detailed table metadata")
    formatted_schema: str = Field(..., description="Human-readable schema context for LLM")


# ============================================================================
# Schema Agent
# ============================================================================

class SchemaAgent:
    """
    Schema Agent - Retrieves relevant database schema using RAG
    """

    def __init__(self):
        """Initialize Schema Agent with RAG retriever"""
        self.rag_retriever = rag_retriever
        logger.info("Schema Agent initialized with RAG retriever")

    def retrieve_schema(self, input_data: SchemaAgentInput) -> SchemaAgentOutput:
        """
        Retrieve relevant schema for user query

        Args:
            input_data: SchemaAgentInput with query and conversation history

        Returns:
            SchemaAgentOutput with retrieved tables and metadata
        """
        logger.info(f"Schema Agent retrieving schema for: {input_data.query}")
        if input_data.conversation_history:
            logger.info(f"Using conversation history with {len(input_data.conversation_history)} messages for domain inference")

        try:
            # Use RAG retriever to get relevant tables (with conversation history)
            rag_result = self.rag_retriever.retrieve_relevant_schema(
                user_query=input_data.query,
                include_similarity_scores=input_data.include_similarity_scores,
                conversation_history=input_data.conversation_history
            )

            # Format schema context for LLM
            formatted_schema = self.rag_retriever.format_schema_context(
                rag_result["all_tables"]
            )

            # Convert tables to TableMetadata objects
            tables = []
            for table_dict in rag_result["all_tables"]:
                # Check if this is an anchor table or RAG-retrieved
                is_anchor = table_dict["full_name"] in rag_result["anchor_tables"]
                similarity = 1.0 if is_anchor else table_dict.get("similarity", 0.0)

                tables.append(TableMetadata(
                    schema_name=table_dict["schema_name"],
                    table_name=table_dict["table_name"],
                    full_name=table_dict["full_name"],
                    description=table_dict["description"],
                    business_terms=table_dict["business_terms"],
                    common_questions=table_dict["common_questions"],
                    key_columns=table_dict["key_columns"],
                    sample_values=table_dict.get("sample_values", {}),
                    row_count=table_dict["row_count"],
                    tier=table_dict["tier"],
                    similarity=similarity
                ))

            # Create output
            output = SchemaAgentOutput(
                query=input_data.query,
                domain=rag_result["domain_info"]["primary_domain"],
                is_cross_departmental=rag_result["domain_info"]["is_cross_departmental"],
                strategy=rag_result["strategy"],
                anchor_tables=rag_result["anchor_tables"],
                rag_retrieved_tables=rag_result["rag_retrieved_tables"],
                total_tables=rag_result["total_tables"],
                tables=tables,
                formatted_schema=formatted_schema
            )

            logger.info(f"Schema Agent retrieved {output.total_tables} tables (Domain: {output.domain})")
            return output

        except Exception as e:
            logger.error(f"Schema Agent error: {e}")
            raise


# ============================================================================
# Convenience Functions
# ============================================================================

def create_schema_agent() -> SchemaAgent:
    """Create and return Schema Agent instance"""
    return SchemaAgent()


def retrieve_schema(query: str, include_similarity: bool = False) -> SchemaAgentOutput:
    """
    Convenience function to retrieve schema

    Args:
        query: User's natural language query
        include_similarity: Whether to include similarity scores

    Returns:
        SchemaAgentOutput with retrieved tables
    """
    input_data = SchemaAgentInput(
        query=query,
        include_similarity_scores=include_similarity
    )

    agent = create_schema_agent()
    return agent.retrieve_schema(input_data)


__all__ = [
    "SchemaAgent",
    "SchemaAgentInput",
    "SchemaAgentOutput",
    "TableMetadata",
    "create_schema_agent",
    "retrieve_schema"
]
