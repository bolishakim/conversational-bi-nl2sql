"""
Executor Agent
Safely executes validated SQL queries with timeout and error handling
"""
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

from utils.database import get_db_connection
from utils.logger import logger


# ============================================================================
# Input/Output Models
# ============================================================================

class ExecutorInput(BaseModel):
    """Input for SQL execution"""
    sql: str = Field(..., description="Validated SQL query to execute")
    user_query: str = Field(..., description="Original user query for context")
    timeout_seconds: int = Field(default=30, description="Query timeout in seconds")
    max_rows: int = Field(default=1000, description="Maximum rows to return")


class ExecutorOutput(BaseModel):
    """Output from SQL execution"""
    success: bool = Field(..., description="Whether execution succeeded")
    results: Optional[List[Dict[str, Any]]] = Field(default=None, description="Query results as list of dicts")
    row_count: int = Field(default=0, description="Number of rows returned")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    columns: Optional[List[str]] = Field(default=None, description="Column names in result set")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")
    was_truncated: bool = Field(default=False, description="Whether results were truncated due to max_rows")


# ============================================================================
# Executor Agent
# ============================================================================

class ExecutorAgent:
    """
    Executor Agent - Safely executes validated SQL queries

    Features:
    - Query timeout protection
    - Result row limiting
    - Connection management
    - Detailed error handling
    - Execution timing
    """

    def __init__(self, default_timeout: int = 30, default_max_rows: int = 1000):
        """
        Initialize Executor Agent

        Args:
            default_timeout: Default query timeout in seconds
            default_max_rows: Default maximum rows to return
        """
        self.default_timeout = default_timeout
        self.default_max_rows = default_max_rows
        logger.info(f"Executor Agent initialized (timeout={default_timeout}s, max_rows={default_max_rows})")

    def execute(self, input_data: ExecutorInput) -> ExecutorOutput:
        """
        Execute validated SQL query safely

        Args:
            input_data: Execution input with SQL and parameters

        Returns:
            ExecutorOutput with results or error
        """
        logger.info(f"Executor Agent executing query for: {input_data.user_query}")
        logger.debug(f"SQL to execute: {input_data.sql[:200]}...")

        start_time = time.time()
        conn = None
        cursor = None

        try:
            # Get database connection
            conn = get_db_connection()
            cursor = conn.cursor()

            # Set statement timeout (PostgreSQL-specific)
            timeout_ms = input_data.timeout_seconds * 1000
            cursor.execute(f"SET statement_timeout = {timeout_ms}")

            # Execute query
            logger.debug("Executing SQL query...")
            cursor.execute(input_data.sql)

            # Fetch results
            rows = cursor.fetchall()
            column_names = [desc[0] for desc in cursor.description] if cursor.description else []

            # Convert to list of dicts
            results = []
            for row in rows[:input_data.max_rows]:
                row_dict = {}
                for i, col_name in enumerate(column_names):
                    value = row[i]
                    # Convert datetime objects to ISO format strings
                    if isinstance(value, datetime):
                        value = value.isoformat()
                    row_dict[col_name] = value
                results.append(row_dict)

            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000

            # Check if results were truncated
            was_truncated = len(rows) > input_data.max_rows
            actual_row_count = min(len(rows), input_data.max_rows)

            logger.info(f"Query executed successfully: {actual_row_count} rows in {execution_time_ms:.2f}ms")
            if was_truncated:
                logger.warning(f"Results truncated: {len(rows)} total rows, returning first {input_data.max_rows}")

            return ExecutorOutput(
                success=True,
                results=results,
                row_count=actual_row_count,
                execution_time_ms=execution_time_ms,
                columns=column_names,
                was_truncated=was_truncated
            )

        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            error_msg = str(e)

            # Categorize error types
            if "timeout" in error_msg.lower() or "canceling statement" in error_msg.lower():
                error_type = "Query timeout"
                logger.error(f"Query timeout after {input_data.timeout_seconds}s: {error_msg}")
            elif "permission denied" in error_msg.lower():
                error_type = "Permission denied"
                logger.error(f"Permission error: {error_msg}")
            elif "does not exist" in error_msg.lower():
                error_type = "Schema error"
                logger.error(f"Schema error: {error_msg}")
            elif "syntax error" in error_msg.lower():
                error_type = "Syntax error"
                logger.error(f"Syntax error: {error_msg}")
            else:
                error_type = "Execution error"
                logger.error(f"Execution error: {error_msg}")

            return ExecutorOutput(
                success=False,
                results=None,
                row_count=0,
                execution_time_ms=execution_time_ms,
                columns=None,
                error_message=f"{error_type}: {error_msg}",
                was_truncated=False
            )

        finally:
            # Clean up resources
            if cursor:
                cursor.close()
            if conn:
                conn.close()
                logger.debug("Database connection closed")


# ============================================================================
# Factory Function
# ============================================================================

def create_executor(timeout: int = 30, max_rows: int = 1000) -> ExecutorAgent:
    """
    Create an Executor Agent instance

    Args:
        timeout: Default query timeout in seconds
        max_rows: Default maximum rows to return

    Returns:
        ExecutorAgent instance
    """
    return ExecutorAgent(default_timeout=timeout, default_max_rows=max_rows)


def execute_sql(
    sql: str,
    user_query: str = "",
    timeout_seconds: int = 30,
    max_rows: int = 1000
) -> ExecutorOutput:
    """
    Convenience function to execute SQL

    Args:
        sql: SQL query to execute
        user_query: Original user query for context
        timeout_seconds: Query timeout
        max_rows: Maximum rows to return

    Returns:
        ExecutorOutput with results or error
    """
    executor = create_executor(timeout=timeout_seconds, max_rows=max_rows)

    input_data = ExecutorInput(
        sql=sql,
        user_query=user_query or "Direct SQL execution",
        timeout_seconds=timeout_seconds,
        max_rows=max_rows
    )

    return executor.execute(input_data)
