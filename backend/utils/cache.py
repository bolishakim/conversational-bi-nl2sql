"""
Simple Redis Cache Utility
Basic caching for query results and schema retrievals
"""
import json
import redis
from typing import Optional, Any
import sys
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from config import settings
from utils.logger import logger


class SimpleCache:
    """Simple Redis cache wrapper"""

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info(f"Redis cache connected: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.redis_client = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache HIT: {key}")
                return json.loads(value)
            logger.debug(f"Cache MISS: {key}")
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default 1 hour)
        """
        if not self.enabled:
            return

        try:
            self.redis_client.setex(
                key,
                ttl,
                json.dumps(value)
            )
            logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

    def delete(self, key: str):
        """
        Delete key from cache

        Args:
            key: Cache key
        """
        if not self.enabled:
            return

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache DELETE: {key}")
        except Exception as e:
            logger.error(f"Cache delete error: {e}")

    def clear_all(self):
        """Clear all cached data"""
        if not self.enabled:
            return

        try:
            self.redis_client.flushdb()
            logger.info("Cache cleared")
        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    def check_rate_limit(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        """
        Fixed-window rate limit via Redis INCR + EXPIRE.

        Returns (allowed, retry_after_seconds). retry_after_seconds is 0 when
        allowed. Fails open (returns allowed=True) when Redis is unavailable
        so the app stays usable during Redis outages.
        """
        if not self.enabled:
            return (True, 0)
        try:
            current = self.redis_client.incr(key)
            if current == 1:
                self.redis_client.expire(key, window_seconds)
            if current > limit:
                ttl = self.redis_client.ttl(key)
                return (False, max(int(ttl), 1))
            return (True, 0)
        except Exception as e:
            logger.error(f"Rate limit check error on {key}: {e}")
            return (True, 0)


# Global cache instance
cache = SimpleCache()


__all__ = ["cache", "SimpleCache"]
