"""Web source filtering for topic relevance.

Filters web sources to ensure they match the conversation topic.
"""


def is_web_source_topic_relevant(
    doc: dict,
    query_keywords: list[str],
    topic_keywords: list[str] | None = None,
) -> bool:
    """DEV-245 Phase 5.5: Check if web source is relevant to the conversation topic.

    CRITICAL: If topic_keywords are provided (e.g., ["rottamazione", "quinquies"]),
    ALL of them must appear in the web result. This prevents "rottamazione ter"
    results from passing when the topic is "rottamazione quinquies".

    Example:
        - Topic: "rottamazione quinquies" → topic_keywords = ["rottamazione", "quinquies"]
        - Q5: "la regione sicilia recepira' la rottamazione dell'irap?"
        - Web result: "Rottamazione Ter 2024 - Sicilia" (contains "rottamazione" + "sicilia")
        - OLD behavior: PASS (any keyword matches)
        - NEW behavior: FAIL (missing "quinquies" from topic)

    Args:
        doc: Web document dict with content/title
        query_keywords: Keywords extracted from reformulated query
        topic_keywords: Core topic keywords that MUST ALL match (DEV-245 Phase 5.5)

    Returns:
        True if web source is relevant, False if it should be filtered
    """
    # Combine title and content for keyword matching
    title = doc.get("source_name", "") or doc.get("title", "") or ""
    content = doc.get("content", "") or ""
    combined_text = f"{title} {content}".lower()

    # DEV-245 Phase 5.5 FIX: Check topic_keywords FIRST (strictest filter)
    # Requires 2+ topic keywords to enable strict matching
    if topic_keywords and isinstance(topic_keywords, list) and len(topic_keywords) >= 2:
        # Require ALL topic keywords to be present
        topic_match = all(kw.lower() in combined_text for kw in topic_keywords)
        if not topic_match:
            return False  # Reject: doesn't match conversation topic

    # No query keywords = allow (but only AFTER topic filter passed above)
    if not query_keywords:
        return True

    # General sanity check: at least one query keyword must match
    return any(kw in combined_text for kw in query_keywords)
