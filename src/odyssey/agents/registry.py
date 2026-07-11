"""Agent registry backed by PostgreSQL."""

from __future__ import annotations

import json
from typing import Any

from odyssey.agents.base import AgentDefinition, BaseAgent
from odyssey.storage.postgres import postgres_store


class AgentRegistry:
    """Registry of all agents, backed by PostgreSQL and in-memory cache."""

    def __init__(self) -> None:
        self._agents: dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register a live agent instance."""
        self._agents[agent.id] = agent

    def unregister(self, agent_id: str) -> None:
        self._agents.pop(agent_id, None)

    def get(self, agent_id: str) -> BaseAgent | None:
        return self._agents.get(agent_id)

    def get_all(self, status: str = "active") -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.definition.status == status]

    def get_by_type(self, agent_type: str) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.definition.type == agent_type]

    async def persist(self, agent: BaseAgent) -> None:
        """Save agent definition to PostgreSQL."""
        d = agent.definition
        await postgres_store.execute(
            """
            INSERT INTO agents (id, name, type, status, capabilities, knowledge_domains, config, quality_metrics, version)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                status = EXCLUDED.status,
                capabilities = EXCLUDED.capabilities,
                knowledge_domains = EXCLUDED.knowledge_domains,
                config = EXCLUDED.config,
                quality_metrics = EXCLUDED.quality_metrics,
                version = EXCLUDED.version,
                last_evolved_at = NOW()
            """,
            d.id,
            d.name,
            d.type,
            d.status,
            d.capabilities,
            d.knowledge_domains,
            json.dumps(d.config),
            json.dumps(d.quality_metrics),
            d.version,
        )

    async def load_definitions(self) -> list[AgentDefinition]:
        """Load all agent definitions from PostgreSQL."""
        rows = await postgres_store.fetch(
            "SELECT * FROM agents WHERE status != 'retired'"
        )
        return [
            AgentDefinition(
                id=r["id"],
                name=r["name"],
                type=r["type"],
                status=r["status"],
                capabilities=r["capabilities"] or [],
                knowledge_domains=r["knowledge_domains"] or [],
                config=json.loads(r["config"]) if r["config"] else {},
                quality_metrics=json.loads(r["quality_metrics"]) if r["quality_metrics"] else {},
                version=r["version"],
                created_at=r["created_at"],
                last_evolved_at=r["last_evolved_at"],
            )
            for r in rows
        ]

    async def update_metrics(self, agent_id: str, metrics: dict[str, Any]) -> None:
        await postgres_store.execute(
            "UPDATE agents SET quality_metrics = $1 WHERE id = $2",
            json.dumps(metrics),
            agent_id,
        )


agent_registry = AgentRegistry()
