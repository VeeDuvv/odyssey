"""Knowledge graph CRUD operations on Neo4j."""

from __future__ import annotations

from typing import Any

from odyssey.knowledge.models import (
    BenchmarkNode,
    CapabilityNode,
    DecisionTemplateNode,
    EdgeType,
    InsightNode,
    KnowledgeEdge,
    PatternNode,
    TechnologyNode,
)
from odyssey.storage.neo4j import neo4j_store


class KnowledgeGraph:
    """Operations on the Neo4j knowledge graph."""

    # --- Technology ---

    async def create_technology(self, tech: TechnologyNode) -> None:
        query = """
        MERGE (t:Technology {id: $id})
        SET t.name = $name,
            t.category = $category,
            t.domain = $domain,
            t.vendor = $vendor,
            t.license = $license,
            t.current_version = $current_version,
            t.status = $status,
            t.description = $description,
            t.confidence = $confidence,
            t.last_verified = datetime(),
            t.updated_at = datetime()
        """
        await neo4j_store.execute_write(query, {
            "id": tech.id,
            "name": tech.name,
            "category": tech.category,
            "domain": tech.domain.value,
            "vendor": tech.vendor,
            "license": tech.license.value if tech.license else None,
            "current_version": tech.current_version,
            "status": tech.status.value,
            "description": tech.description,
            "confidence": tech.confidence.confidence,
        })

    async def get_technology(self, tech_id: str) -> dict[str, Any] | None:
        results = await neo4j_store.execute_read(
            "MATCH (t:Technology {id: $id}) RETURN t", {"id": tech_id}
        )
        return results[0]["t"] if results else None

    async def search_technologies(
        self,
        query: str | None = None,
        category: str | None = None,
        domain: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        conditions = []
        params: dict[str, Any] = {"limit": limit}

        if query:
            conditions.append(
                "(toLower(t.name) CONTAINS toLower($query) OR "
                "toLower(t.description) CONTAINS toLower($query))"
            )
            params["query"] = query
        if category:
            conditions.append("t.category = $category")
            params["category"] = category
        if domain:
            conditions.append("t.domain = $domain")
            params["domain"] = domain

        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        cypher = f"""
        MATCH (t:Technology)
        {where}
        RETURN t
        ORDER BY t.confidence DESC, t.name
        LIMIT $limit
        """
        results = await neo4j_store.execute_read(cypher, params)
        return [r["t"] for r in results]

    async def get_technology_with_relationships(
        self, tech_id: str
    ) -> dict[str, Any] | None:
        results = await neo4j_store.execute_read(
            """
            MATCH (t:Technology {id: $id})
            OPTIONAL MATCH (t)-[r]->(related)
            OPTIONAL MATCH (incoming)-[ri]->(t)
            RETURN t,
                   collect(DISTINCT {type: type(r), target: related, props: properties(r)}) AS outgoing,
                   collect(DISTINCT {type: type(ri), source: incoming, props: properties(ri)}) AS incoming
            """,
            {"id": tech_id},
        )
        if not results:
            return None
        row = results[0]
        return {
            "technology": row["t"],
            "outgoing_relationships": [r for r in row["outgoing"] if r["target"] is not None],
            "incoming_relationships": [r for r in row["incoming"] if r["source"] is not None],
        }

    async def compare_technologies(
        self, tech_ids: list[str]
    ) -> list[dict[str, Any]]:
        results = await neo4j_store.execute_read(
            """
            MATCH (t:Technology) WHERE t.id IN $ids
            OPTIONAL MATCH (t)-[:IMPLEMENTS]->(c:Capability)
            OPTIONAL MATCH (t)-[:HOSTED_ON]->(cloud)
            OPTIONAL MATCH (t)-[:INTEGRATES_WITH]->(integration)
            OPTIONAL MATCH (b:Benchmark {technology_id: t.id})
            RETURN t,
                   collect(DISTINCT c.name) AS capabilities,
                   collect(DISTINCT cloud.name) AS cloud_providers,
                   collect(DISTINCT integration.name) AS integrations,
                   collect(DISTINCT {metric: b.metric, value: b.value, conditions: b.conditions}) AS benchmarks
            """,
            {"ids": tech_ids},
        )
        return results

    # --- Capability ---

    async def create_capability(self, cap: CapabilityNode) -> None:
        await neo4j_store.execute_write(
            """
            MERGE (c:Capability {id: $id})
            SET c.name = $name, c.description = $description, c.domain = $domain
            """,
            {"id": cap.id, "name": cap.name, "description": cap.description, "domain": cap.domain.value},
        )

    # --- Pattern ---

    async def create_pattern(self, pattern: PatternNode) -> None:
        await neo4j_store.execute_write(
            """
            MERGE (p:Pattern {id: $id})
            SET p.name = $name, p.description = $description, p.domain = $domain,
                p.when_to_use = $when_to_use, p.when_not_to_use = $when_not_to_use
            """,
            {
                "id": pattern.id,
                "name": pattern.name,
                "description": pattern.description,
                "domain": pattern.domain.value,
                "when_to_use": pattern.when_to_use,
                "when_not_to_use": pattern.when_not_to_use,
            },
        )

    # --- Benchmark ---

    async def create_benchmark(self, bench: BenchmarkNode) -> None:
        import json

        await neo4j_store.execute_write(
            """
            MERGE (b:Benchmark {id: $id})
            SET b.name = $name, b.technology_id = $technology_id,
                b.metric = $metric, b.value = $value,
                b.conditions = $conditions, b.confidence = $confidence
            """,
            {
                "id": bench.id,
                "name": bench.name,
                "technology_id": bench.technology_id,
                "metric": bench.metric,
                "value": bench.value,
                "conditions": json.dumps(bench.conditions),
                "confidence": bench.confidence,
            },
        )

    # --- Insight ---

    async def create_insight(self, insight: InsightNode) -> None:
        await neo4j_store.execute_write(
            """
            MERGE (i:Insight {id: $id})
            SET i.content = $content, i.domain = $domain,
                i.impacted_technologies = $impacted_technologies,
                i.published_at = datetime($published_at),
                i.confidence = $confidence
            """,
            {
                "id": insight.id,
                "content": insight.content,
                "domain": insight.domain.value,
                "impacted_technologies": insight.impacted_technologies,
                "published_at": insight.published_at.isoformat(),
                "confidence": insight.confidence,
            },
        )

    # --- Decision Template ---

    async def create_decision_template(self, dt: DecisionTemplateNode) -> None:
        await neo4j_store.execute_write(
            """
            MERGE (d:DecisionTemplate {id: $id})
            SET d.slug = $slug, d.question = $question, d.domain = $domain,
                d.altitude = $altitude, d.option_ids = $option_ids,
                d.evaluation_criteria = $evaluation_criteria,
                d.reversibility = $reversibility,
                d.decision_drivers = $decision_drivers
            """,
            {
                "id": dt.id,
                "slug": dt.slug,
                "question": dt.question,
                "domain": dt.domain.value,
                "altitude": dt.altitude,
                "option_ids": dt.option_ids,
                "evaluation_criteria": dt.evaluation_criteria,
                "reversibility": dt.reversibility,
                "decision_drivers": dt.decision_drivers,
            },
        )

    # --- Edges ---

    async def create_edge(self, edge: KnowledgeEdge) -> None:
        import json

        query = f"""
        MATCH (source {{id: $source_id}})
        MATCH (target {{id: $target_id}})
        MERGE (source)-[r:{edge.edge_type.value}]->(target)
        SET r.confidence = $confidence,
            r.properties = $properties,
            r.created_at = datetime()
        """
        await neo4j_store.execute_write(query, {
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "confidence": edge.confidence,
            "properties": json.dumps(edge.properties),
        })

    # --- Traversal queries ---

    async def find_options_for_decision(
        self, decision_slug: str
    ) -> list[dict[str, Any]]:
        return await neo4j_store.execute_read(
            """
            MATCH (d:DecisionTemplate {slug: $slug})
            MATCH (t:Technology) WHERE t.id IN d.option_ids
            OPTIONAL MATCH (t)-[:IMPLEMENTS]->(c:Capability)
            OPTIONAL MATCH (t)-[:HOSTED_ON]->(cloud)
            RETURN t, collect(DISTINCT c.name) AS capabilities,
                   collect(DISTINCT cloud.name) AS cloud_providers
            """,
            {"slug": decision_slug},
        )

    async def find_related_decisions(
        self, technology_id: str
    ) -> list[dict[str, Any]]:
        return await neo4j_store.execute_read(
            """
            MATCH (d:DecisionTemplate)
            WHERE $tech_id IN d.option_ids
            RETURN d
            """,
            {"tech_id": technology_id},
        )

    async def get_graph_stats(self) -> dict[str, int]:
        results = await neo4j_store.execute_read("""
            MATCH (n)
            RETURN labels(n)[0] AS label, count(n) AS count
            ORDER BY count DESC
        """)
        return {r["label"]: r["count"] for r in results}


knowledge_graph = KnowledgeGraph()
