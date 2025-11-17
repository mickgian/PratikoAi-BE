"""
Test fixtures for creating valid RAGState instances.

Provides convenience functions for creating minimal valid state objects
with optional overrides for testing different scenarios.
"""

from typing import Any, Dict, List, Optional

from app.core.langgraph.types import RAGState


def make_state(
    request_id: str = "test-req-123",
    session_id: str = "test-session-456",
    messages: list[dict[str, str]] | None = None,
    processing_stage: str = "init",
    **overrides: Any,
) -> RAGState:
    """
    Create a minimal valid RAGState with optional overrides.

    Args:
        request_id: Request identifier
        session_id: Session identifier
        messages: List of message dicts (user/assistant)
        processing_stage: Current processing stage
        **overrides: Additional state fields to set

    Returns:
        RAGState dict with all required fields
    """
    state: RAGState = {
        "messages": messages or [{"role": "user", "content": "test query"}],
        "request_id": request_id,
        "session_id": session_id,
        "metrics": {},
        "processing_stage": processing_stage,
        "node_history": [],
    }

    # Apply overrides
    state.update(overrides)

    return state


def state_privacy_ok() -> RAGState:
    """Create state that has passed privacy checks."""
    return make_state(
        processing_stage="privacy_checked",
        privacy={"enabled": True, "pii_detected": False, "anonymized": False},
        decisions={"privacy_enabled": True, "pii_detected": False},
    )


def state_needs_llm() -> RAGState:
    """Create state that needs LLM processing (cache miss)."""
    return make_state(
        processing_stage="cache_miss",
        cache={"checked": True, "hit": False},
        decisions={"cache_hit": False},
        provider={"name": "anthropic", "model": "claude-3-5-sonnet-20241022"},
    )


def state_cached_hit() -> RAGState:
    """Create state with cache hit."""
    return make_state(
        processing_stage="cache_checked",
        cache={"checked": True, "hit": True, "response": {"content": "cached response", "cached_at": "2025-01-01"}},
        decisions={"cache_hit": True},
    )


def state_llm_success() -> RAGState:
    """Create state after successful LLM call."""
    return make_state(
        processing_stage="llm_complete",
        llm={
            "success": True,
            "response": {
                "content": "LLM response text",
                "model": "claude-3-5-sonnet-20241022",
                "usage": {"input_tokens": 100, "output_tokens": 50},
            },
        },
        decisions={"llm_success": True},
    )


def state_with_tools() -> RAGState:
    """Create state that requires tool execution."""
    return make_state(
        processing_stage="llm_complete",
        llm={
            "success": True,
            "response": {"content": "", "tool_calls": [{"name": "kb_search", "args": {"query": "test"}}]},
        },
        decisions={"has_tool_calls": True, "llm_success": True},
    )


def state_streaming_enabled() -> RAGState:
    """Create state with streaming enabled."""
    return make_state(
        processing_stage="response_ready",
        streaming={"enabled": True, "requested": True},
        decisions={"streaming_requested": True},
        response={"content": "response text", "complete": True},
    )


def state_golden_eligible() -> RAGState:
    """Create state eligible for golden fast-path."""
    return make_state(
        processing_stage="preflight",
        messages=[{"role": "user", "content": "What is the company policy?"}],
        golden={"eligible": True},
        decisions={"golden_eligible": True},
    )


def state_provider_selected() -> RAGState:
    """Create state with provider selected."""
    return make_state(
        processing_stage="provider_selected",
        provider={
            "name": "anthropic",
            "model": "claude-3-5-sonnet-20241022",
            "strategy": "BEST",
            "cost_estimate": 0.015,
        },
        decisions={"cost_within_budget": True},
    )


def state_complete() -> RAGState:
    """Create state for completed request."""
    return make_state(
        processing_stage="complete",
        response={"content": "Final response text", "complete": True, "metadata": {"steps": 15, "total_ms": 523}},
        complete=True,
        metrics={"total_duration_ms": 523, "llm_calls": 1, "cache_hits": 0, "tool_calls": 0},
    )
