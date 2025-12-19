"""Query Classifier for Dynamic Weight Adjustment - DEV-BE-78 Phase 1.4.

Classifies user queries into types to enable dynamic weight adjustment
for retrieval ranking optimization. Uses fast regex-based patterns (no LLM).

Query Types:
- DEFINITIONAL: Questions asking for definitions ("cos'è", "che cosa significa")
- RECENT: Questions about recent/new information ("ultime novità", "2024/2025")
- CONCEPTUAL: Questions asking for explanations ("come", "perché")
- DEFAULT: Standard queries that don't match specific patterns

Performance: <1ms per classification (regex-based).
"""

import re
from enum import Enum
from typing import Dict


class QueryType(str, Enum):
    """Query type classification for dynamic weight adjustment."""

    DEFINITIONAL = "definitional"  # Definition queries → boost FTS
    RECENT = "recent"  # Recent/temporal queries → boost recency
    CONCEPTUAL = "conceptual"  # Explanation queries → boost vector
    DEFAULT = "default"  # Standard queries → no adjustment


# Compiled regex patterns for performance
# DEFINITIONAL patterns - asking for definitions
_DEFINITIONAL_PATTERNS = re.compile(
    r"""
    (?:
        cos['']?[eè]\b |                    # cos'è, cose, cosè
        che\s+cos['']?[eè]\b |              # che cos'è, che cose
        cosa\s+(?:significa|vuol\s+dire)\b | # cosa significa, cosa vuol dire
        definizione\s+(?:di|del|della)\b |  # definizione di/del/della
        che\s+cosa\s+[eè]\b                 # che cosa è
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# RECENT patterns - asking about recent/new information
_RECENT_PATTERNS = re.compile(
    r"""
    (?:
        ultime?\s+novit[àa]\b |             # ultime novità, ultima novità
        nuov[oiae]\s+\w+ |                  # nuove aliquote, nuovo bonus
        aggiornament[oi]\s+recent[ei]\b |   # aggiornamenti recenti
        modifiche?\s+recent[ei]\b |         # modifiche recenti
        ultima?\s+(?:circolare|risoluzione)\b | # ultima circolare
        novit[àa]\s+normativ[ea]\b |        # novità normative
        (?:cosa\s+)?[eè]\s+cambiat[oa]\b |  # è cambiato, cosa è cambiato
        \b202[4-9]\b |                      # Years 2024-2029
        \b(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+202[4-9]\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# CONCEPTUAL patterns - asking for explanations
_CONCEPTUAL_PATTERNS = re.compile(
    r"""
    (?:
        ^come\s+(?:calcolare|funziona|si\s+(?:calcola|determina|applica))\b |  # come calcolare, come funziona
        ^perch[eé]\s+\w+ |                  # perché devo pagare
        in\s+che\s+modo\s+\w+ |             # in che modo posso
        spiegami\s+\w+ |                    # spiegami il meccanismo
        qual\s+[eè]\s+la\s+differenza\b     # qual è la differenza
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def classify_query(query: str | None) -> QueryType:
    """Classify a query into a QueryType for dynamic weight adjustment.

    Args:
        query: The user's query text

    Returns:
        QueryType enum value indicating the classification

    Performance:
        <1ms per classification (regex-based, no LLM)
    """
    if not query or not isinstance(query, str):
        return QueryType.DEFAULT

    query = query.strip()
    if not query:
        return QueryType.DEFAULT

    # Check patterns in priority order: DEFINITIONAL > RECENT > CONCEPTUAL
    if _DEFINITIONAL_PATTERNS.search(query):
        return QueryType.DEFINITIONAL

    if _RECENT_PATTERNS.search(query):
        return QueryType.RECENT

    if _CONCEPTUAL_PATTERNS.search(query):
        return QueryType.CONCEPTUAL

    return QueryType.DEFAULT


def get_weight_adjustment(query_type: QueryType) -> dict[str, float]:
    """Get weight adjustment factors for a query type.

    Args:
        query_type: The classified query type

    Returns:
        Dictionary with boost values for each weight component:
        - fts_boost: Additive boost for FTS/BM25 weight
        - vector_boost: Additive boost for vector similarity weight
        - recency_boost: Additive boost for recency weight

    The boosts are applied additively to base weights, then normalized.
    """
    adjustments = {
        QueryType.DEFINITIONAL: {
            "fts_boost": 0.10,  # Boost FTS for definition queries
            "vector_boost": 0.0,
            "recency_boost": 0.0,
        },
        QueryType.RECENT: {
            "fts_boost": 0.0,
            "vector_boost": 0.0,
            "recency_boost": 0.10,  # Boost recency for temporal queries
        },
        QueryType.CONCEPTUAL: {
            "fts_boost": 0.0,
            "vector_boost": 0.10,  # Boost vector for conceptual queries
            "recency_boost": 0.0,
        },
        QueryType.DEFAULT: {
            "fts_boost": 0.0,
            "vector_boost": 0.0,
            "recency_boost": 0.0,
        },
    }

    return adjustments.get(
        query_type,
        {"fts_boost": 0.0, "vector_boost": 0.0, "recency_boost": 0.0},
    )
