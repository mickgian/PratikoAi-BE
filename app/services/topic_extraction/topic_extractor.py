"""Topic keyword extraction from user queries.

DEV-245 Phase 5.3: Extract topic keywords from first query.
"""

import re

from app.services.italian_stop_words import STOP_WORDS_MINIMAL


def extract_topic_keywords(query: str) -> list[str]:
    """Extract topic keywords from first query.

    Extracts significant keywords that represent the conversation topic.
    These keywords persist across all turns to prevent context loss.

    DEV-245 Phase 5.14: Uses centralized STOP_WORDS_MINIMAL from italian_stop_words module.

    Example:
        "parlami della rottamazione quinquies"
        → ["rottamazione", "quinquies"]

    Args:
        query: The first user query (natural language)

    Returns:
        List of significant keywords (lowercase), max 5 keywords
    """
    # Normalize: lowercase, remove punctuation
    text = query.lower()
    text = re.sub(r"[^\w\s]", " ", text)

    # Tokenize and filter using centralized stop words
    # DEV-245 Phase 5.14: Use STOP_WORDS_MINIMAL for topic extraction
    words = text.split()
    keywords = [w for w in words if len(w) >= 3 and w not in STOP_WORDS_MINIMAL]

    # Remove duplicates while preserving order
    seen: set[str] = set()
    unique_keywords: list[str] = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    # Cap at 5 keywords
    return unique_keywords[:5]
