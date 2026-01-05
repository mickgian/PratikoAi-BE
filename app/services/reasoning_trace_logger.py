"""Reasoning Trace Logger Service (DEV-238).

Structured logging for reasoning traces with mandatory context fields.

All log events comply with Logging Standards (lines 81-101 in CLAUDE.md)
which mandate specific context fields for all operations.

Coverage Target: 90%+ for new code.
"""

from __future__ import annotations

from typing import Any

import structlog

# Module-level logger following project standards
logger = structlog.get_logger(__name__)


def truncate_for_log(
    value: Any | None,
    max_length: int = 1000,
) -> str:
    """Truncate value for log storage.

    Args:
        value: Value to truncate (str, dict, or None)
        max_length: Maximum length before truncation

    Returns:
        Truncated string representation
    """
    if value is None:
        return ""

    value_str = str(value)

    if len(value_str) <= max_length:
        return value_str

    return value_str[:max_length] + "...[truncated]"


def log_reasoning_trace_recorded(
    state: dict[str, Any],
    elapsed_ms: float,
) -> None:
    """Log successful reasoning trace recording.

    DEV-238: Logs after Step 64 completes with all mandatory context fields.

    Args:
        state: RAG state with reasoning information
        elapsed_ms: Time taken in milliseconds
    """
    logger.info(
        "reasoning_trace_recorded",
        # Mandatory fields from Logging Standards
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        operation="reasoning_trace",
        resource_id=state.get("request_id"),
        # Reasoning-specific fields
        reasoning_type=state.get("reasoning_type"),
        reasoning_trace=truncate_for_log(state.get("reasoning_trace")),
        model_used=state.get("model_used"),
        query_complexity=state.get("query_complexity"),
        latency_ms=elapsed_ms,
    )


def log_reasoning_trace_failed(
    state: dict[str, Any],
    error_type: str,
    error_message: str,
    content_sample: str,
) -> None:
    """Log reasoning trace parsing failure.

    DEV-238: Logs when JSON parsing fails during response processing.

    Args:
        state: RAG state with context
        error_type: Type of error (e.g., "JSONDecodeError")
        error_message: Error message
        content_sample: Sample of content that failed to parse
    """
    logger.warning(
        "reasoning_trace_failed",
        # Mandatory fields from Logging Standards
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        operation="reasoning_trace_parse",
        resource_id=state.get("request_id"),
        # Error-specific fields
        error_type=error_type,
        error_message=error_message,
        content_sample=truncate_for_log(content_sample, max_length=200),
    )


def log_dual_reasoning_generated(
    state: dict[str, Any],
    internal_trace: str,
    public_reasoning: str,
    elapsed_ms: float,
) -> None:
    """Log dual reasoning generation completion.

    DEV-238: Logs when DualReasoning generates both internal and public traces.

    Args:
        state: RAG state with context
        internal_trace: Internal reasoning trace (technical)
        public_reasoning: Public-facing reasoning (user-friendly)
        elapsed_ms: Time taken in milliseconds
    """
    logger.info(
        "dual_reasoning_generated",
        # Mandatory fields from Logging Standards
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        operation="dual_reasoning",
        resource_id=state.get("request_id"),
        # Dual reasoning fields
        internal_trace=truncate_for_log(internal_trace),
        public_reasoning=truncate_for_log(public_reasoning),
        latency_ms=elapsed_ms,
    )


def log_tot_hypothesis_evaluated(
    state: dict[str, Any],
    hypothesis_id: str,
    probability: float,
    source_weight_score: float,
    selected: bool,
) -> None:
    """Log Tree of Thoughts hypothesis evaluation.

    DEV-238: Logs each ToT branch evaluation for debugging and analysis.

    Args:
        state: RAG state with context
        hypothesis_id: Unique identifier for the hypothesis
        probability: Probability score (0-1)
        source_weight_score: Score based on source authority
        selected: Whether this hypothesis was selected
    """
    logger.info(
        "tot_hypothesis_evaluated",
        # Mandatory fields from Logging Standards
        user_id=state.get("user_id"),
        session_id=state.get("session_id"),
        operation="tot_hypothesis_evaluation",
        resource_id=state.get("request_id"),
        # ToT-specific fields
        hypothesis_id=hypothesis_id,
        probability=probability,
        source_weight_score=source_weight_score,
        selected=selected,
    )
