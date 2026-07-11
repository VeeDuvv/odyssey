"""Knowledge graph ontology schema and self-expansion logic."""

from __future__ import annotations

from odyssey.storage.neo4j import neo4j_store

# Base ontology constraints and indexes
ONTOLOGY_SETUP = [
    # Uniqueness constraints
    "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Technology) REQUIRE t.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Capability) REQUIRE c.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (p:Pattern) REQUIRE p.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (b:Benchmark) REQUIRE b.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (i:Insight) REQUIRE i.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (d:DecisionTemplate) REQUIRE d.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (v:Vendor) REQUIRE v.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (cf:ComplianceFramework) REQUIRE cf.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (cp:CloudProvider) REQUIRE cp.id IS UNIQUE",
    # Indexes for common queries
    "CREATE INDEX IF NOT EXISTS FOR (t:Technology) ON (t.category)",
    "CREATE INDEX IF NOT EXISTS FOR (t:Technology) ON (t.domain)",
    "CREATE INDEX IF NOT EXISTS FOR (t:Technology) ON (t.status)",
    "CREATE INDEX IF NOT EXISTS FOR (t:Technology) ON (t.name)",
    "CREATE INDEX IF NOT EXISTS FOR (c:Capability) ON (c.domain)",
    "CREATE INDEX IF NOT EXISTS FOR (p:Pattern) ON (p.domain)",
    "CREATE INDEX IF NOT EXISTS FOR (d:DecisionTemplate) ON (d.slug)",
    "CREATE INDEX IF NOT EXISTS FOR (i:Insight) ON (i.domain)",
]


async def initialize_ontology() -> None:
    """Create all constraints and indexes in Neo4j."""
    for statement in ONTOLOGY_SETUP:
        await neo4j_store.execute_write(statement)


async def get_ontology_stats() -> dict[str, int]:
    """Get counts of each node type in the graph."""
    results = await neo4j_store.execute_read("""
        MATCH (n)
        WITH labels(n)[0] AS label, count(n) AS cnt
        RETURN label, cnt
        ORDER BY cnt DESC
    """)
    return {r["label"]: r["cnt"] for r in results}


async def get_categories() -> list[str]:
    """Get all technology categories currently in the graph."""
    results = await neo4j_store.execute_read("""
        MATCH (t:Technology)
        RETURN DISTINCT t.category AS category
        ORDER BY category
    """)
    return [r["category"] for r in results]


async def get_edge_type_counts() -> dict[str, int]:
    """Get counts of each relationship type."""
    results = await neo4j_store.execute_read("""
        MATCH ()-[r]->()
        RETURN type(r) AS rel_type, count(r) AS cnt
        ORDER BY cnt DESC
    """)
    return {r["rel_type"]: r["cnt"] for r in results}
