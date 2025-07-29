"""
Redis client for caching functionality.
"""

import redis
import logging
from typing import Optional
from ..core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client wrapper with connection management"""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self._connect()
    
    def _connect(self):
        """Establish Redis connection"""
        try:
            self.client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            self.client.ping()
            logger.info("Successfully connected to Redis.")
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Could not connect to Redis: {e}")
            self.client = None
    
    def get(self, key: str) -> Optional[str]:
        """Get value from Redis"""
        if not self.client:
            return None
        try:
            return self.client.get(key)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis GET error: {e}")
            return None
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set value in Redis with optional expiration"""
        if not self.client:
            return False
        try:
            return self.client.set(key, value, ex=ex)
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis SET error: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except redis.exceptions.RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return False
    
    def ping(self) -> bool:
        """Check Redis connection"""
        if not self.client:
            return False
        try:
            return self.client.ping()
        except redis.exceptions.RedisError:
            return False

# Global Redis client instance
redis_client = RedisClient()