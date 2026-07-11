"""FastAPI application — the entry point for Odyssey's API."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from odyssey.agents.bus import agent_bus
from odyssey.agents.core.architect import ArchitectAgent
from odyssey.agents.core.cartographer import CartographerAgent
from odyssey.agents.core.chronicler import ChroniclerAgent
from odyssey.agents.core.navigator import NavigatorAgent
from odyssey.agents.core.sentinel import SentinelAgent
from odyssey.agents.registry import agent_registry
from odyssey.api.middleware.telemetry import TelemetryMiddleware
from odyssey.api.routes import admin, chat, enterprise, knowledge
from odyssey.knowledge.ontology import initialize_ontology
from odyssey.storage.neo4j import neo4j_store
from odyssey.storage.postgres import postgres_store
from odyssey.storage.redis import redis_store


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    # Connect to all stores
    await neo4j_store.connect()
    await postgres_store.connect()
    await redis_store.connect()

    # Initialize schemas
    await postgres_store.initialize_schema()
    await initialize_ontology()

    # Initialize message bus
    await agent_bus.initialize()

    # Register core agents
    navigator = NavigatorAgent()
    cartographer = CartographerAgent()
    sentinel = SentinelAgent()
    architect = ArchitectAgent()
    chronicler = ChroniclerAgent()

    for agent in [navigator, cartographer, sentinel, architect, chronicler]:
        agent_registry.register(agent)
        await agent_registry.persist(agent)

    yield

    # Shutdown
    await neo4j_store.close()
    await postgres_store.close()
    await redis_store.close()


app = FastAPI(
    title="Odyssey",
    description="AI-native, self-evolving enterprise AI & Data architecture navigator",
    version="0.1.0",
    lifespan=lifespan,
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TelemetryMiddleware)

# Routes
app.include_router(chat.router)
app.include_router(knowledge.router)
app.include_router(enterprise.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    """Health check — verifies all service connections."""
    neo4j_ok = await neo4j_store.health_check()
    postgres_ok = await postgres_store.health_check()
    redis_ok = await redis_store.health_check()

    healthy = neo4j_ok and postgres_ok and redis_ok
    return {
        "status": "healthy" if healthy else "degraded",
        "services": {
            "neo4j": "up" if neo4j_ok else "down",
            "postgres": "up" if postgres_ok else "down",
            "redis": "up" if redis_ok else "down",
        },
        "agents": {
            agent.name: agent.definition.status
            for agent in agent_registry.get_all()
        },
    }
