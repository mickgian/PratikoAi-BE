"""Citation validation for LLM responses.

DEV-249: Validates law citations in responses against KB context using HallucinationGuard.
DEV-389: Adds soft/strict mode and timeout support for production integration.

Modes (controlled by ``HALLUCINATION_GUARD_MODE`` env var):
    - **soft** (default): Log warning, continue with flagged response.
    - **strict**: Flag response for regeneration when hallucinations are found.

Timeout (``HALLUCINATION_GUARD_TIMEOUT_S``, default 2.0 s):
    If validation exceeds the timeout the response is returned unvalidated.
"""

import os
import signal
import threading
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import TYPE_CHECKING, Any

from app.core.logging import logger

if TYPE_CHECKING:
    from app.services.hallucination_guard import CitationValidationResult

# Type alias for RAG state dict
RAGStateDict = dict[str, Any]

# DEV-389: Configuration from environment
HALLUCINATION_GUARD_MODE: str = os.getenv("HALLUCINATION_GUARD_MODE", "soft")  # "soft" | "strict"
HALLUCINATION_GUARD_TIMEOUT_S: float = float(os.getenv("HALLUCINATION_GUARD_TIMEOUT_S", "2.0"))

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
    """Validate law citations in LLM response against KB context.

    DEV-249: Core validation logic.
    DEV-389: Soft/strict mode + timeout guard.

    In **soft** mode (default) hallucinations are logged as warnings but
    the response is returned as-is.  In **strict** mode the state is
    flagged with ``hallucination_requires_regeneration = True`` so the
    caller can request re-generation without the hallucinated citations.

    Args:
        response_text: The LLM-generated response text.
        kb_context: The KB context that was provided to the LLM.
        state: RAG state for logging context.

    Returns:
        CitationValidationResult if validation was performed, None if skipped.
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

        # DEV-389: Timeout-guarded validation
        result = _run_with_timeout(guard.validate_citations, response_text, kb_context)
        if result is None:
            # Timeout — return unvalidated
            logger.warning(
                "DEV389_hallucination_guard_timeout",
                timeout_s=HALLUCINATION_GUARD_TIMEOUT_S,
                request_id=state.get("request_id"),
            )
            return None

        # Log hallucination detection with structured context
        if result.has_hallucinations:
            mode = HALLUCINATION_GUARD_MODE

            logger.warning(
                "DEV249_hallucination_detected",
                hallucinated_citations=result.hallucinated_citations,
                valid_citations=result.valid_citations,
                hallucination_rate=result.hallucination_rate,
                guard_mode=mode,
                request_id=state.get("request_id"),
                session_id=state.get("session_id"),
            )

            # DEV-389: Strict mode — flag for regeneration
            if mode == "strict":
                state["hallucination_requires_regeneration"] = True
                state["hallucinated_citations"] = result.hallucinated_citations
                logger.info(
                    "DEV389_strict_mode_regeneration_flagged",
                    hallucinated_count=len(result.hallucinated_citations),
                    request_id=state.get("request_id"),
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


def _run_with_timeout(fn, *args, timeout_s: float | None = None):
    """Run *fn* in a thread pool with a timeout.

    Returns the function result or ``None`` on timeout.
    """
    timeout = timeout_s if timeout_s is not None else HALLUCINATION_GUARD_TIMEOUT_S
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(fn, *args)
            return future.result(timeout=timeout)
    except FuturesTimeoutError:
        return None
