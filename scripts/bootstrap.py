"""Bootstrap script: initializes schemas, ontology, and seeds the knowledge graph."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from odyssey.knowledge.graph import knowledge_graph
from odyssey.knowledge.models import (
    CapabilityNode,
    ConfidenceMetadata,
    DOMAIN_HALFLIFE,
    DecisionTemplateNode,
    EdgeType,
    KnowledgeDomain,
    KnowledgeEdge,
    LicenseType,
    PatternNode,
    Source,
    TechnologyNode,
    TechnologyStatus,
)
from odyssey.knowledge.ontology import initialize_ontology
from odyssey.storage.neo4j import neo4j_store
from odyssey.storage.postgres import postgres_store
from odyssey.storage.redis import redis_store


SEEDS_DIR = Path(__file__).parent.parent / "seeds"


async def bootstrap() -> None:
    print("Odyssey Bootstrap")
    print("=" * 50)

    # 1. Connect to all stores
    print("\n[1/5] Connecting to stores...")
    await neo4j_store.connect()
    await postgres_store.connect()
    await redis_store.connect()
    print("  Neo4j: connected")
    print("  PostgreSQL: connected")
    print("  Redis: connected")

    # 2. Initialize PostgreSQL schema
    print("\n[2/5] Initializing PostgreSQL schema...")
    await postgres_store.initialize_schema()
    print("  Schema created (agents, enterprises, decisions, telemetry, evolution_log)")

    # 3. Initialize Neo4j ontology
    print("\n[3/5] Initializing Neo4j ontology...")
    await initialize_ontology()
    print("  Constraints and indexes created")

    # 4. Seed knowledge graph
    print("\n[4/5] Seeding knowledge graph...")
    seeds_file = SEEDS_DIR / "knowledge_seeds.json"
    if not seeds_file.exists():
        print("  WARNING: seeds/knowledge_seeds.json not found, skipping")
    else:
        with open(seeds_file) as f:
            seeds = json.load(f)
        await seed_knowledge(seeds)

    # 5. Verify
    print("\n[5/5] Verifying...")
    from odyssey.knowledge.ontology import get_ontology_stats

    stats = await get_ontology_stats()
    print(f"  Knowledge graph nodes: {stats}")

    neo4j_ok = await neo4j_store.health_check()
    pg_ok = await postgres_store.health_check()
    redis_ok = await redis_store.health_check()
    print(f"  Health: Neo4j={'OK' if neo4j_ok else 'FAIL'}, "
          f"PostgreSQL={'OK' if pg_ok else 'FAIL'}, "
          f"Redis={'OK' if redis_ok else 'FAIL'}")

    # Cleanup
    await neo4j_store.close()
    await postgres_store.close()
    await redis_store.close()

    print("\nBootstrap complete!")


async def seed_knowledge(seeds: dict) -> None:
    """Seed the knowledge graph from the seeds JSON."""
    source = Source(type="official_docs", url=None, trust_level=0.9)

    # Technologies
    tech_count = 0
    for t in seeds.get("technologies", []):
        domain = KnowledgeDomain(t["domain"])
        tech = TechnologyNode(
            id=t["id"],
            name=t["name"],
            category=t["category"],
            domain=domain,
            vendor=t.get("vendor"),
            license=LicenseType(t["license"]) if t.get("license") else None,
            status=TechnologyStatus(t.get("status", "growing")),
            description=t.get("description", ""),
            confidence=ConfidenceMetadata(
                confidence=0.9,
                sources=[source],
                halflife_days=DOMAIN_HALFLIFE.get(domain, 180),
            ),
        )
        await knowledge_graph.create_technology(tech)
        tech_count += 1
    print(f"  Technologies: {tech_count} seeded")

    # Capabilities
    cap_count = 0
    for c in seeds.get("capabilities", []):
        cap = CapabilityNode(
            id=c["id"],
            name=c["name"],
            domain=KnowledgeDomain(c["domain"]),
            description=c.get("description", ""),
        )
        await knowledge_graph.create_capability(cap)
        cap_count += 1
    print(f"  Capabilities: {cap_count} seeded")

    # Patterns
    pattern_count = 0
    for p in seeds.get("patterns", []):
        pattern = PatternNode(
            id=p["id"],
            name=p["name"],
            domain=KnowledgeDomain(p.get("domain", "ai_patterns")),
            description=p.get("description", ""),
            when_to_use=p.get("when_to_use", []),
            when_not_to_use=p.get("when_not_to_use", []),
        )
        await knowledge_graph.create_pattern(pattern)
        pattern_count += 1
    print(f"  Patterns: {pattern_count} seeded")

    # Decision Templates
    dt_count = 0
    for dt in seeds.get("decision_templates", []):
        template = DecisionTemplateNode(
            id=dt["id"],
            slug=dt["slug"],
            question=dt["question"],
            domain=KnowledgeDomain(dt["domain"]),
            altitude=dt["altitude"],
            option_ids=dt.get("option_ids", []),
            evaluation_criteria=dt.get("evaluation_criteria", []),
            reversibility=dt.get("reversibility", "reversible_with_effort"),
            decision_drivers=dt.get("decision_drivers", []),
        )
        await knowledge_graph.create_decision_template(template)
        dt_count += 1
    print(f"  Decision Templates: {dt_count} seeded")

    # Relationships
    rel_count = 0
    for r in seeds.get("relationships", []):
        try:
            edge_type = EdgeType(r["type"])
        except ValueError:
            continue
        edge = KnowledgeEdge(
            source_id=r["source"],
            target_id=r["target"],
            edge_type=edge_type,
            properties=r.get("properties", {}),
            confidence=0.9,
        )
        await knowledge_graph.create_edge(edge)
        rel_count += 1
    print(f"  Relationships: {rel_count} seeded")


if __name__ == "__main__":
    asyncio.run(bootstrap())
