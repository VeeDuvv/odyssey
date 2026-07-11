"""Redis connection for message bus and caching."""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from odyssey.config import settings


class RedisStore:
    """Async Redis wrapper for message bus and caching."""

    def __init__(self) -> None:
        self._client: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await self._client.ping()

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # --- Stream operations for agent message bus ---

    async def stream_add(self, stream: str, data: dict[str, Any]) -> str:
        """Add a message to a Redis Stream. Returns the message ID."""
        return await self.client.xadd(stream, data)

    async def stream_read(
        self,
        stream: str,
        last_id: str = "0-0",
        count: int = 10,
        block: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        """Read messages from a Redis Stream."""
        results = await self.client.xread({stream: last_id}, count=count, block=block)
        if not results:
            return []
        # results is [(stream_name, [(id, data), ...])]
        return results[0][1]

    async def stream_create_group(
        self, stream: str, group: str, start_id: str = "0"
    ) -> None:
        """Create a consumer group for a stream."""
        try:
            await self.client.xgroup_create(stream, group, start_id, mkstream=True)
        except aioredis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def stream_read_group(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block: int | None = None,
    ) -> list[tuple[str, dict[str, str]]]:
        """Read messages from a stream as part of a consumer group."""
        results = await self.client.xreadgroup(
            group, consumer, {stream: ">"}, count=count, block=block
        )
        if not results:
            return []
        return results[0][1]

    async def stream_ack(self, stream: str, group: str, *message_ids: str) -> int:
        """Acknowledge messages in a consumer group."""
        return await self.client.xack(stream, group, *message_ids)

    # --- Cache operations ---

    async def cache_get(self, key: str) -> str | None:
        return await self.client.get(key)

    async def cache_set(self, key: str, value: str, ttl: int = 3600) -> None:
        await self.client.set(key, value, ex=ttl)

    async def health_check(self) -> bool:
        try:
            return await self.client.ping()
        except Exception:
            return False


redis_store = RedisStore()
