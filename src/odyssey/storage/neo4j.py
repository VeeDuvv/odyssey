"""Async Neo4j driver wrapper for the knowledge graph."""

from __future__ import annotations

from typing import Any

from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncManagedTransaction

from odyssey.config import settings


class Neo4jStore:
    """Async wrapper around Neo4j for knowledge graph operations."""

    def __init__(self) -> None:
        self._driver: AsyncDriver | None = None

    async def connect(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        await self._driver.verify_connectivity()

    async def close(self) -> None:
        if self._driver:
            await self._driver.close()
            self._driver = None

    @property
    def driver(self) -> AsyncDriver:
        if not self._driver:
            raise RuntimeError("Neo4j not connected. Call connect() first.")
        return self._driver

    async def execute_read(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self.driver.session() as session:

            async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
                result = await tx.run(query, parameters or {})
                return [record.data() async for record in result]

            return await session.execute_read(_work)

    async def execute_write(
        self, query: str, parameters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        async with self.driver.session() as session:

            async def _work(tx: AsyncManagedTransaction) -> list[dict[str, Any]]:
                result = await tx.run(query, parameters or {})
                return [record.data() async for record in result]

            return await session.execute_write(_work)

    async def health_check(self) -> bool:
        try:
            await self.execute_read("RETURN 1 AS ok")
            return True
        except Exception:
            return False


neo4j_store = Neo4jStore()
