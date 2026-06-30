import redis.asyncio as aioredis
from backend.config import settings
from backend.shared.logger import get_logger
from typing import Optional

logger = get_logger(__name__)

class RedisClient:
    """
    Asynchronous Redis Client interface with an in-memory fallback if Redis is unavailable.
    """
    def __init__(self):
        self.redis_url = settings.REDIS_URL
        self.client = aioredis.from_url(self.redis_url, decode_responses=True)
        self._in_memory_db = {}
        self._use_fallback = False

    async def get(self, key: str) -> Optional[str]:
        if self._use_fallback:
            return self._in_memory_db.get(key)
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.warning(f"Redis get failed, falling back to in-memory: {e}")
            self._use_fallback = True
            return self._in_memory_db.get(key)

    async def set(self, key: str, value: str, expire_seconds: Optional[int] = None) -> None:
        if self._use_fallback:
            self._in_memory_db[key] = value
            return
        try:
            await self.client.set(key, value, ex=expire_seconds)
        except Exception as e:
            logger.warning(f"Redis set failed, falling back to in-memory: {e}")
            self._use_fallback = True
            self._in_memory_db[key] = value

    async def exists(self, key: str) -> bool:
        if self._use_fallback:
            return key in self._in_memory_db
        try:
            return await self.client.exists(key) > 0
        except Exception as e:
            logger.warning(f"Redis exists failed, falling back to in-memory: {e}")
            self._use_fallback = True
            return key in self._in_memory_db

    async def close(self) -> None:
        if not self._use_fallback:
            try:
                await self.client.aclose()
            except Exception:
                pass

# Global singleton client instance
redis_client = RedisClient()

# INTEGRATION NOTE
# This module exposes a global `redis_client` instance.
# Member 1 (ingestion/fingerprint.py) relies on this to execute SHA256 duplicate verification lookup.

