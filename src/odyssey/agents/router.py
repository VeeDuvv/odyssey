"""Query-to-agent routing."""

from __future__ import annotations

from odyssey.agents.base import AgentQuery, AgentResponse, BaseAgent
from odyssey.agents.registry import agent_registry


class AgentRouter:
    """Routes queries to the best-matching agent."""

    async def route(self, query: AgentQuery) -> AgentResponse:
        """Find the best agent for a query and execute it."""
        agents = agent_registry.get_all(status="active")
        if not agents:
            return AgentResponse(
                agent_id="router",
                agent_name="Router",
                content="No agents available to handle this query.",
                confidence=0.0,
            )

        # Score each agent's ability to handle the query
        scored: list[tuple[float, BaseAgent]] = [
            (agent.can_handle(query), agent) for agent in agents
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        best_score, best_agent = scored[0]
        if best_score <= 0:
            return AgentResponse(
                agent_id="router",
                agent_name="Router",
                content="No agent is confident enough to handle this query.",
                confidence=0.0,
            )

        return await best_agent.process(query)


agent_router = AgentRouter()
