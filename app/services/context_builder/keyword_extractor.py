"""Keyword extraction for web source filtering.

Extracts significant keywords from queries for filtering.
"""

import re

from app.services.italian_stop_words import STOP_WORDS


def extract_filter_keywords_from_query(query: str) -> list[str]:
    """DEV-245 Phase 5.13: Extract keywords using stop word list for web source filtering.

    DEV-245 Phase 5.14: Uses centralized STOP_WORDS from italian_stop_words module.
    This includes comprehensive verb conjugations (future, conditional, imperative)
    to fix the "recepira" problem where future tense verbs slipped through.

    Example:
        - User asks: "irap" (short follow-up)
        - Reformulated by step_039a: "L'IRAP può essere inclusa nella rottamazione quinquies?"
        - Extracted keywords: ["irap", "rottamazione", "quinquies", ...]

    Args:
        query: The reformulated user query

    Returns:
        List of significant keywords for filtering (lowercase), max 10 keywords
    """
    if not query:
        return []

    # Normalize and tokenize
    query_lower = query.lower()
    # Handle Italian contractions: "dell'irap" → "dell irap"
    query_lower = re.sub(r"[''`]", " ", query_lower)
    # Split on non-alphanumeric (keep accented chars)
    words = re.findall(r"[a-zàèéìòùáéíóú]+", query_lower)

    # Filter stop words and short words
    keywords = []
    for word in words:
        if word not in STOP_WORDS and len(word) > 2:
            keywords.append(word)

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    # Return up to 10 keywords for filtering
    return unique_keywords[:10]
