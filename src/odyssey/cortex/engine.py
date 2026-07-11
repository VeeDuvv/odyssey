"""Evolution Engine: the autonomous self-evolution loop.

Ties together introspector, gap detector, evolution planner, governor,
agent factory, and validator into a continuous evolution cycle:

    SENSE -> ASSESS -> PLAN -> EVOLVE -> VALIDATE -> (loop)

This is the heartbeat of Odyssey's nervous system.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from odyssey.agents.factory import agent_factory
from odyssey.agents.lifecycle import agent_lifecycle
from odyssey.agents.registry import agent_registry
from odyssey.cortex.gap_detector import gap_detector
from odyssey.cortex.governor import governor
from odyssey.cortex.introspector import introspector
from odyssey.cortex.models import (
    EvolutionProposal,
    EvolutionType,
    GapReport,
)
from odyssey.cortex.validator import validator

logger = logging.getLogger("odyssey.cortex.engine")


class EvolutionEngine:
    """The autonomous self-evolution loop."""

    def __init__(self) -> None:
        self._running = False
        self._cycle_count = 0
        self._last_gap_report: GapReport | None = None
        self._last_cycle_at: datetime | None = None

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def status(self) -> dict:
        return {
            "running": self._running,
            "cycle_count": self._cycle_count,
            "last_cycle_at": self._last_cycle_at.isoformat() if self._last_cycle_at else None,
            "last_gap_report": {
                "id": self._last_gap_report.report_id,
                "total_gaps": self._last_gap_report.total_gaps,
                "capability_gaps": len(self._last_gap_report.capability_gaps),
                "quality_gaps": len(self._last_gap_report.quality_gaps),
                "knowledge_gaps": len(self._last_gap_report.knowledge_gaps),
            } if self._last_gap_report else None,
            "governor": {
                "kill_switch": governor.limits.kill_switch_active,
                "agents_created_this_week": governor.state.agents_created_this_week,
                "prompts_modified_today": governor.state.prompts_modified_today,
                "total_active_agents": governor.state.total_active_agents,
            },
        }

    async def run_cycle(self) -> dict:
        """Run a single evolution cycle: sense -> assess -> plan -> evolve -> validate.

        Returns a summary of what happened.
        """
        self._cycle_count += 1
        self._last_cycle_at = datetime.utcnow()
        cycle_id = f"cycle-{self._cycle_count}"
        summary = {"cycle_id": cycle_id, "actions": []}

        logger.info(f"[{cycle_id}] Starting evolution cycle")

        # --- SENSE ---
        snapshot = await introspector.take_snapshot(window_hours=24)
        governor.state.total_active_agents = snapshot.active_agent_count
        summary["health"] = {
            "total_queries": snapshot.total_queries,
            "avg_quality": round(snapshot.avg_quality, 3),
            "dead_end_rate": round(snapshot.dead_end_rate, 3),
            "active_agents": snapshot.active_agent_count,
            "knowledge_nodes": snapshot.knowledge_stats.total_nodes,
        }

        # --- ASSESS ---
        gap_report = await gap_detector.analyze(window_hours=24)
        self._last_gap_report = gap_report
        summary["gaps"] = {
            "total": gap_report.total_gaps,
            "capability": len(gap_report.capability_gaps),
            "quality": len(gap_report.quality_gaps),
            "knowledge": len(gap_report.knowledge_gaps),
        }

        if gap_report.total_gaps == 0:
            logger.info(f"[{cycle_id}] No gaps detected. System is healthy.")
            summary["actions"].append({"type": "none", "reason": "No gaps detected"})
            # Still check lifecycle (promotions/retirements)
            await self._run_lifecycle_checks(summary)
            return summary

        # --- PLAN ---
        from odyssey.cortex.evolution_planner import evolution_planner

        proposals = await evolution_planner.plan(gap_report)
        summary["proposals"] = len(proposals)

        if not proposals:
            logger.info(f"[{cycle_id}] No actionable proposals generated.")
            summary["actions"].append({"type": "none", "reason": "No proposals generated"})
            await self._run_lifecycle_checks(summary)
            return summary

        # --- EVOLVE + VALIDATE ---
        for proposal in proposals[:3]:  # Max 3 actions per cycle
            action = await self._execute_proposal(proposal, cycle_id)
            summary["actions"].append(action)

        # --- LIFECYCLE ---
        await self._run_lifecycle_checks(summary)

        logger.info(
            f"[{cycle_id}] Cycle complete. "
            f"{len(summary['actions'])} actions taken."
        )
        return summary

    async def run_loop(
        self, interval_minutes: int = 60, max_cycles: int | None = None
    ) -> None:
        """Run the evolution loop continuously.

        Args:
            interval_minutes: Minutes between cycles.
            max_cycles: Stop after N cycles (None = run forever).
        """
        self._running = True
        cycles = 0

        logger.info(
            f"Evolution engine started. Interval: {interval_minutes}m, "
            f"max_cycles: {max_cycles or 'unlimited'}"
        )

        try:
            while self._running:
                try:
                    await self.run_cycle()
                except Exception as e:
                    logger.error(f"Evolution cycle failed: {e}", exc_info=True)

                cycles += 1
                if max_cycles and cycles >= max_cycles:
                    logger.info(f"Reached max cycles ({max_cycles}). Stopping.")
                    break

                await asyncio.sleep(interval_minutes * 60)
        finally:
            self._running = False
            logger.info("Evolution engine stopped.")

    def stop(self) -> None:
        """Signal the evolution loop to stop."""
        self._running = False

    async def _execute_proposal(
        self, proposal: EvolutionProposal, cycle_id: str
    ) -> dict:
        """Execute a single evolution proposal through the governor."""
        action = {
            "type": proposal.type.value,
            "priority": proposal.priority,
            "blast_radius": proposal.blast_radius.value,
        }

        # Governor check
        decision = await governor.evaluate(proposal)
        if not decision.approved:
            action["outcome"] = "blocked"
            action["reason"] = decision.reason
            logger.info(
                f"[{cycle_id}] Proposal BLOCKED: {proposal.type.value} — {decision.reason}"
            )
            return action

        # Capture baseline metrics
        metrics_before = await validator.capture_baseline_metrics()

        # Execute based on type
        try:
            match proposal.type:
                case EvolutionType.NEW_AGENT:
                    await self._execute_new_agent(proposal)
                case EvolutionType.AGENT_RETRAIN:
                    await self._execute_agent_retrain(proposal)
                case EvolutionType.KNOWLEDGE_EXPANSION:
                    await self._execute_knowledge_expansion(proposal)
                case EvolutionType.SOURCE_ADDITION:
                    await self._execute_source_addition(proposal)
                case EvolutionType.AGENT_RETIRE:
                    await self._execute_agent_retire(proposal)
                case EvolutionType.ONTOLOGY_EXTENSION:
                    await self._execute_ontology_extension(proposal)

            # Record execution
            await governor.record_execution(proposal, metrics_before)
            action["outcome"] = "executed"
            action["rationale"] = proposal.rationale
            logger.info(
                f"[{cycle_id}] Proposal EXECUTED: {proposal.type.value} — {proposal.rationale}"
            )

        except Exception as e:
            action["outcome"] = "failed"
            action["error"] = str(e)
            logger.error(
                f"[{cycle_id}] Proposal FAILED: {proposal.type.value} — {e}",
                exc_info=True,
            )

        return action

    async def _execute_new_agent(self, proposal: EvolutionProposal) -> None:
        """Spawn a new dynamic agent."""
        spec = proposal.specification
        agent = await agent_factory.create_agent(spec)
        agent_registry.register(agent)
        await agent_registry.persist(agent)
        logger.info(f"New agent created: {agent.name} (id={agent.id}, status=canary)")

    async def _execute_agent_retrain(self, proposal: EvolutionProposal) -> None:
        """Update an existing agent's configuration."""
        spec = proposal.specification
        agent_id = spec.get("agent_id")
        if not agent_id:
            return

        agent = agent_registry.get(agent_id)
        if not agent:
            return

        # Update version
        agent.definition.version += 1
        agent.definition.last_evolved_at = datetime.utcnow()

        # If the agent is dynamic, we can update its system prompt
        from odyssey.agents.factory import DynamicAgent

        if isinstance(agent, DynamicAgent):
            improvements = spec.get("improvements", [])
            if improvements:
                new_prompt = await self._generate_improved_prompt(
                    agent, improvements
                )
                agent.system_prompt = new_prompt
                agent.definition.config["system_prompt"] = new_prompt

        await agent_registry.persist(agent)
        logger.info(f"Agent retrained: {agent.name} v{agent.definition.version}")

    async def _execute_knowledge_expansion(
        self, proposal: EvolutionProposal
    ) -> None:
        """Trigger knowledge ingestion for a target domain."""
        spec = proposal.specification
        target_domain = spec.get("target_domain", "")
        sample_queries = spec.get("sample_queries", [])

        # Use the cartographer to expand knowledge
        cartographer = agent_registry.get("cartographer")
        if cartographer:
            from odyssey.agents.base import AgentQuery

            for query in sample_queries[:5]:
                await cartographer.process(AgentQuery(
                    query=f"Learn about: {query}",
                    context={"content": query, "domain": target_domain},
                ))

        logger.info(f"Knowledge expanded for domain: {target_domain}")

    async def _execute_source_addition(
        self, proposal: EvolutionProposal
    ) -> None:
        """Add new monitoring sources."""
        # For now, log the intent — full source management comes later
        spec = proposal.specification
        logger.info(
            f"Source addition proposed for domain '{spec.get('target_domain')}': "
            f"{spec.get('missing_topics', [])}"
        )

    async def _execute_agent_retire(self, proposal: EvolutionProposal) -> None:
        """Retire an underperforming agent."""
        agent_id = proposal.specification.get("agent_id")
        if not agent_id:
            return
        agent = agent_registry.get(agent_id)
        if agent:
            agent.definition.status = "retired"
            agent_registry.unregister(agent_id)
            await agent_registry.persist(agent)
            logger.info(f"Agent retired: {agent.name}")

    async def _execute_ontology_extension(
        self, proposal: EvolutionProposal
    ) -> None:
        """Extend the knowledge graph ontology."""
        # For now, log — full ontology extension is complex
        logger.info(f"Ontology extension proposed: {proposal.specification}")

    async def _generate_improved_prompt(
        self, agent: BaseAgent, improvements: list[str]
    ) -> str:
        """Generate an improved system prompt for an agent."""
        from odyssey.agents.factory import DynamicAgent

        current_prompt = ""
        if isinstance(agent, DynamicAgent):
            current_prompt = agent.system_prompt

        result = await llm_client.generate(
            prompt=(
                f"Here is the current system prompt for agent '{agent.name}':\n\n"
                f"{current_prompt}\n\n"
                f"Improve it based on this feedback:\n"
                + "\n".join(f"- {imp}" for imp in improvements)
                + "\n\nReturn ONLY the improved system prompt, nothing else."
            ),
            system="You are improving an AI agent's system prompt. Return only the improved prompt.",
            temperature=0.3,
        )
        return result

    async def _run_lifecycle_checks(self, summary: dict) -> None:
        """Check for agent promotions and retirements."""
        promoted = await agent_lifecycle.check_promotions()
        if promoted:
            summary["actions"].append({
                "type": "promotion",
                "agents": promoted,
            })

        retired = await agent_lifecycle.check_retirements()
        if retired:
            summary["actions"].append({
                "type": "retirement",
                "agents": retired,
            })


# Singleton — import from here
from odyssey.llm.client import llm_client  # noqa: E402

evolution_engine = EvolutionEngine()
