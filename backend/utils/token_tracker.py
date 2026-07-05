"""
Token Usage Tracking and Cost Calculation
Tracks LLM API usage and calculates costs based on Claude pricing
"""
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# Claude API Pricing (as of December 2025)
# ============================================================================

CLAUDE_PRICING = {
    "claude-opus-4-5": {
        "base_input": 5.00,           # $5 per million tokens
        "cache_write_5m": 6.25,       # $6.25 per million tokens (5-minute cache)
        "cache_write_1h": 10.00,      # $10 per million tokens (1-hour cache)
        "cache_hit": 0.50,            # $0.50 per million tokens
        "output": 25.00                # $25 per million tokens
    },
    "claude-sonnet-4-5": {
        "base_input": 3.00,           # $3 per million tokens
        "cache_write_5m": 3.75,       # $3.75 per million tokens (5-minute cache)
        "cache_write_1h": 6.00,       # $6 per million tokens (1-hour cache)
        "cache_hit": 0.30,            # $0.30 per million tokens
        "output": 15.00               # $15 per million tokens
    },
    "claude-haiku-4-5": {
        "base_input": 1.00,           # $1 per million tokens
        "cache_write_5m": 1.25,       # $1.25 per million tokens (5-minute cache)
        "cache_write_1h": 2.00,       # $2 per million tokens (1-hour cache)
        "cache_hit": 0.10,            # $0.10 per million tokens
        "output": 5.00                # $5 per million tokens
    }
}


@dataclass
class TokenUsage:
    """Token usage statistics for a single LLM call"""
    agent_name: str
    model: str
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "agent_name": self.agent_name,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat()
        }

    @property
    def total_tokens(self) -> int:
        """Total tokens used (input + output)"""
        return (self.input_tokens +
                self.cache_creation_input_tokens +
                self.cache_read_input_tokens +
                self.output_tokens)


@dataclass
class CostBreakdown:
    """Detailed cost breakdown for LLM usage"""
    base_input_cost: float = 0.0
    cache_write_cost: float = 0.0
    cache_hit_cost: float = 0.0
    output_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total cost in USD"""
        return (self.base_input_cost +
                self.cache_write_cost +
                self.cache_hit_cost +
                self.output_cost)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            "base_input_cost": round(self.base_input_cost, 6),
            "cache_write_cost": round(self.cache_write_cost, 6),
            "cache_hit_cost": round(self.cache_hit_cost, 6),
            "output_cost": round(self.output_cost, 6),
            "total_cost": round(self.total_cost, 6)
        }


def calculate_cost(usage: TokenUsage) -> CostBreakdown:
    """
    Calculate cost for a single LLM call based on token usage

    Args:
        usage: TokenUsage object with token counts

    Returns:
        CostBreakdown with detailed cost information
    """
    model = usage.model.lower()

    # Get pricing for the model (default to Sonnet if not found)
    pricing = CLAUDE_PRICING.get(model, CLAUDE_PRICING["claude-sonnet-4-5"])

    breakdown = CostBreakdown()

    # Calculate costs (convert tokens to millions)
    breakdown.base_input_cost = (usage.input_tokens / 1_000_000) * pricing["base_input"]
    breakdown.cache_write_cost = (usage.cache_creation_input_tokens / 1_000_000) * pricing["cache_write_5m"]
    breakdown.cache_hit_cost = (usage.cache_read_input_tokens / 1_000_000) * pricing["cache_hit"]
    breakdown.output_cost = (usage.output_tokens / 1_000_000) * pricing["output"]

    return breakdown


def aggregate_usage(usages: List[TokenUsage]) -> Dict[str, Any]:
    """
    Aggregate token usage across multiple LLM calls

    Args:
        usages: List of TokenUsage objects

    Returns:
        Dictionary with aggregated statistics
    """
    if not usages:
        return {
            "total_input_tokens": 0,
            "total_cache_creation_tokens": 0,
            "total_cache_read_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "by_agent": {},
            "by_model": {}
        }

    total_input = sum(u.input_tokens for u in usages)
    total_cache_creation = sum(u.cache_creation_input_tokens for u in usages)
    total_cache_read = sum(u.cache_read_input_tokens for u in usages)
    total_output = sum(u.output_tokens for u in usages)

    # Calculate total cost
    total_cost = sum(calculate_cost(u).total_cost for u in usages)

    # Group by agent
    by_agent: Dict[str, Dict[str, Any]] = {}
    for usage in usages:
        if usage.agent_name not in by_agent:
            by_agent[usage.agent_name] = {
                "input_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "calls": 0
            }

        agent_data = by_agent[usage.agent_name]
        agent_data["input_tokens"] += usage.input_tokens
        agent_data["cache_creation_tokens"] += usage.cache_creation_input_tokens
        agent_data["cache_read_tokens"] += usage.cache_read_input_tokens
        agent_data["output_tokens"] += usage.output_tokens
        agent_data["total_tokens"] += usage.total_tokens
        agent_data["cost"] += calculate_cost(usage).total_cost
        agent_data["calls"] += 1

    # Group by model
    by_model: Dict[str, Dict[str, Any]] = {}
    for usage in usages:
        if usage.model not in by_model:
            by_model[usage.model] = {
                "input_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
                "cost": 0.0,
                "calls": 0
            }

        model_data = by_model[usage.model]
        model_data["input_tokens"] += usage.input_tokens
        model_data["cache_creation_tokens"] += usage.cache_creation_input_tokens
        model_data["cache_read_tokens"] += usage.cache_read_input_tokens
        model_data["output_tokens"] += usage.output_tokens
        model_data["total_tokens"] += usage.total_tokens
        model_data["cost"] += calculate_cost(usage).total_cost
        model_data["calls"] += 1

    return {
        "total_input_tokens": total_input,
        "total_cache_creation_tokens": total_cache_creation,
        "total_cache_read_tokens": total_cache_read,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_cache_creation + total_cache_read + total_output,
        "total_cost": round(total_cost, 6),
        "total_llm_calls": len(usages),
        "by_agent": {k: {**v, "cost": round(v["cost"], 6)} for k, v in by_agent.items()},
        "by_model": {k: {**v, "cost": round(v["cost"], 6)} for k, v in by_model.items()}
    }


def extract_token_usage_from_response(
    agent_name: str,
    model: str,
    response: Any
) -> Optional[TokenUsage]:
    """
    Extract token usage from Claude API response

    Args:
        agent_name: Name of the agent making the call
        model: Model name used
        response: Raw response from Claude API

    Returns:
        TokenUsage object or None if extraction fails
    """
    try:
        # Claude API returns usage in response.usage
        if hasattr(response, 'usage'):
            usage_data = response.usage

            return TokenUsage(
                agent_name=agent_name,
                model=model,
                input_tokens=getattr(usage_data, 'input_tokens', 0),
                cache_creation_input_tokens=getattr(usage_data, 'cache_creation_input_tokens', 0),
                cache_read_input_tokens=getattr(usage_data, 'cache_read_input_tokens', 0),
                output_tokens=getattr(usage_data, 'output_tokens', 0)
            )

        return None

    except Exception:
        return None


__all__ = [
    "TokenUsage",
    "CostBreakdown",
    "CLAUDE_PRICING",
    "calculate_cost",
    "aggregate_usage",
    "extract_token_usage_from_response"
]
