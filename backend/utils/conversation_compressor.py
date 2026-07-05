"""
Conversation History Compression
Compresses older conversation messages to reduce token usage
"""
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.logger import logger


class ConversationCompressor:
    """
    Compresses conversation history to reduce token usage

    Strategy:
    1. Keep last N messages in full (recent context)
    2. Compress older messages into summaries
    3. Total token budget: ~500-1000 tokens (vs 2000+ uncompressed)
    """

    def __init__(
        self,
        keep_recent: int = 3,  # Keep last 3 exchanges in full
        max_summary_length: int = 150,  # Max chars per summary
        max_total_length: int = 2000  # Max total chars for all history
    ):
        """
        Initialize conversation compressor

        Args:
            keep_recent: Number of recent message pairs to keep in full
            max_summary_length: Maximum length of each compressed summary
            max_total_length: Maximum total length of conversation history
        """
        self.keep_recent = keep_recent
        self.max_summary_length = max_summary_length
        self.max_total_length = max_total_length

    def compress(
        self,
        conversation_history: List[Dict[str, str]]
    ) -> List[Dict[str, str]]:
        """
        Compress conversation history

        Args:
            conversation_history: List of {role, content} dicts

        Returns:
            Compressed conversation history
        """
        if not conversation_history:
            return []

        # Calculate number of messages to keep in full
        # Each exchange = user message + assistant response = 2 messages
        messages_to_keep_full = self.keep_recent * 2

        if len(conversation_history) <= messages_to_keep_full:
            # No compression needed
            return conversation_history

        # Split into old (to compress) and recent (keep full)
        old_messages = conversation_history[:-messages_to_keep_full]
        recent_messages = conversation_history[-messages_to_keep_full:]

        # Compress old messages into summary
        compressed_old = self._compress_old_messages(old_messages)

        # Combine: compressed summary + recent full messages
        if compressed_old:
            return [compressed_old] + recent_messages
        else:
            return recent_messages

    def _compress_old_messages(
        self,
        messages: List[Dict[str, str]]
    ) -> Dict[str, str]:
        """
        Compress old messages into a single summary message

        Args:
            messages: Old messages to compress

        Returns:
            Single summary message
        """
        if not messages:
            return None

        # Group messages into exchanges (user + assistant pairs)
        exchanges = []
        for i in range(0, len(messages), 2):
            if i + 1 < len(messages):
                user_msg = messages[i]
                assistant_msg = messages[i + 1]

                # Create concise summary of exchange
                summary = self._summarize_exchange(user_msg, assistant_msg)
                if summary:
                    exchanges.append(summary)

        if not exchanges:
            return None

        # Combine all exchange summaries
        combined_summary = "\n".join([
            f"- Q: {exch['query']} → A: {exch['response']}"
            for exch in exchanges
        ])

        # Truncate if too long
        if len(combined_summary) > self.max_total_length // 2:
            combined_summary = combined_summary[:self.max_total_length // 2] + "..."

        return {
            "role": "system",
            "content": f"Previous conversation context (compressed):\n{combined_summary}"
        }

    def _summarize_exchange(
        self,
        user_msg: Dict[str, str],
        assistant_msg: Dict[str, str]
    ) -> Dict[str, str]:
        """
        Summarize a single user-assistant exchange

        Args:
            user_msg: User message dict
            assistant_msg: Assistant response dict

        Returns:
            Summary dict with query and response
        """
        user_query = user_msg.get("content", "")
        assistant_response = assistant_msg.get("content", "")

        # Extract query (truncate if long)
        query_summary = user_query[:100] + "..." if len(user_query) > 100 else user_query

        # Extract key information from assistant response
        response_summary = self._extract_key_info(assistant_response)

        return {
            "query": query_summary,
            "response": response_summary
        }

    def _extract_key_info(self, text: str) -> str:
        """
        Extract key information from assistant response

        Args:
            text: Full assistant response text

        Returns:
            Concise summary (max max_summary_length chars)
        """
        if not text:
            return "No response"

        # Look for domain indicators
        domain = None
        if "Domain: sales" in text:
            domain = "sales"
        elif "Domain: hr" in text:
            domain = "hr"
        elif "Domain: production" in text:
            domain = "production"

        # Extract result count if present
        result_count = None
        import re
        count_match = re.search(r'(\d+)\s+row', text, re.IGNORECASE)
        if count_match:
            result_count = count_match.group(1)

        # Build concise summary
        parts = []
        if domain:
            parts.append(f"domain={domain}")
        if result_count:
            parts.append(f"{result_count} rows")

        # If we found structured info, use it
        if parts:
            summary = ", ".join(parts)
        else:
            # Otherwise, take first sentence or N chars
            summary = text[:self.max_summary_length]
            if len(text) > self.max_summary_length:
                summary += "..."

        return summary


# ============================================================================
# Factory Function
# ============================================================================

_compressor_instance = None

def get_conversation_compressor() -> ConversationCompressor:
    """
    Get or create conversation compressor singleton

    Returns:
        ConversationCompressor instance
    """
    global _compressor_instance

    if _compressor_instance is None:
        _compressor_instance = ConversationCompressor(
            keep_recent=3,  # Keep last 3 exchanges in full
            max_summary_length=150,
            max_total_length=2000
        )

    return _compressor_instance


__all__ = ["ConversationCompressor", "get_conversation_compressor"]
