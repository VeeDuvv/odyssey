"""Agent Factory: generates new agents from specifications using LLM.

This is the mechanism that makes self-evolution concrete — the factory takes
an EvolutionProposal of type NEW_AGENT, generates a system prompt,
configures tool bindings, and deploys the agent to canary.
"""

from __future__ import annotations

import uuid
from typing import Any

from odyssey.agents.base import AgentDefinition, AgentQuery, AgentResponse, BaseAgent
from odyssey.knowledge.graph import knowledge_graph
from odyssey.llm.client import llm_client

AGENT_GENERATION_PROMPT = """You are generating the system prompt for a new specialized agent in Odyssey,
an AI-native enterprise AI & Data architecture advisor.

Agent specification:
- Name: {agent_name}
- Description: {description}
- Knowledge domains: {knowledge_domains}
- Capabilities: {capabilities}
- Routing keywords: {routing_keywords}

Generate a system prompt for this agent. The prompt should:
1. Define the agent's role and expertise clearly
2. Specify how it should interact with enterprise architects and CTOs
3. Include guidance on adapting to different altitudes (strategic/tactical/operational)
4. Reference that it has access to a knowledge graph for factual grounding
5. Include guidelines specific to its domain expertise
6. Be 200-400 words

Respond as JSON with key "system_prompt" containing the generated prompt.
"""


class DynamicAgent(BaseAgent):
    """A dynamically generated agent with an LLM-generated system prompt."""

    def __init__(
        self,
        definition: AgentDefinition,
        system_prompt: str,
        routing_keywords: list[str],
    ) -> None:
        super().__init__(definition)
        self.system_prompt = system_prompt
        self.routing_keywords = [kw.lower() for kw in routing_keywords]

    def can_handle(self, query: AgentQuery) -> float:
        """Score based on keyword match against routing keywords."""
        query_lower = query.query.lower()
        matches = sum(1 for kw in self.routing_keywords if kw in query_lower)
        if matches == 0:
            return 0.0
        # Scale: 1 match = 0.6, 2 = 0.7, 3+ = 0.8+
        return min(0.95, 0.5 + matches * 0.1)

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process a query using this agent's generated system prompt."""
        # Gather relevant knowledge from the graph
        kg_context = await self._search_knowledge(query.query)

        prompt_parts = [f"User query (altitude: {query.altitude}): {query.query}"]
        if kg_context:
            prompt_parts.append("\n--- Knowledge Graph Context ---")
            for tech in kg_context[:5]:
                prompt_parts.append(
                    f"- {tech.get('name', 'Unknown')}: {tech.get('description', '')}"
                )

        prompt_parts.append(
            "\nProvide a clear, actionable response grounded in the knowledge context. "
            "End with 2-3 follow-up questions."
        )

        response_text = await llm_client.generate(
            prompt="\n".join(prompt_parts),
            system=self.system_prompt,
            temperature=0.5,
        )

        return self._make_response(
            content=response_text,
            confidence=0.7,
            metadata={"dynamic_agent": True, "keywords_matched": True},
        )

    async def _search_knowledge(self, query: str) -> list[dict]:
        """Search knowledge graph scoped to this agent's domains."""
        results = []
        for domain in self.definition.knowledge_domains:
            techs = await knowledge_graph.search_technologies(
                query=query, domain=domain, limit=5
            )
            results.extend(techs)
        return results


class AgentFactory:
    """Generates and deploys new agents from evolution proposals."""

    async def create_agent(
        self, specification: dict[str, Any]
    ) -> DynamicAgent:
        """Create a new dynamic agent from a specification.

        Args:
            specification: Dict with keys:
                - agent_name: str
                - description: str
                - capabilities: list[str]
                - knowledge_domains: list[str]
                - routing_keywords: list[str]

        Returns:
            A DynamicAgent ready for registration.
        """
        agent_name = specification.get("agent_name", "Dynamic Agent")
        description = specification.get("description", "")
        capabilities = specification.get("capabilities", [])
        knowledge_domains = specification.get("knowledge_domains", [])
        routing_keywords = specification.get("routing_keywords", [])

        # Generate system prompt using LLM
        system_prompt = await self._generate_system_prompt(
            agent_name=agent_name,
            description=description,
            capabilities=capabilities,
            knowledge_domains=knowledge_domains,
            routing_keywords=routing_keywords,
        )

        # Create agent definition
        agent_id = f"dynamic-{agent_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:6]}"
        definition = AgentDefinition(
            id=agent_id,
            name=agent_name,
            type="dynamic",
            status="canary",  # Start in canary mode
            capabilities=capabilities,
            knowledge_domains=knowledge_domains,
            config={
                "system_prompt": system_prompt,
                "routing_keywords": routing_keywords,
                "specification": specification,
            },
        )

        return DynamicAgent(
            definition=definition,
            system_prompt=system_prompt,
            routing_keywords=routing_keywords,
        )

    async def _generate_system_prompt(
        self,
        agent_name: str,
        description: str,
        capabilities: list[str],
        knowledge_domains: list[str],
        routing_keywords: list[str],
    ) -> str:
        """Use LLM to generate a system prompt for the new agent."""
        try:
            result = await llm_client.generate_structured(
                prompt=AGENT_GENERATION_PROMPT.format(
                    agent_name=agent_name,
                    description=description,
                    capabilities=", ".join(capabilities),
                    knowledge_domains=", ".join(knowledge_domains),
                    routing_keywords=", ".join(routing_keywords),
                ),
            )
            return result.get("system_prompt", self._fallback_prompt(agent_name, description))
        except Exception:
            return self._fallback_prompt(agent_name, description)

    @staticmethod
    def _fallback_prompt(agent_name: str, description: str) -> str:
        """Generate a basic system prompt when LLM is unavailable."""
        return (
            f"You are {agent_name}, a specialized agent in Odyssey — "
            f"an AI-native enterprise AI & Data architecture advisor.\n\n"
            f"Your specialty: {description}\n\n"
            f"Guidelines:\n"
            f"- Adapt response depth to user altitude (strategic/tactical/operational)\n"
            f"- Ground recommendations in knowledge graph data when available\n"
            f"- Be honest about confidence levels\n"
            f"- Suggest follow-up questions to refine recommendations"
        )


agent_factory = AgentFactory()
