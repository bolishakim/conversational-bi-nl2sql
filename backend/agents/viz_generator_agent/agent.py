"""
Visualization Generator Agent
Intelligently selects chart types and generates visualization configurations
"""
import json
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from anthropic import Anthropic

from config import settings
from utils.logger import logger
from utils.token_tracker import extract_token_usage_from_response, calculate_cost
from agents.viz_generator_agent.prompts import (
    VIZ_GENERATOR_SYSTEM_PROMPT,
    GENERATE_VIZ_PROMPT
)


# ============================================================================
# Input/Output Models
# ============================================================================

class VizGeneratorInput(BaseModel):
    """Input for Visualization Generator Agent"""
    user_query: str = Field(..., description="Original user query")
    sql_query: str = Field(..., description="SQL query that was executed")
    results: List[Dict[str, Any]] = Field(..., description="Query results as list of dicts")
    row_count: int = Field(..., description="Number of rows returned")


class ChartConfig(BaseModel):
    """Chart configuration for frontend"""
    x_axis: Optional[str] = Field(None, description="Column name for X axis")
    y_axis: Optional[str] = Field(None, description="Column name for Y axis")
    title: str = Field(..., description="Chart title")
    labels: List[str] = Field(default_factory=list, description="Data labels")
    values: List[Any] = Field(default_factory=list, description="Data values")
    colors: Optional[List[str]] = Field(None, description="Optional color scheme")


class VizGeneratorOutput(BaseModel):
    """Output from Visualization Generator Agent"""
    chart_type: str = Field(..., description="Selected chart type: bar, line, pie, table")
    reasoning: str = Field(..., description="Why this chart type was selected")
    chart_config: Dict[str, Any] = Field(..., description="Chart configuration for frontend")
    data_insights: List[str] = Field(default_factory=list, description="Key observations about data")
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage and cost for this LLM call"
    )


# ============================================================================
# Visualization Generator Agent
# ============================================================================

class VizGeneratorAgent:
    """
    Visualization Generator Agent - Intelligently selects chart types

    Features:
    - Smart chart type selection based on data structure
    - Considers user intent from original query
    - Handles edge cases (single row, many columns, etc.)
    - Generates frontend-ready chart configurations
    """

    def __init__(self, model: str = None):
        """Initialize Visualization Generator with Claude client"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # Use Sonnet for intelligent chart selection
        self.model = model or settings.CLAUDE_SONNET_MODEL
        logger.info(f"VizGenerator Agent initialized with model: {self.model}")

    def generate_visualization(self, input_data: VizGeneratorInput) -> VizGeneratorOutput:
        """
        Generate visualization configuration based on query results

        Args:
            input_data: VizGeneratorInput with query and results

        Returns:
            VizGeneratorOutput with chart type and configuration
        """
        logger.info(f"VizGenerator analyzing {input_data.row_count} rows for visualization")

        # Prepare results preview (first 10 rows)
        results_preview = input_data.results[:10]
        results_json = json.dumps(results_preview, indent=2, default=str)

        # Extract column information
        column_info = self._analyze_columns(input_data.results)

        # Build user prompt
        user_prompt = GENERATE_VIZ_PROMPT.format(
            user_query=input_data.user_query,
            sql_query=input_data.sql_query,
            row_count=input_data.row_count,
            results_preview=results_json,
            column_info=column_info
        )

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=0.0,  # Deterministic for visualization logic
                system=VIZ_GENERATOR_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract response text
            response_text = response.content[0].text
            logger.debug(f"VizGenerator response: {response_text[:200]}...")

            # Extract token usage
            token_usage_data = None
            token_info = extract_token_usage_from_response("viz_generator", self.model, response)
            if token_info:
                cost = calculate_cost(token_info)
                token_usage_data = {
                    **token_info.to_dict(),
                    "cost_breakdown": cost.to_dict()
                }
                logger.info(f"VizGenerator tokens: {token_info.total_tokens} (cost: ${cost.total_cost:.6f})")

            # Parse JSON response
            result = self._parse_response(response_text)

            # Create output
            output = VizGeneratorOutput(
                chart_type=result.get("chart_type", "table"),
                reasoning=result.get("reasoning", "Chart type selected based on data structure"),
                chart_config=result.get("chart_config", {}),
                data_insights=result.get("data_insights", []),
                token_usage=token_usage_data
            )

            logger.info(f"VizGenerator selected: {output.chart_type}")
            return output

        except Exception as e:
            logger.error(f"VizGenerator error: {e}")
            # Fallback to table on error
            return VizGeneratorOutput(
                chart_type="table",
                reasoning=f"Error during visualization generation: {str(e)}. Defaulting to table.",
                chart_config={
                    "title": "Query Results",
                    "labels": [],
                    "values": []
                },
                data_insights=[]
            )

    def _analyze_columns(self, results: List[Dict[str, Any]]) -> str:
        """
        Analyze column structure of results

        Args:
            results: Query results

        Returns:
            Formatted column information string
        """
        if not results or len(results) == 0:
            return "No data returned"

        first_row = results[0]
        columns = list(first_row.keys())

        column_info_lines = [
            f"Total Columns: {len(columns)}",
            "\nColumns:"
        ]

        for i, col in enumerate(columns, 1):
            # Sample first few values to determine type
            sample_values = [row.get(col) for row in results[:5] if row.get(col) is not None]

            if sample_values:
                sample_type = type(sample_values[0]).__name__
                sample_preview = str(sample_values[0])[:30]
                column_info_lines.append(
                    f"  {i}. {col} ({sample_type}) - Example: {sample_preview}"
                )
            else:
                column_info_lines.append(f"  {i}. {col} (unknown type)")

        return "\n".join(column_info_lines)

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
                logger.warning("No JSON found in VizGenerator response")
                return {
                    "chart_type": "table",
                    "reasoning": "Could not parse visualization recommendation",
                    "chart_config": {},
                    "data_insights": []
                }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in VizGenerator: {e}")
            return {
                "chart_type": "table",
                "reasoning": "JSON parsing failed, defaulting to table",
                "chart_config": {},
                "data_insights": []
            }


# ============================================================================
# Factory Function
# ============================================================================

def create_viz_generator(model: str = None) -> VizGeneratorAgent:
    """
    Create a new Visualization Generator Agent instance

    Args:
        model: Optional Claude model name

    Returns:
        VizGeneratorAgent instance
    """
    return VizGeneratorAgent(model=model)


__all__ = ["VizGeneratorAgent", "VizGeneratorInput", "VizGeneratorOutput", "create_viz_generator"]
