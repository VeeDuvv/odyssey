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

    try:
        response = await agent_router.route(agent_query)
    except Exception as e:
        # Never let the chat endpoint 500 — always return something useful
        error_msg = str(e)
        if "credit balance" in error_msg or "api_key" in error_msg.lower():
            content = (
                "Odyssey's AI engine is currently unavailable — your Anthropic API account "
                "needs credits. Please visit console.anthropic.com to add credits.\n\n"
                "In the meantime, you can explore the Knowledge Graph page to browse "
                "technologies, or check the Cortex page to see the self-evolution engine."
            )
        else:
            content = f"Something went wrong processing your query. Error: {error_msg}"
        return ChatResponse(
            content=content,
            agent="System",
            confidence=0.0,
            metadata={"error": True},
        )

    return ChatResponse(
        content=response.content,
        agent=response.agent_name,
        confidence=response.confidence,
        sources=response.sources,
        follow_up_questions=response.follow_up_questions,
        metadata=response.metadata,
    )
