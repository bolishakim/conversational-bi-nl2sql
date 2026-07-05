"""
SQL Agent
Generates SQL queries from natural language using retrieved schema
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from anthropic import Anthropic

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings
from utils.logger import logger
from utils.token_tracker import extract_token_usage_from_response, TokenUsage
from agents.sql_agent.prompts import SQL_AGENT_SYSTEM_PROMPT, GENERATE_SQL_PROMPT


# ============================================================================
# Input/Output Schemas
# ============================================================================

class SQLAgentInput(BaseModel):
    """Input to SQL Agent"""
    query: str = Field(..., description="User's natural language query")
    schema_context: str = Field(..., description="Formatted schema context from Schema Agent")
    domain: str = Field(..., description="Query domain (sales, hr, production, etc.)")
    query_type: str = Field(
        default="factual",
        description="Query type (factual, analytical, comparison, trend)"
    )
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Previous conversation messages for context (follow-up queries)"
    )
    validation_feedback: Optional[List[Dict[str, str]]] = Field(
        default=None,
        description="Validation issues from previous SQL attempt (for retry)"
    )
    execution_error: Optional[str] = Field(
        default=None,
        description="Execution error from previous SQL attempt (for learning from PostgreSQL errors)"
    )
    previous_sql: Optional[str] = Field(
        default=None,
        description="Previous SQL that failed validation or execution (for retry)"
    )
    retry_attempt: int = Field(
        default=0,
        description="Retry attempt number (0 = first attempt)"
    )
    query_iteration: int = Field(
        default=0,
        description="Query iteration number for multi-query mode (0 = first query)"
    )
    max_iterations: int = Field(
        default=3,
        description="Maximum number of query iterations allowed"
    )
    followup_query_reason: Optional[str] = Field(
        default=None,
        description="Reason why follow-up query is needed (from analyst)"
    )


class SQLAgentOutput(BaseModel):
    """Output from SQL Agent"""
    query: str = Field(..., description="Original user query")
    reasoning_steps: List[str] = Field(
        ...,
        description="Chain-of-thought reasoning steps taken to generate the SQL"
    )
    sql: str = Field(..., description="Generated PostgreSQL SQL query")
    explanation: str = Field(..., description="Explanation of what the query does")
    tables_used: List[str] = Field(..., description="List of tables used in the query")
    key_assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions made during query generation"
    )
    domain: str = Field(..., description="Query domain")
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage and cost for this LLM call"
    )


# ============================================================================
# SQL Agent
# ============================================================================

class SQLAgent:
    """
    SQL Agent - Generates PostgreSQL SQL from natural language
    """

    def __init__(self, model: str = None):
        """Initialize SQL Agent with Claude client (uses Sonnet for quality with multi-query iteration)"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # CHANGED: Back to Sonnet for multi-query iteration - Haiku struggles with complex window functions
        self.model = model or settings.CLAUDE_SONNET_MODEL
        logger.info(f"SQL Agent initialized with model: {self.model}")

    def generate_sql(self, input_data: SQLAgentInput) -> SQLAgentOutput:
        """
        Generate SQL query from natural language

        Args:
            input_data: SQLAgentInput with query and schema context

        Returns:
            SQLAgentOutput with generated SQL and metadata
        """
        if input_data.retry_attempt > 0:
            logger.info(f"SQL Agent RETRY (attempt {input_data.retry_attempt}) for: {input_data.query}")
        else:
            logger.info(f"SQL Agent generating query for: {input_data.query}")

        # Format conversation history for context
        history_text = self._format_conversation_history(input_data.conversation_history)

        # Build iteration context message
        iteration_context = ""
        if input_data.query_iteration > 0:
            iteration_context = f"\n**This is iteration {input_data.query_iteration + 1} of a multi-query analysis.**\n"
            if input_data.followup_query_reason:
                iteration_context += f"**Analyst's Request:** {input_data.followup_query_reason}\n"
                iteration_context += "Build upon previous query results to provide deeper analysis.\n"

        # Build user prompt
        user_prompt = GENERATE_SQL_PROMPT.format(
            query=input_data.query,
            iteration=input_data.query_iteration + 1,
            max_iterations=input_data.max_iterations,
            iteration_context=iteration_context,
            conversation_history=history_text,
            schema_context=input_data.schema_context,
            query_type=input_data.query_type,
            domain=input_data.domain
        )

        # Add validation feedback if this is a retry
        if input_data.validation_feedback and input_data.previous_sql:
            feedback_text = self._format_validation_feedback(
                input_data.previous_sql,
                input_data.validation_feedback,
                input_data.retry_attempt
            )
            user_prompt = feedback_text + "\n\n" + user_prompt

        # Add execution error feedback if SQL failed to execute
        if input_data.execution_error and input_data.previous_sql:
            execution_feedback = self._format_execution_error_feedback(
                input_data.previous_sql,
                input_data.execution_error,
                input_data.retry_attempt
            )
            user_prompt = execution_feedback + "\n\n" + user_prompt

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Increased from 2048 to handle complex multi-CTE queries
                temperature=0.0,  # Deterministic for SQL generation
                system=SQL_AGENT_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract response text
            response_text = response.content[0].text
            logger.debug(f"Claude response: {response_text}")

            # Extract token usage
            token_usage_data = None
            token_info = extract_token_usage_from_response("sql_agent", self.model, response)
            if token_info:
                from utils.token_tracker import calculate_cost
                cost = calculate_cost(token_info)
                token_usage_data = {
                    **token_info.to_dict(),
                    "cost_breakdown": cost.to_dict()
                }
                logger.info(f"SQL Agent tokens: {token_info.total_tokens} (cost: ${cost.total_cost:.6f})")

            # Parse JSON response
            result = self._parse_response(response_text)

            # Create output
            output = SQLAgentOutput(
                query=input_data.query,
                reasoning_steps=result.get("reasoning_steps", []),
                sql=result.get("sql", ""),
                explanation=result.get("explanation", "No explanation provided"),
                tables_used=result.get("tables_used", []),
                key_assumptions=result.get("key_assumptions", []),
                domain=input_data.domain,
                token_usage=token_usage_data
            )

            logger.info(f"SQL Agent generated query using {len(output.tables_used)} tables with {len(output.reasoning_steps)} reasoning steps")
            return output

        except Exception as e:
            logger.error(f"SQL Agent error: {e}")
            raise

    def _format_conversation_history(
        self,
        conversation_history: Optional[List[Dict[str, str]]]
    ) -> str:
        """
        Format conversation history for SQL generation context

        Args:
            conversation_history: List of conversation messages

        Returns:
            Formatted history string
        """
        if not conversation_history or len(conversation_history) == 0:
            return "No previous conversation"

        # Format last 3 query-response pairs (6 messages) for context
        recent_history = conversation_history[-6:]

        formatted = []
        for msg in recent_history:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            formatted.append(f"{role}: {content}")

        return "\n".join(formatted)

    def _format_validation_feedback(
        self,
        previous_sql: str,
        validation_issues: List[Dict[str, str]],
        retry_attempt: int
    ) -> str:
        """
        Format validation feedback into a prompt for retry

        Args:
            previous_sql: SQL that failed validation
            validation_issues: List of validation issues
            retry_attempt: Current retry attempt number

        Returns:
            Formatted feedback text
        """
        feedback_lines = [
            f"⚠️ VALIDATION FEEDBACK (Retry Attempt {retry_attempt}):",
            "",
            "Your previous SQL query failed validation. Please fix the issues below:",
            "",
            "PREVIOUS SQL:",
            "```sql",
            previous_sql,
            "```",
            "",
            "VALIDATION ISSUES:"
        ]

        for i, issue in enumerate(validation_issues, 1):
            feedback_lines.append(f"\n{i}. {issue.get('category', 'Unknown').upper()}")
            feedback_lines.append(f"   Severity: {issue.get('severity', 'unknown')}")
            feedback_lines.append(f"   Issue: {issue.get('message', 'No message')}")
            if issue.get('suggestion'):
                feedback_lines.append(f"   Suggestion: {issue.get('suggestion')}")

        feedback_lines.extend([
            "",
            "Please generate a CORRECTED SQL query that addresses all the issues above.",
            "Make sure to:",
            "- Fix all validation errors",
            "- Follow the suggestions provided",
            "- Ensure the query is safe and correct",
            "- Maintain the original intent of the query",
            ""
        ])

        return "\n".join(feedback_lines)

    def _format_execution_error_feedback(
        self,
        previous_sql: str,
        execution_error: str,
        retry_attempt: int
    ) -> str:
        """
        Format PostgreSQL execution error into helpful feedback for SQL Agent

        Args:
            previous_sql: SQL that failed to execute
            execution_error: PostgreSQL error message
            retry_attempt: Current retry attempt number

        Returns:
            Formatted error feedback text
        """
        feedback_lines = [
            f"❌ EXECUTION ERROR FEEDBACK (Retry Attempt {retry_attempt}):",
            "",
            "Your previous SQL query passed validation but FAILED during execution in PostgreSQL.",
            "The database returned the following error:",
            "",
            "PREVIOUS SQL:",
            "```sql",
            previous_sql,
            "```",
            "",
            "POSTGRESQL ERROR:",
            "```",
            execution_error,
            "```",
            "",
            "COMMON FIXES FOR THIS ERROR:",
            ""
        ]

        # Provide specific guidance based on error type
        if "extract(unknown" in execution_error.lower() or "does not exist" in execution_error.lower():
            feedback_lines.extend([
                "🔧 TYPE CASTING ERROR DETECTED:",
                "",
                "This error occurs when PostgreSQL cannot determine the data type of an expression.",
                "For date/timestamp arithmetic, you MUST use explicit type casts:",
                "",
                "WRONG:",
                "  EXTRACT(EPOCH FROM (enddate - hiredate))",
                "",
                "CORRECT:",
                "  EXTRACT(EPOCH FROM (enddate::timestamp - hiredate::timestamp))",
                "",
                "Or use the AGE function:",
                "  EXTRACT(YEAR FROM AGE(enddate::timestamp, hiredate::timestamp))",
                "",
                "Apply explicit ::timestamp or ::date casts to ALL date columns used in arithmetic operations.",
                ""
            ])
        elif "column" in execution_error.lower() and "does not exist" in execution_error.lower():
            feedback_lines.extend([
                "🔧 COLUMN NOT FOUND:",
                "",
                "The column referenced in your query doesn't exist in the table.",
                "Check the schema context provided and use exact column names (case-sensitive).",
                "Verify you're querying the correct table/view.",
                ""
            ])
        elif "relation" in execution_error.lower() and "does not exist" in execution_error.lower():
            feedback_lines.extend([
                "🔧 TABLE/VIEW NOT FOUND:",
                "",
                "The table or view doesn't exist. Always use schema-qualified names:",
                "CORRECT: schema_name.table_name",
                "WRONG: table_name",
                ""
            ])
        elif "syntax error" in execution_error.lower():
            feedback_lines.extend([
                "🔧 SQL SYNTAX ERROR:",
                "",
                "There's a syntax error in your SQL. Common issues:",
                "- Missing commas between SELECT columns",
                "- Unclosed parentheses or quotes",
                "- Invalid keywords or function names",
                "- Incorrect JOIN syntax",
                ""
            ])
        elif "division by zero" in execution_error.lower():
            feedback_lines.extend([
                "🔧 DIVISION BY ZERO:",
                "",
                "Use NULLIF to prevent division by zero:",
                "CORRECT: value / NULLIF(denominator, 0)",
                "WRONG: value / denominator",
                ""
            ])
        else:
            feedback_lines.extend([
                "🔧 GENERAL DEBUGGING TIPS:",
                "",
                "- Check data types match for all operations",
                "- Verify all column and table names exist in schema",
                "- Ensure JOIN conditions use compatible types",
                "- Add explicit type casts where needed (::type)",
                ""
            ])

        feedback_lines.extend([
            "Please generate a CORRECTED SQL query that fixes the execution error.",
            "Focus on:",
            "1. Adding explicit type casts for all date/timestamp operations",
            "2. Verifying all column and table names against the schema",
            "3. Ensuring proper PostgreSQL syntax",
            ""
        ])

        return "\n".join(feedback_lines)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed result dictionary
        """
        try:
            # Try to find JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                result = json.loads(json_text)
                return result
            else:
                logger.warning("No JSON found in response")
                return {
                    "reasoning_steps": [],
                    "sql": "",
                    "explanation": "Could not parse response",
                    "tables_used": [],
                    "key_assumptions": ["Failed to parse Claude response"]
                }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "reasoning_steps": [],
                "sql": "",
                "explanation": "JSON parse error",
                "tables_used": [],
                "key_assumptions": [f"Failed to parse JSON: {str(e)}"]
            }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_sql_agent() -> SQLAgent:
    """Create and return SQL Agent instance"""
    return SQLAgent()


def generate_sql(
    query: str,
    schema_context: str,
    domain: str,
    query_type: str = "factual"
) -> SQLAgentOutput:
    """
    Convenience function to generate SQL

    Args:
        query: User's natural language query
        schema_context: Formatted schema context
        domain: Query domain
        query_type: Type of query

    Returns:
        SQLAgentOutput with generated SQL
    """
    input_data = SQLAgentInput(
        query=query,
        schema_context=schema_context,
        domain=domain,
        query_type=query_type
    )

    agent = create_sql_agent()
    return agent.generate_sql(input_data)


__all__ = [
    "SQLAgent",
    "SQLAgentInput",
    "SQLAgentOutput",
    "create_sql_agent",
    "generate_sql"
]
