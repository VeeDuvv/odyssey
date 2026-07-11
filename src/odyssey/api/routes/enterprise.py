"""Enterprise context management routes."""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends

from odyssey.api.middleware.auth import verify_api_key
from odyssey.enterprise.models import (
    BudgetEnvelope,
    Constraint,
    EnterpriseProfile,
    Industry,
    MaturityAssessment,
    ScaleProfile,
    StrategicGoal,
    TechStackComponent,
)
from odyssey.storage.postgres import postgres_store

router = APIRouter(
    prefix="/api/enterprise", tags=["enterprise"], dependencies=[Depends(verify_api_key)]
)


class CreateEnterpriseRequest(BaseModel):
    name: str
    industry: Industry = Industry.OTHER
    scale: ScaleProfile = Field(default_factory=ScaleProfile)
    maturity: MaturityAssessment = Field(default_factory=MaturityAssessment)
    constraints: list[Constraint] = Field(default_factory=list)
    goals: list[StrategicGoal] = Field(default_factory=list)
    tech_stack: list[TechStackComponent] = Field(default_factory=list)
    budget: BudgetEnvelope = Field(default_factory=BudgetEnvelope)


class UpdateEnterpriseRequest(BaseModel):
    name: str | None = None
    industry: Industry | None = None
    scale: ScaleProfile | None = None
    maturity: MaturityAssessment | None = None
    constraints: list[Constraint] | None = None
    goals: list[StrategicGoal] | None = None
    tech_stack: list[TechStackComponent] | None = None
    budget: BudgetEnvelope | None = None


@router.get("")
async def list_enterprises() -> dict:
    """List all enterprise profiles."""
    rows = await postgres_store.fetch(
        "SELECT id, name, industry, created_at, updated_at FROM enterprises ORDER BY updated_at DESC"
    )
    return {"enterprises": [dict(r) for r in rows], "count": len(rows)}


@router.post("")
async def create_enterprise(request: CreateEnterpriseRequest) -> dict:
    """Create a new enterprise profile."""
    enterprise_id = str(uuid.uuid4())[:12]

    profile = EnterpriseProfile(
        id=enterprise_id,
        name=request.name,
        industry=request.industry,
        scale=request.scale,
        maturity=request.maturity,
        constraints=request.constraints,
        goals=request.goals,
        tech_stack=request.tech_stack,
        budget=request.budget,
    )

    await postgres_store.execute(
        """
        INSERT INTO enterprises (id, name, industry, profile, maturity, constraints, goals, tech_stack, budget)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        profile.id,
        profile.name,
        profile.industry.value,
        json.dumps(profile.scale.model_dump()),
        json.dumps(profile.maturity.model_dump(mode="json")),
        json.dumps([c.model_dump() for c in profile.constraints]),
        json.dumps([g.model_dump() for g in profile.goals]),
        json.dumps([t.model_dump() for t in profile.tech_stack]),
        json.dumps(profile.budget.model_dump()),
    )

    return {"id": enterprise_id, "name": profile.name, "status": "created"}


@router.get("/{enterprise_id}")
async def get_enterprise(enterprise_id: str) -> dict:
    """Get an enterprise profile."""
    row = await postgres_store.fetchrow(
        "SELECT * FROM enterprises WHERE id = $1", enterprise_id
    )
    if not row:
        return {"error": "Enterprise not found"}
    return dict(row)


@router.put("/{enterprise_id}")
async def update_enterprise(enterprise_id: str, request: UpdateEnterpriseRequest) -> dict:
    """Update an enterprise profile."""
    updates = []
    params = [enterprise_id]
    idx = 2

    if request.name is not None:
        updates.append(f"name = ${idx}")
        params.append(request.name)
        idx += 1
    if request.industry is not None:
        updates.append(f"industry = ${idx}")
        params.append(request.industry.value)
        idx += 1
    if request.maturity is not None:
        updates.append(f"maturity = ${idx}")
        params.append(json.dumps(request.maturity.model_dump(mode="json")))
        idx += 1
    if request.constraints is not None:
        updates.append(f"constraints = ${idx}")
        params.append(json.dumps([c.model_dump() for c in request.constraints]))
        idx += 1
    if request.goals is not None:
        updates.append(f"goals = ${idx}")
        params.append(json.dumps([g.model_dump() for g in request.goals]))
        idx += 1
    if request.tech_stack is not None:
        updates.append(f"tech_stack = ${idx}")
        params.append(json.dumps([t.model_dump() for t in request.tech_stack]))
        idx += 1
    if request.budget is not None:
        updates.append(f"budget = ${idx}")
        params.append(json.dumps(request.budget.model_dump()))
        idx += 1

    if not updates:
        return {"error": "No fields to update"}

    updates.append("updated_at = NOW()")
    query = f"UPDATE enterprises SET {', '.join(updates)} WHERE id = $1"
    await postgres_store.execute(query, *params)

    return {"id": enterprise_id, "status": "updated"}


# --- Alerts ---


@router.get("/{enterprise_id}/alerts")
async def get_enterprise_alerts(enterprise_id: str) -> dict:
    """Get proactive alerts for an enterprise."""
    from odyssey.enterprise.alerts import alert_engine

    alerts = await alert_engine.get_alerts(enterprise_id)
    return {"enterprise_id": enterprise_id, "count": len(alerts), "alerts": alerts}


@router.post("/{enterprise_id}/alerts/check")
async def check_alerts(enterprise_id: str) -> dict:
    """Manually trigger alert check for an enterprise."""
    from odyssey.enterprise.alerts import alert_engine

    alerts = await alert_engine.check_for_alerts()
    enterprise_alerts = [a for a in alerts if a.enterprise_id == enterprise_id]
    return {
        "enterprise_id": enterprise_id,
        "new_alerts": len(enterprise_alerts),
        "alerts": [a.model_dump(mode="json") for a in enterprise_alerts],
    }


@router.post("/{enterprise_id}/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(enterprise_id: str, alert_id: str) -> dict:
    """Acknowledge an alert."""
    from odyssey.enterprise.alerts import alert_engine

    await alert_engine.acknowledge_alert(alert_id)
    return {"alert_id": alert_id, "status": "acknowledged"}


# --- Decisions ---


class RecordDecisionRequest(BaseModel):
    question: str
    chosen_option: str
    alternatives_considered: list[str] = Field(default_factory=list)
    rationale: str = ""
    decision_template_id: str | None = None


class RecordOutcomeRequest(BaseModel):
    outcome: str
    rating: int | None = None  # 1-5


@router.post("/{enterprise_id}/decisions")
async def record_decision(enterprise_id: str, request: RecordDecisionRequest) -> dict:
    """Record an architecture decision."""
    from odyssey.enterprise.decisions import Decision, decision_tracker

    decision = Decision(
        enterprise_id=enterprise_id,
        decision_template_id=request.decision_template_id,
        question=request.question,
        chosen_option=request.chosen_option,
        alternatives_considered=request.alternatives_considered,
        rationale=request.rationale,
    )
    decision_id = await decision_tracker.record_decision(decision)
    return {"id": decision_id, "status": "recorded"}


@router.post("/{enterprise_id}/decisions/{decision_id}/outcome")
async def record_decision_outcome(
    enterprise_id: str, decision_id: str, request: RecordOutcomeRequest
) -> dict:
    """Record the outcome of a past decision."""
    from odyssey.enterprise.decisions import decision_tracker

    await decision_tracker.record_outcome(decision_id, request.outcome, request.rating)
    return {"decision_id": decision_id, "status": "outcome_recorded"}


@router.get("/{enterprise_id}/decisions")
async def get_decisions(enterprise_id: str) -> dict:
    """Get all recorded decisions for an enterprise."""
    from odyssey.enterprise.decisions import decision_tracker

    decisions = await decision_tracker.get_enterprise_decisions(enterprise_id)
    return {"enterprise_id": enterprise_id, "count": len(decisions), "decisions": decisions}


@router.get("/{enterprise_id}/recommendations")
async def get_recommendations(enterprise_id: str) -> dict:
    """Get context-aware architecture recommendations for an enterprise."""
    from odyssey.agents.base import AgentQuery
    from odyssey.agents.router import agent_router

    # Route through the architect agent with enterprise context
    response = await agent_router.route(AgentQuery(
        query="What are the most important architecture decisions and improvements "
              "this enterprise should consider based on their current state, goals, and the "
              "current technology landscape?",
        enterprise_id=enterprise_id,
        altitude="strategic",
    ))
    return {
        "enterprise_id": enterprise_id,
        "agent": response.agent_name,
        "recommendations": response.content,
        "confidence": response.confidence,
        "structured_data": response.structured_data,
    }
