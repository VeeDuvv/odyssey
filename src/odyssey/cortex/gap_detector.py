"""Gap Detector: identifies capability, quality, and knowledge gaps.

Analyzes introspector telemetry to find where Odyssey is falling short.
Produces GapReports that feed into the Evolution Planner.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from odyssey.agents.registry import agent_registry
from odyssey.cortex.introspector import introspector
from odyssey.cortex.models import (
    CapabilityGap,
    GapReport,
    KnowledgeGap,
    QualityGap,
)
from odyssey.knowledge.models import DOMAIN_HALFLIFE, KnowledgeDomain
from odyssey.storage.neo4j import neo4j_store


# Quality thresholds
MIN_AGENT_QUALITY = 0.6
MAX_DEAD_END_RATE = 0.2
MIN_DOMAIN_COVERAGE = 5  # Minimum nodes per domain


class GapDetector:
    """Detects gaps in Odyssey's capabilities, quality, and knowledge."""

    async def analyze(self, window_hours: int = 24) -> GapReport:
        """Run full gap analysis and produce a report."""
        report_id = f"gap-{uuid.uuid4().hex[:12]}"

        # Take a fresh health snapshot
        snapshot = await introspector.take_snapshot(window_hours=window_hours)

        # Detect gaps in parallel
        capability_gaps = await self._detect_capability_gaps(window_hours)
        quality_gaps = await self._detect_quality_gaps(snapshot)
        knowledge_gaps = await self._detect_knowledge_gaps(snapshot)

        return GapReport(
            report_id=report_id,
            health_snapshot=snapshot,
            capability_gaps=capability_gaps,
            quality_gaps=quality_gaps,
            knowledge_gaps=knowledge_gaps,
        )

    async def _detect_capability_gaps(
        self, window_hours: int
    ) -> list[CapabilityGap]:
        """Find domains where query demand exceeds what Odyssey can handle."""
        gaps: list[CapabilityGap] = []

        # Get domain distribution of queries
        since = datetime.utcnow() - timedelta(hours=window_hours)
        domain_queries = await introspector.get_query_domain_distribution(since)
        dead_end_queries = await introspector.get_dead_end_queries(since)

        # Count dead ends per domain (approximation via keyword matching)
        domain_dead_ends: dict[str, int] = {}
        for dq in dead_end_queries:
            query_lower = (dq.get("query") or "").lower()
            for domain in KnowledgeDomain:
                # Simple heuristic: check if any domain keyword appears
                domain_kw = domain.value.replace("_", " ")
                if domain_kw in query_lower or domain.value in query_lower:
                    domain_dead_ends[domain.value] = domain_dead_ends.get(domain.value, 0) + 1

        total_queries = sum(domain_queries.values()) or 1

        for domain_val, query_count in domain_queries.items():
            signal_strength = query_count / total_queries
            dead_ends = domain_dead_ends.get(domain_val, 0)
            coverage = 1.0 - (dead_ends / max(query_count, 1))
            gap_score = signal_strength * (1.0 - coverage)

            if gap_score > 0.1:  # Only report significant gaps
                # Gather sample dead-end queries for this domain
                samples = [
                    dq["query"] for dq in dead_end_queries
                    if domain_val.replace("_", " ") in (dq.get("query") or "").lower()
                ][:5]

                gaps.append(CapabilityGap(
                    domain=domain_val,
                    signal_strength=round(signal_strength, 3),
                    current_coverage=round(coverage, 3),
                    gap_score=round(gap_score, 3),
                    evidence=[
                        f"{query_count} queries in this domain",
                        f"{dead_ends} resulted in dead ends",
                    ],
                    sample_queries=samples,
                ))

        gaps.sort(key=lambda g: g.gap_score, reverse=True)
        return gaps

    async def _detect_quality_gaps(
        self, snapshot: 'SystemHealthSnapshot'
    ) -> list[QualityGap]:
        """Find agents whose quality metrics are below thresholds or declining."""
        gaps: list[QualityGap] = []

        for agent_id, stats in snapshot.agent_stats.items():
            agent = agent_registry.get(agent_id)
            agent_name = agent.name if agent else agent_id

            # Check absolute quality threshold
            if stats.avg_quality > 0 and stats.avg_quality < MIN_AGENT_QUALITY:
                gaps.append(QualityGap(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    metric="avg_quality",
                    current_value=round(stats.avg_quality, 3),
                    target_value=MIN_AGENT_QUALITY,
                    trend=stats.trend,
                    evidence=[
                        f"Average quality {stats.avg_quality:.2f} below threshold {MIN_AGENT_QUALITY}",
                        f"Based on {stats.query_count} queries",
                    ],
                ))

            # Check dead end rate
            if stats.dead_end_rate > MAX_DEAD_END_RATE:
                gaps.append(QualityGap(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    metric="dead_end_rate",
                    current_value=round(stats.dead_end_rate, 3),
                    target_value=MAX_DEAD_END_RATE,
                    trend=stats.trend,
                    evidence=[
                        f"Dead end rate {stats.dead_end_rate:.1%} exceeds threshold {MAX_DEAD_END_RATE:.1%}",
                        f"Based on {stats.query_count} queries",
                    ],
                ))

            # Check for declining trend regardless of absolute value
            if stats.trend == "declining" and stats.query_count >= 10:
                gaps.append(QualityGap(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    metric="trend",
                    current_value=round(stats.avg_quality, 3),
                    target_value=stats.avg_quality + 0.1,  # At least recover
                    trend="declining",
                    evidence=[
                        f"Quality trend is declining (currently {stats.avg_quality:.2f})",
                        f"Based on {stats.query_count} queries",
                    ],
                ))

        return gaps

    async def _detect_knowledge_gaps(
        self, snapshot: 'SystemHealthSnapshot'
    ) -> list[KnowledgeGap]:
        """Find stale, sparse, or missing knowledge in the graph."""
        gaps: list[KnowledgeGap] = []
        kg_stats = snapshot.knowledge_stats

        # Check each domain for coverage
        for domain in KnowledgeDomain:
            node_count = kg_stats.domains_coverage.get(domain.value, 0)

            if node_count < MIN_DOMAIN_COVERAGE:
                gaps.append(KnowledgeGap(
                    domain=domain.value,
                    stale_node_count=0,
                    avg_confidence=0.0,
                    evidence=[
                        f"Only {node_count} nodes in {domain.value} (minimum: {MIN_DOMAIN_COVERAGE})",
                    ],
                    missing_signals=[
                        f"Domain {domain.value} is underrepresented in the knowledge graph"
                    ],
                ))

        # Check for stale knowledge per domain
        try:
            stale_by_domain = await neo4j_store.execute_read("""
                MATCH (t:Technology)
                WHERE t.confidence < 0.5
                RETURN t.domain AS domain, count(t) AS stale_count,
                       avg(t.confidence) AS avg_conf
            """)
            for r in stale_by_domain:
                if r["stale_count"] > 0:
                    domain = r["domain"]
                    total_in_domain = kg_stats.domains_coverage.get(domain, 1)
                    stale_ratio = r["stale_count"] / max(total_in_domain, 1)

                    if stale_ratio > 0.3:  # More than 30% stale
                        gaps.append(KnowledgeGap(
                            domain=domain,
                            stale_node_count=r["stale_count"],
                            avg_confidence=float(r["avg_conf"]) if r["avg_conf"] else 0.0,
                            evidence=[
                                f"{r['stale_count']}/{total_in_domain} nodes are stale ({stale_ratio:.0%})",
                                f"Average confidence: {r['avg_conf']:.2f}" if r["avg_conf"] else "No confidence data",
                            ],
                        ))
        except Exception:
            pass  # Don't let graph errors block gap detection

        # Check for topics queried but not in the graph
        try:
            dead_ends = await introspector.get_dead_end_queries(limit=100)
            missing_topics: set[str] = set()
            for dq in dead_ends:
                query = dq.get("query", "")
                if query:
                    # Extract potential technology names from failed queries
                    # This is a heuristic — the evolution planner will refine
                    missing_topics.add(query[:100])

            if missing_topics:
                gaps.append(KnowledgeGap(
                    domain="unknown",
                    missing_signals=list(missing_topics)[:20],
                    evidence=[
                        f"{len(missing_topics)} unique queries hit dead ends — potential missing knowledge",
                    ],
                ))
        except Exception:
            pass

        return gaps


gap_detector = GapDetector()
