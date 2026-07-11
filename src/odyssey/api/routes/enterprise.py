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
