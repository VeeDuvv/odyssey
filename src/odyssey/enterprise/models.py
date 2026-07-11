"""Enterprise context models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Industry(str, Enum):
    FINANCIAL_SERVICES = "financial_services"
    HEALTHCARE = "healthcare"
    RETAIL = "retail"
    MANUFACTURING = "manufacturing"
    TECHNOLOGY = "technology"
    MEDIA = "media"
    ENERGY = "energy"
    GOVERNMENT = "government"
    EDUCATION = "education"
    OTHER = "other"


class MaturityLevel(int, Enum):
    L1_EXPLORING = 1
    L2_EXPERIMENTING = 2
    L3_SCALING = 3
    L4_OPTIMIZING = 4
    L5_LEADING = 5


class ConstraintType(str, Enum):
    REGULATORY = "regulatory"
    BUDGET = "budget"
    TALENT = "talent"
    TIMELINE = "timeline"
    VENDOR_LOCK = "vendor_lock"
    LEGACY_SYSTEM = "legacy_system"
    DATA_RESIDENCY = "data_residency"


class ConstraintSeverity(str, Enum):
    HARD = "hard"  # non-negotiable
    SOFT = "soft"  # prefer to avoid


class GoalPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TimeHorizon(str, Enum):
    NOW = "now"
    NEXT_QUARTER = "next_quarter"
    NEXT_YEAR = "next_year"
    LONG_TERM = "long_term"


class CostSensitivity(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# --- Component Models ---


class ScaleProfile(BaseModel):
    data_volume_gb: float = 0
    daily_ingest_gb: float = 0
    query_volume_per_day: int = 0
    ml_models_in_production: int = 0
    embedding_count: int = 0
    concurrent_users: int = 0
    regions: list[str] = Field(default_factory=list)


class MaturityAssessment(BaseModel):
    overall: MaturityLevel = MaturityLevel.L1_EXPLORING
    data_engineering: MaturityLevel = MaturityLevel.L1_EXPLORING
    ml_ops: MaturityLevel = MaturityLevel.L1_EXPLORING
    gen_ai: MaturityLevel = MaturityLevel.L1_EXPLORING
    governance: MaturityLevel = MaturityLevel.L1_EXPLORING
    cloud_native: MaturityLevel = MaturityLevel.L1_EXPLORING
    assessed_at: datetime = Field(default_factory=datetime.utcnow)


class Constraint(BaseModel):
    type: ConstraintType
    description: str
    severity: ConstraintSeverity = ConstraintSeverity.SOFT
    details: dict[str, Any] = Field(default_factory=dict)


class StrategicGoal(BaseModel):
    id: str
    description: str
    time_horizon: TimeHorizon = TimeHorizon.NEXT_YEAR
    priority: GoalPriority = GoalPriority.MEDIUM
    measurable_outcome: str = ""
    related_domains: list[str] = Field(default_factory=list)


class TechStackComponent(BaseModel):
    technology_id: str  # FK to Technology node in knowledge graph
    role: str  # What it does in their stack
    version: str = ""
    deployment_type: str = "managed"  # managed, self_hosted, hybrid
    satisfaction: int = 3  # 1-5
    pain_points: list[str] = Field(default_factory=list)


class BudgetEnvelope(BaseModel):
    annual_infra_usd: float = 0
    annual_tooling_usd: float = 0
    annual_team_usd: float = 0
    cloud_spend_trend: str = "stable"  # growing, stable, shrinking
    cost_sensitivity: CostSensitivity = CostSensitivity.MEDIUM


# --- Enterprise Profile ---


class EnterpriseProfile(BaseModel):
    id: str
    name: str
    industry: Industry = Industry.OTHER
    scale: ScaleProfile = Field(default_factory=ScaleProfile)
    maturity: MaturityAssessment = Field(default_factory=MaturityAssessment)
    constraints: list[Constraint] = Field(default_factory=list)
    goals: list[StrategicGoal] = Field(default_factory=list)
    tech_stack: list[TechStackComponent] = Field(default_factory=list)
    budget: BudgetEnvelope = Field(default_factory=BudgetEnvelope)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
