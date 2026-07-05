"""
Schema Agent Module
Retrieves relevant database schema using RAG
"""
from agents.schema.agent import (
    SchemaAgent,
    SchemaAgentInput,
    SchemaAgentOutput,
    TableMetadata,
    create_schema_agent,
    retrieve_schema
)
from agents.schema.prompts import SCHEMA_AGENT_SYSTEM_PROMPT

__all__ = [
    "SchemaAgent",
    "SchemaAgentInput",
    "SchemaAgentOutput",
    "TableMetadata",
    "create_schema_agent",
    "retrieve_schema",
    "SCHEMA_AGENT_SYSTEM_PROMPT"
]
