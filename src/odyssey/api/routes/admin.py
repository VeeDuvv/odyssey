"""Admin routes: observe and control Odyssey's self-evolution."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from fastapi import APIRouter, BackgroundTasks, Depends

from odyssey.api.middleware.auth import verify_api_key
from odyssey.cortex.engine import evolution_engine
from odyssey.cortex.gap_detector import gap_detector
from odyssey.cortex.governor import governor
from odyssey.cortex.introspector import introspector
from odyssey.agents.registry import agent_registry

router = APIRouter(
    prefix="/api/admin", tags=["admin"], dependencies=[Depends(verify_api_key)]
)


# --- System Status ---


@router.get("/status")
async def system_status() -> dict:
    """Get full system status including evolution engine state."""
    snapshot = await introspector.take_snapshot(window_hours=24)
    return {
        "evolution_engine": evolution_engine.status,
        "health": {
            "total_queries_24h": snapshot.total_queries,
            "avg_quality": round(snapshot.avg_quality, 3),
            "avg_latency_ms": snapshot.avg_latency_ms,
            "dead_end_rate": round(snapshot.dead_end_rate, 3),
        },
        "agents": {
            agent.name: {
                "id": agent.id,
                "type": agent.definition.type,
                "status": agent.definition.status,
                "version": agent.definition.version,
            }
            for agent in agent_registry.get_all()
        },
        "knowledge": {
            "total_nodes": snapshot.knowledge_stats.total_nodes,
            "stale_nodes": snapshot.knowledge_stats.stale_nodes,
            "avg_confidence": round(snapshot.knowledge_stats.avg_confidence, 3),
            "domain_coverage": snapshot.knowledge_stats.domains_coverage,
        },
        "governor": {
            "kill_switch": governor.limits.kill_switch_active,
            "limits": governor.limits.model_dump(),
            "state": governor.state.model_dump(mode="json"),
        },
    }


# --- Evolution Control ---


@router.post("/evolution/cycle")
async def trigger_evolution_cycle() -> dict:
    """Manually trigger a single evolution cycle."""
    result = await evolution_engine.run_cycle()
    return result


@router.post("/evolution/start")
async def start_evolution_loop(
    background_tasks: BackgroundTasks,
    interval_minutes: int = 60,
) -> dict:
    """Start the continuous evolution loop in the background."""
    if evolution_engine.is_running:
        return {"status": "already_running"}

    background_tasks.add_task(
        evolution_engine.run_loop, interval_minutes=interval_minutes
    )
    return {"status": "started", "interval_minutes": interval_minutes}


@router.post("/evolution/stop")
async def stop_evolution_loop() -> dict:
    """Stop the continuous evolution loop."""
    evolution_engine.stop()
    return {"status": "stopped"}


# --- Gap Analysis ---


@router.get("/gaps")
async def get_gap_report(window_hours: int = 24) -> dict:
    """Run gap analysis and return the report."""
    report = await gap_detector.analyze(window_hours=window_hours)
    return report.model_dump(mode="json")


# --- Governor Control ---


@router.post("/governor/kill-switch/activate")
async def activate_kill_switch() -> dict:
    """Activate the kill switch — immediately halt all evolution."""
    governor.activate_kill_switch()
    return {"kill_switch": "active", "message": "All evolution is now frozen."}


@router.post("/governor/kill-switch/deactivate")
async def deactivate_kill_switch() -> dict:
    """Deactivate the kill switch — resume evolution."""
    governor.deactivate_kill_switch()
    return {"kill_switch": "inactive", "message": "Evolution resumed."}


class UpdateLimitsRequest(BaseModel):
    max_new_agents_per_week: int | None = None
    max_prompt_modifications_per_day: int | None = None
    max_ontology_extensions_per_day: int | None = None
    max_total_agents: int | None = None
    quality_regression_threshold: float | None = None
    canary_duration_hours: int | None = None


@router.put("/governor/limits")
async def update_governor_limits(request: UpdateLimitsRequest) -> dict:
    """Update governor safety limits."""
    if request.max_new_agents_per_week is not None:
        governor.limits.max_new_agents_per_week = request.max_new_agents_per_week
    if request.max_prompt_modifications_per_day is not None:
        governor.limits.max_prompt_modifications_per_day = request.max_prompt_modifications_per_day
    if request.max_ontology_extensions_per_day is not None:
        governor.limits.max_ontology_extensions_per_day = request.max_ontology_extensions_per_day
    if request.max_total_agents is not None:
        governor.limits.max_total_agents = request.max_total_agents
    if request.quality_regression_threshold is not None:
        governor.limits.quality_regression_threshold = request.quality_regression_threshold
    if request.canary_duration_hours is not None:
        governor.limits.canary_duration_hours = request.canary_duration_hours

    return {"status": "updated", "limits": governor.limits.model_dump()}


# --- Telemetry ---


@router.get("/telemetry/dead-ends")
async def get_dead_end_queries(limit: int = 50) -> dict:
    """Get queries that hit dead ends (low quality responses)."""
    dead_ends = await introspector.get_dead_end_queries(limit=limit)
    return {"count": len(dead_ends), "queries": dead_ends}


@router.get("/telemetry/domains")
async def get_domain_distribution() -> dict:
    """Get distribution of queries across knowledge domains."""
    distribution = await introspector.get_query_domain_distribution()
    return {"domains": distribution}


# --- Agent Management ---


@router.get("/agents")
async def list_agents() -> dict:
    """List all registered agents with their details."""
    agents = []
    for agent in agent_registry.get_all():
        agents.append({
            "id": agent.id,
            "name": agent.name,
            "type": agent.definition.type,
            "status": agent.definition.status,
            "capabilities": agent.definition.capabilities,
            "knowledge_domains": agent.definition.knowledge_domains,
            "version": agent.definition.version,
            "created_at": agent.definition.created_at.isoformat(),
            "last_evolved_at": agent.definition.last_evolved_at.isoformat(),
        })
    return {"agents": agents, "total": len(agents)}
