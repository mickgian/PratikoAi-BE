# ruff: noqa: UP043
"""Custom Langfuse spans for non-LLM operations in the RAG pipeline.

This module provides context managers for creating custom spans that track
non-LLM operations like:
- Retrieval/search operations
- LangGraph node execution
- Document processing
- Cache operations

All span functions degrade gracefully when Langfuse is unavailable.

Updated for Langfuse SDK v3.x:
- Uses get_client() singleton pattern
- Uses start_span() / start_as_current_span() with trace_context
- Removed deprecated client.trace(id=...).span(...) pattern
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager, suppress
from typing import Any, Optional

from langfuse import get_client

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_langfuse_client():
    """Get the Langfuse client singleton (v3 SDK pattern).

    Returns:
        Langfuse client instance, or None if credentials are missing.
    """
    if not settings.LANGFUSE_PUBLIC_KEY or not settings.LANGFUSE_SECRET_KEY:
        return None

    try:
        return get_client()
    except Exception as e:
        logger.warning(
            "Failed to get Langfuse client",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return None


class NoOpSpan:
    """No-operation span for graceful degradation."""

    def set_output(self, output: Any) -> None:
        """No-op output setter."""
        pass

    def update(self, **kwargs: Any) -> None:
        """No-op update method."""
        pass

    def end(self) -> None:
        """No-op end method."""
        pass


class SpanWrapper:
    """Wrapper around Langfuse span for easier output handling."""

    def __init__(self, span: Any) -> None:
        self._span = span
        self._output: dict[str, Any] | None = None

    def set_output(self, output: dict[str, Any]) -> None:
        """Set the output to be recorded when span ends."""
        self._output = output
        if self._span:
            self._span.update(output=output)

    def update(self, **kwargs: Any) -> None:
        """Update span with additional data."""
        if self._span:
            self._span.update(**kwargs)

    def end(self) -> None:
        """End the span."""
        if self._span:
            self._span.end()


def create_span(
    name: str,
    trace_id: str,
    input_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    level: str = "DEFAULT",
) -> Any | None:
    """Create a custom span for non-LLM operations (v3 SDK).

    Args:
        name: Name of the span (e.g., "retrieval_step", "cache_lookup")
        trace_id: ID of the parent trace
        input_data: Optional input data to record
        metadata: Optional metadata for filtering/searching
        level: Span level (DEFAULT, DEBUG, WARNING, ERROR)

    Returns:
        Langfuse span object, or None if client unavailable.
    """
    client = get_langfuse_client()
    if not client:
        return None

    try:
        # v3 SDK: Use start_span() with trace_context to attach to existing trace
        span = client.start_span(
            name=name,
            input=input_data or {},
            metadata=metadata or {},
            level=level,
            trace_context={"trace_id": trace_id},
        )
        return span
    except Exception as e:
        logger.debug(
            "Failed to create Langfuse span",
            extra={"name": name, "error": str(e)},
        )
        return None


@contextmanager
def span_context(
    name: str,
    trace_id: str,
    input_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    level: str = "DEFAULT",
) -> Generator[SpanWrapper, None, None]:
    """Context manager for creating and auto-ending spans (v3 SDK).

    Usage:
        ```python
        with span_context(name="retrieval", trace_id="trace-123") as span:
            results = await search(query)
            span.set_output({"results_count": len(results)})
        ```

    Args:
        name: Name of the span
        trace_id: ID of the parent trace
        input_data: Optional input data to record
        metadata: Optional metadata for filtering/searching
        level: Span level (DEFAULT, DEBUG, WARNING, ERROR)

    Yields:
        SpanWrapper for setting output and metadata.
    """
    client = get_langfuse_client()

    if not client:
        yield SpanWrapper(None)
        return

    span = None
    wrapper = SpanWrapper(None)
    try:
        # v3 SDK: Use start_span() with trace_context to attach to existing trace
        span = client.start_span(
            name=name,
            input=input_data or {},
            metadata=metadata or {},
            level=level,
            trace_context={"trace_id": trace_id},
        )
        wrapper = SpanWrapper(span)
    except Exception as e:
        logger.debug(
            "Error creating span",
            extra={"name": name, "error": str(e)},
        )

    try:
        yield wrapper
    finally:
        if span:
            with suppress(Exception):
                span.end()


@contextmanager
def node_span(
    node_name: str,
    step_number: str,
    trace_id: str,
    input_data: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Generator[SpanWrapper, None, None]:
    """Context manager for LangGraph node spans.

    Creates a span with standardized naming: "{step_number}_{node_name}"

    Usage:
        ```python
        with node_span(
            node_name="build_context",
            step_number="S040",
            trace_id="trace-123",
        ) as span:
            context = await build_kb_context(state)
            span.set_output({"chunks_count": len(context.chunks)})
        ```

    Args:
        node_name: Name of the LangGraph node
        step_number: Step identifier (e.g., "S040", "S064")
        trace_id: ID of the parent trace
        input_data: Optional input data to record
        metadata: Optional additional metadata

    Yields:
        SpanWrapper for setting output and metadata.
    """
    # Format name as "{step}_{node}"
    formatted_name = f"{step_number}_{node_name}"

    # Include step number in metadata
    full_metadata = {
        "step_number": step_number,
        "node_name": node_name,
        **(metadata or {}),
    }

    with span_context(
        name=formatted_name,
        trace_id=trace_id,
        input_data=input_data,
        metadata=full_metadata,
    ) as span:
        yield span


@contextmanager
def retrieval_span(
    query: str,
    trace_id: str,
    search_type: str = "hybrid",
    metadata: dict[str, Any] | None = None,
) -> Generator[SpanWrapper, None, None]:
    """Context manager for retrieval/search operation spans.

    Usage:
        ```python
        with retrieval_span(
            query="rottamazione quater",
            trace_id="trace-123",
            search_type="hybrid",
        ) as span:
            results = await hybrid_search(query)
            span.set_output({"results_count": len(results)})
        ```

    Args:
        query: The search query
        trace_id: ID of the parent trace
        search_type: Type of search (hybrid, vector, bm25)
        metadata: Optional additional metadata

    Yields:
        SpanWrapper for setting output and metadata.
    """
    full_metadata = {
        "search_type": search_type,
        **(metadata or {}),
    }

    with span_context(
        name="retrieval",
        trace_id=trace_id,
        input_data={"query": query},
        metadata=full_metadata,
    ) as span:
        yield span
