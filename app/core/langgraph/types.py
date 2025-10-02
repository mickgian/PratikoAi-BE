"""Types and utilities for LangGraph RAG implementation."""

from contextlib import contextmanager
from typing import Any, Dict, List, Optional, TypedDict
import time
import logging

# Get logger for rag_step_log
logger = logging.getLogger(__name__)


class RAGState(TypedDict, total=False):
    """Complete state definition for RAG workflow.

    Includes all fields that may be used across the RAG pipeline.
    All fields are optional to allow gradual population during workflow.
    """

    # request/session
    request_id: str
    session_id: str
    user_id: Optional[str]
    messages: List[dict]  # original request messages (as dicts)
    streaming: bool

    # privacy
    privacy_enabled: bool
    pii_detected: bool
    anonymized_input: Optional[str]

    # facts & attachments
    atomic_facts: Optional[List[dict]]
    canonical_facts: Optional[List[dict]]
    attachments: Optional[List[dict]]  # incl. hashes
    doc_facts: Optional[List[dict]]

    # golden/knowledge
    golden_hit: Optional[bool]
    golden_answer: Optional[dict]
    kb_docs: Optional[List[dict]]

    # provider & cost
    route_strategy: Optional[str]
    provider_choice: Optional[str]
    estimated_cost: Optional[float]

    # cache
    cache_key: Optional[str]
    cache_hit: Optional[bool]
    cached_response: Optional[dict]

    # llm/tool results
    llm_request: Optional[dict]
    llm_response: Optional[dict]
    tool_calls: Optional[List[dict]]
    tool_results: Optional[List[dict]]

    # response/stream
    final_response: Optional[dict]

    # metrics/epochs (always present)
    metrics: dict  # counters/timers; always present (can be {})
    epochs: Optional[dict]  # kb_epoch/golden_epoch/etc.

    # Additional fields for compatibility with existing nodes
    request_valid: Optional[bool]
    user_authenticated: Optional[bool]
    anonymized_messages: Optional[List[Any]]
    llm_success: Optional[bool]
    error_message: Optional[str]
    error_code: Optional[int]
    processing_stage: str
    node_history: List[str]


def rag_step_log(step: int, msg: str, **attrs) -> None:
    """Log a RAG step event with optional attributes.

    Args:
        step: Step number (e.g., 1, 3, 6, etc.)
        msg: Message (typically "enter" or "exit")
        **attrs: Additional attributes to log
    """
    log_data = {"step": step, "msg": msg, **attrs}
    logger.info(f"RAG_STEP_{step}: {msg}", extra=log_data)


@contextmanager
def rag_step_timer(step: int):
    """Context manager for timing RAG steps.

    Args:
        step: Step number

    Yields:
        None

    Logs the duration when exiting the context.
    """
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"RAG_STEP_{step}_TIMER: {duration:.3f}s",
                   extra={"step": step, "duration_seconds": duration})


# For backwards compatibility, also export GraphState
from app.schemas.graph import GraphState

__all__ = ["RAGState", "rag_step_log", "rag_step_timer", "GraphState"]