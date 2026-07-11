"""Decision tracking: records and learns from enterprise architecture decisions."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from odyssey.storage.postgres import postgres_store


class Decision(BaseModel):
    """A recorded architecture decision."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    enterprise_id: str
    decision_template_id: str | None = None  # FK to DecisionTemplate in knowledge graph
    question: str  # What was decided
    chosen_option: str  # What was chosen
    alternatives_considered: list[str] = Field(default_factory=list)
    rationale: str = ""
    outcome: str | None = None  # How it turned out (filled in later)
    outcome_rating: int | None = None  # 1-5
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: datetime | None = None


class DecisionTracker:
    """Tracks enterprise architecture decisions for learning and recommendations."""

    async def record_decision(self, decision: Decision) -> str:
        """Record a new architecture decision."""
        await postgres_store.execute(
            """
            INSERT INTO decisions (id, enterprise_id, decision_template_id, chosen_option, rationale, decided_at)
            VALUES ($1, $2, $3, $4, $5, $6)
            """,
            decision.id,
            decision.enterprise_id,
            decision.decision_template_id,
            json.dumps({
                "question": decision.question,
                "chosen": decision.chosen_option,
                "alternatives": decision.alternatives_considered,
            }),
            decision.rationale,
            decision.decided_at,
        )
        return decision.id

    async def record_outcome(
        self, decision_id: str, outcome: str, rating: int | None = None
    ) -> None:
        """Record the outcome of a past decision."""
        await postgres_store.execute(
            """
            UPDATE decisions
            SET outcome = $1
            WHERE id = $2
            """,
            json.dumps({"outcome": outcome, "rating": rating}),
            decision_id,
        )

    async def get_enterprise_decisions(
        self, enterprise_id: str, limit: int = 50
    ) -> list[dict]:
        """Get all decisions for an enterprise."""
        rows = await postgres_store.fetch(
            """
            SELECT * FROM decisions
            WHERE enterprise_id = $1
            ORDER BY decided_at DESC
            LIMIT $2
            """,
            enterprise_id,
            limit,
        )
        return [dict(r) for r in rows]

    async def get_decisions_for_template(
        self, template_id: str, limit: int = 100
    ) -> list[dict]:
        """Get all decisions made for a specific decision template.

        Useful for learning: what do enterprises typically choose for this decision?
        """
        rows = await postgres_store.fetch(
            """
            SELECT chosen_option, rationale, outcome, decided_at
            FROM decisions
            WHERE decision_template_id = $1
            ORDER BY decided_at DESC
            LIMIT $2
            """,
            template_id,
            limit,
        )
        return [dict(r) for r in rows]

    async def get_decision_stats(self) -> dict[str, Any]:
        """Get aggregate statistics on decisions across all enterprises."""
        row = await postgres_store.fetchrow("""
            SELECT
                COUNT(*) AS total_decisions,
                COUNT(DISTINCT enterprise_id) AS enterprises_with_decisions,
                COUNT(outcome) AS decisions_with_outcomes
            FROM decisions
        """)
        if not row:
            return {"total_decisions": 0}
        return dict(row)


decision_tracker = DecisionTracker()
