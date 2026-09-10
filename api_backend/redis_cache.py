"""
VisionGuard AI - Redis Cache Layer
====================================
Provides async-compatible caching for audit results using Redis.
Prevents redundant LLM calls and browser sessions for recently
audited URLs, dramatically reducing cost and latency.
"""

import hashlib
import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("visionguard.redis_cache")

# Redis connection parameters from environment
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Default TTL: 1 hour (in seconds)
DEFAULT_CACHE_TTL = int(os.getenv("CACHE_TTL_SECONDS", 3600))


def _generate_cache_key(url: str) -> str:
    """Generate a deterministic cache key from a URL."""
    url_hash = hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]
    return f"visionguard:audit:{url_hash}"


class RedisCache:
    """
    Async-compatible Redis caching layer for VisionGuard audit results.
    
    Uses a lazy-connection pattern: the Redis client is only created
    when the first cache operation is attempted. This allows the app
    to start even if Redis is not yet available.
    """
    
    def __init__(
        self,
        host: str = REDIS_HOST,
        port: int = REDIS_PORT,
        db: int = REDIS_DB,
        password: Optional[str] = REDIS_PASSWORD,
        ttl: int = DEFAULT_CACHE_TTL,
    ):
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.ttl = ttl
        self._client = None
        self._available = True  # Flag to avoid repeated connection attempts

    def _get_client(self):
        """Lazily create the Redis client."""
        if not self._available:
            return None
        
        if self._client is None:
            try:
                import redis
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    decode_responses=True,
                    socket_connect_timeout=2,
                )
                # Test the connection
                self._client.ping()
                logger.info(f"Redis connected at {self.host}:{self.port}")
            except Exception as e:
                logger.warning(
                    f"Redis not available ({e}). "
                    f"Cache disabled — all requests will hit the pipeline directly."
                )
                self._client = None
                self._available = False
        
        return self._client

    def get_cached_audit(self, url: str) -> Optional[dict]:
        """
        Retrieve a cached audit result for the given URL.
        
        Args:
            url: The audited URL.
        
        Returns:
            The cached audit result dict, or None if not cached.
        """
        client = self._get_client()
        if client is None:
            return None
        
        try:
            key = _generate_cache_key(url)
            data = client.get(key)
            if data:
                logger.info(f"Cache HIT for {url}")
                return json.loads(data)
            else:
                logger.info(f"Cache MISS for {url}")
                return None
        except Exception as e:
            logger.error(f"Redis GET error: {e}")
            return None

    def cache_audit_result(self, url: str, result: dict) -> bool:
        """
        Store an audit result in the cache.
        
        Args:
            url: The audited URL.
            result: The audit result dictionary to cache.
        
        Returns:
            True if cached successfully, False otherwise.
        """
        client = self._get_client()
        if client is None:
            return False
        
        try:
            key = _generate_cache_key(url)
            client.setex(key, self.ttl, json.dumps(result, default=str))
            logger.info(f"Cached result for {url} (TTL: {self.ttl}s)")
            return True
        except Exception as e:
            logger.error(f"Redis SET error: {e}")
            return False

    def invalidate(self, url: str) -> bool:
        """Remove a cached audit result."""
        client = self._get_client()
        if client is None:
            return False
        
        try:
            key = _generate_cache_key(url)
            client.delete(key)
            logger.info(f"Invalidated cache for {url}")
            return True
        except Exception as e:
            logger.error(f"Redis DELETE error: {e}")
            return False

    def is_available(self) -> bool:
        """Check if Redis is reachable."""
        client = self._get_client()
        return client is not None
