"""Architect: generates architecture recommendations, comparisons, and roadmaps.

The Architect combines enterprise context with landscape knowledge to produce
actionable architecture decisions. It reasons about trade-offs, dependencies,
and sequences decisions into phased roadmaps.
"""

from __future__ import annotations

import json
from typing import Any

from odyssey.agents.base import AgentDefinition, AgentQuery, AgentResponse, BaseAgent
from odyssey.enterprise.models import EnterpriseProfile
from odyssey.knowledge.graph import knowledge_graph
from odyssey.llm.client import llm_client
from odyssey.storage.postgres import postgres_store

ARCHITECT_SYSTEM = """You are the Architect agent of Odyssey, an AI-native enterprise AI & Data architecture advisor.

Your role is to produce structured, actionable architecture recommendations by combining:
1. The enterprise's current state (stack, maturity, constraints, goals, budget)
2. The AI & Data technology landscape (from the knowledge graph)
3. Proven architectural patterns and anti-patterns

You operate at three altitudes:
- STRATEGIC: Board-level decisions. Focus on business outcomes, competitive positioning, investment thesis, risk exposure. Output: executive summary + decision framework.
- TACTICAL: Architecture team decisions. Focus on technology comparison, integration paths, migration strategies, team impact. Output: comparison matrix + recommended approach + implementation phases.
- OPERATIONAL: Engineering decisions. Focus on specific configurations, benchmarks, code patterns, deployment topology. Output: implementation guide + configuration recommendations.

When generating recommendations:
- Always ground them in the knowledge graph data provided
- Score options against the enterprise's specific constraints and goals
- Surface hidden dependencies ("if you choose X, you'll also need Y")
- Flag irreversible decisions and their long-term implications
- Include a confidence level for each recommendation
- Propose a phased roadmap when multiple decisions are involved

When generating roadmaps:
- Phase 1 should be achievable in 1-3 months
- Each phase should deliver measurable value independently
- Order by: dependency resolution → risk reduction → value delivery
- Flag decisions that are time-sensitive (e.g., vendor pricing changes, EOL dates)
"""

RECOMMENDATION_PROMPT = """Based on the following enterprise context and knowledge graph data, provide an architecture recommendation.

## Enterprise Context
{enterprise_context}

## Knowledge Graph Context
{kg_context}

## Query
{query}

## Altitude: {altitude}

Provide your recommendation as JSON with this structure:
{{
    "summary": "Executive summary of the recommendation (2-3 sentences)",
    "recommendation": {{
        "primary_option": {{
            "technology": "name",
            "rationale": "why this is the best fit",
            "fit_score": 0-100,
            "key_strengths": ["..."],
            "key_risks": ["..."]
        }},
        "alternatives": [
            {{
                "technology": "name",
                "rationale": "when to choose this instead",
                "fit_score": 0-100,
                "trade_offs": ["..."]
            }}
        ]
    }},
    "dependencies": ["decisions or changes this recommendation depends on"],
    "roadmap": [
        {{
            "phase": 1,
            "name": "Phase name",
            "timeframe": "1-3 months",
            "actions": ["..."],
            "deliverables": ["..."],
            "estimated_effort": "low|medium|high"
        }}
    ],
    "risks": [
        {{
            "description": "risk description",
            "likelihood": "low|medium|high",
            "impact": "low|medium|high",
            "mitigation": "how to mitigate"
        }}
    ],
    "follow_up_questions": ["questions to refine this recommendation"],
    "confidence": 0.0-1.0
}}
"""

COMPARISON_PROMPT = """Compare the following technologies for the given enterprise context.

## Enterprise Context
{enterprise_context}

## Technologies to Compare
{technologies}

## Evaluation Criteria
{criteria}

## Query
{query}

Provide a structured comparison as JSON:
{{
    "comparison_matrix": [
        {{
            "technology": "name",
            "scores": {{"criterion1": 0-10, "criterion2": 0-10}},
            "overall_score": 0-100,
            "best_for": "scenario where this excels",
            "avoid_when": "scenario where this is a poor fit"
        }}
    ],
    "recommendation": {{
        "winner": "technology name",
        "rationale": "why",
        "runner_up": "technology name",
        "runner_up_rationale": "when to choose this instead"
    }},
    "decision_factors": ["key factors that should influence the choice"],
    "confidence": 0.0-1.0
}}
"""

ROADMAP_PROMPT = """Generate a technology roadmap for this enterprise based on their goals and current state.

## Enterprise Context
{enterprise_context}

## Current Stack
{current_stack}

## Strategic Goals
{goals}

## Knowledge Graph Context
{kg_context}

Generate a phased roadmap as JSON:
{{
    "vision": "Where the enterprise should be in 18 months (2-3 sentences)",
    "current_state_assessment": "Where they are now (2-3 sentences)",
    "gap_analysis": "Key gaps between current and target state",
    "phases": [
        {{
            "phase": 1,
            "name": "Phase name",
            "timeframe": "Q3 2026",
            "theme": "What this phase achieves",
            "decisions": [
                {{
                    "decision": "What to decide",
                    "recommendation": "Recommended option",
                    "rationale": "Why",
                    "reversibility": "easy|moderate|hard",
                    "estimated_cost": "low|medium|high"
                }}
            ],
            "milestones": ["Measurable milestone"],
            "risks": ["Key risk for this phase"],
            "dependencies": ["What must be done before this phase"]
        }}
    ],
    "quick_wins": ["Things that can be done immediately with minimal effort"],
    "confidence": 0.0-1.0
}}
"""


class ArchitectAgent(BaseAgent):
    """Generates architecture recommendations, comparisons, and roadmaps."""

    def __init__(self) -> None:
        super().__init__(
            AgentDefinition(
                id="architect",
                name="Architect",
                type="core",
                capabilities=[
                    "architecture_recommendation",
                    "technology_comparison",
                    "roadmap_generation",
                    "decision_analysis",
                    "trade_off_analysis",
                ],
                knowledge_domains=[
                    "data_platforms", "ml_infrastructure", "ai_models",
                    "ai_patterns", "data_governance", "cloud_deployment",
                    "organizational",
                ],
            )
        )

    def can_handle(self, query: AgentQuery) -> float:
        q = query.query.lower()
        # High confidence for architecture-specific queries
        strong_signals = [
            "recommend", "should we", "which", "compare", "roadmap",
            "architecture", "migrate", "best option", "trade-off",
            "build vs buy", "evaluate", "decision", "strategy",
            "what should", "how should", "plan for",
        ]
        if any(sig in q for sig in strong_signals):
            return 0.85

        # Medium confidence for technology questions
        medium_signals = [
            "vs", "versus", "or", "better", "alternative",
            "upgrade", "replace", "switch", "cost",
        ]
        if any(sig in q for sig in medium_signals):
            return 0.7

        return 0.2

    async def process(self, query: AgentQuery) -> AgentResponse:
        """Process an architecture query."""
        # Gather contexts
        kg_context = await self._gather_kg_context(query.query)
        enterprise_context = ""
        enterprise_profile = None
        if query.enterprise_id:
            enterprise_profile = await self._load_enterprise(query.enterprise_id)
            if enterprise_profile:
                enterprise_context = self._format_enterprise_context(enterprise_profile)

        # Check if LLM is available; if not, return knowledge graph data directly
        if not llm_client.available:
            return self._make_response(
                content=f"Here's what the knowledge graph has for your query:\n\n{kg_context}\n\n"
                "Note: Full AI-powered architecture analysis requires an ANTHROPIC_API_KEY in your .env file.",
                confidence=0.4,
                metadata={"query_type": "fallback", "llm_available": False},
            )

        # Determine query type and route to handler
        query_type = self._classify_query(query.query)
        match query_type:
            case "comparison":
                return await self._handle_comparison(query, kg_context, enterprise_context)
            case "roadmap":
                return await self._handle_roadmap(query, kg_context, enterprise_context, enterprise_profile)
            case _:
                return await self._handle_recommendation(query, kg_context, enterprise_context)

    async def _handle_recommendation(
        self, query: AgentQuery, kg_context: str, enterprise_context: str
    ) -> AgentResponse:
        """Generate an architecture recommendation."""
        prompt = RECOMMENDATION_PROMPT.format(
            enterprise_context=enterprise_context or "No enterprise context provided.",
            kg_context=kg_context,
            query=query.query,
            altitude=query.altitude.upper(),
        )
        try:
            result = await llm_client.generate_structured(
                prompt=prompt, system=ARCHITECT_SYSTEM, max_tokens=4096
            )
            # Format the response based on altitude
            content = self._format_recommendation(result, query.altitude)
            return self._make_response(
                content=content,
                structured_data=result,
                confidence=result.get("confidence", 0.7),
                follow_up_questions=result.get("follow_up_questions", []),
                metadata={"query_type": "recommendation", "altitude": query.altitude},
            )
        except Exception as e:
            # Fallback to unstructured generation
            content = await llm_client.generate(
                prompt=f"Enterprise context: {enterprise_context}\n\n"
                f"Knowledge: {kg_context}\n\n"
                f"Query ({query.altitude}): {query.query}",
                system=ARCHITECT_SYSTEM,
            )
            return self._make_response(content=content, confidence=0.5)

    async def _handle_comparison(
        self, query: AgentQuery, kg_context: str, enterprise_context: str
    ) -> AgentResponse:
        """Generate a technology comparison."""
        # Extract technology names from the query
        techs = await self._extract_technologies(query.query)

        # Get detailed info from knowledge graph
        tech_details = []
        for tech_id in techs:
            detail = await knowledge_graph.get_technology_with_relationships(tech_id)
            if detail:
                tech_details.append(detail)

        if not tech_details:
            tech_details_str = kg_context
        else:
            tech_details_str = json.dumps(tech_details, default=str)[:4000]

        prompt = COMPARISON_PROMPT.format(
            enterprise_context=enterprise_context or "No enterprise context provided.",
            technologies=tech_details_str,
            criteria="performance, cost, operational complexity, ecosystem, scalability, team expertise required",
            query=query.query,
        )
        try:
            result = await llm_client.generate_structured(
                prompt=prompt, system=ARCHITECT_SYSTEM, max_tokens=4096
            )
            content = self._format_comparison(result)
            return self._make_response(
                content=content,
                structured_data=result,
                confidence=result.get("confidence", 0.7),
                metadata={"query_type": "comparison", "technologies": techs},
            )
        except Exception:
            content = await llm_client.generate(
                prompt=f"Compare these technologies: {', '.join(techs)}\n\n"
                f"Context: {enterprise_context}\n\nKnowledge: {kg_context}\n\n"
                f"Query: {query.query}",
                system=ARCHITECT_SYSTEM,
            )
            return self._make_response(content=content, confidence=0.5)

    async def _handle_roadmap(
        self, query: AgentQuery, kg_context: str, enterprise_context: str,
        profile: EnterpriseProfile | None
    ) -> AgentResponse:
        """Generate a technology roadmap."""
        current_stack = ""
        goals = ""
        if profile:
            current_stack = json.dumps(
                [t.model_dump() for t in profile.tech_stack], default=str
            )[:2000]
            goals = json.dumps(
                [g.model_dump() for g in profile.goals], default=str
            )[:2000]

        prompt = ROADMAP_PROMPT.format(
            enterprise_context=enterprise_context or "No enterprise context provided.",
            current_stack=current_stack or "Not specified.",
            goals=goals or "Not specified.",
            kg_context=kg_context,
        )
        try:
            result = await llm_client.generate_structured(
                prompt=prompt, system=ARCHITECT_SYSTEM, max_tokens=6000
            )
            content = self._format_roadmap(result)
            return self._make_response(
                content=content,
                structured_data=result,
                confidence=result.get("confidence", 0.7),
                metadata={"query_type": "roadmap"},
            )
        except Exception:
            content = await llm_client.generate(
                prompt=f"Generate an AI/Data architecture roadmap.\n\n"
                f"Context: {enterprise_context}\nStack: {current_stack}\n"
                f"Goals: {goals}\n\nKnowledge: {kg_context}",
                system=ARCHITECT_SYSTEM,
            )
            return self._make_response(content=content, confidence=0.5)

    # --- Helpers ---

    def _classify_query(self, query: str) -> str:
        q = query.lower()
        if any(w in q for w in ["compare", "vs", "versus", "difference between", "or"]):
            return "comparison"
        if any(w in q for w in ["roadmap", "plan", "phases", "timeline", "sequence"]):
            return "roadmap"
        return "recommendation"

    async def _gather_kg_context(self, query: str) -> str:
        techs = await knowledge_graph.search_technologies(query=query, limit=10)
        if not techs:
            return "No relevant technologies found in knowledge graph."
        parts = []
        for t in techs[:8]:
            parts.append(
                f"- {t.get('name', '?')}: {t.get('description', '')} "
                f"[{t.get('category', '')}, {t.get('status', '')}]"
            )
        return "\n".join(parts)

    async def _extract_technologies(self, query: str) -> list[str]:
        """Extract technology IDs mentioned in a query."""
        # Search knowledge graph for all mentioned techs
        all_techs = await knowledge_graph.search_technologies(query=query, limit=20)
        mentioned = []
        q_lower = query.lower()
        for t in all_techs:
            name = t.get("name", "").lower()
            if name and name in q_lower:
                mentioned.append(t.get("id", ""))
        # If no exact matches, return the top results
        if not mentioned and all_techs:
            mentioned = [t["id"] for t in all_techs[:3]]
        return mentioned

    async def _load_enterprise(self, enterprise_id: str) -> EnterpriseProfile | None:
        row = await postgres_store.fetchrow(
            "SELECT * FROM enterprises WHERE id = $1", enterprise_id
        )
        if not row:
            return None
        try:
            return EnterpriseProfile(
                id=row["id"],
                name=row["name"],
                industry=row.get("industry", "other"),
                maturity=json.loads(row["maturity"]) if row["maturity"] else {},
                constraints=json.loads(row["constraints"]) if row["constraints"] else [],
                goals=json.loads(row["goals"]) if row["goals"] else [],
                tech_stack=json.loads(row["tech_stack"]) if row["tech_stack"] else [],
                budget=json.loads(row["budget"]) if row["budget"] else {},
            )
        except Exception:
            return None

    def _format_enterprise_context(self, profile: EnterpriseProfile) -> str:
        parts = [f"Enterprise: {profile.name} ({profile.industry.value})"]
        parts.append(f"Maturity: overall={profile.maturity.overall.name}")
        if profile.constraints:
            parts.append("Constraints: " + ", ".join(
                f"{c.type.value}({c.severity.value}): {c.description}"
                for c in profile.constraints
            ))
        if profile.goals:
            parts.append("Goals: " + ", ".join(
                f"[{g.priority.value}/{g.time_horizon.value}] {g.description}"
                for g in profile.goals
            ))
        if profile.tech_stack:
            parts.append("Current stack: " + ", ".join(
                f"{t.technology_id} (satisfaction: {t.satisfaction}/5)"
                for t in profile.tech_stack
            ))
        if profile.budget.annual_infra_usd > 0:
            parts.append(
                f"Budget: ${profile.budget.annual_infra_usd:,.0f} infra, "
                f"${profile.budget.annual_tooling_usd:,.0f} tooling, "
                f"sensitivity={profile.budget.cost_sensitivity.value}"
            )
        return "\n".join(parts)

    def _format_recommendation(self, result: dict, altitude: str) -> str:
        parts = [result.get("summary", "")]
        rec = result.get("recommendation", {})
        primary = rec.get("primary_option", {})
        if primary:
            parts.append(f"\n**Recommended: {primary.get('technology', '?')}** "
                        f"(fit score: {primary.get('fit_score', '?')}/100)")
            parts.append(f"Rationale: {primary.get('rationale', '')}")
            if primary.get("key_strengths"):
                parts.append("Strengths: " + ", ".join(primary["key_strengths"]))
            if primary.get("key_risks"):
                parts.append("Risks: " + ", ".join(primary["key_risks"]))

        alts = rec.get("alternatives", [])
        if alts:
            parts.append("\n**Alternatives:**")
            for alt in alts:
                parts.append(f"- {alt.get('technology', '?')} "
                           f"(score: {alt.get('fit_score', '?')}/100): "
                           f"{alt.get('rationale', '')}")

        deps = result.get("dependencies", [])
        if deps:
            parts.append("\n**Dependencies:** " + ", ".join(deps))

        roadmap = result.get("roadmap", [])
        if roadmap and altitude != "operational":
            parts.append("\n**Implementation Phases:**")
            for phase in roadmap:
                parts.append(f"  Phase {phase.get('phase', '?')}: {phase.get('name', '')} "
                           f"({phase.get('timeframe', '')})")
                for action in phase.get("actions", []):
                    parts.append(f"    - {action}")

        return "\n".join(parts)

    def _format_comparison(self, result: dict) -> str:
        parts = []
        matrix = result.get("comparison_matrix", [])
        for item in matrix:
            parts.append(f"**{item.get('technology', '?')}** "
                        f"(overall: {item.get('overall_score', '?')}/100)")
            parts.append(f"  Best for: {item.get('best_for', '')}")
            parts.append(f"  Avoid when: {item.get('avoid_when', '')}")
            scores = item.get("scores", {})
            if scores:
                score_str = ", ".join(f"{k}: {v}/10" for k, v in scores.items())
                parts.append(f"  Scores: {score_str}")

        rec = result.get("recommendation", {})
        if rec:
            parts.append(f"\n**Winner: {rec.get('winner', '?')}**")
            parts.append(f"Rationale: {rec.get('rationale', '')}")
            if rec.get("runner_up"):
                parts.append(f"Runner-up: {rec['runner_up']} — {rec.get('runner_up_rationale', '')}")

        return "\n".join(parts)

    def _format_roadmap(self, result: dict) -> str:
        parts = []
        if result.get("vision"):
            parts.append(f"**Vision:** {result['vision']}")
        if result.get("current_state_assessment"):
            parts.append(f"**Current State:** {result['current_state_assessment']}")
        if result.get("gap_analysis"):
            parts.append(f"**Gap:** {result['gap_analysis']}")

        for phase in result.get("phases", []):
            parts.append(f"\n**Phase {phase.get('phase', '?')}: {phase.get('name', '')}** "
                        f"({phase.get('timeframe', '')})")
            parts.append(f"Theme: {phase.get('theme', '')}")
            for d in phase.get("decisions", []):
                parts.append(f"  Decision: {d.get('decision', '')}")
                parts.append(f"    → {d.get('recommendation', '')} ({d.get('rationale', '')})")
            for m in phase.get("milestones", []):
                parts.append(f"  Milestone: {m}")

        quick_wins = result.get("quick_wins", [])
        if quick_wins:
            parts.append("\n**Quick Wins:**")
            for qw in quick_wins:
                parts.append(f"  - {qw}")

        return "\n".join(parts)
