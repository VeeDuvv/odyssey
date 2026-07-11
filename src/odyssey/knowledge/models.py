"""Knowledge graph node and edge models."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---


class KnowledgeDomain(str, Enum):
    DATA_PLATFORMS = "data_platforms"
    ML_INFRASTRUCTURE = "ml_infrastructure"
    AI_MODELS = "ai_models"
    AI_PATTERNS = "ai_patterns"
    DATA_GOVERNANCE = "data_governance"
    CLOUD_DEPLOYMENT = "cloud_deployment"
    ORGANIZATIONAL = "organizational"


class TechnologyStatus(str, Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    MATURE = "mature"
    DECLINING = "declining"
    DEPRECATED = "deprecated"


class LicenseType(str, Enum):
    OPEN_SOURCE = "open_source"
    SOURCE_AVAILABLE = "source_available"
    PROPRIETARY = "proprietary"
    FREEMIUM = "freemium"


class AdoptionTrend(str, Enum):
    ACCELERATING = "accelerating"
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"


class EdgeType(str, Enum):
    IMPLEMENTS = "IMPLEMENTS"
    COMPETES_WITH = "COMPETES_WITH"
    INTEGRATES_WITH = "INTEGRATES_WITH"
    REQUIRES = "REQUIRES"
    SUPERSEDES = "SUPERSEDES"
    HOSTED_ON = "HOSTED_ON"
    ENABLES = "ENABLES"
    MEASURED_BY = "MEASURED_BY"
    ADDRESSES = "ADDRESSES"
    OPTION_IN = "OPTION_IN"
    DEPENDS_ON = "DEPENDS_ON"
    IMPACTS = "IMPACTS"
    COMPLIANT_WITH = "COMPLIANT_WITH"
    SKILL_REQUIRED = "SKILL_REQUIRED"
    EVOLVED_FROM = "EVOLVED_FROM"


# --- Source & Confidence ---


class Source(BaseModel):
    type: str  # official_docs, benchmark, community, news, expert_opinion, inferred
    url: str | None = None
    retrieved_at: datetime = Field(default_factory=datetime.utcnow)
    trust_level: float = 0.5  # 0-1


class ConfidenceMetadata(BaseModel):
    confidence: float = 0.5  # 0-1 base confidence
    sources: list[Source] = Field(default_factory=list)
    first_asserted: datetime = Field(default_factory=datetime.utcnow)
    last_verified: datetime = Field(default_factory=datetime.utcnow)
    valid_from: datetime = Field(default_factory=datetime.utcnow)
    valid_until: datetime | None = None
    contradicted_by: list[str] = Field(default_factory=list)

    # Domain-specific halflife in days for confidence decay
    halflife_days: int = 180

    def effective_confidence(self, as_of: datetime | None = None) -> float:
        now = as_of or datetime.utcnow()
        days_since = (now - self.last_verified).days
        decay = max(0.3, 1.0 - (days_since / self.halflife_days) * 0.5)
        return self.confidence * decay


# Domain-specific halflives
DOMAIN_HALFLIFE: dict[KnowledgeDomain, int] = {
    KnowledgeDomain.AI_MODELS: 90,
    KnowledgeDomain.AI_PATTERNS: 120,
    KnowledgeDomain.ML_INFRASTRUCTURE: 150,
    KnowledgeDomain.DATA_PLATFORMS: 180,
    KnowledgeDomain.CLOUD_DEPLOYMENT: 180,
    KnowledgeDomain.ORGANIZATIONAL: 270,
    KnowledgeDomain.DATA_GOVERNANCE: 365,
}


# --- Trend Signal ---


class TrendSignal(BaseModel):
    adoption_trend: AdoptionTrend = AdoptionTrend.STABLE
    github_stars: int | None = None
    github_stars_trend: int | None = None  # monthly delta
    last_updated: datetime = Field(default_factory=datetime.utcnow)


# --- Node Types ---


class TechnologyNode(BaseModel):
    id: str
    name: str
    category: str  # vector_database, streaming_platform, etc.
    domain: KnowledgeDomain
    vendor: str | None = None
    license: LicenseType | None = None
    current_version: str | None = None
    release_date: datetime | None = None
    status: TechnologyStatus = TechnologyStatus.GROWING
    description: str = ""
    trend: TrendSignal = Field(default_factory=TrendSignal)
    confidence: ConfidenceMetadata = Field(default_factory=ConfidenceMetadata)


class CapabilityNode(BaseModel):
    id: str
    name: str  # e.g., "real-time-feature-serving"
    description: str = ""
    domain: KnowledgeDomain


class PatternNode(BaseModel):
    id: str
    name: str  # e.g., "RAG", "Lambda Architecture"
    description: str = ""
    when_to_use: list[str] = Field(default_factory=list)
    when_not_to_use: list[str] = Field(default_factory=list)
    anti_patterns: list[str] = Field(default_factory=list)
    domain: KnowledgeDomain = KnowledgeDomain.AI_PATTERNS


class BenchmarkNode(BaseModel):
    id: str
    name: str
    technology_id: str
    metric: str  # p99_latency_ms, throughput_qps, recall_at_10
    value: float
    conditions: dict[str, Any] = Field(default_factory=dict)
    measured_at: datetime = Field(default_factory=datetime.utcnow)
    source: Source | None = None
    confidence: float = 0.5


class InsightNode(BaseModel):
    id: str
    content: str  # Natural language description of the insight
    domain: KnowledgeDomain
    impacted_technologies: list[str] = Field(default_factory=list)
    published_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    source: Source | None = None
    confidence: float = 0.7


class DecisionTemplateNode(BaseModel):
    id: str
    slug: str  # e.g., "choose-vector-database"
    question: str  # Natural language framing
    domain: KnowledgeDomain
    altitude: str  # strategic, tactical, operational
    option_ids: list[str] = Field(default_factory=list)  # Technology IDs
    evaluation_criteria: list[str] = Field(default_factory=list)
    reversibility: str = "reversible_with_effort"
    decision_drivers: list[str] = Field(default_factory=list)


# --- Edge Models ---


class KnowledgeEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: EdgeType
    properties: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.7
    created_at: datetime = Field(default_factory=datetime.utcnow)
