"""Base agent class that all Odyssey agents implement."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentQuery(BaseModel):
    """Input to an agent."""

    query: str
    enterprise_id: str | None = None
    altitude: str = "tactical"  # strategic, tactical, operational
    context: dict[str, Any] = Field(default_factory=dict)
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class AgentResponse(BaseModel):
    """Output from an agent."""

    agent_id: str
    agent_name: str
    content: str
    structured_data: dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.7
    sources: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentDefinition(BaseModel):
    """Metadata describing an agent's capabilities."""

    id: str
    name: str
    type: str = "core"  # core or dynamic
    status: str = "active"  # canary, active, deprecated, retired
    capabilities: list[str] = Field(default_factory=list)
    knowledge_domains: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)
    quality_metrics: dict[str, float] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_evolved_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1


class BaseAgent(ABC):
    """Abstract base class for all Odyssey agents."""

    def __init__(self, definition: AgentDefinition) -> None:
        self.definition = definition

    @property
    def id(self) -> str:
        return self.definition.id

    @property
    def name(self) -> str:
        return self.definition.name

    @abstractmethod
    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process a query and return a response."""
        ...

    def can_handle(self, query: AgentQuery) -> float:
        """Return a score (0-1) for how well this agent can handle the query.

        Override in subclasses for domain-specific routing.
        Default returns 0.1 (low confidence, acts as fallback).
        """
        return 0.1

    def _make_response(self, content: str, **kwargs: Any) -> AgentResponse:
        """Helper to create an AgentResponse with common fields."""
        return AgentResponse(
            agent_id=self.id,
            agent_name=self.name,
            content=content,
            **kwargs,
        )
