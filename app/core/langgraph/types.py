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
    user_id: Optional[str]
    user_query: Optional[str]  # Original user query text
    messages: List[dict]  # original request messages (as dicts)
    streaming: Optional[dict]  # Phase 7: {requested, setup, mode, channel, chunks_sent, done, ...}

    # Phase 6 Request/Privacy fields
    session: Optional[dict]  # Session data from validation
    user: Optional[dict]  # User data from authentication
    validated_request: Optional[dict]  # Validated request data
    validation_result: Optional[dict]  # Validation result details from Step 3
    privacy: Optional[dict]  # Privacy tracking: {gdpr_logged, pii_detected, anonymized_input, pii_entities, ...}

    # privacy (legacy fields - kept for compatibility)
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

    # Prompt and context fields (for steps 40-47)
    context: Optional[str]  # Merged context from step 40 (KB docs + facts)
    selected_prompt: Optional[str]  # Selected prompt from step 41
    system_prompt: Optional[str]  # System prompt for message insertion (step 47)
    prompt_metadata: Optional[dict]  # Prompt selection metadata
    classification: Optional[dict]  # Domain/action classification result
    context_metadata: Optional[dict]  # Context building metadata from step 40
    kb_results: Optional[dict]  # KB search results from step 39

    # provider & cost (legacy fields - kept for compatibility)
    route_strategy: Optional[str]
    provider_choice: Optional[str]
    estimated_cost: Optional[float]

    # provider governance (Phase 5)
    provider: Optional[
        dict
    ]  # {"strategy": str|None, "selected": str|None, "estimate": float|None, "budget_ok": bool|None}
    decisions: Optional[dict]  # {"strategy_type": "CHEAP|BEST|BALANCED|PRIMARY", "cost_ok": bool, ...}

    # cache
    cache: Optional[dict]  # Cache state: {key, hit, value}
    cache_key: Optional[str]  # Legacy field
    cache_hit: Optional[bool]  # Legacy field
    cached_response: Optional[dict]  # Legacy field

    # llm/tool results
    llm: Optional[dict]  # LLM state: {request, response, success, retry_count, retry_strategy, ...}
    tools: Optional[dict]  # Tools state: {requested, type, executed, kb_results, ccnl_results, ...}
    llm_request: Optional[dict]  # Legacy field
    llm_response: Optional[dict]  # Legacy field
    tool_calls: Optional[List[dict]]
    tool_results: Optional[List[dict]]

    # response/stream
    final_response: Optional[dict]
    agent_initialized: Optional[bool]  # Step 8: Agent workflow initialized
    workflow_ready: Optional[bool]  # Step 8: Workflow ready to process

    # metrics/epochs (always present)
    metrics: dict  # counters/timers; always present (can be {})
    epochs: Optional[dict]  # kb_epoch/golden_epoch/etc.
    retries: Optional[dict]  # Retry tracking: {llm_attempts, total_attempts, last_error, ...}

    # Additional fields for compatibility with existing nodes
    request_valid: Optional[bool]
    user_authenticated: Optional[bool]
    anonymized_messages: Optional[List[Any]]
    llm_success: Optional[bool]
    llm_success_decision: Optional[bool]  # Step 67 decision
    cache_hit_decision: Optional[bool]  # Step 62 decision
    tools_requested: Optional[bool]  # Step 75
    tool_type: Optional[str]  # Step 79
    returning_cached: Optional[bool]  # Step 66
    retry_allowed: Optional[bool]  # Step 69
    attempt_number: Optional[int]  # Current retry attempt number
    is_production: Optional[bool]  # Step 70
    should_failover: Optional[bool]  # Step 70
    error_message: Optional[str]
    error_code: Optional[int]
    error_response: Optional[dict]  # Step 5: Error response details
    error_details: Optional[dict]  # Step 5: Additional error information
    workflow_terminated: Optional[bool]  # Step 5: Workflow termination flag
    terminal_step: Optional[bool]  # Step 5: Indicates terminal node reached
    status_code: Optional[int]  # Step 5: HTTP status code for error responses
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
        logger.info(f"RAG_STEP_{step}_TIMER: {duration:.3f}s", extra={"step": step, "duration_seconds": duration})


# For backwards compatibility, also export GraphState
from app.schemas.graph import GraphState

__all__ = ["RAGState", "rag_step_log", "rag_step_timer", "GraphState"]
