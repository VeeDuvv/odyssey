"""Proactive alert engine: pushes relevant changes to enterprises.

When the landscape changes (new insights, technology status shifts, regulatory updates),
the alert engine checks which connected enterprises are affected and generates alerts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from odyssey.knowledge.graph import knowledge_graph
from odyssey.llm.client import llm_client
from odyssey.storage.neo4j import neo4j_store
from odyssey.storage.postgres import postgres_store


class Alert(BaseModel):
    """A proactive alert for an enterprise."""

    id: str = Field(default_factory=lambda: f"alert-{uuid.uuid4().hex[:12]}")
    enterprise_id: str
    enterprise_name: str = ""
    severity: str = "info"  # info, warning, action_required
    title: str
    body: str
    affected_technologies: list[str] = Field(default_factory=list)
    affected_decisions: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    source_insight_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    acknowledged: bool = False


ALERT_RELEVANCE_PROMPT = """Determine if this landscape change is relevant to this enterprise.

## Change/Insight
{insight}

## Enterprise Context
Name: {enterprise_name}
Industry: {industry}
Current Stack: {tech_stack}
Goals: {goals}
Constraints: {constraints}

Is this change relevant to this enterprise? If yes, generate an alert.

Respond as JSON:
{{
    "relevant": true/false,
    "severity": "info|warning|action_required",
    "title": "Alert title (short)",
    "body": "Why this matters to this enterprise (2-3 sentences)",
    "affected_technologies": ["tech IDs from their stack that are affected"],
    "recommended_action": "What should they do about it"
}}
"""


class AlertEngine:
    """Generates and manages proactive alerts for enterprises."""

    async def check_for_alerts(self) -> list[Alert]:
        """Check all enterprises against recent insights and generate alerts."""
        alerts: list[Alert] = []

        # Get recent unprocessed insights
        insights = await self._get_unprocessed_insights()
        if not insights:
            return alerts

        # Get all enterprises
        enterprises = await self._get_all_enterprises()
        if not enterprises:
            return alerts

        for insight in insights:
            for enterprise in enterprises:
                alert = await self._evaluate_relevance(insight, enterprise)
                if alert:
                    await self._store_alert(alert)
                    alerts.append(alert)

        return alerts

    async def evaluate_insight_for_enterprise(
        self, insight_content: str, enterprise_id: str
    ) -> Alert | None:
        """Evaluate a specific insight's relevance to a specific enterprise."""
        enterprise = await self._get_enterprise(enterprise_id)
        if not enterprise:
            return None

        insight = {"content": insight_content, "id": "manual"}
        return await self._evaluate_relevance(insight, enterprise)

    async def get_alerts(
        self,
        enterprise_id: str,
        include_acknowledged: bool = False,
        limit: int = 50,
    ) -> list[dict]:
        """Get alerts for an enterprise."""
        if include_acknowledged:
            rows = await postgres_store.fetch(
                """
                SELECT * FROM telemetry
                WHERE event_type = 'alert' AND enterprise_id = $1
                ORDER BY time DESC LIMIT $2
                """,
                enterprise_id, limit,
            )
        else:
            rows = await postgres_store.fetch(
                """
                SELECT * FROM telemetry
                WHERE event_type = 'alert' AND enterprise_id = $1
                  AND (metadata->>'acknowledged')::boolean IS NOT TRUE
                ORDER BY time DESC LIMIT $2
                """,
                enterprise_id, limit,
            )
        return [dict(r) for r in rows]

    async def acknowledge_alert(self, alert_id: str) -> None:
        """Mark an alert as acknowledged."""
        await postgres_store.execute(
            """
            UPDATE telemetry
            SET metadata = jsonb_set(metadata, '{acknowledged}', 'true')
            WHERE event_type = 'alert' AND metadata->>'alert_id' = $1
            """,
            alert_id,
        )

    async def _evaluate_relevance(
        self, insight: dict, enterprise: dict
    ) -> Alert | None:
        """Use LLM to determine if an insight is relevant to an enterprise."""
        try:
            result = await llm_client.generate_structured(
                prompt=ALERT_RELEVANCE_PROMPT.format(
                    insight=insight.get("content", ""),
                    enterprise_name=enterprise.get("name", "Unknown"),
                    industry=enterprise.get("industry", "Unknown"),
                    tech_stack=enterprise.get("tech_stack", "[]"),
                    goals=enterprise.get("goals", "[]"),
                    constraints=enterprise.get("constraints", "[]"),
                ),
            )
        except Exception:
            return None

        if not result.get("relevant", False):
            return None

        return Alert(
            enterprise_id=enterprise["id"],
            enterprise_name=enterprise.get("name", ""),
            severity=result.get("severity", "info"),
            title=result.get("title", "Landscape Change"),
            body=result.get("body", ""),
            affected_technologies=result.get("affected_technologies", []),
            recommended_action=result.get("recommended_action", ""),
            source_insight_id=insight.get("id"),
        )

    async def _store_alert(self, alert: Alert) -> None:
        """Store an alert in the telemetry table."""
        await postgres_store.execute(
            """
            INSERT INTO telemetry (event_type, enterprise_id, query, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            "alert",
            alert.enterprise_id,
            alert.title,
            json.dumps(alert.model_dump(mode="json")),
        )

    async def _get_unprocessed_insights(self, limit: int = 20) -> list[dict]:
        """Get recent insights from the knowledge graph."""
        try:
            results = await neo4j_store.execute_read("""
                MATCH (i:Insight)
                RETURN i.id AS id, i.content AS content, i.domain AS domain,
                       i.impacted_technologies AS impacted_technologies,
                       i.confidence AS confidence
                ORDER BY i.published_at DESC
                LIMIT $limit
            """, {"limit": limit})
            return results
        except Exception:
            return []

    async def _get_all_enterprises(self) -> list[dict]:
        """Get all enterprise profiles."""
        rows = await postgres_store.fetch(
            "SELECT id, name, industry, tech_stack, goals, constraints FROM enterprises"
        )
        return [dict(r) for r in rows]

    async def _get_enterprise(self, enterprise_id: str) -> dict | None:
        row = await postgres_store.fetchrow(
            "SELECT id, name, industry, tech_stack, goals, constraints FROM enterprises WHERE id = $1",
            enterprise_id,
        )
        return dict(row) if row else None


alert_engine = AlertEngine()
