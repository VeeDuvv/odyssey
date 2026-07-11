"""Introspector: the sensing layer of Odyssey's nervous system.

Continuously collects telemetry on all agent interactions, knowledge graph health,
and system performance. Produces SystemHealthSnapshots for the gap detector.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from odyssey.agents.registry import agent_registry
from odyssey.cortex.models import (
    AgentHealthStats,
    KnowledgeHealthStats,
    SystemHealthSnapshot,
)
from odyssey.knowledge.ontology import get_ontology_stats
from odyssey.storage.neo4j import neo4j_store
from odyssey.storage.postgres import postgres_store


class Introspector:
    """Senses the state of the entire Odyssey system."""

    async def record_query(
        self,
        query: str,
        agent_id: str,
        enterprise_id: str | None,
        response_quality: float | None,
        latency_ms: int,
        hit_dead_end: bool,
        metadata: dict | None = None,
    ) -> None:
        """Record a single query interaction to the telemetry table."""
        await postgres_store.execute(
            """
            INSERT INTO telemetry (event_type, agent_id, enterprise_id, query, response_quality, latency_ms, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            "agent_query",
            agent_id,
            enterprise_id,
            query,
            response_quality,
            latency_ms,
            json.dumps(metadata or {}),
        )

    async def record_evolution(
        self,
        proposal_type: str,
        proposal: dict,
        outcome: str,
        rationale: str,
        metrics_before: dict | None = None,
        metrics_after: dict | None = None,
    ) -> None:
        """Record an evolution action to the immutable audit log."""
        await postgres_store.execute(
            """
            INSERT INTO evolution_log (proposal_type, proposal, outcome, rationale, metrics_before, metrics_after)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            proposal_type,
            json.dumps(proposal),
            outcome,
            rationale,
            json.dumps(metrics_before or {}),
            json.dumps(metrics_after or {}),
        )

    async def take_snapshot(self, window_hours: int = 24) -> SystemHealthSnapshot:
        """Take a point-in-time health snapshot of the system."""
        since = datetime.utcnow() - timedelta(hours=window_hours)

        # Query telemetry for the window
        query_stats = await self._get_query_stats(since)
        agent_stats = await self._get_agent_stats(since)
        knowledge_stats = await self._get_knowledge_stats()

        active_agents = agent_registry.get_all(status="active")

        return SystemHealthSnapshot(
            total_queries=query_stats["total"],
            avg_quality=query_stats["avg_quality"],
            avg_latency_ms=query_stats["avg_latency"],
            dead_end_rate=query_stats["dead_end_rate"],
            agent_stats=agent_stats,
            knowledge_stats=knowledge_stats,
            active_agent_count=len(active_agents),
        )

    async def _get_query_stats(self, since: datetime) -> dict:
        """Aggregate query statistics from telemetry."""
        row = await postgres_store.fetchrow(
            """
            SELECT
                COUNT(*) AS total,
                COALESCE(AVG(response_quality), 0) AS avg_quality,
                COALESCE(AVG(latency_ms), 0) AS avg_latency,
                COALESCE(
                    SUM(CASE WHEN response_quality IS NOT NULL AND response_quality < 0.3 THEN 1 ELSE 0 END)::FLOAT
                    / NULLIF(COUNT(*), 0),
                    0
                ) AS dead_end_rate
            FROM telemetry
            WHERE event_type = 'agent_query' AND time >= $1
            """,
            since,
        )
        if not row:
            return {"total": 0, "avg_quality": 0, "avg_latency": 0, "dead_end_rate": 0}
        return {
            "total": row["total"],
            "avg_quality": float(row["avg_quality"]),
            "avg_latency": int(row["avg_latency"]),
            "dead_end_rate": float(row["dead_end_rate"]),
        }

    async def _get_agent_stats(self, since: datetime) -> dict[str, AgentHealthStats]:
        """Per-agent statistics from telemetry."""
        rows = await postgres_store.fetch(
            """
            SELECT
                agent_id,
                COUNT(*) AS query_count,
                COALESCE(AVG(response_quality), 0) AS avg_quality,
                COALESCE(AVG(latency_ms), 0) AS avg_latency,
                COALESCE(
                    SUM(CASE WHEN response_quality IS NOT NULL AND response_quality < 0.3 THEN 1 ELSE 0 END)::FLOAT
                    / NULLIF(COUNT(*), 0),
                    0
                ) AS dead_end_rate
            FROM telemetry
            WHERE event_type = 'agent_query' AND time >= $1 AND agent_id IS NOT NULL
            GROUP BY agent_id
            """,
            since,
        )
        stats = {}
        for r in rows:
            agent_id = r["agent_id"]
            # Determine trend by comparing to previous window
            prev_quality = await self._get_previous_quality(agent_id, since)
            current_quality = float(r["avg_quality"])
            if prev_quality is not None:
                if current_quality > prev_quality + 0.05:
                    trend = "improving"
                elif current_quality < prev_quality - 0.05:
                    trend = "declining"
                else:
                    trend = "stable"
            else:
                trend = "stable"

            stats[agent_id] = AgentHealthStats(
                agent_id=agent_id,
                query_count=r["query_count"],
                avg_quality=current_quality,
                avg_latency_ms=int(r["avg_latency"]),
                dead_end_rate=float(r["dead_end_rate"]),
                trend=trend,
            )
        return stats

    async def _get_previous_quality(
        self, agent_id: str, current_since: datetime
    ) -> float | None:
        """Get average quality for the previous equivalent window."""
        window = datetime.utcnow() - current_since
        prev_end = current_since
        prev_start = prev_end - window
        row = await postgres_store.fetchrow(
            """
            SELECT COALESCE(AVG(response_quality), NULL) AS avg_quality
            FROM telemetry
            WHERE event_type = 'agent_query' AND agent_id = $1
              AND time >= $2 AND time < $3
            """,
            agent_id,
            prev_start,
            prev_end,
        )
        if row and row["avg_quality"] is not None:
            return float(row["avg_quality"])
        return None

    async def _get_knowledge_stats(self) -> KnowledgeHealthStats:
        """Assess health of the knowledge graph."""
        try:
            ontology_stats = await get_ontology_stats()
            total_nodes = sum(ontology_stats.values())

            # Count stale nodes (confidence below threshold)
            stale_results = await neo4j_store.execute_read("""
                MATCH (t:Technology)
                WHERE t.confidence < 0.5
                RETURN count(t) AS stale_count
            """)
            stale_count = stale_results[0]["stale_count"] if stale_results else 0

            # Average confidence
            conf_results = await neo4j_store.execute_read("""
                MATCH (t:Technology)
                RETURN avg(t.confidence) AS avg_conf
            """)
            avg_conf = conf_results[0]["avg_conf"] if conf_results and conf_results[0]["avg_conf"] else 0.0

            # Domain coverage
            domain_results = await neo4j_store.execute_read("""
                MATCH (t:Technology)
                RETURN t.domain AS domain, count(t) AS cnt
            """)
            domains = {r["domain"]: r["cnt"] for r in domain_results}

            return KnowledgeHealthStats(
                total_nodes=total_nodes,
                stale_nodes=stale_count,
                domains_coverage=domains,
                avg_confidence=float(avg_conf),
            )
        except Exception:
            return KnowledgeHealthStats()

    async def get_dead_end_queries(
        self, since: datetime | None = None, limit: int = 50
    ) -> list[dict]:
        """Get queries that hit dead ends (low quality responses)."""
        since = since or (datetime.utcnow() - timedelta(days=7))
        rows = await postgres_store.fetch(
            """
            SELECT query, agent_id, response_quality, latency_ms, time
            FROM telemetry
            WHERE event_type = 'agent_query'
              AND response_quality IS NOT NULL AND response_quality < 0.3
              AND time >= $1
            ORDER BY time DESC
            LIMIT $2
            """,
            since,
            limit,
        )
        return [dict(r) for r in rows]

    async def get_query_domain_distribution(
        self, since: datetime | None = None
    ) -> dict[str, int]:
        """Analyze what domains users are querying about."""
        since = since or (datetime.utcnow() - timedelta(days=7))
        rows = await postgres_store.fetch(
            """
            SELECT query FROM telemetry
            WHERE event_type = 'agent_query' AND time >= $1
            """,
            since,
        )
        # Simple keyword-based domain detection
        domain_counts: dict[str, int] = {}
        domain_keywords = {
            "data_platforms": ["database", "warehouse", "lake", "kafka", "spark", "airflow", "snowflake", "databricks", "bigquery", "streaming", "flink", "dbt"],
            "ml_infrastructure": ["mlflow", "mlops", "feature store", "model registry", "training", "serving", "sagemaker", "vertex", "experiment"],
            "ai_models": ["gpt", "claude", "llama", "gemini", "mistral", "foundation model", "llm", "fine-tun"],
            "ai_patterns": ["rag", "vector", "embedding", "agent", "langchain", "llamaindex", "pinecone", "guardrail"],
            "data_governance": ["governance", "quality", "catalog", "lineage", "compliance", "gdpr", "privacy", "collibra"],
            "cloud_deployment": ["aws", "gcp", "azure", "cloud", "kubernetes", "docker", "deploy"],
            "organizational": ["team", "hiring", "skill", "maturity", "cost", "budget", "vendor"],
        }
        for r in rows:
            query_lower = (r["query"] or "").lower()
            for domain, keywords in domain_keywords.items():
                if any(kw in query_lower for kw in keywords):
                    domain_counts[domain] = domain_counts.get(domain, 0) + 1
        return domain_counts


introspector = Introspector()
