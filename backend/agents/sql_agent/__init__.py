"""
SQL Agent Module
Generates SQL queries from natural language
"""
from agents.sql_agent.agent import (
    SQLAgent,
    SQLAgentInput,
    SQLAgentOutput,
    create_sql_agent,
    generate_sql
)
from agents.sql_agent.prompts import (
    SQL_AGENT_SYSTEM_PROMPT,
    GENERATE_SQL_PROMPT
)

__all__ = [
    "SQLAgent",
    "SQLAgentInput",
    "SQLAgentOutput",
    "create_sql_agent",
    "generate_sql",
    "SQL_AGENT_SYSTEM_PROMPT",
    "GENERATE_SQL_PROMPT"
]
