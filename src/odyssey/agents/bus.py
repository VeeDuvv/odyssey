"""Inter-agent message bus using Redis Streams."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from odyssey.storage.redis import redis_store

AGENT_BUS_STREAM = "odyssey:agent:bus"


class BusMessage(BaseModel):
    """Message exchanged between agents on the bus."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_agent: str
    target_agent: str | None = None  # None = broadcast
    message_type: str  # query, response, alert, insight, evolution
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class AgentBus:
    """Redis Streams-based message bus for agent communication."""

    async def initialize(self) -> None:
        """Create consumer groups for the bus."""
        await redis_store.stream_create_group(AGENT_BUS_STREAM, "agents")

    async def publish(self, message: BusMessage) -> str:
        """Publish a message to the bus."""
        data = {
            "id": message.id,
            "source_agent": message.source_agent,
            "target_agent": message.target_agent or "",
            "message_type": message.message_type,
            "payload": json.dumps(message.payload),
            "timestamp": message.timestamp.isoformat(),
        }
        return await redis_store.stream_add(AGENT_BUS_STREAM, data)

    async def consume(
        self, consumer_name: str, count: int = 10, block: int | None = 1000
    ) -> list[BusMessage]:
        """Consume messages from the bus as part of the agents group."""
        raw = await redis_store.stream_read_group(
            AGENT_BUS_STREAM, "agents", consumer_name, count=count, block=block
        )
        messages = []
        for msg_id, data in raw:
            messages.append(
                BusMessage(
                    id=data.get("id", msg_id),
                    source_agent=data["source_agent"],
                    target_agent=data.get("target_agent") or None,
                    message_type=data["message_type"],
                    payload=json.loads(data.get("payload", "{}")),
                    timestamp=datetime.fromisoformat(data["timestamp"]),
                )
            )
            await redis_store.stream_ack(AGENT_BUS_STREAM, "agents", msg_id)
        return messages


agent_bus = AgentBus()
