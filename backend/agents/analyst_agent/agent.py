"""
Analyst Agent
Analyzes query results and generates business insights with chain-of-thought reasoning
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from anthropic import Anthropic

from config import settings
from utils.logger import logger
from utils.token_tracker import extract_token_usage_from_response, calculate_cost
from agents.analyst_agent.prompts import (
    ANALYST_AGENT_SYSTEM_PROMPT,
    ANALYZE_RESULTS_PROMPT,
    ITERATIVE_ANALYST_SYSTEM_PROMPT,
    ITERATIVE_ANALYZE_PROMPT
)


# ============================================================================
# Input/Output Models
# ============================================================================

class AnalystInput(BaseModel):
    """Input for Analyst Agent"""
    user_query: str = Field(..., description="Original user query")
    sql: str = Field(..., description="SQL query that was executed")
    results: List[Dict[str, Any]] = Field(..., description="Query results as list of dicts")
    result_count: int = Field(..., description="Number of rows returned")


class AnalystOutput(BaseModel):
    """Output from Analyst Agent"""
    reasoning_steps: List[str] = Field(..., description="Chain-of-thought reasoning steps")
    summary: str = Field(..., description="One-sentence key finding")
    key_insights: List[str] = Field(..., description="Bulleted insights with specific numbers")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    data_quality_notes: List[str] = Field(default_factory=list, description="Caveats and limitations")
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage and cost for this LLM call"
    )


class IterativeAnalystInput(BaseModel):
    """Input for Analyst Agent in iterative multi-query mode"""
    user_query: str = Field(..., description="Original user query")
    current_iteration: int = Field(..., description="Current query iteration number (0-based)")
    max_iterations: int = Field(default=3, description="Maximum allowed iterations")
    all_query_results: List[Dict[str, Any]] = Field(..., description="All query results collected so far")


class IterativeAnalystOutput(BaseModel):
    """Output from Analyst Agent with iteration decision"""
    needs_followup_query: bool = Field(..., description="Whether more data is needed")
    followup_query_reason: Optional[str] = Field(None, description="Why follow-up query is needed")
    suggested_next_query: Optional[str] = Field(None, description="Natural language description of what to query next")
    final_answer_ready: bool = Field(..., description="Whether we have enough data for final answer")

    # Standard analysis fields (populated if final_answer_ready=True)
    reasoning_steps: List[str] = Field(default_factory=list, description="Chain-of-thought reasoning")
    summary: str = Field(default="", description="One-sentence key finding")
    key_insights: List[str] = Field(default_factory=list, description="Insights with numbers")
    recommendations: List[str] = Field(default_factory=list, description="Actionable recommendations")
    data_quality_notes: List[str] = Field(default_factory=list, description="Caveats")
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage and cost for this LLM call"
    )


# ============================================================================
# Analyst Agent
# ============================================================================

class AnalystAgent:
    """
    Analyst Agent - Analyzes query results with chain-of-thought reasoning

    Features:
    - 3-step chain-of-thought analysis framework
    - Business-focused insights
    - Data quality assessment
    """

    def __init__(self, model: str = None):
        """
        Initialize Analyst Agent (uses Sonnet for quality analysis with multi-query iteration)

        Args:
            model: Claude model to use
        """
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # CHANGED: Back to Sonnet for multi-query iteration - need quality analysis and iteration decisions
        self.model = model or settings.CLAUDE_SONNET_MODEL
        logger.info(f"Analyst Agent initialized with model: {self.model}")

    def analyze(self, input_data: AnalystInput) -> AnalystOutput:
        """
        Analyze query results and generate insights

        Args:
            input_data: Analysis input with query, SQL, and results

        Returns:
            AnalystOutput with reasoning and insights
        """
        logger.info(f"Analyst Agent analyzing results for: {input_data.user_query}")

        # Format results for Claude
        results_summary = self._format_results_for_analysis(
            input_data.results,
            input_data.result_count
        )

        # Build user prompt
        user_prompt = ANALYZE_RESULTS_PROMPT.format(
            query=input_data.user_query,
            sql=input_data.sql,
            results_summary=results_summary,
            result_count=input_data.result_count
        )

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=ANALYST_AGENT_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # Extract response content
            response_text = response.content[0].text
            logger.debug(f"Claude response: {response_text[:200]}...")

            # Extract token usage
            token_usage_data = None
            token_info = extract_token_usage_from_response("analyst", self.model, response)
            if token_info:
                cost = calculate_cost(token_info)
                token_usage_data = {
                    **token_info.to_dict(),
                    "cost_breakdown": cost.to_dict()
                }
                logger.info(f"Analyst tokens: {token_info.total_tokens} (cost: ${cost.total_cost:.6f})")

            # Parse JSON response
            result = self._parse_response(response_text)

            # Create output
            output = AnalystOutput(
                reasoning_steps=result.get("reasoning_steps", []),
                summary=result.get("summary", "Analysis completed"),
                key_insights=result.get("key_insights", []),
                recommendations=result.get("recommendations", []),
                data_quality_notes=result.get("data_quality_notes", []),
                token_usage=token_usage_data
            )

            logger.info(f"Analyst generated {len(output.key_insights)} insights with {len(output.reasoning_steps)} reasoning steps")
            return output

        except Exception as e:
            logger.error(f"Analyst Agent error: {e}")
            raise

    def _format_results_for_analysis(
        self,
        results: List[Dict[str, Any]],
        result_count: int,
        max_rows_to_show: int = 20
    ) -> str:
        """
        Format query results for Claude analysis

        Args:
            results: Query results
            result_count: Total result count
            max_rows_to_show: Maximum rows to include

        Returns:
            Formatted results string
        """
        if not results:
            return "No results returned"

        # Show first N rows
        rows_to_show = results[:max_rows_to_show]

        # Format as readable text
        lines = []
        for i, row in enumerate(rows_to_show, 1):
            row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
            lines.append(f"  Row {i}: {row_str}")

        formatted = "\n".join(lines)

        # Add truncation note if needed
        if result_count > max_rows_to_show:
            formatted += f"\n\n  ... (showing first {max_rows_to_show} of {result_count} rows)"

        return formatted

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response

        Args:
            response_text: Raw response text

        Returns:
            Parsed JSON dict
        """
        # Extract JSON from markdown code blocks if present
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_text = response_text[start:end].strip()
        else:
            json_text = response_text.strip()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Response text: {response_text}")
            raise ValueError(f"Invalid JSON response from Claude: {e}")

    def iterative_analyze(self, input_data: IterativeAnalystInput) -> IterativeAnalystOutput:
        """
        Analyze accumulated results and determine if follow-up query is needed

        Args:
            input_data: Iterative analysis input with all query results

        Returns:
            IterativeAnalystOutput with decision and optional final analysis
        """
        logger.info(f"Iterative Analyst analyzing iteration {input_data.current_iteration}/{input_data.max_iterations}")

        # Format all results for Claude
        all_results_summary = self._format_all_query_results(input_data.all_query_results)

        # Build user prompt
        user_prompt = ITERATIVE_ANALYZE_PROMPT.format(
            user_query=input_data.user_query,
            current_iteration=input_data.current_iteration,
            max_iterations=input_data.max_iterations,
            all_results_summary=all_results_summary
        )

        try:
            # Call Claude API with iterative system prompt
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                system=ITERATIVE_ANALYST_SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            )

            # Extract response content
            response_text = response.content[0].text
            logger.debug(f"Iterative analyst response: {response_text[:200]}...")

            # Extract token usage
            token_usage_data = None
            token_info = extract_token_usage_from_response("analyst", self.model, response)
            if token_info:
                cost = calculate_cost(token_info)
                token_usage_data = {
                    **token_info.to_dict(),
                    "cost_breakdown": cost.to_dict()
                }
                logger.info(f"Analyst (iterative) tokens: {token_info.total_tokens} (cost: ${cost.total_cost:.6f})")

            # Parse JSON response
            result = self._parse_response(response_text)

            # Create output
            output = IterativeAnalystOutput(
                needs_followup_query=result.get("needs_followup_query", False),
                followup_query_reason=result.get("followup_query_reason"),
                suggested_next_query=result.get("suggested_next_query"),
                final_answer_ready=result.get("final_answer_ready", False),
                reasoning_steps=result.get("reasoning_steps", []),
                summary=result.get("summary", ""),
                key_insights=result.get("key_insights", []),
                recommendations=result.get("recommendations", []),
                data_quality_notes=result.get("data_quality_notes", []),
                token_usage=token_usage_data
            )

            if output.needs_followup_query:
                logger.info(f"Analyst requests follow-up query: {output.followup_query_reason}")
            else:
                logger.info(f"Analyst ready with final answer: {len(output.key_insights)} insights")

            return output

        except Exception as e:
            logger.error(f"Iterative Analyst error: {e}")
            raise

    def _format_all_query_results(
        self,
        all_query_results: List[Dict[str, Any]],
        max_rows_per_query: int = 10
    ) -> str:
        """
        Format all accumulated query results for iterative analysis

        Args:
            all_query_results: List of query result dicts
            max_rows_per_query: Max rows to show per query

        Returns:
            Formatted string with all results
        """
        if not all_query_results:
            return "No query results yet"

        lines = []
        for query_result in all_query_results:
            iteration = query_result.get("iteration", 0)
            sql = query_result.get("sql", "")
            purpose = query_result.get("purpose", "")
            results = query_result.get("results") or []  # Handle None
            row_count = query_result.get("row_count", 0)

            # Safely calculate row_count if not provided
            if row_count == 0 and results:
                row_count = len(results)

            lines.append(f"\n### Query {iteration + 1}:")
            if purpose:
                lines.append(f"**Purpose:** {purpose}")
            lines.append(f"**SQL:**\n{sql[:300]}...")  # Truncate long SQL

            # Check if query had execution error
            if row_count == 0 and not results:
                lines.append(f"**Results:** Query failed or returned 0 rows")
            else:
                lines.append(f"**Results:** {row_count} rows")

            # Show sample rows
            if results and len(results) > 0:
                rows_to_show = results[:max_rows_per_query]
                for i, row in enumerate(rows_to_show, 1):
                    row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
                    lines.append(f"  Row {i}: {row_str}")

                if row_count > max_rows_per_query:
                    lines.append(f"  ... ({row_count - max_rows_per_query} more rows)")

        return "\n".join(lines)


# ============================================================================
# Factory Function
# ============================================================================

def create_analyst(model: str = "claude-sonnet-4-5") -> AnalystAgent:
    """
    Create an Analyst Agent instance

    Args:
        model: Claude model to use

    Returns:
        AnalystAgent instance
    """
    return AnalystAgent(model=model)


def analyze_results(
    user_query: str,
    sql: str,
    results: List[Dict[str, Any]],
    result_count: int
) -> AnalystOutput:
    """
    Convenience function to analyze query results

    Args:
        user_query: Original user query
        sql: SQL query that was executed
        results: Query results
        result_count: Number of rows

    Returns:
        AnalystOutput with insights
    """
    analyst = create_analyst()

    input_data = AnalystInput(
        user_query=user_query,
        sql=sql,
        results=results,
        result_count=result_count
    )

    return analyst.analyze(input_data)
