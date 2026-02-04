"""Langfuse configuration and handler creation for LangGraph observability.

Updated for Langfuse SDK v3.x which uses a different API:
- CallbackHandler accepts no constructor arguments
- Session ID, user ID, tags passed via config["metadata"] with langfuse_ prefix

This module provides:
- Environment-aware sampling rates (100% DEV/QA, 10% PROD)
- Session ID and user ID propagation via metadata
- Searchable metadata enrichment
- Graceful degradation when Langfuse is unavailable

Performance constraints:
- Handler creation: <1ms
- Sampling decision: <0.1ms
"""

import logging
import random
import uuid
from typing import Any

from langfuse.langchain import CallbackHandler

from app.core.config import Environment, settings

logger = logging.getLogger(__name__)

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
        # Clamp to valid range
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
        # Check for settings override first
        rate = getattr(settings, "LANGFUSE_SAMPLING_RATE", None)

    sampling_rate = get_sampling_rate(settings.ENVIRONMENT, rate)

    # For 100% sampling, skip random call for performance
    if sampling_rate >= 1.0:
        return True
    if sampling_rate <= 0.0:
        return False

    return random.random() < sampling_rate


def create_langfuse_handler(
    session_id: str | None = None,
    user_id: str | None = None,
    request_id: str | None = None,
    stage: str | None = None,
    tags: list[str] | None = None,
    trace_name: str | None = None,
    is_followup: bool = False,
    has_attachments: bool = False,
    studio_id: str | None = None,
) -> tuple[CallbackHandler | None, dict[str, Any]]:
    """Create a Langfuse CallbackHandler with enhanced tracking (v3 API).

    In Langfuse SDK v3, the CallbackHandler accepts no constructor arguments.
    Session ID, user ID, and tags are passed via config["metadata"] with
    the langfuse_ prefix when invoking the chain.

    Args:
        session_id: Unique session/conversation identifier. If not provided, generates UUID.
        user_id: User identifier. Defaults to "anonymous" if not provided.
        request_id: Optional request identifier for tracing.
        stage: Optional pipeline stage identifier (e.g., "retrieval", "generation").
        tags: Optional list of tags for filtering in Langfuse UI.
        trace_name: Langfuse trace name describing the user operation (e.g., "rag-query").
            Overrides the auto-detected graph compile name.
        is_followup: Whether this is a follow-up question in a conversation.
        has_attachments: Whether the request includes file attachments.
        studio_id: Multi-tenant studio identifier for isolation tracking.

    Returns:
        Tuple of (CallbackHandler, metadata_dict) where metadata_dict should be
        merged into config["metadata"] when invoking the chain.
        Returns (None, {}) if credentials are missing or creation fails.

    Example:
        ```python
        handler, langfuse_metadata = create_langfuse_handler(
            session_id="conv-123",
            user_id="user-456",
            trace_name="rag-query",
            tags=["rag", "streaming", "new"],
        )
        if handler:
            config = {
                "callbacks": [handler],
                "metadata": {**langfuse_metadata, "other_key": "value"},
            }
            await graph.ainvoke(state, config)
        ```
    """
    # Check for credentials
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        logger.debug("Langfuse credentials not configured, skipping handler creation")
        return None, {}

    # Generate session ID if not provided
    effective_session_id = session_id or str(uuid.uuid4())

    # Default to anonymous user
    effective_user_id = str(user_id) if user_id else "anonymous"

    # Build Langfuse v3 metadata (prefixed with langfuse_)
    langfuse_metadata: dict[str, Any] = {
        "langfuse_session_id": effective_session_id,
        "langfuse_user_id": effective_user_id,
        "langfuse_tags": tags or ["rag"],
        "langfuse_update_parent": True,
    }

    # Override trace name if provided (Langfuse v3 convention)
    if trace_name:
        langfuse_metadata["langfuse_trace_name"] = trace_name

    # Add custom metadata (non-prefixed for general use)
    if request_id:
        langfuse_metadata["request_id"] = request_id
    if stage:
        langfuse_metadata["stage"] = stage
    if studio_id:
        langfuse_metadata["studio_id"] = studio_id

    langfuse_metadata["query_type"] = "followup" if is_followup else "new"
    langfuse_metadata["has_attachments"] = has_attachments
    langfuse_metadata["pipeline_version"] = "unified"

    try:
        logger.info(
            "Creating Langfuse v3 handler",
            extra={
                "session_id": effective_session_id,
                "user_id": effective_user_id,
                "trace_name": trace_name,
                "has_public_key": bool(settings.LANGFUSE_PUBLIC_KEY),
                "has_secret_key": bool(settings.LANGFUSE_SECRET_KEY),
            },
        )
        # Langfuse v3: CallbackHandler takes no constructor arguments
        handler = CallbackHandler()
        logger.info("Langfuse v3 handler created successfully")
        return handler, langfuse_metadata
    except Exception as e:
        logger.warning(
            "Failed to create Langfuse handler",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return None, {}


def flush_langfuse_handler(handler: CallbackHandler | None) -> None:
    """Flush pending traces to Langfuse.

    The CallbackHandler queues traces asynchronously. Call this after the
    LangGraph invocation completes to ensure traces are sent to Langfuse.

    Args:
        handler: The CallbackHandler to flush, or None (no-op).

    Example:
        ```python
        handler, metadata = create_langfuse_handler(session_id="conv-123")
        try:
            result = await graph.ainvoke(state, {"callbacks": [handler], "metadata": metadata})
        finally:
            flush_langfuse_handler(handler)
        ```
    """
    if handler is None:
        logger.debug("flush_langfuse_handler: handler is None, skipping")
        return

    try:
        # Langfuse v3: Use global client to flush
        from langfuse import get_client

        client = get_client()
        client.flush()
        logger.debug("flush_langfuse_handler: flushed via get_client()")
    except Exception as e:
        logger.warning(
            "Failed to flush Langfuse handler",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
