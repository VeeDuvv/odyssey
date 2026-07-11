"""Query-to-agent routing with telemetry recording."""

from __future__ import annotations

import time

from odyssey.agents.base import AgentQuery, AgentResponse, BaseAgent
from odyssey.agents.registry import agent_registry


class AgentRouter:
    """Routes queries to the best-matching agent and records telemetry."""

    async def route(self, query: AgentQuery) -> AgentResponse:
        """Find the best agent for a query and execute it."""
        agents = agent_registry.get_all(status="active")

        # Also include canary agents (they get a chance to handle queries)
        canary_agents = agent_registry.get_all(status="canary")
        all_agents = agents + canary_agents

        if not all_agents:
            response = AgentResponse(
                agent_id="router",
                agent_name="Router",
                content="No agents available to handle this query.",
                confidence=0.0,
            )
            await self._record_telemetry(query, response, 0)
            return response

        # Score each agent's ability to handle the query
        scored: list[tuple[float, BaseAgent]] = [
            (agent.can_handle(query), agent) for agent in all_agents
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_agent = scored[0]
        if best_score <= 0:
            response = AgentResponse(
                agent_id="router",
                agent_name="Router",
                content="No agent is confident enough to handle this query.",
                confidence=0.0,
            )
            await self._record_telemetry(query, response, 0)
            return response

        start = time.monotonic()
        response = await best_agent.process(query)
        latency_ms = int((time.monotonic() - start) * 1000)

        # Record telemetry for the introspector
        await self._record_telemetry(query, response, latency_ms)

        return response

    async def _record_telemetry(
        self, query: AgentQuery, response: AgentResponse, latency_ms: int
    ) -> None:
        """Record query telemetry for the cortex introspector."""
        try:
            from odyssey.cortex.introspector import introspector

            await introspector.record_query(
                query=query.query,
                agent_id=response.agent_id,
                enterprise_id=query.enterprise_id,
                response_quality=response.confidence if response.confidence > 0 else None,
                latency_ms=latency_ms,
                hit_dead_end=response.confidence < 0.3,
                metadata={
                    "altitude": query.altitude,
                    "agent_name": response.agent_name,
                },
            )
        except Exception:
            pass  # Telemetry should never break query handling


agent_router = AgentRouter()
