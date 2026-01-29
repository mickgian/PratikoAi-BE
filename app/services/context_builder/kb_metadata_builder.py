"""KB metadata builder for action grounding.

Builds structured metadata for action grounding from KB documents.
"""

from app.core.logging import logger
from app.services.paragraph_extractor import ParagraphExtractor

from .constants import MIN_FONTI_RELEVANCE_SCORE
from .hierarchy_utils import get_category_label_it, get_hierarchy_weight
from .paragraph_utils import extract_paragraph_excerpt, generate_paragraph_id
from .title_simplifier import simplify_title
from .topic_extractor import extract_topics, extract_values


def build_kb_sources_metadata(
    kb_documents: list[dict],
    user_query: str | None = None,
    min_score: float = MIN_FONTI_RELEVANCE_SCORE,
) -> list[dict]:
    """Build structured metadata for action grounding from KB documents.

    DEV-236: Now includes paragraph_id and paragraph_excerpt for paragraph-level grounding.
    DEV-237: Uses ParagraphExtractor for query-relevant paragraph extraction.
    DEV-244: Filters out low-relevance documents to improve Fonti quality.

    Args:
        kb_documents: List of KB document dictionaries
        user_query: User query for relevance-based paragraph extraction (DEV-237)
        min_score: Minimum RRF/combined score to include in Fonti (DEV-244)

    Returns:
        List of metadata dictionaries for each document
    """
    metadata_list = []
    filtered_count = 0

    # DEV-237: Initialize paragraph extractor for relevance-based extraction
    extractor = ParagraphExtractor()

    for doc in kb_documents:
        if not isinstance(doc, dict):
            continue

        # DEV-250 DIAGNOSTIC: Log document metadata to trace authority_boost propagation
        logger.debug(
            "DEV250_kb_metadata_processing_doc",
            doc_id=doc.get("id", "")[:20] if doc.get("id") else "",
            title=doc.get("title", "")[:50],
            type=doc.get("type", ""),
            authority_boost=doc.get("authority_boost", "NOT_SET"),
            rrf_score=doc.get("rrf_score") or doc.get("combined_score") or doc.get("score"),
        )

        # DEV-244: Filter out low-relevance documents from Fonti display
        # DEV-250 FIX: Never filter high-authority sources (legge, decreto, circolare, etc.)
        # Documents with authority_boost > 1.0 were identified as official sources
        # in parallel_retrieval.py using GERARCHIA_FONTI (legge=1.8, decreto=1.6, etc.)
        authority_boost = doc.get("authority_boost", 1.0)
        is_high_authority = authority_boost > 1.0  # Boosted = official source

        filter_score = doc.get("rrf_score") or doc.get("combined_score") or doc.get("score")
        # Only filter sources WITHOUT authority boost that have low scores
        if not is_high_authority and filter_score and filter_score > 0 and filter_score < min_score:
            filtered_count += 1
            continue

        doc_id = doc.get("id", "")
        content = doc.get("content", "")

        # DEV-237: Extract most relevant paragraph using query
        paragraph_id = generate_paragraph_id(doc_id, 0)  # Default to first
        paragraph_excerpt = extract_paragraph_excerpt(content)
        relevance_score = 0.0

        if user_query and content:
            paragraph_result = extractor.extract_best_paragraph(
                content=content,
                query=user_query,
                doc_id=doc_id,
            )
            if paragraph_result:
                paragraph_id = paragraph_result.paragraph_id
                paragraph_excerpt = paragraph_result.excerpt
                relevance_score = paragraph_result.relevance_score

        # DEV-245: Simplify title and use Italian category labels
        raw_title = doc.get("title", "")
        raw_type = doc.get("type", "") or doc.get("category", "")

        metadata = {
            "id": doc_id,
            "title": simplify_title(raw_title),
            "type": get_category_label_it(raw_type),
            "date": doc.get("date") or "",
            "url": doc.get("source_url") or doc.get("url") or doc.get("metadata", {}).get("source_url"),
            "key_topics": extract_topics(doc),
            "key_values": extract_values(doc),
            "hierarchy_weight": get_hierarchy_weight(raw_type),
            "paragraph_id": paragraph_id,
            "paragraph_excerpt": paragraph_excerpt,
            "paragraph_relevance_score": relevance_score,
        }
        metadata_list.append(metadata)

    # DEV-244: Log filtering results
    if filtered_count > 0:
        logger.info(
            "fonti_low_relevance_filtered",
            filtered_count=filtered_count,
            remaining_count=len(metadata_list),
            min_score=min_score,
        )

    return metadata_list
