"""Evolution Planner: generates concrete evolution proposals from gap reports.

Takes GapReports from the gap detector and produces EvolutionProposals —
actionable plans for new agents, knowledge expansion, agent retraining, etc.
Uses LLM reasoning to determine the best course of action.
"""

from __future__ import annotations

import uuid
from typing import Any

from odyssey.cortex.models import (
    BlastRadius,
    CapabilityGap,
    EvolutionProposal,
    EvolutionType,
    GapReport,
    KnowledgeGap,
    QualityGap,
)
from odyssey.llm.client import llm_client

EVOLUTION_REASONING_PROMPT = """You are the Evolution Planner for Odyssey, an AI-native enterprise architecture advisor.

You've received a gap report identifying weaknesses in the system. Your job is to propose concrete evolution actions.

## Gap Report Summary
{gap_summary}

## Current System State
- Active agents: {agent_count}
- Knowledge graph nodes: {total_nodes}
- Domain coverage: {domain_coverage}
- Average quality: {avg_quality}

## Available Evolution Actions
1. NEW_AGENT: Spawn a new specialized agent for an underserved domain
2. AGENT_RETRAIN: Update an existing agent's system prompt and capabilities
3. KNOWLEDGE_EXPANSION: Trigger targeted knowledge ingestion for a sparse domain
4. ONTOLOGY_EXTENSION: Add new node/edge types to the knowledge graph
5. SOURCE_ADDITION: Add new RSS/web sources to monitor
6. AGENT_RETIRE: Retire an underperforming or unused agent

## Guidelines
- Prioritize high-gap-score items
- Prefer knowledge expansion over new agents when the gap is about missing data
- Prefer agent retraining over new agents when the gap is about quality
- Only propose new agents when there's sustained demand for a specialized capability
- Each proposal must include a rollback plan
- Be specific in specifications — what exactly should be done

Respond as JSON with key "proposals" containing a list of proposals. Each proposal:
{{
    "type": "NEW_AGENT|AGENT_RETRAIN|KNOWLEDGE_EXPANSION|ONTOLOGY_EXTENSION|SOURCE_ADDITION|AGENT_RETIRE",
    "priority": 1-10 (1=highest),
    "rationale": "why this evolution is needed",
    "specification": {{...type-specific details...}},
    "blast_radius": "low|medium|high",
    "rollback_plan": "how to undo this if it fails",
    "success_criteria": ["measurable outcome 1", "measurable outcome 2"],
    "estimated_impact": "expected improvement"
}}

For NEW_AGENT specifications:
{{
    "agent_name": "name",
    "capabilities": ["cap1", "cap2"],
    "knowledge_domains": ["domain1"],
    "routing_keywords": ["keyword1", "keyword2"],
    "description": "what this agent does"
}}

For KNOWLEDGE_EXPANSION specifications:
{{
    "target_domain": "domain",
    "target_topics": ["topic1", "topic2"],
    "suggested_sources": ["url1", "url2"]
}}

For AGENT_RETRAIN specifications:
{{
    "agent_id": "id",
    "improvements": ["what to improve"],
    "focus_areas": ["area1"]
}}
"""


class EvolutionPlanner:
    """Generates evolution proposals from gap reports."""

    async def plan(self, gap_report: GapReport) -> list[EvolutionProposal]:
        """Analyze a gap report and produce evolution proposals."""
        if gap_report.total_gaps == 0:
            return []

        # Build gap summary for LLM reasoning
        gap_summary = self._build_gap_summary(gap_report)

        # Use LLM to reason about the best evolution actions
        raw_proposals = await self._reason_about_evolution(gap_report, gap_summary)

        # Convert to typed proposals
        proposals = []
        for raw in raw_proposals:
            proposal = self._parse_proposal(raw, gap_report.report_id)
            if proposal:
                proposals.append(proposal)

        # Sort by priority
        proposals.sort(key=lambda p: p.priority)
        return proposals

    async def plan_for_capability_gap(
        self, gap: CapabilityGap
    ) -> EvolutionProposal | None:
        """Generate a targeted proposal for a single capability gap."""
        if gap.gap_score < 0.1:
            return None

        # Determine the right action based on gap characteristics
        if gap.current_coverage < 0.3:
            # Very low coverage — likely missing knowledge
            return EvolutionProposal(
                id=f"evo-{uuid.uuid4().hex[:12]}",
                type=EvolutionType.KNOWLEDGE_EXPANSION,
                priority=3,
                rationale=f"Domain '{gap.domain}' has only {gap.current_coverage:.0%} coverage. "
                f"Signal strength: {gap.signal_strength:.0%}. "
                f"Evidence: {'; '.join(gap.evidence)}",
                specification={
                    "target_domain": gap.domain,
                    "sample_queries": gap.sample_queries,
                    "target_coverage": 0.7,
                },
                blast_radius=BlastRadius.LOW,
                rollback_plan="Remove newly added knowledge nodes from the target domain",
                success_criteria=[
                    f"Coverage in {gap.domain} improves to >0.5",
                    "Dead end rate for domain queries drops by 30%",
                ],
                gap_references=[gap.domain],
            )
        else:
            # Moderate coverage but high demand — may need a specialist agent
            return EvolutionProposal(
                id=f"evo-{uuid.uuid4().hex[:12]}",
                type=EvolutionType.NEW_AGENT,
                priority=5,
                rationale=f"High demand for '{gap.domain}' ({gap.signal_strength:.0%} of queries) "
                f"with {gap.current_coverage:.0%} coverage. A specialist agent would improve quality.",
                specification={
                    "agent_name": f"{gap.domain.replace('_', ' ').title()} Specialist",
                    "capabilities": [f"{gap.domain}_analysis", f"{gap.domain}_recommendation"],
                    "knowledge_domains": [gap.domain],
                    "routing_keywords": gap.sample_queries[:5],
                    "description": f"Specialist agent for {gap.domain} architecture decisions",
                },
                blast_radius=BlastRadius.HIGH,
                rollback_plan="Retire the new agent and route queries back to Navigator",
                success_criteria=[
                    f"Dead end rate for {gap.domain} queries drops by 50%",
                    "Average quality for domain queries exceeds 0.7",
                ],
                gap_references=[gap.domain],
            )

    async def plan_for_quality_gap(
        self, gap: QualityGap
    ) -> EvolutionProposal:
        """Generate a targeted proposal for a quality gap."""
        return EvolutionProposal(
            id=f"evo-{uuid.uuid4().hex[:12]}",
            type=EvolutionType.AGENT_RETRAIN,
            priority=4,
            rationale=f"Agent '{gap.agent_name}' has {gap.metric}={gap.current_value:.3f} "
            f"(target: {gap.target_value:.3f}), trend: {gap.trend}. "
            f"Evidence: {'; '.join(gap.evidence)}",
            specification={
                "agent_id": gap.agent_id,
                "improvements": gap.evidence,
                "target_metric": gap.metric,
                "target_value": gap.target_value,
            },
            blast_radius=BlastRadius.MEDIUM,
            rollback_plan=f"Revert agent '{gap.agent_id}' to previous version",
            success_criteria=[
                f"{gap.metric} improves from {gap.current_value:.3f} to {gap.target_value:.3f}",
                "No regression in other metrics",
            ],
            gap_references=[gap.agent_id],
        )

    async def plan_for_knowledge_gap(
        self, gap: KnowledgeGap
    ) -> EvolutionProposal:
        """Generate a targeted proposal for a knowledge gap."""
        if gap.stale_node_count > 0:
            # Stale knowledge — re-verify
            return EvolutionProposal(
                id=f"evo-{uuid.uuid4().hex[:12]}",
                type=EvolutionType.KNOWLEDGE_EXPANSION,
                priority=3,
                rationale=f"Domain '{gap.domain}' has {gap.stale_node_count} stale nodes "
                f"(avg confidence: {gap.avg_confidence:.2f}). "
                f"Evidence: {'; '.join(gap.evidence)}",
                specification={
                    "target_domain": gap.domain,
                    "action": "reverify_stale",
                    "stale_count": gap.stale_node_count,
                },
                blast_radius=BlastRadius.LOW,
                rollback_plan="Revert confidence scores to pre-verification values",
                success_criteria=[
                    f"Stale nodes in {gap.domain} reduced by 50%",
                    "Average confidence in domain improves to >0.6",
                ],
                gap_references=[gap.domain],
            )
        else:
            # Missing knowledge — ingest new sources
            return EvolutionProposal(
                id=f"evo-{uuid.uuid4().hex[:12]}",
                type=EvolutionType.SOURCE_ADDITION,
                priority=4,
                rationale=f"Domain '{gap.domain}' is underrepresented. "
                f"Evidence: {'; '.join(gap.evidence)}",
                specification={
                    "target_domain": gap.domain,
                    "missing_topics": gap.missing_signals[:10],
                },
                blast_radius=BlastRadius.LOW,
                rollback_plan="Remove newly added sources and their ingested knowledge",
                success_criteria=[
                    f"Node count in {gap.domain} increases by 50%",
                ],
                gap_references=[gap.domain],
            )

    async def _reason_about_evolution(
        self, gap_report: GapReport, gap_summary: str
    ) -> list[dict]:
        """Use LLM to reason about the best evolution actions."""
        snapshot = gap_report.health_snapshot
        prompt = EVOLUTION_REASONING_PROMPT.format(
            gap_summary=gap_summary,
            agent_count=snapshot.active_agent_count,
            total_nodes=snapshot.knowledge_stats.total_nodes,
            domain_coverage=snapshot.knowledge_stats.domains_coverage,
            avg_quality=f"{snapshot.avg_quality:.2f}",
        )
        try:
            result = await llm_client.generate_structured(prompt=prompt)
            return result.get("proposals", [])
        except Exception:
            # Fall back to rule-based planning if LLM fails
            return await self._rule_based_planning(gap_report)

    async def _rule_based_planning(
        self, gap_report: GapReport
    ) -> list[dict]:
        """Fallback rule-based planning when LLM is unavailable."""
        proposals = []

        # Handle capability gaps
        for gap in gap_report.capability_gaps[:3]:
            proposal = await self.plan_for_capability_gap(gap)
            if proposal:
                proposals.append(proposal.model_dump(mode="json"))

        # Handle quality gaps
        for gap in gap_report.quality_gaps[:3]:
            proposal = await self.plan_for_quality_gap(gap)
            proposals.append(proposal.model_dump(mode="json"))

        # Handle knowledge gaps
        for gap in gap_report.knowledge_gaps[:3]:
            proposal = await self.plan_for_knowledge_gap(gap)
            proposals.append(proposal.model_dump(mode="json"))

        return proposals

    def _build_gap_summary(self, report: GapReport) -> str:
        """Build a human-readable summary of gaps for LLM reasoning."""
        parts = []

        if report.capability_gaps:
            parts.append("CAPABILITY GAPS:")
            for g in report.capability_gaps:
                parts.append(
                    f"  - {g.domain}: gap_score={g.gap_score:.2f}, "
                    f"signal={g.signal_strength:.0%}, coverage={g.current_coverage:.0%}"
                )
                for e in g.evidence:
                    parts.append(f"    Evidence: {e}")

        if report.quality_gaps:
            parts.append("QUALITY GAPS:")
            for g in report.quality_gaps:
                parts.append(
                    f"  - Agent '{g.agent_name}': {g.metric}={g.current_value:.3f} "
                    f"(target: {g.target_value:.3f}), trend: {g.trend}"
                )

        if report.knowledge_gaps:
            parts.append("KNOWLEDGE GAPS:")
            for g in report.knowledge_gaps:
                parts.append(
                    f"  - {g.domain}: {g.stale_node_count} stale nodes, "
                    f"avg_confidence={g.avg_confidence:.2f}"
                )

        return "\n".join(parts) if parts else "No significant gaps detected."

    def _parse_proposal(
        self, raw: dict, report_id: str
    ) -> EvolutionProposal | None:
        """Parse a raw proposal dict into a typed EvolutionProposal."""
        try:
            evo_type = EvolutionType(raw.get("type", "").lower())
        except ValueError:
            return None

        try:
            blast = BlastRadius(raw.get("blast_radius", "low").lower())
        except ValueError:
            blast = BlastRadius.LOW

        return EvolutionProposal(
            id=f"evo-{uuid.uuid4().hex[:12]}",
            type=evo_type,
            priority=raw.get("priority", 5),
            rationale=raw.get("rationale", ""),
            specification=raw.get("specification", {}),
            blast_radius=blast,
            rollback_plan=raw.get("rollback_plan", ""),
            success_criteria=raw.get("success_criteria", []),
            estimated_impact=raw.get("estimated_impact", ""),
            gap_references=[report_id],
        )


evolution_planner = EvolutionPlanner()
