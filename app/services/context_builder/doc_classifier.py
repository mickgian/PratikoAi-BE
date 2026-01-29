"""Document classification utilities.

Classifies documents as KB or web sources.
"""


def is_web_document(doc: dict) -> bool:
    """Check if document is a web source.

    Args:
        doc: Document dictionary

    Returns:
        True if document is a web source
    """
    if not isinstance(doc, dict):
        return False
    metadata = doc.get("metadata") or {}
    source_type = doc.get("source_type", "") or ""
    return (
        metadata.get("is_web_result", False)
        or source_type in ("web", "web_ai_summary")
        or doc.get("document_id", "").startswith("web_")
    )


def separate_kb_and_web_docs(documents: list[dict]) -> tuple[list[dict], list[dict]]:
    """Separate documents into KB and web sources.

    Args:
        documents: List of document dictionaries

    Returns:
        Tuple of (kb_docs, web_docs)
    """
    kb_docs = []
    web_docs = []
    for doc in documents:
        if not isinstance(doc, dict):
            continue
        if is_web_document(doc):
            web_docs.append(doc)
        else:
            kb_docs.append(doc)
    return kb_docs, web_docs


def build_web_metadata_entry(doc: dict) -> dict:
    """Build metadata entry for a web document.

    Args:
        doc: Web document dictionary

    Returns:
        Metadata dictionary for Fonti display
    """
    content = doc.get("content", "")
    excerpt = content[:500] if content else ""
    return {
        "id": doc.get("document_id", ""),
        "title": doc.get("source_name", "") or doc.get("title", ""),
        "url": doc.get("source_url") or doc.get("metadata", {}).get("source_url"),
        "type": "web",
        "date": "",
        "excerpt": excerpt,
        "is_ai_synthesis": doc.get("metadata", {}).get("is_ai_synthesis", False),
        "key_topics": [],
        "key_values": [],
        "hierarchy_weight": 0.3,
        "paragraph_id": "",
        "paragraph_excerpt": excerpt,
        "paragraph_relevance_score": 0.0,
    }
