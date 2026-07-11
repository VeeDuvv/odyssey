"""Chronicler: maintains temporal knowledge — what was true, what changed, what is true now.

Enables queries like:
- "What changed in the vector DB landscape in the last 3 months?"
- "When did Pinecone launch serverless?"
- "What was our recommended data platform 6 months ago?"
- "Show me the evolution of RAG patterns this year"
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from odyssey.agents.base import AgentDefinition, AgentQuery, AgentResponse, BaseAgent
from odyssey.llm.client import llm_client
from odyssey.storage.neo4j import neo4j_store
from odyssey.storage.postgres import postgres_store

CHRONICLER_SYSTEM = """You are the Chronicler agent of Odyssey, an AI-native enterprise AI & Data architecture advisor.

Your specialty is temporal awareness — understanding how the AI & Data landscape has changed over time
and what those changes mean for enterprise architecture decisions.

You track:
- Technology releases, acquisitions, pricing changes, deprecations
- Shifts in adoption trends and community momentum
- Regulatory changes and compliance deadlines
- Evolution of architectural patterns (what's emerging, what's maturing, what's declining)

When answering temporal queries:
- Be specific about dates and timelines
- Explain the significance of changes for enterprise architects
- Highlight changes that might affect existing decisions
- Surface emerging trends that warrant attention
- Compare past recommendations to current best practices

You have access to:
- The knowledge graph with timestamped insights and technology status history
- The evolution audit log showing how Odyssey itself has evolved
- Historical telemetry showing what enterprises are asking about
"""


class ChroniclerAgent(BaseAgent):
    """Maintains temporal knowledge and answers questions about change over time."""

    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="chronicler",
                name="Chronicler",
                type="core",
                capabilities=[
                    "temporal_queries",
                    "change_detection",
                    "trend_analysis",
                    "historical_comparison",
                ],
                knowledge_domains=[
                    "data_platforms", "ml_infrastructure", "ai_models",
                    "ai_patterns", "data_governance", "cloud_deployment",
                ],
            )
        )

    def can_handle(self, query: AgentQuery) -> float:
        q = query.query.lower()
        strong_signals = [
            "changed", "change", "evolution", "history", "timeline",
            "when did", "since", "last month", "last quarter", "last year",
            "trend", "emerging", "declining", "what's new", "recent",
            "used to", "before", "after", "compared to",
        ]
        if any(sig in q for sig in strong_signals):
            return 0.85
        return 0.15

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process a temporal/change query."""
        # Gather temporal context
        recent_insights = await self._get_recent_insights()
        evolution_history = await self._get_evolution_history()
        query_trends = await self._get_query_trends()
        landscape_changes = await self._detect_landscape_changes()

        # Build temporal context for LLM
        context_parts = [f"User query: {query.query}"]

        if recent_insights:
            context_parts.append("\n--- Recent Insights ---")
            for insight in recent_insights[:10]:
                context_parts.append(
                    f"- [{insight.get('published_at', 'unknown')}] "
                    f"{insight.get('content', '')} "
                    f"(domain: {insight.get('domain', '')}, "
                    f"confidence: {insight.get('confidence', 'N/A')})"
                )

        if landscape_changes:
            context_parts.append("\n--- Landscape Changes ---")
            for change in landscape_changes[:10]:
                context_parts.append(f"- {change}")

        if evolution_history:
            context_parts.append("\n--- System Evolution History ---")
            for entry in evolution_history[:5]:
                context_parts.append(
                    f"- [{entry.get('timestamp', '')}] {entry.get('proposal_type', '')}: "
                    f"{entry.get('rationale', '')}"
                )

        if query_trends:
            context_parts.append("\n--- Query Trends ---")
            for domain, count in sorted(query_trends.items(), key=lambda x: x[1], reverse=True):
                context_parts.append(f"- {domain}: {count} queries")

        response_text = await llm_client.generate(
            prompt="\n".join(context_parts),
            system=CHRONICLER_SYSTEM,
            temperature=0.5,
        )

        return self._make_response(
            content=response_text,
            confidence=0.7,
            structured_data={
                "insights_count": len(recent_insights),
                "evolution_entries": len(evolution_history),
                "landscape_changes": len(landscape_changes),
            },
            metadata={"query_type": "temporal"},
        )

    async def _get_recent_insights(self, days: int = 30) -> list[dict]:
        """Get recent insights from the knowledge graph."""
        try:
            results = await neo4j_store.execute_read(
                """
                MATCH (i:Insight)
                WHERE i.published_at >= datetime($since)
                RETURN i
                ORDER BY i.published_at DESC
                LIMIT 20
                """,
                {"since": (datetime.utcnow() - timedelta(days=days)).isoformat()},
            )
            return [r["i"] for r in results]
        except Exception:
            return []

    async def _get_evolution_history(self, limit: int = 20) -> list[dict]:
        """Get Odyssey's own evolution history."""
        try:
            rows = await postgres_store.fetch(
                """
                SELECT timestamp, proposal_type, outcome, rationale
                FROM evolution_log
                ORDER BY timestamp DESC
                LIMIT $1
                """,
                limit,
            )
            return [dict(r) for r in rows]
        except Exception:
            return []

    async def _get_query_trends(self) -> dict[str, int]:
        """Get what domains users have been asking about."""
        try:
            from odyssey.cortex.introspector import introspector
            return await introspector.get_query_domain_distribution()
        except Exception:
            return {}

    async def _detect_landscape_changes(self) -> list[str]:
        """Detect significant changes in the knowledge graph."""
        changes = []
        try:
            # Technologies with status changes
            status_changes = await neo4j_store.execute_read("""
                MATCH (t:Technology)
                WHERE t.status IN ['emerging', 'deprecated', 'declining']
                RETURN t.name AS name, t.status AS status, t.category AS category
                ORDER BY t.status
            """)
            for r in status_changes:
                changes.append(
                    f"{r['name']} ({r['category']}) is {r['status']}"
                )

            # Technologies with low confidence (potentially stale)
            stale = await neo4j_store.execute_read("""
                MATCH (t:Technology)
                WHERE t.confidence < 0.4
                RETURN t.name AS name, t.confidence AS confidence
                ORDER BY t.confidence ASC
                LIMIT 10
            """)
            for r in stale:
                changes.append(
                    f"{r['name']} knowledge is stale (confidence: {r['confidence']:.2f})"
                )

        except Exception:
            pass
        return changes
