# Odyssey

AI-native, self-evolving enterprise AI & Data architecture navigator.

## Tech Stack
- Python 3.12+, uv package manager
- FastAPI (async API)
- Neo4j (knowledge graph)
- PostgreSQL 16+ with TimescaleDB (enterprise context, agent registry, telemetry)
- Redis Streams (agent message bus, caching)
- Anthropic Claude (primary LLM)

## Project Structure
- `src/odyssey/` — main package
  - `storage/` — database connection wrappers (Neo4j, PostgreSQL, Redis)
  - `knowledge/` — knowledge graph, ontology, confidence scoring, source ingestion
  - `enterprise/` — enterprise profiles, maturity model, constraints, goals
  - `agents/` — agent base class, registry, router, core agents, dynamic agents
  - `cortex/` — self-evolution: introspector, gap detector, evolution planner, governor
  - `api/` — FastAPI app, routes, middleware
  - `llm/` — LLM client abstraction
- `seeds/` — bootstrap ontology and knowledge data
- `scripts/` — bootstrap and setup scripts
- `tests/` — unit, integration, evolution tests

## Conventions
- Use Pydantic models for all data structures
- Async everywhere — all DB operations, API handlers, agent methods
- Type hints on all functions
- Neo4j for knowledge graph, PostgreSQL for everything else
- Redis Streams for inter-agent communication
- All knowledge assertions carry confidence scores and temporal metadata
