"""Agent Lifecycle: canary deployment, promotion, and retirement.

Manages the full lifecycle of dynamic agents:
CANARY -> ACTIVE -> (DEPRECATED) -> RETIRED
"""

from __future__ import annotations

from datetime import datetime, timedelta

from odyssey.agents.base import BaseAgent
from odyssey.agents.registry import agent_registry
from odyssey.cortex.introspector import introspector
from odyssey.storage.postgres import postgres_store


# Promotion thresholds
MIN_CANARY_QUERIES = 10  # Minimum queries before considering promotion
MIN_CANARY_QUALITY = 0.6  # Minimum average quality to promote
MIN_CANARY_HOURS = 24  # Minimum hours in canary

# Retirement thresholds
MIN_QUERIES_PER_WEEK = 5  # Below this, consider retirement
INACTIVE_WEEKS_TO_RETIRE = 4  # Weeks below threshold before retirement


class AgentLifecycle:
    """Manages agent lifecycle transitions."""

    async def check_promotions(self) -> list[str]:
        """Check if any canary agents should be promoted to active.

        Returns list of promoted agent IDs.
        """
        promoted = []
        canary_agents = [
            a for a in agent_registry.get_all(status="canary")
            if a.definition.type == "dynamic"
        ]

        for agent in canary_agents:
            if await self._should_promote(agent):
                agent.definition.status = "active"
                await agent_registry.persist(agent)
                promoted.append(agent.id)

                await introspector.record_evolution(
                    proposal_type="agent_promotion",
                    proposal={"agent_id": agent.id, "agent_name": agent.name},
                    outcome="executed",
                    rationale=f"Agent '{agent.name}' promoted from canary to active "
                    f"after meeting quality thresholds",
                )

        return promoted

    async def check_retirements(self) -> list[str]:
        """Check if any dynamic agents should be retired due to low usage.

        Returns list of retired agent IDs.
        """
        retired = []
        dynamic_agents = [
            a for a in agent_registry.get_all(status="active")
            if a.definition.type == "dynamic"
        ]

        for agent in dynamic_agents:
            if await self._should_retire(agent):
                agent.definition.status = "retired"
                agent_registry.unregister(agent.id)
                await agent_registry.persist(agent)
                retired.append(agent.id)

                await introspector.record_evolution(
                    proposal_type="agent_retirement",
                    proposal={"agent_id": agent.id, "agent_name": agent.name},
                    outcome="executed",
                    rationale=f"Agent '{agent.name}' retired due to low usage "
                    f"(below {MIN_QUERIES_PER_WEEK} queries/week for "
                    f"{INACTIVE_WEEKS_TO_RETIRE} weeks)",
                )

        return retired

    async def _should_promote(self, agent: BaseAgent) -> bool:
        """Determine if a canary agent is ready for promotion."""
        # Check minimum time in canary
        age_hours = (
            datetime.utcnow() - agent.definition.created_at
        ).total_seconds() / 3600
        if age_hours < MIN_CANARY_HOURS:
            return False

        # Check query volume and quality
        stats = await self._get_agent_stats(agent.id, hours=int(age_hours))
        if stats["query_count"] < MIN_CANARY_QUERIES:
            return False
        if stats["avg_quality"] < MIN_CANARY_QUALITY:
            return False

        return True

    async def _should_retire(self, agent: BaseAgent) -> bool:
        """Determine if an active agent should be retired."""
        # Check retirement threshold from agent config
        config = agent.definition.config
        min_queries = config.get("min_queries_per_week", MIN_QUERIES_PER_WEEK)
        inactive_weeks = config.get("inactive_weeks_to_retire", INACTIVE_WEEKS_TO_RETIRE)

        # Check usage over the retirement window
        window_hours = inactive_weeks * 7 * 24
        stats = await self._get_agent_stats(agent.id, hours=window_hours)

        if stats["query_count"] == 0:
            # No queries at all in the window
            return True

        queries_per_week = stats["query_count"] / max(inactive_weeks, 1)
        return queries_per_week < min_queries

    async def _get_agent_stats(
        self, agent_id: str, hours: int = 168
    ) -> dict:
        """Get query stats for an agent over a time window."""
        since = datetime.utcnow() - timedelta(hours=hours)
        row = await postgres_store.fetchrow(
            """
            SELECT
                COUNT(*) AS query_count,
                COALESCE(AVG(response_quality), 0) AS avg_quality,
                COALESCE(AVG(latency_ms), 0) AS avg_latency
            FROM telemetry
            WHERE event_type = 'agent_query' AND agent_id = $1 AND time >= $2
            """,
            agent_id,
            since,
        )
        if not row:
            return {"query_count": 0, "avg_quality": 0, "avg_latency": 0}
        return {
            "query_count": row["query_count"],
            "avg_quality": float(row["avg_quality"]),
            "avg_latency": int(row["avg_latency"]),
        }


agent_lifecycle = AgentLifecycle()
