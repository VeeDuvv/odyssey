"""Chat route — conversational interface to Odyssey."""

from __future__ import annotations

from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends

from odyssey.agents.base import AgentQuery
from odyssey.agents.router import agent_router
from odyssey.api.middleware.auth import verify_api_key

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(verify_api_key)])


class ChatRequest(BaseModel):
    query: str
    enterprise_id: str | None = None
    altitude: str = "tactical"
    context: dict = Field(default_factory=dict)


class ChatResponse(BaseModel):
    content: str
    agent: str
    confidence: float
    sources: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """Send a query to Odyssey and get an AI-powered architecture recommendation."""
    agent_query = AgentQuery(
        query=request.query,
        enterprise_id=request.enterprise_id,
        altitude=request.altitude,
        context=request.context,
    )

    response = await agent_router.route(agent_query)

    return ChatResponse(
        content=response.content,
        agent=response.agent_name,
        confidence=response.confidence,
        sources=response.sources,
        follow_up_questions=response.follow_up_questions,
        metadata=response.metadata,
    )
