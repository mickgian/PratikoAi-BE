"""Citation validation for LLM responses.

Validates law citations in responses against KB context using HallucinationGuard.
"""

from typing import TYPE_CHECKING, Any

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.hallucination_guard import CitationValidationResult

# Type alias for RAG state dict
RAGStateDict = dict[str, Any]

# DEV-249: Cached HallucinationGuard instance
_hallucination_guard_instance = None


def _get_hallucination_guard():
    """Get or create HallucinationGuard instance (lazy loading)."""
    global _hallucination_guard_instance
    if _hallucination_guard_instance is None:
        from app.services.hallucination_guard import HallucinationGuard

        _hallucination_guard_instance = HallucinationGuard()
    return _hallucination_guard_instance


def validate_citations_in_response(
    response_text: str,
    kb_context: str,
    state: RAGStateDict,
) -> "CitationValidationResult | None":
    """DEV-249: Validate law citations in LLM response against KB context.

    This function integrates HallucinationGuard into the LangGraph pipeline.
    It validates that law citations (e.g., "Legge 199/2025") in the LLM response
    actually exist in the KB context that was provided to the LLM.

    Args:
        response_text: The LLM-generated response text
        kb_context: The KB context that was provided to the LLM
        state: RAG state for logging context

    Returns:
        CitationValidationResult if validation was performed, None if skipped
    """
    # Skip if no response or context
    if not response_text or not kb_context:
        logger.debug(
            "DEV249_hallucination_check_skipped",
            reason="empty_input",
            has_response=bool(response_text),
            has_context=bool(kb_context),
            request_id=state.get("request_id"),
        )
        return None

    try:
        guard = _get_hallucination_guard()
        result = guard.validate_citations(response_text, kb_context)

        # Log hallucination detection with structured context
        if result.has_hallucinations:
            logger.warning(
                "DEV249_hallucination_detected",
                hallucinated_citations=result.hallucinated_citations,
                valid_citations=result.valid_citations,
                hallucination_rate=result.hallucination_rate,
                request_id=state.get("request_id"),
                session_id=state.get("session_id"),
            )
        elif result.extracted_citations:
            logger.info(
                "DEV249_citations_validated",
                citation_count=len(result.extracted_citations),
                all_valid=True,
                request_id=state.get("request_id"),
            )

        return result

    except Exception as e:
        # Graceful degradation: log error but don't break the pipeline
        logger.error(
            "DEV249_hallucination_guard_error",
            error_type=type(e).__name__,
            error_message=str(e),
            request_id=state.get("request_id"),
        )
        return None
