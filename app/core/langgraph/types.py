"""Types and utilities for LangGraph RAG implementation."""

import logging
import time
from contextlib import contextmanager
from typing import (
    Any,
    List,
    Optional,
    TypedDict,
)

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
    user_id: str | None
    user_query: str | None  # Original user query text
    messages: list[dict]  # original request messages (as dicts)
    streaming: dict | None  # Phase 7: {requested, setup, mode, channel, chunks_sent, done, ...}

    # Phase 6 Request/Privacy fields
    session: dict | None  # Session data from validation
    user: dict | None  # User data from authentication
    validated_request: dict | None  # Validated request data
    validation_result: dict | None  # Validation result details from Step 3
    privacy: dict | None  # Privacy tracking: {gdpr_logged, pii_detected, anonymized_input, pii_entities, ...}

    # privacy (legacy fields - kept for compatibility)
    privacy_enabled: bool
    pii_detected: bool
    anonymized_input: str | None

    # facts & attachments
    atomic_facts: list[dict] | None
    canonical_facts: list[dict] | None
    attachments: list[dict] | None  # incl. hashes
    doc_facts: list[dict] | None

    # golden/knowledge
    golden_hit: bool | None
    golden_answer: str | None  # Answer text from Step 28 for streaming response handler
    golden_match: dict | None  # Match data from Step 24 (faq_id, similarity_score, answer, etc.) for Step 25
    kb_docs: list[dict] | None

    # Prompt and context fields (for steps 40-47)
    context: str | None  # Merged context from step 40 (KB docs + facts)
    selected_prompt: str | None  # Selected prompt from step 41
    system_prompt: str | None  # System prompt for message insertion (step 47)
    prompt_metadata: dict | None  # Prompt selection metadata
    classification: dict | None  # Domain/action classification result
    context_metadata: dict | None  # Context building metadata from step 40
    kb_results: dict | None  # KB search results from step 39

    # provider & cost (legacy fields - kept for compatibility)
    route_strategy: str | None
    provider_choice: str | None
    estimated_cost: float | None

    # provider governance (Phase 5)
    provider: (
        dict | None
    )  # {"strategy": str|None, "selected": str|None, "estimate": float|None, "budget_ok": bool|None}
    decisions: dict | None  # {"strategy_type": "CHEAP|BEST|BALANCED|PRIMARY", "cost_ok": bool, ...}

    # cache
    cache: dict | None  # Cache state: {key, hit, value}
    cache_key: str | None  # Legacy field
    cache_hit: bool | None  # Legacy field
    cached_response: dict | None  # Legacy field

    # llm/tool results
    llm: dict | None  # LLM state: {request, response, success, retry_count, retry_strategy, ...}
    tools: dict | None  # Tools state: {requested, type, executed, kb_results, ccnl_results, ...}
    llm_request: dict | None  # Legacy field
    llm_response: dict | None  # Legacy field
    tool_calls: list[dict] | None
    tool_results: list[dict] | None

    # response/stream
    final_response: dict | None
    agent_initialized: bool | None  # Step 8: Agent workflow initialized
    workflow_ready: bool | None  # Step 8: Workflow ready to process

    # metrics/epochs (always present)
    metrics: dict  # counters/timers; always present (can be {})
    epochs: dict | None  # kb_epoch/golden_epoch/etc.
    retries: dict | None  # Retry tracking: {llm_attempts, total_attempts, last_error, ...}

    # Additional fields for compatibility with existing nodes
    request_valid: bool | None
    user_authenticated: bool | None
    anonymized_messages: list[Any] | None
    llm_success: bool | None
    llm_success_decision: bool | None  # Step 67 decision
    cache_hit_decision: bool | None  # Step 62 decision
    tools_requested: bool | None  # Step 75
    tool_type: str | None  # Step 79
    returning_cached: bool | None  # Step 66
    retry_allowed: bool | None  # Step 69
    attempt_number: int | None  # Current retry attempt number
    is_production: bool | None  # Step 70
    should_failover: bool | None  # Step 70
    error_message: str | None
    error_code: int | None
    error_response: dict | None  # Step 5: Error response details
    error_details: dict | None  # Step 5: Additional error information
    workflow_terminated: bool | None  # Step 5: Workflow termination flag
    terminal_step: bool | None  # Step 5: Indicates terminal node reached
    status_code: int | None  # Step 5: HTTP status code for error responses
    processing_stage: str
    node_history: list[str]


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
        logger.info(f"RAG_STEP_{step}_TIMER: {duration:.3f}s", extra={"step": step, "duration_seconds": duration})


# For backwards compatibility, also export GraphState
from app.schemas.graph import GraphState

__all__ = ["RAGState", "rag_step_log", "rag_step_timer", "GraphState"]
