"""
Analyst Agent Module
Analyzes query results and generates business insights
"""
from agents.analyst_agent.agent import (
    AnalystAgent,
    AnalystInput,
    AnalystOutput,
    create_analyst,
    analyze_results
)
from agents.analyst_agent.prompts import (
    ANALYST_AGENT_SYSTEM_PROMPT,
    ANALYZE_RESULTS_PROMPT
)

__all__ = [
    "AnalystAgent",
    "AnalystInput",
    "AnalystOutput",
    "create_analyst",
    "analyze_results",
    "ANALYST_AGENT_SYSTEM_PROMPT",
    "ANALYZE_RESULTS_PROMPT"
]
