"""Result builders for query variant operations."""

from typing import Any


def variants_to_dict(variants: Any) -> dict[str, Any]:
    """Convert QueryVariants to a serializable dict for state storage.

    Args:
        variants: QueryVariants object from MultiQueryGeneratorService

    Returns:
        Serializable dict with all query variant fields
    """
    return {
        "bm25_query": variants.bm25_query,
        "vector_query": variants.vector_query,
        "entity_query": variants.entity_query,
        "original_query": variants.original_query,
        "document_references": variants.document_references,  # ADR-022
        "semantic_expansions": variants.semantic_expansions,  # DEV-242
        "skipped": False,
        "fallback": False,
    }


def create_skip_result(query: str, reason: str) -> dict[str, Any]:
    """Create a skip result when expansion is not needed.

    Args:
        query: Original user query
        reason: Reason for skipping expansion

    Returns:
        Dict with all variant fields set to original query
    """
    return {
        "bm25_query": query,
        "vector_query": query,
        "entity_query": query,
        "original_query": query,
        "document_references": None,
        "semantic_expansions": None,  # DEV-242
        "skipped": True,
        "skip_reason": reason,
        "fallback": False,
    }


def create_fallback_result(query: str) -> dict[str, Any]:
    """Create a fallback result using original query for all variants.

    Args:
        query: Original user query (may be expanded)

    Returns:
        Dict with all variant fields set to query, marked as fallback
    """
    return {
        "bm25_query": query,
        "vector_query": query,
        "entity_query": query,
        "original_query": query,
        "document_references": None,
        "semantic_expansions": None,  # DEV-242
        "skipped": False,
        "fallback": True,
    }
