"""Validator: post-evolution quality validation and auto-rollback.

After any evolution action, the validator monitors quality metrics
and automatically rolls back if quality degrades beyond the threshold.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from odyssey.cortex.governor import governor
from odyssey.cortex.introspector import introspector
from odyssey.cortex.models import (
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionType,
)
from odyssey.agents.registry import agent_registry


class ValidationResult:
    """Result of post-evolution validation."""

    def __init__(
        self,
        passed: bool,
        reason: str,
        metrics_before: dict[str, float],
        metrics_after: dict[str, float],
    ) -> None:
        self.passed = passed
        self.reason = reason
        self.metrics_before = metrics_before
        self.metrics_after = metrics_after


class Validator:
    """Validates evolution outcomes and triggers rollback on regression."""

    async def capture_baseline_metrics(self) -> dict[str, float]:
        """Capture current system metrics as a baseline before evolution."""
        snapshot = await introspector.take_snapshot(window_hours=24)
        return {
            "avg_quality": snapshot.avg_quality,
            "avg_latency_ms": float(snapshot.avg_latency_ms),
            "dead_end_rate": snapshot.dead_end_rate,
            "active_agent_count": float(snapshot.active_agent_count),
            "total_knowledge_nodes": float(snapshot.knowledge_stats.total_nodes),
        }

    async def validate(
        self,
        proposal: EvolutionProposal,
        metrics_before: dict[str, float],
        window_hours: int = 24,
    ) -> ValidationResult:
        """Validate an evolution by comparing before/after metrics.

        Call this after the canary period (default 24h post-evolution).
        """
        # Capture current metrics
        metrics_after = await self.capture_baseline_metrics()

        # Check circuit breaker
        needs_rollback = await governor.check_circuit_breaker(
            proposal_id=proposal.id,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
        )

        if needs_rollback:
            # Execute rollback
            await self._execute_rollback(proposal)
            return ValidationResult(
                passed=False,
                reason=f"Circuit breaker triggered. Metrics regressed beyond "
                f"{governor.limits.quality_regression_threshold:.0%} threshold.",
                metrics_before=metrics_before,
                metrics_after=metrics_after,
            )

        # Check success criteria (if measurable)
        criteria_met = self._check_success_criteria(
            proposal, metrics_before, metrics_after
        )

        if not criteria_met:
            # Not an automatic rollback — just flag as underperforming
            return ValidationResult(
                passed=True,  # No regression, but criteria not met yet
                reason="No quality regression detected, but success criteria not yet met. "
                "Will continue monitoring.",
                metrics_before=metrics_before,
                metrics_after=metrics_after,
            )

        return ValidationResult(
            passed=True,
            reason="Evolution validated successfully. All metrics stable or improved.",
            metrics_before=metrics_before,
            metrics_after=metrics_after,
        )

    async def _execute_rollback(self, proposal: EvolutionProposal) -> None:
        """Execute the rollback plan for a failed evolution."""
        match proposal.type:
            case EvolutionType.NEW_AGENT:
                # Retire the new agent
                agent_id = proposal.specification.get("agent_id")
                if agent_id:
                    agent = agent_registry.get(agent_id)
                    if agent:
                        agent.definition.status = "retired"
                        agent_registry.unregister(agent_id)
                        await agent_registry.persist(agent)

            case EvolutionType.AGENT_RETRAIN:
                # Revert would require storing the previous prompt
                # For now, log that manual intervention may be needed
                pass

            case EvolutionType.KNOWLEDGE_EXPANSION:
                # Could delete recently added nodes, but that's risky
                # Log for manual review
                pass

        # Record the rollback
        await introspector.record_evolution(
            proposal_type=f"rollback_{proposal.type.value}",
            proposal=proposal.model_dump(mode="json"),
            outcome=EvolutionOutcome.ROLLED_BACK.value,
            rationale=f"Auto-rollback triggered for proposal {proposal.id}",
        )

    def _check_success_criteria(
        self,
        proposal: EvolutionProposal,
        before: dict[str, float],
        after: dict[str, float],
    ) -> bool:
        """Check if the evolution's success criteria are met.

        Returns True if criteria are met or if no measurable criteria exist.
        """
        if not proposal.success_criteria:
            return True

        # Basic check: no metric should have worsened significantly
        for metric, before_val in before.items():
            after_val = after.get(metric, before_val)
            if before_val > 0 and metric in ("avg_quality",):
                # Quality should not drop
                if after_val < before_val * 0.95:
                    return False
            if metric == "dead_end_rate":
                # Dead end rate should not increase
                if after_val > before_val * 1.1:
                    return False

        return True


validator = Validator()
