"""Sentinel: monitors external sources for changes relevant to the knowledge graph."""

from __future__ import annotations

import uuid
from datetime import datetime

import feedparser
import httpx

from odyssey.agents.base import AgentDefinition, AgentQuery, AgentResponse, BaseAgent
from odyssey.agents.bus import BusMessage, agent_bus
from odyssey.knowledge.graph import knowledge_graph
from odyssey.knowledge.models import InsightNode, KnowledgeDomain
from odyssey.llm.client import llm_client

RELEVANCE_PROMPT = """You are analyzing a news/blog item for relevance to enterprise AI & Data architecture.

Title: {title}
Summary: {summary}
Source: {source}

Determine:
1. Is this relevant to enterprise AI/Data architecture decisions? (yes/no)
2. If yes, which domain? (data_platforms, ml_infrastructure, ai_models, ai_patterns, data_governance, cloud_deployment, organizational)
3. Which technologies are impacted? (list of names)
4. A concise insight statement (1-2 sentences) summarizing why this matters for enterprise architects.
5. Confidence (0-1) in this being significant.

Respond as JSON with keys: relevant (bool), domain (str), impacted_technologies (list[str]), insight (str), confidence (float).
"""


class SentinelAgent(BaseAgent):
    """Monitors external world for changes relevant to connected enterprises."""

    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="sentinel",
                name="Sentinel",
                type="core",
                capabilities=["source_monitoring", "change_detection", "alert_generation"],
                knowledge_domains=[
                    "data_platforms", "ml_infrastructure", "ai_models",
                    "ai_patterns", "data_governance", "cloud_deployment",
                ],
            )
        )

    def can_handle(self, query: AgentQuery) -> float:
        q = query.query.lower()
        if any(kw in q for kw in ["monitor", "watch", "alert", "what's new", "latest"]):
            return 0.8
        return 0.1

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process monitoring request or report latest insights."""
        feeds = query.context.get("feeds", [])
        if feeds:
            insights = await self.scan_feeds(feeds)
            return self._make_response(
                content=f"Scanned {len(feeds)} feeds, found {len(insights)} relevant insights.",
                structured_data={"insights": [i.model_dump(mode="json") for i in insights]},
            )

        # Return recent insights from the graph
        return self._make_response(
            content="Sentinel is monitoring configured sources for changes.",
        )

    async def scan_feeds(self, feed_urls: list[str]) -> list[InsightNode]:
        """Scan RSS/Atom feeds for relevant changes."""
        insights: list[InsightNode] = []

        for url in feed_urls:
            try:
                entries = await self._fetch_feed(url)
                for entry in entries[:5]:  # Process latest 5 entries per feed
                    insight = await self._analyze_entry(entry, url)
                    if insight:
                        await knowledge_graph.create_insight(insight)
                        insights.append(insight)
                        # Publish to bus for other agents
                        await agent_bus.publish(
                            BusMessage(
                                source_agent=self.id,
                                message_type="insight",
                                payload=insight.model_dump(mode="json"),
                            )
                        )
            except Exception:
                continue  # Don't let one bad feed stop the scan

        return insights

    async def _fetch_feed(self, url: str) -> list[dict]:
        """Fetch and parse an RSS/Atom feed."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(url)
            response.raise_for_status()

        feed = feedparser.parse(response.text)
        return [
            {
                "title": entry.get("title", ""),
                "summary": entry.get("summary", entry.get("description", "")),
                "link": entry.get("link", ""),
                "published": entry.get("published", ""),
            }
            for entry in feed.entries
        ]

    async def _analyze_entry(self, entry: dict, source_url: str) -> InsightNode | None:
        """Analyze a feed entry for relevance using LLM."""
        try:
            result = await llm_client.generate_structured(
                prompt=RELEVANCE_PROMPT.format(
                    title=entry["title"],
                    summary=entry["summary"][:2000],
                    source=source_url,
                ),
            )
        except Exception:
            return None

        if not result.get("relevant", False):
            return None

        domain = result.get("domain", "ai_models")
        try:
            knowledge_domain = KnowledgeDomain(domain)
        except ValueError:
            knowledge_domain = KnowledgeDomain.AI_MODELS

        return InsightNode(
            id=f"insight-{uuid.uuid4().hex[:12]}",
            content=result.get("insight", entry["title"]),
            domain=knowledge_domain,
            impacted_technologies=result.get("impacted_technologies", []),
            confidence=result.get("confidence", 0.5),
            source={"type": "news", "url": entry.get("link", source_url)},
        )
