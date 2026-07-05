"""
Query History Service
Handles saving and retrieving query history from the database
"""
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from database.models import QueryHistory
from database.connection import get_db_session
from utils.logger import logger


# ============================================================================
# Query History Service
# ============================================================================

class HistoryService:
    """
    History Service - Manages query history persistence

    Features:
    - Save query results to database
    - Retrieve user query history
    - Filter and paginate history
    - Delete old queries
    """

    def _convert_decimals(self, obj):
        """
        Recursively convert Decimal objects to float for JSON serialization

        Args:
            obj: Object that may contain Decimal values

        Returns:
            Object with Decimals converted to float
        """
        from decimal import Decimal

        if isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._convert_decimals(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_decimals(item) for item in obj]
        return obj

    async def save_query(
        self,
        user_id: str,
        query_data: Dict[str, Any],
        participant_id: Optional[str] = None
    ) -> str:
        """
        Save a query and its complete workflow to history (Extended for thesis analysis)

        Args:
            user_id: User ID
            query_data: Complete query response data from workflow
            participant_id: Optional participant ID (for shared user accounts)

        Returns:
            Query history ID
        """
        try:
            async with get_db_session() as session:
                import json

                # Convert any Decimal values in result_data
                result_data = query_data.get("result_data")
                if result_data:
                    result_data = self._convert_decimals(result_data)

                # Extract and prepare fields
                history_entry = QueryHistory(
                    user_id=user_id,
                    participant_id=participant_id,  # Link to specific participant

                    # ========================================================================
                    # Query Information
                    # ========================================================================
                    user_query=query_data.get("query", ""),
                    domain=query_data.get("domain"),
                    is_cross_departmental=query_data.get("is_cross_departmental", False),
                    conversation_context=query_data.get("conversation_context"),

                    # ========================================================================
                    # Orchestrator Output
                    # ========================================================================
                    orchestrator_action=query_data.get("orchestrator_action"),
                    orchestrator_reasoning=query_data.get("orchestrator_reasoning"),
                    needs_visualization=query_data.get("needs_visualization", False),

                    # ========================================================================
                    # Schema Retrieval (RAG)
                    # ========================================================================
                    retrieved_tables=query_data.get("retrieved_tables", []),
                    anchor_tables=query_data.get("anchor_tables"),
                    rag_retrieved_tables=query_data.get("rag_retrieved_tables"),
                    similarity_scores=query_data.get("similarity_scores"),
                    retrieval_strategy=query_data.get("retrieval_strategy"),

                    # ========================================================================
                    # SQL Generation
                    # ========================================================================
                    generated_sql=query_data.get("generated_sql"),
                    sql_explanation=query_data.get("sql_explanation"),
                    sql_reasoning_steps=query_data.get("sql_reasoning_steps"),
                    tables_used=query_data.get("tables_used"),
                    sql_assumptions=query_data.get("sql_assumptions"),
                    sql_retry_count=query_data.get("sql_retry_count", 0),

                    # ========================================================================
                    # SQL Validation
                    # ========================================================================
                    validation_passed=query_data.get("validation_passed"),
                    validation_severity=query_data.get("validation_severity"),
                    validation_issues=query_data.get("validation_issues"),
                    validation_summary=query_data.get("validation_summary"),

                    # ========================================================================
                    # Query Execution
                    # ========================================================================
                    execution_status=query_data.get("execution_status"),
                    execution_error=query_data.get("execution_error"),
                    result_data=result_data,
                    row_count=result_data.get("row_count") if result_data else query_data.get("row_count"),
                    execution_time_ms=result_data.get("execution_time_ms") if result_data else query_data.get("execution_time_ms"),

                    # ========================================================================
                    # Multi-Query Iteration
                    # ========================================================================
                    query_iteration_count=query_data.get("query_iteration_count", 0),
                    needs_followup_query=query_data.get("needs_followup_query", False),
                    followup_query_reason=query_data.get("followup_query_reason"),
                    all_query_results=query_data.get("all_query_results"),

                    # ========================================================================
                    # Analysis
                    # ========================================================================
                    analysis_reasoning_steps=query_data.get("analysis_reasoning_steps"),
                    analysis_summary=query_data.get("analysis_summary"),
                    key_insights=query_data.get("key_insights"),
                    recommendations=query_data.get("recommendations"),
                    data_quality_notes=query_data.get("data_quality_notes"),

                    # ========================================================================
                    # Visualization
                    # ========================================================================
                    chart_type=query_data.get("chart_type"),
                    chart_config=query_data.get("chart_config"),
                    chart_reasoning=query_data.get("chart_reasoning"),
                    visualization_code=query_data.get("visualization_code"),

                    # ========================================================================
                    # Token Usage & Cost
                    # ========================================================================
                    token_usage=query_data.get("token_usage"),
                    total_input_tokens=query_data.get("total_input_tokens"),
                    total_output_tokens=query_data.get("total_output_tokens"),
                    total_tokens=query_data.get("total_tokens"),
                    total_cost_usd=str(query_data.get("total_cost")) if query_data.get("total_cost") else None,
                    llm_calls_count=query_data.get("llm_calls_count"),

                    # ========================================================================
                    # Workflow Metadata
                    # ========================================================================
                    workflow_id=query_data.get("workflow_id"),
                    workflow_started_at=query_data.get("started_at"),
                    workflow_completed_at=query_data.get("completed_at"),
                    total_duration_ms=query_data.get("total_duration_ms"),
                    error_occurred=query_data.get("error_occurred", False),
                    error_stage=query_data.get("error_stage"),
                    error_details=query_data.get("error_details"),

                    # ========================================================================
                    # Metadata
                    # ========================================================================
                    created_at=datetime.now(timezone.utc)
                )

                # Backward compatibility: Save legacy analysis field if present
                analysis = query_data.get("analysis")
                if analysis and isinstance(analysis, dict):
                    history_entry.analysis = json.dumps(self._convert_decimals(analysis))

                session.add(history_entry)
                await session.commit()
                await session.refresh(history_entry)

                logger.info(f"Saved query history: {history_entry.id} (workflow: {history_entry.workflow_id})")
                return history_entry.id

        except Exception as e:
            logger.error(f"Error saving query history: {e}")
            raise

    async def get_user_history(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        domain: Optional[str] = None,
        participant_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve query history for a user, optionally filtered by participant

        Args:
            user_id: User ID
            limit: Maximum number of queries to return
            offset: Number of queries to skip
            domain: Optional domain filter (sales, hr, production)
            participant_id: Optional participant ID filter (for shared user accounts)

        Returns:
            List of query history entries
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, desc

                # Build query
                query = select(QueryHistory).where(QueryHistory.user_id == user_id)

                # Add participant filter if specified (for shared user accounts)
                # This ensures participants only see their own history
                if participant_id:
                    query = query.where(QueryHistory.participant_id == participant_id)

                # Add domain filter if specified
                if domain:
                    query = query.where(QueryHistory.domain == domain)

                # Order by most recent first
                query = query.order_by(desc(QueryHistory.created_at))

                # Add pagination
                query = query.limit(limit).offset(offset)

                # Execute query
                result = await session.execute(query)
                history_entries = result.scalars().all()

                # Format results
                return [self._format_history_entry(entry) for entry in history_entries]

        except Exception as e:
            logger.error(f"Error retrieving user history: {e}")
            raise

    async def get_query_by_id(
        self,
        query_id: str,
        user_id: str,
        participant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific query by ID

        Args:
            query_id: Query history ID
            user_id: User ID (for authorization)
            participant_id: Optional participant ID filter (for shared user accounts)

        Returns:
            Query history entry or None
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select

                # Get query with user ID check
                query = select(QueryHistory).where(
                    QueryHistory.id == query_id,
                    QueryHistory.user_id == user_id
                )

                # Add participant filter if specified
                if participant_id:
                    query = query.where(QueryHistory.participant_id == participant_id)

                result = await session.execute(query)
                entry = result.scalar_one_or_none()

                if entry:
                    return self._format_history_entry(entry)
                return None

        except Exception as e:
            logger.error(f"Error retrieving query by ID: {e}")
            raise

    async def delete_query(
        self,
        query_id: str,
        user_id: str,
        participant_id: Optional[str] = None
    ) -> bool:
        """
        Delete a query from history

        Args:
            query_id: Query history ID
            user_id: User ID (for authorization)
            participant_id: Optional participant ID filter (for shared user accounts)

        Returns:
            True if deleted, False if not found
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, delete

                # Check if query exists and belongs to user
                query = select(QueryHistory).where(
                    QueryHistory.id == query_id,
                    QueryHistory.user_id == user_id
                )

                # Add participant filter if specified
                if participant_id:
                    query = query.where(QueryHistory.participant_id == participant_id)

                result = await session.execute(query)
                entry = result.scalar_one_or_none()

                if not entry:
                    return False

                # Delete the query
                await session.delete(entry)
                await session.commit()

                logger.info(f"Deleted query history: {query_id}")
                return True

        except Exception as e:
            logger.error(f"Error deleting query: {e}")
            raise

    async def get_history_stats(
        self,
        user_id: str,
        participant_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics about user's query history

        Args:
            user_id: User ID
            participant_id: Optional participant ID filter (for shared user accounts)

        Returns:
            Statistics dict
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, func

                # Base filter conditions
                base_conditions = [QueryHistory.user_id == user_id]
                if participant_id:
                    base_conditions.append(QueryHistory.participant_id == participant_id)

                # Total queries
                total_query = select(func.count(QueryHistory.id)).where(*base_conditions)
                total_result = await session.execute(total_query)
                total_queries = total_result.scalar()

                # Successful queries
                success_query = select(func.count(QueryHistory.id)).where(
                    *base_conditions,
                    QueryHistory.execution_status == "success"
                )
                success_result = await session.execute(success_query)
                successful_queries = success_result.scalar()

                # Domain breakdown
                domain_query = select(
                    QueryHistory.domain,
                    func.count(QueryHistory.id).label("count")
                ).where(*base_conditions).group_by(QueryHistory.domain)

                domain_result = await session.execute(domain_query)
                domain_breakdown = {row.domain or "unknown": row.count for row in domain_result}

                return {
                    "total_queries": total_queries,
                    "successful_queries": successful_queries,
                    "failed_queries": total_queries - successful_queries,
                    "success_rate": (successful_queries / total_queries * 100) if total_queries > 0 else 0,
                    "domain_breakdown": domain_breakdown
                }

        except Exception as e:
            logger.error(f"Error getting history stats: {e}")
            raise

    async def get_recent_conversation(
        self,
        user_id: str,
        limit: int = 5,
        compress: bool = True
    ) -> List[Dict[str, str]]:
        """
        Get recent conversation history formatted for agent context (WITH COMPRESSION)

        Returns the last N query-response pairs formatted as conversation messages
        for the Orchestrator to understand context in follow-up questions.

        OPTIMIZATION: Compresses older messages to reduce token usage.

        Args:
            user_id: User ID
            limit: Number of recent queries to retrieve (default 5)
            compress: Whether to compress older messages (default True)

        Returns:
            List of conversation messages in format:
            [
                {"role": "user", "content": "query text"},
                {"role": "assistant", "content": "summary of results"},
                ...
            ]
        """
        try:
            async with get_db_session() as session:
                from sqlalchemy import select, desc

                # Get recent queries
                query = select(QueryHistory).where(
                    QueryHistory.user_id == user_id
                ).order_by(desc(QueryHistory.created_at)).limit(limit)

                result = await session.execute(query)
                history_entries = result.scalars().all()

                # Format as conversation messages (most recent last)
                conversation = []
                for entry in reversed(history_entries):  # Reverse to get chronological order
                    # Add user query
                    conversation.append({
                        "role": "user",
                        "content": entry.user_query
                    })

                    # Add assistant response with summary
                    assistant_content = self._create_assistant_summary(entry)
                    conversation.append({
                        "role": "assistant",
                        "content": assistant_content
                    })

                # OPTIMIZATION: Compress conversation to reduce tokens
                if compress and len(conversation) > 6:  # More than 3 exchanges
                    from utils.conversation_compressor import get_conversation_compressor
                    compressor = get_conversation_compressor()
                    conversation = compressor.compress(conversation)
                    logger.info(f"Compressed conversation history from {len(history_entries)*2} to {len(conversation)} messages")

                return conversation

        except Exception as e:
            logger.error(f"Error retrieving recent conversation: {e}")
            # Return empty conversation on error - don't fail the query
            return []

    def _create_assistant_summary(self, entry: QueryHistory) -> str:
        """
        Create a concise summary of the assistant's response for conversation context

        Args:
            entry: QueryHistory database model

        Returns:
            Summary string for conversation history
        """
        import json

        if entry.execution_status != "success":
            return f"Query failed: {entry.execution_error or 'Unknown error'}"

        # Parse analysis for summary
        summary = None
        key_insights = []
        if entry.analysis:
            try:
                analysis = json.loads(entry.analysis)
                summary = analysis.get("summary")
                key_insights = analysis.get("key_insights", [])
            except:
                pass

        # If we have a good summary from analysis, use it with some context
        if summary:
            context_parts = []

            # Add domain context
            if entry.domain:
                context_parts.append(f"Domain: {entry.domain}")

            # Add the summary
            context_parts.append(summary)

            # Add first key insight if available for extra context
            if key_insights and len(key_insights) > 0:
                first_insight = key_insights[0]
                if len(first_insight) < 200:  # Only include if not too long
                    context_parts.append(f"Detail: {first_insight}")

            return ". ".join(context_parts)

        # Fallback: Build basic summary from available data
        parts = []

        # Add domain
        if entry.domain:
            parts.append(f"Domain: {entry.domain}")

        # Add SQL query info
        if entry.generated_sql:
            tables = entry.retrieved_tables or []
            if tables:
                parts.append(f"Queried {', '.join(tables[:3])}")

        # Add result summary
        if entry.row_count is not None:
            parts.append(f"returned {entry.row_count} row(s)")

        return ". ".join(parts) if parts else "Query executed successfully"

    def _format_history_entry(self, entry: QueryHistory) -> Dict[str, Any]:
        """
        Format a QueryHistory entry for API response

        Args:
            entry: QueryHistory database model

        Returns:
            Formatted dict
        """
        import json

        # Parse analysis JSON if present
        analysis = None
        if entry.analysis:
            try:
                analysis = json.loads(entry.analysis)
            except:
                analysis = entry.analysis

        return {
            "id": entry.id,
            "user_query": entry.user_query,
            "domain": entry.domain,
            "orchestrator_action": entry.orchestrator_action,
            "retrieved_tables": entry.retrieved_tables,
            "generated_sql": entry.generated_sql,
            "sql_explanation": entry.sql_explanation,
            "execution_status": entry.execution_status,
            "execution_error": entry.execution_error,
            "result_data": entry.result_data,
            "row_count": entry.row_count,
            "execution_time_ms": entry.execution_time_ms,
            "analysis": analysis,
            "chart_type": entry.chart_type,
            "chart_config": entry.chart_config,
            "total_duration_ms": entry.total_duration_ms,
            "error_occurred": entry.error_occurred,
            "created_at": entry.created_at.isoformat() if entry.created_at else None
        }


# ============================================================================
# Factory Function
# ============================================================================

_history_service_instance = None

def get_history_service() -> HistoryService:
    """
    Get or create history service singleton

    Returns:
        HistoryService instance
    """
    global _history_service_instance

    if _history_service_instance is None:
        _history_service_instance = HistoryService()

    return _history_service_instance


__all__ = ["HistoryService", "get_history_service"]
