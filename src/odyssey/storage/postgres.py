"""Async PostgreSQL connection pool and query helpers."""

from __future__ import annotations

from typing import Any

import asyncpg

from odyssey.config import settings

SCHEMA_SQL = """
-- Agent registry
CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('core', 'dynamic')),
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('canary', 'active', 'deprecated', 'retired')),
    capabilities TEXT[] DEFAULT '{}',
    knowledge_domains TEXT[] DEFAULT '{}',
    config JSONB DEFAULT '{}',
    quality_metrics JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_evolved_at TIMESTAMPTZ DEFAULT NOW(),
    version INT DEFAULT 1
);

-- Enterprise profiles
CREATE TABLE IF NOT EXISTS enterprises (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    industry TEXT,
    profile JSONB NOT NULL DEFAULT '{}',
    maturity JSONB DEFAULT '{}',
    constraints JSONB DEFAULT '[]',
    goals JSONB DEFAULT '[]',
    tech_stack JSONB DEFAULT '[]',
    budget JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Decision log
CREATE TABLE IF NOT EXISTS decisions (
    id TEXT PRIMARY KEY,
    enterprise_id TEXT REFERENCES enterprises(id),
    decision_template_id TEXT,
    chosen_option JSONB,
    rationale TEXT,
    outcome JSONB,
    decided_at TIMESTAMPTZ DEFAULT NOW()
);

-- Telemetry (time-series)
CREATE TABLE IF NOT EXISTS telemetry (
    time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    agent_id TEXT,
    enterprise_id TEXT,
    query TEXT,
    response_quality REAL,
    latency_ms INT,
    metadata JSONB DEFAULT '{}'
);

-- Evolution audit log (immutable)
CREATE TABLE IF NOT EXISTS evolution_log (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    proposal_type TEXT NOT NULL,
    proposal JSONB NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('executed', 'rolled_back', 'blocked')),
    rationale TEXT,
    metrics_before JSONB,
    metrics_after JSONB
);

-- Convert telemetry to hypertable if TimescaleDB is available
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
        PERFORM create_hypertable('telemetry', 'time', if_not_exists => TRUE);
    END IF;
END $$;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_telemetry_time ON telemetry (time DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_agent ON telemetry (agent_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_enterprise ON telemetry (enterprise_id);
CREATE INDEX IF NOT EXISTS idx_decisions_enterprise ON decisions (enterprise_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON agents (status);
""";


class PostgresStore:
    """Async PostgreSQL connection pool."""

    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(settings.postgres_dsn, min_size=2, max_size=10)

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None

    @property
    def pool(self) -> asyncpg.Pool:
        if not self._pool:
            raise RuntimeError("PostgreSQL not connected. Call connect() first.")
        return self._pool

    async def initialize_schema(self) -> None:
        async with self.pool.acquire() as conn:
            await conn.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            await conn.execute(SCHEMA_SQL)

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetchrow(self, query: str, *args: Any) -> asyncpg.Record | None:
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def health_check(self) -> bool:
        try:
            row = await self.fetchrow("SELECT 1 AS ok")
            return row is not None
        except Exception:
            return False


postgres_store = PostgresStore()
