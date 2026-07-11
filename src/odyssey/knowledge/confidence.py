"""Confidence scoring and decay for knowledge assertions."""

from __future__ import annotations

from datetime import datetime

from odyssey.knowledge.models import DOMAIN_HALFLIFE, KnowledgeDomain


def compute_effective_confidence(
    base_confidence: float,
    last_verified: datetime,
    domain: KnowledgeDomain,
    as_of: datetime | None = None,
) -> float:
    """Compute effective confidence with time-based decay.

    Confidence decays based on domain-specific halflife:
    - AI Models: 90 days (fast-moving)
    - Data Platforms: 180 days
    - Compliance: 365 days
    """
    now = as_of or datetime.utcnow()
    halflife = DOMAIN_HALFLIFE.get(domain, 180)
    days_since = (now - last_verified).days
    decay = max(0.3, 1.0 - (days_since / halflife) * 0.5)
    return round(base_confidence * decay, 4)


def compute_source_confidence(
    source_count: int,
    avg_trust_level: float,
    has_contradictions: bool,
) -> float:
    """Compute base confidence from source signals."""
    # More sources = higher confidence, with diminishing returns
    source_factor = min(1.0, 0.3 + (source_count * 0.15))
    contradiction_penalty = 0.3 if has_contradictions else 0.0
    return round(max(0.1, source_factor * avg_trust_level - contradiction_penalty), 4)


def needs_reverification(
    last_verified: datetime,
    domain: KnowledgeDomain,
    base_confidence: float,
    threshold: float = 0.5,
) -> bool:
    """Check if a knowledge assertion needs re-verification."""
    effective = compute_effective_confidence(base_confidence, last_verified, domain)
    return effective < threshold
