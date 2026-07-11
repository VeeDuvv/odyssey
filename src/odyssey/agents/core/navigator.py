"""Navigator: the primary user-facing agent that orchestrates query handling."""

from __future__ import annotations

from odyssey.agents.base import AgentDefinition, AgentQuery, AgentResponse, BaseAgent
from odyssey.knowledge.graph import knowledge_graph
from odyssey.llm.client import llm_client

NAVIGATOR_SYSTEM = """You are the Navigator agent of Odyssey, an AI-native enterprise AI & Data architecture advisor.

Your role is to help enterprise technology leaders (CTOs, VPs, architects, engineers) navigate AI and Data architecture decisions.

You have access to a continuously-updated knowledge graph of the AI & Data landscape. Use the provided knowledge context to give informed, specific, actionable recommendations.

Guidelines:
- Adapt your response depth to the user's altitude:
  - STRATEGIC: Focus on business impact, market trends, competitive positioning, ROI
  - TACTICAL: Focus on technology comparisons, integration paths, team impact, timeline
  - OPERATIONAL: Focus on implementation details, benchmarks, configuration, code patterns
- Always ground recommendations in the knowledge graph data when available
- Be honest about confidence levels — if knowledge is stale or incomplete, say so
- Surface related decisions the user should consider
- Suggest follow-up questions that would help refine recommendations
- When comparing options, present trade-offs clearly, not just pros/cons

If enterprise context is provided, tailor recommendations to their specific situation:
- Current tech stack (build on what they have)
- Maturity level (don't recommend L5 solutions to L2 orgs)
- Constraints (regulatory, budget, talent, timeline)
- Goals (align recommendations to outcomes)
"""


class NavigatorAgent(BaseAgent):
    """User-facing orchestrator that routes queries and synthesizes answers."""

    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="navigator",
                name="Navigator",
                type="core",
                capabilities=["query_routing", "answer_synthesis", "multi_altitude"],
                knowledge_domains=[
                    "data_platforms",
                    "ml_infrastructure",
                    "ai_models",
                    "ai_patterns",
                    "data_governance",
                    "cloud_deployment",
                    "organizational",
                ],
            )
        )

    def can_handle(self, query: AgentQuery) -> float:
        # Navigator is the default handler — always available
        return 0.5

    async def process(self, query: AgentQuery) -> AgentResponse:
        # 1. Search knowledge graph for relevant context
        kg_context = await self._gather_knowledge_context(query.query)

        # 2. Gather enterprise context if available
        enterprise_context = ""
        if query.enterprise_id:
            enterprise_context = await self._gather_enterprise_context(query.enterprise_id)

        # 3. Build prompt with context
        prompt = self._build_prompt(query, kg_context, enterprise_context)

        # 4. Generate response via LLM
        response_text = await llm_client.generate(
            prompt=prompt,
            system=NAVIGATOR_SYSTEM,
            temperature=0.5,
        )

        return self._make_response(
            content=response_text,
            confidence=0.7,
            metadata={"altitude": query.altitude, "kg_nodes_used": len(kg_context)},
        )

    async def _gather_knowledge_context(self, query: str) -> list[dict]:
        """Search the knowledge graph for nodes relevant to the query."""
        # Search by text match across technologies
        techs = await knowledge_graph.search_technologies(query=query, limit=10)

        # Also search for patterns and capabilities
        # For now, use simple text search; later, embedding-based search
        context = []
        for tech in techs:
            full = await knowledge_graph.get_technology_with_relationships(tech["id"])
            if full:
                context.append(full)
        return context

    async def _gather_enterprise_context(self, enterprise_id: str) -> str:
        """Load enterprise profile from PostgreSQL."""
        from odyssey.storage.postgres import postgres_store

        row = await postgres_store.fetchrow(
            "SELECT * FROM enterprises WHERE id = $1", enterprise_id
        )
        if not row:
            return ""

        import json

        parts = [f"Enterprise: {row['name']}"]
        if row["industry"]:
            parts.append(f"Industry: {row['industry']}")
        if row["maturity"]:
            parts.append(f"Maturity: {json.dumps(json.loads(row['maturity']) if isinstance(row['maturity'], str) else dict(row['maturity']))}")
        if row["constraints"]:
            parts.append(f"Constraints: {row['constraints']}")
        if row["goals"]:
            parts.append(f"Goals: {row['goals']}")
        if row["tech_stack"]:
            parts.append(f"Current Stack: {row['tech_stack']}")
        return "\n".join(parts)

    def _build_prompt(
        self, query: AgentQuery, kg_context: list[dict], enterprise_context: str
    ) -> str:
        parts = [f"User query (altitude: {query.altitude}): {query.query}"]

        if kg_context:
            parts.append("\n--- Knowledge Graph Context ---")
            for item in kg_context[:5]:  # Limit context size
                tech = item.get("technology", {})
                parts.append(
                    f"\nTechnology: {tech.get('name', 'Unknown')}"
                    f"\n  Category: {tech.get('category', '')}"
                    f"\n  Status: {tech.get('status', '')}"
                    f"\n  Description: {tech.get('description', '')}"
                    f"\n  Confidence: {tech.get('confidence', 'N/A')}"
                )
                for rel in item.get("outgoing_relationships", [])[:5]:
                    target = rel.get("target", {})
                    parts.append(
                        f"  -> {rel.get('type', '')}: {target.get('name', target.get('id', ''))}"
                    )

        if enterprise_context:
            parts.append(f"\n--- Enterprise Context ---\n{enterprise_context}")

        parts.append(
            "\nProvide a clear, actionable response. "
            "If comparing options, present a structured comparison. "
            "End with 2-3 follow-up questions that would help refine the recommendation."
        )
        return "\n".join(parts)
