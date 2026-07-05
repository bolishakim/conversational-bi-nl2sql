"""
Orchestrator Agent
Routes queries and decides which agents to invoke
"""
import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from anthropic import Anthropic

# Add backend to Python path
backend_dir = Path(__file__).parent.parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings
from utils.logger import logger
from utils.token_tracker import extract_token_usage_from_response, calculate_cost
from agents.orchestrator.prompts import ORCHESTRATOR_SYSTEM_PROMPT, ANALYZE_QUERY_PROMPT


# ============================================================================
# Input/Output Schemas
# ============================================================================

class ConversationMessage(BaseModel):
    """Single conversation message"""
    role: str = Field(..., description="User or assistant")
    content: str = Field(..., description="Message content")
    timestamp: Optional[str] = None


class OrchestratorInput(BaseModel):
    """Input to Orchestrator Agent"""
    query: str = Field(..., description="User's natural language query")
    conversation_history: List[ConversationMessage] = Field(
        default_factory=list,
        description="Previous conversation messages"
    )
    has_previous_results: bool = Field(
        default=False,
        description="Whether previous query results exist"
    )


class OrchestratorOutput(BaseModel):
    """Output from Orchestrator Agent"""
    action: str = Field(
        ...,
        description="Action type: DIRECT_ANSWER, INTERPRET_PREVIOUS, MODIFY_VISUALIZATION, FULL_PIPELINE"
    )
    reasoning: str = Field(..., description="Why this action was chosen")
    needs_visualization: bool = Field(
        default=False,
        description="Whether the query needs visualization"
    )
    direct_response: Optional[str] = Field(
        None,
        description="Direct response text if action is DIRECT_ANSWER"
    )
    context_required: List[str] = Field(
        default_factory=list,
        description="Required context from previous queries (e.g., 'previous_sql', 'previous_results')"
    )
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage and cost for this LLM call"
    )


# ============================================================================
# Orchestrator Agent
# ============================================================================

class OrchestratorAgent:
    """
    Orchestrator Agent - Routes queries and decides agent workflow
    """

    def __init__(self, model: str = None):
        """Initialize Orchestrator with Claude client (uses Haiku for cost efficiency)"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = model or settings.CLAUDE_HAIKU_MODEL
        logger.info(f"Orchestrator Agent initialized with model: {self.model}")

    def analyze(self, input_data: OrchestratorInput) -> OrchestratorOutput:
        """
        Analyze user query and decide routing

        Args:
            input_data: OrchestratorInput with query and conversation history

        Returns:
            OrchestratorOutput with action type and reasoning
        """
        logger.info(f"Orchestrator analyzing query: {input_data.query}")

        # Format conversation history
        history_text = self._format_history(input_data.conversation_history)

        # Build user prompt
        user_prompt = ANALYZE_QUERY_PROMPT.format(
            query=input_data.query,
            history=history_text if history_text else "No previous conversation",
            has_previous_results="Yes" if input_data.has_previous_results else "No"
        )

        try:
            # Call Claude API
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                system=ORCHESTRATOR_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract response text
            response_text = response.content[0].text
            logger.debug(f"Claude response: {response_text}")

            # Extract token usage
            token_usage_data = None
            token_info = extract_token_usage_from_response("orchestrator", self.model, response)
            if token_info:
                cost = calculate_cost(token_info)
                token_usage_data = {
                    **token_info.to_dict(),
                    "cost_breakdown": cost.to_dict()
                }
                logger.info(f"Orchestrator tokens: {token_info.total_tokens} (cost: ${cost.total_cost:.6f})")

            # Parse JSON response
            decision = self._parse_response(response_text)

            # Create output
            output = OrchestratorOutput(
                action=decision.get("action", "FULL_PIPELINE"),
                reasoning=decision.get("reasoning", "No reasoning provided"),
                needs_visualization=decision.get("needs_visualization", False),
                direct_response=decision.get("direct_response"),
                context_required=decision.get("context_required", []),
                token_usage=token_usage_data
            )

            logger.info(f"Orchestrator decision: {output.action}")
            return output

        except Exception as e:
            logger.error(f"Orchestrator error: {e}")
            # Fallback to FULL_PIPELINE on error
            return OrchestratorOutput(
                action="FULL_PIPELINE",
                reasoning=f"Error during analysis: {str(e)}. Defaulting to full pipeline.",
                needs_visualization=False
            )

    def _format_history(self, history: List[ConversationMessage]) -> str:
        """
        Format conversation history for the prompt

        Args:
            history: List of conversation messages

        Returns:
            Formatted history string
        """
        if not history:
            return ""

        formatted = []
        for msg in history[-5:]:  # Only last 5 messages
            role = msg.role.upper()
            formatted.append(f"{role}: {msg.content}")

        return "\n".join(formatted)

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed decision dictionary
        """
        try:
            # Try to find JSON in the response
            start_idx = response_text.find("{")
            end_idx = response_text.rfind("}") + 1

            if start_idx != -1 and end_idx > start_idx:
                json_text = response_text[start_idx:end_idx]
                decision = json.loads(json_text)
                return decision
            else:
                logger.warning("No JSON found in response")
                return {"action": "FULL_PIPELINE", "reasoning": "Could not parse response"}

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {"action": "FULL_PIPELINE", "reasoning": "JSON parse error"}


# ============================================================================
# Convenience Functions
# ============================================================================

def create_orchestrator() -> OrchestratorAgent:
    """Create and return Orchestrator Agent instance"""
    return OrchestratorAgent()


def analyze_query(
    query: str,
    conversation_history: Optional[List[Dict[str, str]]] = None,
    has_previous_results: bool = False
) -> OrchestratorOutput:
    """
    Convenience function to analyze a query

    Args:
        query: User's natural language query
        conversation_history: List of previous messages (optional)
        has_previous_results: Whether previous results exist

    Returns:
        OrchestratorOutput with routing decision
    """
    # Convert dict history to ConversationMessage objects
    messages = []
    if conversation_history:
        for msg in conversation_history:
            messages.append(ConversationMessage(
                role=msg.get("role", "user"),
                content=msg.get("content", "")
            ))

    # Create input
    input_data = OrchestratorInput(
        query=query,
        conversation_history=messages,
        has_previous_results=has_previous_results
    )

    # Analyze
    orchestrator = create_orchestrator()
    return orchestrator.analyze(input_data)


__all__ = [
    "OrchestratorAgent",
    "OrchestratorInput",
    "OrchestratorOutput",
    "ConversationMessage",
    "create_orchestrator",
    "analyze_query"
]
