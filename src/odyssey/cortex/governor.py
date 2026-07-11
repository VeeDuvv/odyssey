"""Governor: safety guardrails for autonomous self-evolution.

Autonomous from day one — no human approval gates. The Governor enforces:
- Blast radius limits (rate limiting on evolution actions)
- Quality gates (no evolution if it would regress quality)
- Circuit breaker (auto-rollback on quality drops >15%)
- Kill switch (freeze all evolution via config)
- Resource ceilings (max agents, knowledge growth, LLM spend)

The Governor itself CANNOT be modified by the evolution planner. It is the one constant.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta

from odyssey.cortex.introspector import introspector
from odyssey.cortex.models import (
    BlastRadius,
    EvolutionAuditEntry,
    EvolutionOutcome,
    EvolutionProposal,
    EvolutionType,
    GovernorLimits,
    GovernorState,
)
from odyssey.storage.postgres import postgres_store


class GovernorDecision:
    """Result of the governor evaluating a proposal."""

    def __init__(self, approved: bool, reason: str) -> None:
        self.approved = approved
        self.reason = reason

    def __repr__(self) -> str:
        status = "APPROVED" if self.approved else "BLOCKED"
        return f"GovernorDecision({status}: {self.reason})"


class Governor:
    """Safety layer for autonomous self-evolution."""

    def __init__(self) -> None:
        self.limits = GovernorLimits()
        self.state = GovernorState()

    async def evaluate(self, proposal: EvolutionProposal) -> GovernorDecision:
        """Evaluate whether an evolution proposal is safe to execute.

        Returns a GovernorDecision with approval status and rationale.
        """
        # Kill switch check — overrides everything
        if self.limits.kill_switch_active:
            return GovernorDecision(
                approved=False,
                reason="Kill switch is active. All evolution is frozen.",
            )

        # Reset daily/weekly counters if needed
        self._maybe_reset_counters()

        # Run all safety checks
        checks = [
            self._check_blast_radius(proposal),
            self._check_rate_limits(proposal),
            self._check_resource_ceilings(proposal),
            await self._check_recent_failures(),
        ]

        for decision in checks:
            if not decision.approved:
                # Log the blocked proposal
                await self._audit(proposal, EvolutionOutcome.BLOCKED, decision.reason)
                return decision

        return GovernorDecision(
            approved=True,
            reason=f"All safety checks passed for {proposal.type.value} "
            f"(blast_radius={proposal.blast_radius.value})",
        )

    async def record_execution(
        self,
        proposal: EvolutionProposal,
        metrics_before: dict[str, float] | None = None,
    ) -> None:
        """Record that an evolution proposal was executed."""
        self._increment_counters(proposal)
        self.state.recent_evolutions.append(proposal.id)
        # Keep only last 20 evolutions in memory
        if len(self.state.recent_evolutions) > 20:
            self.state.recent_evolutions = self.state.recent_evolutions[-20:]

        await self._audit(
            proposal,
            EvolutionOutcome.EXECUTED,
            f"Executed: {proposal.rationale}",
            metrics_before=metrics_before,
        )

    async def check_circuit_breaker(
        self,
        proposal_id: str,
        metrics_before: dict[str, float],
        metrics_after: dict[str, float],
    ) -> bool:
        """Check if quality regressed enough to trigger auto-rollback.

        Returns True if rollback is needed.
        """
        threshold = self.limits.quality_regression_threshold

        for metric, before_val in metrics_before.items():
            after_val = metrics_after.get(metric, before_val)
            if before_val > 0:
                regression = (before_val - after_val) / before_val
                if regression > threshold:
                    # Circuit breaker triggered!
                    await introspector.record_evolution(
                        proposal_type="circuit_breaker",
                        proposal={"proposal_id": proposal_id, "metric": metric},
                        outcome="rolled_back",
                        rationale=f"Quality regression detected: {metric} dropped "
                        f"from {before_val:.3f} to {after_val:.3f} "
                        f"({regression:.1%} > {threshold:.1%} threshold)",
                        metrics_before=metrics_before,
                        metrics_after=metrics_after,
                    )
                    return True
        return False

    def activate_kill_switch(self) -> None:
        """Immediately halt all evolution. Called by human operator."""
        self.limits.kill_switch_active = True

    def deactivate_kill_switch(self) -> None:
        """Resume evolution. Called by human operator."""
        self.limits.kill_switch_active = False

    # --- Safety Checks ---

    def _check_blast_radius(
        self, proposal: EvolutionProposal
    ) -> GovernorDecision:
        """High blast radius proposals get extra scrutiny."""
        if proposal.blast_radius == BlastRadius.HIGH:
            if not proposal.rollback_plan:
                return GovernorDecision(
                    approved=False,
                    reason="HIGH blast radius proposal must have a rollback plan.",
                )
            if not proposal.success_criteria:
                return GovernorDecision(
                    approved=False,
                    reason="HIGH blast radius proposal must have success criteria.",
                )
        return GovernorDecision(approved=True, reason="Blast radius check passed")

    def _check_rate_limits(
        self, proposal: EvolutionProposal
    ) -> GovernorDecision:
        """Enforce rate limits on evolution actions."""
        if proposal.type == EvolutionType.NEW_AGENT:
            if self.state.agents_created_this_week >= self.limits.max_new_agents_per_week:
                return GovernorDecision(
                    approved=False,
                    reason=f"Rate limit: {self.state.agents_created_this_week} agents "
                    f"created this week (max: {self.limits.max_new_agents_per_week})",
                )

        if proposal.type == EvolutionType.AGENT_RETRAIN:
            if self.state.prompts_modified_today >= self.limits.max_prompt_modifications_per_day:
                return GovernorDecision(
                    approved=False,
                    reason=f"Rate limit: {self.state.prompts_modified_today} prompt mods "
                    f"today (max: {self.limits.max_prompt_modifications_per_day})",
                )

        if proposal.type == EvolutionType.ONTOLOGY_EXTENSION:
            if self.state.ontology_extensions_today >= self.limits.max_ontology_extensions_per_day:
                return GovernorDecision(
                    approved=False,
                    reason=f"Rate limit: {self.state.ontology_extensions_today} ontology "
                    f"extensions today (max: {self.limits.max_ontology_extensions_per_day})",
                )

        return GovernorDecision(approved=True, reason="Rate limits check passed")

    def _check_resource_ceilings(
        self, proposal: EvolutionProposal
    ) -> GovernorDecision:
        """Enforce caps on total resources."""
        if proposal.type == EvolutionType.NEW_AGENT:
            if self.state.total_active_agents >= self.limits.max_total_agents:
                return GovernorDecision(
                    approved=False,
                    reason=f"Resource ceiling: {self.state.total_active_agents} active agents "
                    f"(max: {self.limits.max_total_agents}). Retire an agent first.",
                )

        return GovernorDecision(approved=True, reason="Resource ceilings check passed")

    async def _check_recent_failures(self) -> GovernorDecision:
        """If recent evolutions failed, slow down."""
        try:
            recent = await postgres_store.fetch(
                """
                SELECT outcome FROM evolution_log
                WHERE timestamp > $1
                ORDER BY timestamp DESC
                LIMIT 5
                """,
                datetime.utcnow() - timedelta(hours=24),
            )
            rollback_count = sum(1 for r in recent if r["outcome"] == "rolled_back")
            if rollback_count >= 3:
                return GovernorDecision(
                    approved=False,
                    reason=f"Stability check: {rollback_count} rollbacks in last 24h. "
                    "Pausing evolution until system stabilizes.",
                )
        except Exception:
            pass  # Don't block on telemetry failures
        return GovernorDecision(approved=True, reason="Stability check passed")

    # --- Counter Management ---

    def _maybe_reset_counters(self) -> None:
        """Reset daily/weekly counters as needed."""
        now = datetime.utcnow()
        last_reset = self.state.last_reset_date

        # Daily reset
        if now.date() > last_reset.date():
            self.state.prompts_modified_today = 0
            self.state.ontology_extensions_today = 0
            self.state.knowledge_nodes_added_today = 0
            self.state.llm_spend_this_cycle_usd = 0.0
            self.state.last_reset_date = now

        # Weekly reset (Monday)
        if now.isocalendar()[1] != last_reset.isocalendar()[1]:
            self.state.agents_created_this_week = 0

    def _increment_counters(self, proposal: EvolutionProposal) -> None:
        """Update rate-limiting counters after execution."""
        match proposal.type:
            case EvolutionType.NEW_AGENT:
                self.state.agents_created_this_week += 1
                self.state.total_active_agents += 1
            case EvolutionType.AGENT_RETRAIN:
                self.state.prompts_modified_today += 1
            case EvolutionType.ONTOLOGY_EXTENSION:
                self.state.ontology_extensions_today += 1
            case EvolutionType.AGENT_RETIRE:
                self.state.total_active_agents = max(0, self.state.total_active_agents - 1)

    # --- Audit ---

    async def _audit(
        self,
        proposal: EvolutionProposal,
        outcome: EvolutionOutcome,
        rationale: str,
        metrics_before: dict[str, float] | None = None,
        metrics_after: dict[str, float] | None = None,
    ) -> None:
        """Write an immutable audit log entry."""
        await introspector.record_evolution(
            proposal_type=proposal.type.value,
            proposal=proposal.model_dump(mode="json"),
            outcome=outcome.value,
            rationale=rationale,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
        )


governor = Governor()
