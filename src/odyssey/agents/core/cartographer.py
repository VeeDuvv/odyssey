"""Cartographer: maintains the knowledge graph by ingesting and extracting from sources."""

from __future__ import annotations

import uuid
from datetime import datetime

from odyssey.agents.base import AgentDefinition, AgentQuery, AgentResponse, BaseAgent
from odyssey.knowledge.graph import knowledge_graph
from odyssey.knowledge.models import (
    CapabilityNode,
    ConfidenceMetadata,
    EdgeType,
    KnowledgeDomain,
    KnowledgeEdge,
    LicenseType,
    Source,
    TechnologyNode,
    TechnologyStatus,
)
from odyssey.llm.client import llm_client

EXTRACTION_PROMPT = """Analyze the following content and extract AI/Data technology entities and their relationships.

For each technology found, extract:
- name: official name
- category: one of (database, vector_database, streaming_platform, compute_engine, orchestrator,
  experiment_tracker, feature_store, model_registry, serving_platform, training_platform,
  monitoring_tool, foundation_model, agent_framework, guardrail, governance_platform,
  data_quality_tool, catalog_tool, cloud_provider, container_platform, embedding_model)
- domain: one of (data_platforms, ml_infrastructure, ai_models, ai_patterns, data_governance,
  cloud_deployment, organizational)
- vendor: company or org behind it
- license: open_source, source_available, proprietary, or freemium
- status: emerging, growing, mature, declining, or deprecated
- description: 1-2 sentence description

For relationships between technologies, extract:
- source: technology name
- target: technology name
- type: one of (COMPETES_WITH, INTEGRATES_WITH, REQUIRES, SUPERSEDES, HOSTED_ON, IMPLEMENTS)

Content to analyze:
{content}

Respond as JSON with keys "technologies" (list) and "relationships" (list).
"""


class CartographerAgent(BaseAgent):
    """Maintains the knowledge graph by ingesting sources and extracting entities."""

    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="cartographer",
                name="Cartographer",
                type="core",
                capabilities=["knowledge_ingestion", "entity_extraction", "ontology_expansion"],
                knowledge_domains=[
                    "data_platforms", "ml_infrastructure", "ai_models",
                    "ai_patterns", "data_governance", "cloud_deployment",
                ],
            )
        )

    def can_handle(self, query: AgentQuery) -> float:
        q = query.query.lower()
        if any(kw in q for kw in ["ingest", "add knowledge", "learn about", "update knowledge"]):
            return 0.9
        return 0.1

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process a knowledge ingestion request."""
        content = query.context.get("content", query.query)
        source_url = query.context.get("source_url")

        extracted = await self._extract_entities(content)
        stats = await self._merge_into_graph(extracted, source_url)

        return self._make_response(
            content=f"Ingested knowledge: {stats['technologies_added']} technologies, "
            f"{stats['relationships_added']} relationships added/updated.",
            structured_data=stats,
            confidence=0.8,
        )

    async def _extract_entities(self, content: str) -> dict:
        """Use LLM to extract technology entities and relationships from content."""
        return await llm_client.generate_structured(
            prompt=EXTRACTION_PROMPT.format(content=content[:8000]),
        )

    async def _merge_into_graph(
        self, extracted: dict, source_url: str | None = None
    ) -> dict:
        """Merge extracted entities into the knowledge graph."""
        techs_added = 0
        rels_added = 0
        name_to_id: dict[str, str] = {}

        source = Source(
            type="community" if not source_url else "official_docs",
            url=source_url,
        )

        for tech_data in extracted.get("technologies", []):
            tech_id = tech_data.get("name", "").lower().replace(" ", "-").replace(".", "-")
            if not tech_id:
                continue

            name_to_id[tech_data["name"]] = tech_id

            domain = self._parse_domain(tech_data.get("domain", ""))
            tech = TechnologyNode(
                id=tech_id,
                name=tech_data["name"],
                category=tech_data.get("category", "other"),
                domain=domain,
                vendor=tech_data.get("vendor"),
                license=self._parse_license(tech_data.get("license")),
                status=self._parse_status(tech_data.get("status", "growing")),
                description=tech_data.get("description", ""),
                confidence=ConfidenceMetadata(
                    confidence=0.7,
                    sources=[source],
                    halflife_days=90 if domain == KnowledgeDomain.AI_MODELS else 180,
                ),
            )
            await knowledge_graph.create_technology(tech)
            techs_added += 1

        for rel_data in extracted.get("relationships", []):
            source_name = rel_data.get("source", "")
            target_name = rel_data.get("target", "")
            source_id = name_to_id.get(source_name, source_name.lower().replace(" ", "-"))
            target_id = name_to_id.get(target_name, target_name.lower().replace(" ", "-"))

            edge_type = self._parse_edge_type(rel_data.get("type", "INTEGRATES_WITH"))
            if edge_type:
                edge = KnowledgeEdge(
                    source_id=source_id,
                    target_id=target_id,
                    edge_type=edge_type,
                )
                await knowledge_graph.create_edge(edge)
                rels_added += 1

        return {"technologies_added": techs_added, "relationships_added": rels_added}

    @staticmethod
    def _parse_domain(val: str) -> KnowledgeDomain:
        try:
            return KnowledgeDomain(val)
        except ValueError:
            return KnowledgeDomain.DATA_PLATFORMS

    @staticmethod
    def _parse_license(val: str | None) -> LicenseType | None:
        if not val:
            return None
        try:
            return LicenseType(val)
        except ValueError:
            return None

    @staticmethod
    def _parse_status(val: str) -> TechnologyStatus:
        try:
            return TechnologyStatus(val)
        except ValueError:
            return TechnologyStatus.GROWING

    @staticmethod
    def _parse_edge_type(val: str) -> EdgeType | None:
        try:
            return EdgeType(val)
        except ValueError:
            return None
