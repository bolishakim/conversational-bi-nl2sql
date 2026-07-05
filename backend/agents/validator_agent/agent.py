"""
Validator Agent
Validates SQL queries for syntax, safety, and schema correctness
"""
import json
import re
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
from utils.token_tracker import extract_token_usage_from_response, calculate_cost
from agents.validator_agent.prompts import VALIDATOR_AGENT_SYSTEM_PROMPT, VALIDATE_SQL_PROMPT


# ============================================================================
# Input/Output Schemas
# ============================================================================

class ValidationIssue(BaseModel):
    """Single validation issue"""
    category: str = Field(..., description="Issue category: syntax, safety, schema, complexity")
    severity: str = Field(..., description="Issue severity: error, warning, info")
    message: str = Field(..., description="Detailed description of the issue")
    suggestion: Optional[str] = Field(None, description="How to fix it")


class ValidatorInput(BaseModel):
    """Input to Validator Agent"""
    user_query: str = Field(..., description="Original user query")
    sql: str = Field(..., description="Generated SQL query to validate")
    schema_summary: str = Field(..., description="Summary of available tables/columns")


class ValidatorOutput(BaseModel):
    """Output from Validator Agent"""
    is_valid: bool = Field(..., description="Whether query is safe to execute")
    severity: str = Field(..., description="Overall severity: safe, warning, error, critical")
    issues: List[ValidationIssue] = Field(
        default_factory=list,
        description="List of validation issues found"
    )
    validated_sql: str = Field(..., description="The validated SQL query")
    summary: str = Field(..., description="Brief validation summary")
    token_usage: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Token usage and cost for this LLM call"
    )


# ============================================================================
# Validator Agent
# ============================================================================

class ValidatorAgent:
    """
    Validator Agent - Validates SQL queries before execution
    """

    # Dangerous SQL keywords that should be blocked
    DANGEROUS_KEYWORDS = [
        r'\bDROP\b', r'\bTRUNCATE\b', r'\bDELETE\b', r'\bUPDATE\b',
        r'\bINSERT\b', r'\bALTER\b', r'\bCREATE\b', r'\bGRANT\b',
        r'\bREVOKE\b', r'\bEXEC\b', r'\bEXECUTE\b'
    ]

    def __init__(self, model: str = None):
        """Initialize Validator Agent with Claude client (uses Sonnet for JSON reliability)"""
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        # CHANGED: Use Sonnet instead of Haiku - Haiku produces malformed JSON too often
        self.model = model or settings.CLAUDE_SONNET_MODEL
        logger.info(f"Validator Agent initialized with model: {self.model}")

    def validate(self, input_data: ValidatorInput) -> ValidatorOutput:
        """
        Validate SQL query

        Args:
            input_data: ValidatorInput with SQL query and schema

        Returns:
            ValidatorOutput with validation results
        """
        logger.info(f"Validator Agent validating SQL for: {input_data.user_query}")

        # Quick safety check first (before calling LLM)
        quick_safety_result = self._quick_safety_check(input_data.sql)
        if not quick_safety_result["is_safe"]:
            logger.warning(f"Quick safety check failed: {quick_safety_result['reason']}")
            return ValidatorOutput(
                is_valid=False,
                severity="critical",
                issues=[
                    ValidationIssue(
                        category="safety",
                        severity="error",
                        message=quick_safety_result["reason"],
                        suggestion="Only SELECT queries are allowed. Remove any data modification operations."
                    )
                ],
                validated_sql=input_data.sql,
                summary="Query rejected: Contains dangerous operations"
            )

        # Build user prompt
        user_prompt = VALIDATE_SQL_PROMPT.format(
            user_query=input_data.user_query,
            sql=input_data.sql,
            schema_summary=input_data.schema_summary
        )

        try:
            # Call Claude API for comprehensive validation
            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,  # Increased to prevent JSON truncation with full SQL + detailed validation
                temperature=0.0,  # Deterministic for validation
                system=VALIDATOR_AGENT_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            # Extract response text
            response_text = response.content[0].text
            logger.debug(f"Claude validation response: {response_text}")

            # Extract token usage
            token_usage_data = None
            token_info = extract_token_usage_from_response("validator", self.model, response)
            if token_info:
                cost = calculate_cost(token_info)
                token_usage_data = {
                    **token_info.to_dict(),
                    "cost_breakdown": cost.to_dict()
                }
                logger.info(f"Validator tokens: {token_info.total_tokens} (cost: ${cost.total_cost:.6f})")

            # Parse JSON response
            result = self._parse_response(response_text)

            # Create output
            issues = [
                ValidationIssue(**issue) for issue in result.get("issues", [])
            ]

            # Ensure validated_sql is never None (required by Pydantic)
            validated_sql = result.get("validated_sql")
            if not validated_sql or validated_sql is None:
                validated_sql = input_data.sql

            output = ValidatorOutput(
                is_valid=result.get("is_valid", False),
                severity=result.get("severity", "error"),
                issues=issues,
                validated_sql=validated_sql,
                summary=result.get("summary", "Validation completed"),
                token_usage=token_usage_data
            )

            logger.info(f"Validator: is_valid={output.is_valid}, severity={output.severity}, issues={len(output.issues)}")
            return output

        except Exception as e:
            logger.error(f"Validator Agent error: {e}")
            # Return safe default (reject query on error)
            return ValidatorOutput(
                is_valid=False,
                severity="error",
                issues=[
                    ValidationIssue(
                        category="syntax",
                        severity="error",
                        message=f"Validation error: {str(e)}",
                        suggestion="Please review the SQL syntax"
                    )
                ],
                validated_sql=input_data.sql,
                summary="Validation failed due to error"
            )

    def _quick_safety_check(self, sql: str) -> Dict[str, Any]:
        """
        Quick regex-based safety check for dangerous keywords

        Args:
            sql: SQL query to check

        Returns:
            Dictionary with is_safe and reason
        """
        sql_upper = sql.upper()

        # Check for dangerous keywords
        for pattern in self.DANGEROUS_KEYWORDS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                keyword = pattern.replace(r'\b', '').replace('\\', '')
                return {
                    "is_safe": False,
                    "reason": f"Query contains dangerous keyword: {keyword}. Only SELECT queries are allowed."
                }

        # Check if it's a SELECT query
        if not sql_upper.strip().startswith(('SELECT', 'WITH')):
            return {
                "is_safe": False,
                "reason": "Query must start with SELECT or WITH (for CTEs). Only read-only queries are allowed."
            }

        return {"is_safe": True, "reason": "Passed quick safety check"}

    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """
        Parse Claude's JSON response

        Args:
            response_text: Raw response from Claude

        Returns:
            Parsed validation result dictionary
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
                logger.warning("No JSON found in validation response")
                return {
                    "is_valid": False,
                    "severity": "error",
                    "issues": [{
                        "category": "syntax",
                        "severity": "error",
                        "message": "Could not parse validation response",
                        "suggestion": "Please check SQL syntax and try again"
                    }],
                    "validated_sql": "",
                    "summary": "Validation parse error"
                }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in validation: {e}")
            return {
                "is_valid": False,
                "severity": "error",
                "issues": [{
                    "category": "syntax",
                    "severity": "error",
                    "message": f"JSON parse error: {str(e)}",
                    "suggestion": "Validator could not parse LLM response. Please regenerate SQL query."
                }],
                "validated_sql": "",
                "summary": "Validation JSON parse error"
            }


# ============================================================================
# Convenience Functions
# ============================================================================

def create_validator() -> ValidatorAgent:
    """Create and return Validator Agent instance"""
    return ValidatorAgent()


def validate_sql(
    user_query: str,
    sql: str,
    schema_summary: str
) -> ValidatorOutput:
    """
    Convenience function to validate SQL

    Args:
        user_query: Original user query
        sql: Generated SQL to validate
        schema_summary: Summary of available schema

    Returns:
        ValidatorOutput with validation results
    """
    input_data = ValidatorInput(
        user_query=user_query,
        sql=sql,
        schema_summary=schema_summary
    )

    validator = create_validator()
    return validator.validate(input_data)


__all__ = [
    "ValidatorAgent",
    "ValidatorInput",
    "ValidatorOutput",
    "ValidationIssue",
    "create_validator",
    "validate_sql"
]
