"""Cortex data models: gap reports, evolution proposals, governor state."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# --- Enums ---


class GapType(str, Enum):
    CAPABILITY = "capability"  # Domain demand exceeds coverage
    QUALITY = "quality"  # Agent quality is declining
    KNOWLEDGE = "knowledge"  # Stale or missing knowledge


class EvolutionType(str, Enum):
    NEW_AGENT = "new_agent"
    AGENT_RETRAIN = "agent_retrain"
    AGENT_RETIRE = "agent_retire"
    KNOWLEDGE_EXPANSION = "knowledge_expansion"
    ONTOLOGY_EXTENSION = "ontology_extension"
    SOURCE_ADDITION = "source_addition"


class BlastRadius(str, Enum):
    LOW = "low"  # Knowledge updates, source additions
    MEDIUM = "medium"  # Agent prompt updates, retraining
    HIGH = "high"  # New agents, ontology changes, agent retirement


class EvolutionOutcome(str, Enum):
    EXECUTED = "executed"
    ROLLED_BACK = "rolled_back"
    BLOCKED = "blocked"


# --- Introspector Models ---


class QueryRecord(BaseModel):
    """A single recorded query and its outcome."""
    query: str
    agent_id: str
    enterprise_id: str | None = None
    altitude: str = "tactical"
    response_quality: float | None = None  # 0-1, None if not rated
    latency_ms: int = 0
    hit_dead_end: bool = False  # True if agent returned low confidence
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    domain_signals: list[str] = Field(default_factory=list)  # Detected domains


class SystemHealthSnapshot(BaseModel):
    """Point-in-time health of the system."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    total_queries: int = 0
    avg_quality: float = 0.0
    avg_latency_ms: int = 0
    dead_end_rate: float = 0.0  # % of queries hitting dead ends
    agent_stats: dict[str, AgentHealthStats] = Field(default_factory=dict)
    knowledge_stats: KnowledgeHealthStats = Field(default_factory=lambda: KnowledgeHealthStats())
    active_agent_count: int = 0


class AgentHealthStats(BaseModel):
    """Health metrics for a single agent."""
    agent_id: str
    query_count: int = 0
    avg_quality: float = 0.0
    avg_latency_ms: int = 0
    dead_end_rate: float = 0.0
    error_rate: float = 0.0
    trend: str = "stable"  # improving, stable, declining


class KnowledgeHealthStats(BaseModel):
    """Health of the knowledge graph."""
    total_nodes: int = 0
    stale_nodes: int = 0  # Below confidence threshold
    domains_coverage: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    last_ingestion: datetime | None = None


# --- Gap Detector Models ---


class CapabilityGap(BaseModel):
    """A domain where demand exceeds current coverage."""
    domain: str
    signal_strength: float  # 0-1, how strong the demand signal is
    current_coverage: float  # 0-1, how well we handle it today
    gap_score: float  # signal_strength * (1 - current_coverage)
    evidence: list[str] = Field(default_factory=list)
    sample_queries: list[str] = Field(default_factory=list)


class QualityGap(BaseModel):
    """An agent whose quality is declining."""
    agent_id: str
    agent_name: str
    metric: str  # satisfaction, latency, dead_end_rate
    current_value: float
    target_value: float
    trend: str  # improving, stable, declining
    evidence: list[str] = Field(default_factory=list)


class KnowledgeGap(BaseModel):
    """Missing or stale knowledge in the graph."""
    domain: str
    stale_node_count: int = 0
    missing_signals: list[str] = Field(default_factory=list)  # Topics queried but not in graph
    avg_confidence: float = 0.0
    evidence: list[str] = Field(default_factory=list)


class GapReport(BaseModel):
    """Full gap analysis output from the gap detector."""
    report_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    health_snapshot: SystemHealthSnapshot = Field(default_factory=SystemHealthSnapshot)
    capability_gaps: list[CapabilityGap] = Field(default_factory=list)
    quality_gaps: list[QualityGap] = Field(default_factory=list)
    knowledge_gaps: list[KnowledgeGap] = Field(default_factory=list)

    @property
    def total_gaps(self) -> int:
        return len(self.capability_gaps) + len(self.quality_gaps) + len(self.knowledge_gaps)

    @property
    def top_gap(self) -> CapabilityGap | QualityGap | KnowledgeGap | None:
        all_scored: list[tuple[float, Any]] = []
        for g in self.capability_gaps:
            all_scored.append((g.gap_score, g))
        for g in self.quality_gaps:
            all_scored.append((abs(g.current_value - g.target_value), g))
        for g in self.knowledge_gaps:
            all_scored.append((g.stale_node_count / max(1, self.health_snapshot.knowledge_stats.total_nodes), g))
        if not all_scored:
            return None
        all_scored.sort(key=lambda x: x[0], reverse=True)
        return all_scored[0][1]


# --- Evolution Planner Models ---


class EvolutionProposal(BaseModel):
    """A concrete, executable proposal for system evolution."""
    id: str
    type: EvolutionType
    priority: int = 5  # 1 (highest) to 10 (lowest)
    rationale: str
    gap_references: list[str] = Field(default_factory=list)  # Gap report IDs
    specification: dict[str, Any] = Field(default_factory=dict)
    blast_radius: BlastRadius = BlastRadius.LOW
    rollback_plan: str = ""
    success_criteria: list[str] = Field(default_factory=list)
    estimated_impact: str = ""  # Expected improvement description
    created_at: datetime = Field(default_factory=datetime.utcnow)


# --- Governor Models ---


class GovernorLimits(BaseModel):
    """Rate limits and safety thresholds for self-evolution."""
    max_new_agents_per_week: int = 1
    max_prompt_modifications_per_day: int = 3
    max_ontology_extensions_per_day: int = 1
    max_total_agents: int = 20
    max_knowledge_growth_per_day: int = 500  # Max new nodes per day
    max_llm_spend_per_cycle_usd: float = 10.0
    quality_regression_threshold: float = 0.15  # 15% drop triggers rollback
    canary_duration_hours: int = 48
    kill_switch_active: bool = False  # When True, all evolution halts


class GovernorState(BaseModel):
    """Current state of the governor's rate limiting."""
    agents_created_this_week: int = 0
    prompts_modified_today: int = 0
    ontology_extensions_today: int = 0
    total_active_agents: int = 0
    knowledge_nodes_added_today: int = 0
    llm_spend_this_cycle_usd: float = 0.0
    last_reset_date: datetime = Field(default_factory=datetime.utcnow)
    recent_evolutions: list[str] = Field(default_factory=list)  # Last N evolution IDs


class EvolutionAuditEntry(BaseModel):
    """Immutable audit log entry for an evolution action."""
    proposal_id: str
    proposal_type: EvolutionType
    outcome: EvolutionOutcome
    rationale: str
    metrics_before: dict[str, float] = Field(default_factory=dict)
    metrics_after: dict[str, float] = Field(default_factory=dict)
    executed_at: datetime = Field(default_factory=datetime.utcnow)
    rolled_back_at: datetime | None = None
