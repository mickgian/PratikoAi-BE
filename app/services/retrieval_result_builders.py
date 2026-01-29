"""Result builders for parallel retrieval operations.

DEV-250: Extracted from step_039c__parallel_retrieval.py to reduce node size.
"""

from typing import Any


def retrieval_result_to_dict(result: Any) -> dict[str, Any]:
    """Convert RetrievalResult to a serializable dict for state storage.

    Args:
        result: RetrievalResult from ParallelRetrievalService

    Returns:
        Serializable dict with all fields including documents
    """
    documents = []
    for doc in result.documents:
        doc_dict = {
            "document_id": doc.document_id,
            "content": doc.content,
            "score": doc.score,
            "rrf_score": doc.rrf_score,
            "source_type": doc.source_type,
            "source_name": doc.source_name,
            "published_date": doc.published_date.isoformat() if doc.published_date else None,
            # DEV-244 FIX: Extract source_url from metadata for kb_sources_metadata
            # Without this, the Fonti dropdown won't have URLs and won't display
            "source_url": doc.metadata.get("source_url"),
            "metadata": doc.metadata,
        }
        documents.append(doc_dict)

    return {
        "documents": documents,
        "total_found": result.total_found,
        "search_time_ms": result.search_time_ms,
        "search_keywords": result.search_keywords,  # DEV-245 Phase 4.2.1
        "search_keywords_with_scores": result.search_keywords_with_scores,  # DEV-245 Phase 5.12
        "skipped": False,
        "error": False,
    }


def create_retrieval_skip_result(reason: str) -> dict[str, Any]:
    """Create a skip result when retrieval is not needed.

    Args:
        reason: Reason for skipping retrieval

    Returns:
        Empty result dict marked as skipped
    """
    return {
        "documents": [],
        "total_found": 0,
        "search_time_ms": 0.0,
        "skipped": True,
        "skip_reason": reason,
        "error": False,
    }


def create_retrieval_error_result() -> dict[str, Any]:
    """Create an error result when retrieval fails.

    Returns:
        Empty result dict marked as error
    """
    return {
        "documents": [],
        "total_found": 0,
        "search_time_ms": 0.0,
        "skipped": False,
        "error": True,
    }
