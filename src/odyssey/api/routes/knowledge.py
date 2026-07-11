"""Knowledge graph API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from odyssey.api.middleware.auth import verify_api_key
from odyssey.knowledge.graph import knowledge_graph
from odyssey.knowledge.ontology import get_ontology_stats

router = APIRouter(
    prefix="/api/knowledge", tags=["knowledge"], dependencies=[Depends(verify_api_key)]
)


@router.get("/search")
async def search_knowledge(
    q: str = Query(..., description="Search query"),
    category: str | None = Query(None, description="Filter by category"),
    domain: str | None = Query(None, description="Filter by domain"),
    limit: int = Query(20, ge=1, le=100),
) -> dict:
    """Search the knowledge graph for technologies."""
    results = await knowledge_graph.search_technologies(
        query=q, category=category, domain=domain, limit=limit
    )
    return {"query": q, "count": len(results), "results": results}


@router.get("/technology/{tech_id}")
async def get_technology(tech_id: str) -> dict:
    """Get a technology with all its relationships."""
    result = await knowledge_graph.get_technology_with_relationships(tech_id)
    if not result:
        return {"error": "Technology not found"}
    return result


@router.get("/compare")
async def compare_technologies(
    technologies: str = Query(
        ..., description="Comma-separated technology IDs to compare"
    ),
) -> dict:
    """Compare multiple technologies side by side."""
    tech_ids = [t.strip() for t in technologies.split(",")]
    results = await knowledge_graph.compare_technologies(tech_ids)
    return {"technologies": tech_ids, "comparison": results}


@router.get("/stats")
async def graph_stats() -> dict:
    """Get knowledge graph statistics."""
    node_stats = await knowledge_graph.get_graph_stats()
    ontology_stats = await get_ontology_stats()
    return {"nodes": node_stats, "ontology": ontology_stats}
