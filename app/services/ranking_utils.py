"""Ranking Utilities for Retrieval Optimization - DEV-BE-78 Phase 1.3.

Provides utility functions for source authority weighting and other
ranking optimizations.

Source Authority Tiers:
- Official (0.15): ADE, INPS, MEF, Gazzetta Ufficiale
- Semi-Official (0.10): Professional associations
- Baseline (0.00): Aggregators, blogs, unknown sources
"""

from typing import Any

# Source authority weights by tier
# Official Italian government sources: +0.15 boost
_OFFICIAL_SOURCE_PREFIXES = frozenset(
    [
        "agenzia_entrate",  # Agenzia delle Entrate (all variants)
        "inps",  # INPS (all variants)
        "mef",  # Ministero Economia e Finanze
        "gazzetta_ufficiale",  # Gazzetta Ufficiale
        "ministero_lavoro",  # Ministero del Lavoro
        "inail",  # INAIL
        "corte_cassazione",  # Corte di Cassazione
    ]
)

# Semi-official professional associations: +0.10 boost
_SEMI_OFFICIAL_SOURCE_PREFIXES = frozenset(
    [
        "confindustria",
        "ordine_commercialisti",
        "consiglio_nazionale_forense",
        "cndcec",  # Consiglio Nazionale Dottori Commercialisti
        "fondazione_nazionale_commercialisti",
    ]
)


def get_source_authority_boost(source: Any) -> float:
    """Get the authority boost for a document source.

    Args:
        source: The source identifier string (e.g., "agenzia_entrate_normativa")

    Returns:
        Authority boost value:
        - 0.15 for official government sources
        - 0.10 for semi-official professional associations
        - 0.00 for unknown/baseline sources

    Performance:
        O(n) prefix matching, <0.01ms per call
    """
    if not source or not isinstance(source, str):
        return 0.0

    source_lower = source.lower().strip()
    if not source_lower:
        return 0.0

    # Check official sources (prefix match for variants like agenzia_entrate_news)
    for prefix in _OFFICIAL_SOURCE_PREFIXES:
        if source_lower.startswith(prefix):
            return 0.15

    # Check semi-official sources
    for prefix in _SEMI_OFFICIAL_SOURCE_PREFIXES:
        if source_lower.startswith(prefix):
            return 0.10

    return 0.0


# DEV-242 Phase 11: Tier-based ranking multipliers
# Applied to combined score to prioritize authoritative documents
TIER_MULTIPLIERS = {
    1: 1.25,  # CRITICAL: Laws, Decrees, DPR - highest priority
    2: 1.10,  # IMPORTANT: Circulars, Resolutions, Interpelli
    3: 0.80,  # REFERENCE: News, FAQ, Guides - lower priority
}


def get_tier_multiplier(tier: int | None) -> float:
    """Get score multiplier based on document tier classification.

    Args:
        tier: Document tier (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
              None for unclassified documents

    Returns:
        Multiplier value:
        - 1.25 for Tier 1 (laws, decrees)
        - 1.10 for Tier 2 (circulars)
        - 0.80 for Tier 3 (news, FAQ)
        - 1.00 for unknown/None

    Performance:
        O(1) dictionary lookup
    """
    if tier is None:
        return 1.0
    return TIER_MULTIPLIERS.get(tier, 1.0)


def normalize_weights(
    fts: float,
    vector: float,
    recency: float,
    quality: float = 0.0,
    source: float = 0.0,
) -> tuple[float, float, float, float, float]:
    """Normalize weights to sum to 1.0.

    Args:
        fts: FTS/BM25 weight
        vector: Vector similarity weight
        recency: Recency weight
        quality: Text quality weight
        source: Source authority weight

    Returns:
        Tuple of normalized weights (fts, vector, recency, quality, source)

    Raises:
        ValueError: If all weights are zero
    """
    total = fts + vector + recency + quality + source

    if total <= 0:
        raise ValueError("At least one weight must be positive")

    return (
        fts / total,
        vector / total,
        recency / total,
        quality / total,
        source / total,
    )


def clamp_quality(value: float | None) -> float:
    """Clamp text_quality value to [0.0, 1.0] range.

    Args:
        value: Raw text_quality value (may be None or out of range)

    Returns:
        Clamped value in [0.0, 1.0], with None → 0.5 (neutral)
    """
    if value is None:
        return 0.5
    return max(0.0, min(1.0, float(value)))
