# Odyssey

AI-native, self-evolving enterprise AI & Data architecture navigator.

Odyssey is a living service that helps enterprises navigate AI and Data architecture decisions. It continuously maintains a knowledge graph of the technology landscape, understands each enterprise's unique context, and provides actionable architecture recommendations — from CTO to platform engineer.

## Quick Start

```bash
# Start infrastructure
docker-compose up -d

# Install dependencies
uv sync

# Bootstrap (initialize schemas + seed knowledge)
uv run python scripts/bootstrap.py

# Start API server
uv run uvicorn odyssey.api.app:app --reload
```

## Architecture

See the [architecture plan](docs/architecture/overview.md) for full details.
