"""Langfuse configuration and tracing for LangGraph observability.

Updated for Langfuse SDK v3.x best-practice pattern:
- open_langfuse_trace() context manager using start_as_current_span()
- Natural root span creation (SDK auto-generates W3C trace ID)
- get_current_trace_id() retrieves the auto-generated ID
- update_current_trace() for user_id, session_id, tags
- CallbackHandler created inside the span context

This module provides:
- Environment-aware sampling rates (100% DEV/QA, 10% PROD)
- Session ID and user ID propagation via update_current_trace
- Searchable metadata enrichment
- Graceful degradation when Langfuse is unavailable

Performance constraints:
- Handler creation: <1ms
- Sampling decision: <0.1ms
"""

import contextvars
import logging
import random
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

from langfuse import get_client
from langfuse.langchain import CallbackHandler

from app.core.config import Environment, settings

logger = logging.getLogger(__name__)

# Async-safe trace_id and observation_id propagation (DEV-255)
_current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("_current_trace_id", default=None)
_current_observation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "_current_observation_id", default=None
)


@dataclass
class LangfuseTraceContext:
    """Context yielded by open_langfuse_trace().

    Attributes:
        handler: LangChain CallbackHandler for graph invocation, or None if disabled.
        trace_id: W3C 32-char hex trace ID, or "" if disabled.
        metadata: Custom metadata dict for config["metadata"] merging.
    """

    handler: CallbackHandler | None
    trace_id: str
    metadata: dict[str, Any] = field(default_factory=dict)


_NOOP_CONTEXT = LangfuseTraceContext(handler=None, trace_id="", metadata={})


def get_current_trace_id() -> str | None:
    """Get the current trace_id set by open_langfuse_trace.

    Returns:
        The trace_id string, or None if no trace is active in this context.
    """
    return _current_trace_id.get()


def get_current_observation_id() -> str | None:
    """Get the current observation_id (span_id) set by open_langfuse_trace.

    This is the 16-char hex ID of the root span, used as parent_span_id when
    creating nested generations to ensure they appear under the correct parent
    in the Langfuse trace hierarchy.

    Returns:
        The observation_id string, or None if no trace is active in this context.
    """
    return _current_observation_id.get()


# Default sampling rates by environment
DEFAULT_SAMPLING_RATES = {
    Environment.DEVELOPMENT: 1.0,  # 100% sampling
    Environment.QA: 1.0,  # 100% sampling
    Environment.PRODUCTION: 0.1,  # 10% sampling
}


def get_sampling_rate(
    environment: Environment,
    override_rate: float | None = None,
) -> float:
    """Get the sampling rate for the given environment.

    Args:
        environment: The application environment
        override_rate: Optional rate to override the default (0.0 to 1.0)

    Returns:
        Sampling rate between 0.0 and 1.0
    """
    if override_rate is not None:
        return max(0.0, min(1.0, override_rate))

    return DEFAULT_SAMPLING_RATES.get(environment, 1.0)


def should_sample(override_rate: float | None = None) -> bool:
    """Determine if the current request should be sampled.

    Uses environment-aware sampling rates:
    - DEV/QA: Always sample (100%)
    - PROD: Sample 10% (configurable via settings.LANGFUSE_SAMPLING_RATE)

    Args:
        override_rate: Optional rate to override the default

    Returns:
        True if the request should be sampled, False otherwise
    """
    rate = override_rate
    if rate is None:
        rate = getattr(settings, "LANGFUSE_SAMPLING_RATE", None)

    sampling_rate = get_sampling_rate(settings.ENVIRONMENT, rate)

    if sampling_rate >= 1.0:
        return True
    if sampling_rate <= 0.0:
        return False

    return random.random() < sampling_rate


@contextmanager
def open_langfuse_trace(
    trace_name: str,
    session_id: str | None = None,
    user_id: str | None = None,
    tags: list[str] | None = None,
    is_followup: bool = False,
    has_attachments: bool = False,
    studio_id: str | None = None,
    account_code: str | None = None,
) -> Iterator[LangfuseTraceContext]:
    """Open a Langfuse trace span using the v3 best-practice pattern.

    Uses start_as_current_span() to create a root span, then
    update_current_trace() to set trace-level metadata (name, user_id,
    session_id, tags). A CallbackHandler is created inside the span
    context so LangChain callbacks attach to the correct trace.

    Gracefully degrades: yields a no-op LangfuseTraceContext when
    credentials are missing or any error occurs. Never raises.

    Args:
        trace_name: Trace name shown in Langfuse UI (e.g., "rag-query").
        session_id: Session/conversation ID for grouping traces.
        user_id: Numeric user ID (fallback if account_code not provided).
        tags: Filterable tags (e.g., ["streaming", "workflow"]).
        is_followup: Whether this is a follow-up in a conversation.
        has_attachments: Whether the request includes file attachments.
        studio_id: Multi-tenant studio identifier.
        account_code: Human-readable account code (e.g., PRA70021-1).

    Yields:
        LangfuseTraceContext with handler, trace_id, and metadata.
    """
    # Check for credentials
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.debug("Langfuse credentials not configured, skipping trace")
        yield _NOOP_CONTEXT
        return

    # Try to set up Langfuse tracing
    try:
        client = get_client()

        # Build custom metadata (non-prefixed, for config["metadata"])
        custom_metadata: dict[str, Any] = {
            "query_type": "followup" if is_followup else "new",
            "has_attachments": has_attachments,
            "pipeline_version": "unified",
        }
        if studio_id:
            custom_metadata["studio_id"] = studio_id

        # Prefer account_code for readable Langfuse analytics
        effective_user_id = account_code or (str(user_id) if user_id else "anonymous")
        effective_session_id = session_id or str(uuid.uuid4())
    except Exception as e:
        # Setup failed - yield no-op context and return
        logger.warning(
            "Langfuse trace setup failed, yielding no-op context",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        yield _NOOP_CONTEXT
        return

    # DEV-255 Fix: Use natural root span pattern (v3 SDK).
    # start_as_current_span() creates a real root span with auto-generated
    # W3C trace_id. We retrieve it via get_current_trace_id() INSIDE the
    # context, then use update_current_trace() to set trace-level metadata.
    #
    # User exceptions inside the context MUST propagate - only catch Langfuse errors.
    with client.start_as_current_span(name=trace_name):
        # Get the auto-generated trace_id and observation_id from the SDK
        trace_id = client.get_current_trace_id() or ""
        observation_id = client.get_current_observation_id() or ""

        # Set contextvars for downstream consumers (e.g., _report_langfuse_generation)
        _current_trace_id.set(trace_id)
        _current_observation_id.set(observation_id)

        try:
            # Set trace-level attributes (name, user_id, session_id, tags)
            client.update_current_trace(
                name=trace_name,
                user_id=effective_user_id,
                session_id=effective_session_id,
                tags=tags or [],
                metadata=custom_metadata,
            )

            # Create CallbackHandler inside span context
            handler = CallbackHandler()

            ctx = LangfuseTraceContext(
                handler=handler,
                trace_id=trace_id,
                metadata=custom_metadata,
            )

            logger.info(
                "Langfuse trace opened",
                extra={
                    "trace_name": trace_name,
                    "trace_id": trace_id,
                    "session_id": effective_session_id,
                    "user_id": effective_user_id,
                },
            )

            yield ctx
        finally:
            # Reset contextvars to prevent leakage across async contexts
            _current_trace_id.set(None)
            _current_observation_id.set(None)
            client.flush()


def record_latency_score(
    latency_ms: float,
    trace_id: str | None = None,
) -> None:
    """Record pipeline latency as a Langfuse score.

    Creates a numeric score named "latency-ms" attached to the trace.
    Degrades gracefully: logs warning on any error, never raises.

    Args:
        latency_ms: Pipeline latency in milliseconds.
        trace_id: The W3C trace_id to attach the score to.
    """
    if trace_id is None:
        return

    if latency_ms < 0:
        return

    try:
        client = get_client()
        client.create_score(
            name="latency-ms",
            value=latency_ms,
            trace_id=trace_id,
            data_type="NUMERIC",
        )
        logger.debug("record_latency_score: recorded %.1fms for trace %s", latency_ms, trace_id)
    except Exception as e:
        logger.warning(
            "Failed to record latency score",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "latency_ms": latency_ms,
                "trace_id": trace_id,
            },
        )
