"""Types and utilities for LangGraph RAG implementation."""

import logging
import time
from contextlib import contextmanager
from typing import (
    Annotated,
    Any,
    List,
    Optional,
    TypedDict,
)

# Get logger for rag_step_log
logger = logging.getLogger(__name__)


def _extract_message_key(msg: Any) -> tuple[str | None, str | None] | None:
    """Extract (role, content) from a message, handling both dicts and LangChain message objects.

    DEV-007 P0.8 FIX: LangChain message objects (AIMessage, HumanMessage, etc.) have
    .type/.role and .content attributes, while dicts use .get(). This helper normalizes
    both to prevent message duplication on page refresh.

    Args:
        msg: A message as dict or LangChain BaseMessage object

    Returns:
        (role, content) tuple for deduplication, or None if can't extract
    """
    if isinstance(msg, dict):
        return (msg.get("role"), msg.get("content"))

    # LangChain message objects have .type (ai, human, system) or .role attribute
    # and .content attribute
    if hasattr(msg, "content"):
        # Get role from .type (LangChain standard) or .role attribute
        role = getattr(msg, "type", None) or getattr(msg, "role", None)
        content = getattr(msg, "content", None)
        # Map LangChain types to OpenAI roles
        role_map = {"ai": "assistant", "human": "user", "system": "system"}
        normalized_role = role_map.get(role, role) if role else None
        return (normalized_role, content)

    return None


def merge_messages(existing: list[dict] | None, new: list[dict] | None) -> list[dict]:
    """Custom reducer that MERGES messages instead of replacing.

    LangGraph calls this reducer when state["messages"] is updated.
    Without a reducer, updates REPLACE the entire list.
    With this reducer, new messages are APPENDED, avoiding duplicates.

    DEV-007 FIX: Prevents page refresh checkpoint corruption where
    Turn 2's messages would be lost/corrupted because checkpoint
    REPLACED messages instead of MERGING them.

    DEV-007 P0.8 FIX: Now handles both dict messages AND LangChain message objects
    (AIMessage, HumanMessage, etc.) for deduplication. This prevents message
    duplication on page refresh when checkpoint contains AIMessage objects but
    new messages are passed as dicts.

    Args:
        existing: Current messages in checkpoint (may be None)
        new: New messages being set (may be None)

    Returns:
        Merged list with duplicates removed by (role, content) tuple
    """
    if existing is None:
        return new or []
    if new is None:
        return existing

    # DEV-007 P0.11 DIAGNOSTIC: Log merger inputs for debugging
    def _get_role(msg):
        if isinstance(msg, dict):
            return msg.get("role")
        return getattr(msg, "type", None) or getattr(msg, "role", None)

    existing_roles = [_get_role(m) for m in existing]
    new_roles = [_get_role(m) for m in new]
    logger.info(
        f"DEV007_merge_messages_called: existing_count={len(existing)}, new_count={len(new)}, "
        f"existing_roles={existing_roles}, new_roles={new_roles}"
    )

    # Build set of existing (role, content) tuples for deduplication
    # DEV-007 P0.8: Handle both dicts AND LangChain message objects
    existing_keys: set[tuple[str | None, str | None]] = set()
    for msg in existing:
        key = _extract_message_key(msg)
        if key:
            existing_keys.add(key)

    # Start with existing messages
    merged = list(existing)

    # Add new messages that don't already exist
    added_count = 0
    skipped_count = 0
    for msg in new:
        key = _extract_message_key(msg)
        if key and key not in existing_keys:
            merged.append(msg)
            existing_keys.add(key)
            added_count += 1
        else:
            skipped_count += 1

    merged_roles = [_get_role(m) for m in merged]
    logger.info(
        f"DEV007_merge_messages_result: merged_count={len(merged)}, merged_roles={merged_roles}, "
        f"added_count={added_count}, skipped_count={skipped_count}"
    )

    return merged


def merge_attachments(existing: list[dict] | None, new: list[dict] | None) -> list[dict]:
    """Custom reducer that MERGES attachments instead of replacing.

    LangGraph calls this reducer when state["attachments"] is updated.
    Without a reducer, updates REPLACE the entire list.
    With this reducer, new attachments are MERGED, with newer uploads
    taking priority over stale checkpoint data.

    DEV-007 P0.5 FIX: Prevents attachments from being lost during
    graph execution when nodes update state without including attachments.

    Priority: NEW attachments override PRIOR attachments with same ID
    (because new uploads have correct current message_index).

    Args:
        existing: Current attachments in checkpoint (may be None)
        new: New attachments being set (may be None)

    Returns:
        Merged list with duplicates removed by attachment ID,
        preferring newer attachments over existing ones.
    """
    if existing is None:
        return new or []
    if new is None:
        return existing

    # Build map of existing attachments by ID
    merged_by_id = {}

    # Add existing attachments first
    for att in existing:
        if isinstance(att, dict):
            att_id = att.get("id")
            if att_id:
                merged_by_id[att_id] = att

    # Add/override with new attachments (NEW takes priority)
    for att in new:
        if isinstance(att, dict):
            att_id = att.get("id")
            if att_id:
                merged_by_id[att_id] = att  # Override existing with new

    return list(merged_by_id.values())


def preserve_conversation_topic(
    existing: str | None,
    new: str | None,
) -> str | None:
    """DEV-245 Phase 5.7: Preserve conversation_topic across node transitions.

    LangGraph uses REPLACE semantics by default for fields without reducers.
    This means any node that doesn't explicitly return conversation_topic
    will replace it with None, losing the topic context.

    This reducer ensures the topic persists across all node transitions
    by only updating if a new value is explicitly set (not None).

    Args:
        existing: Current topic in state (may be None)
        new: New topic being set (may be None)

    Returns:
        The new value if set, otherwise preserves existing value.
    """
    if new is not None:
        return new
    return existing


def preserve_topic_keywords(
    existing: list[str] | None,
    new: list[str] | None,
) -> list[str] | None:
    """DEV-245 Phase 5.7: Preserve topic_keywords across node transitions.

    LangGraph uses REPLACE semantics by default for fields without reducers.
    This means any node that doesn't explicitly return topic_keywords
    will replace it with None, losing the topic filtering capability.

    This reducer ensures topic_keywords persists across all node transitions
    by only updating if a new non-empty value is explicitly set.

    Args:
        existing: Current keywords in state (may be None)
        new: New keywords being set (may be None or empty)

    Returns:
        The new value if set and non-empty, otherwise preserves existing value.
    """
    if new is not None and len(new) > 0:
        return new
    return existing


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
    # DEV-007 FIX: Use merge_messages reducer to MERGE messages in checkpoint
    # Without reducer: checkpoint REPLACES messages (causes Turn 2 corruption after refresh)
    # With reducer: checkpoint MERGES messages (appends new, dedupes by role+content)
    messages: Annotated[list[dict], merge_messages]  # original request messages (as dicts)
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
    # DEV-007 P0.5 FIX: Use merge_attachments reducer to MERGE attachments in checkpoint
    # Without reducer: checkpoint REPLACES attachments (causes Turn 2 new uploads to be lost)
    # With reducer: checkpoint MERGES attachments (new uploads preserved with correct message_index)
    attachments: Annotated[list[dict] | None, merge_attachments]  # incl. hashes
    doc_facts: list[dict] | None

    # DEV-007 Issue 9: Query composition for adaptive context prioritization
    # Values: "pure_kb", "pure_doc", "hybrid", "chat" (from QueryComposition enum)
    query_composition: str | None

    # DEV-194: LLM Router semantic classification result
    # Contains: route, confidence, reasoning, entities, requires_freshness, suggested_sources, needs_retrieval
    routing_decision: dict | None

    # DEV-195: Query Expansion and Retrieval (Step 39a, 39b, 39c)
    # Step 39a: Multi-Query variants (bm25_query, vector_query, entity_query, original_query)
    query_variants: dict | None
    # Step 39b: HyDE result (hypothetical_document, word_count, skipped, skip_reason)
    hyde_result: dict | None
    # Step 39c: Parallel retrieval result (documents, total_found, search_time_ms)
    retrieval_result: dict | None

    # DEV-196: Parsed synthesis result with Verdetto Operativo
    # Contains: answer_text, verdetto (azione_consigliata, analisi_rischio, scadenza, documentazione, indice_fonti)
    parsed_synthesis: dict | None

    # DEV-007 FIX: Index of current user message for marking current vs prior attachments
    current_message_index: int | None

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

    # DEV-200: Proactivity fields for LangGraph nodes (Step 14, Step 100)
    # proactivity: {
    #   pre_response: {question: InteractiveQuestion | None, skip_rag: bool},
    #   post_response: {actions: list[Action], source: "template"|"llm_parsed"}
    # }
    proactivity: dict | None
    skip_rag_for_proactivity: bool | None  # Step 14: If True, skip RAG and return question

    # DEV-245: Web verification results from Step 100
    # Structure: {caveats: list[str], has_caveats: bool, web_sources_checked: int, verification_performed: bool}
    web_verification: dict | None

    # ==========================================================================
    # Phase 9: LLM Excellence Fields (DEV-210)
    # ==========================================================================

    # Phase 9: LLM Excellence - KB Preservation (DEV-213)
    # Preserved KB documents from Step 40 for downstream use (Step 64, Step 100)
    kb_documents: list[dict] | None
    # Source metadata for action grounding with hierarchy weights
    # Structure: [{id, title, type, date, url, key_topics, key_values, hierarchy_weight}]
    kb_sources_metadata: list[dict] | None

    # DEV-245: Parallel Hybrid RAG - Web sources from Brave Search
    # Separated from KB documents for proper attribution
    web_documents: list[dict] | None
    # Web source metadata for citation
    # Structure: [{id, title, url, type, is_ai_synthesis}]
    web_sources_metadata: list[dict] | None

    # DEV-245 Phase 4.2: Previously shown sources for Fonti deduplication
    # Set of URLs already shown in prior conversation turns (used to avoid repetition in Fonti)
    prior_shown_source_urls: set[str] | None

    # DEV-245 Phase 4.2.1: Search keywords used for Brave search
    # Passed to Step 040 for consistent web source filtering (same keywords as search)
    search_keywords: list[str] | None
    # DEV-245 Phase 5.12: Keyword scores for evaluation (YAKE statistical scoring)
    # Structure: [{"keyword": "rottamazione", "score": 0.02}, ...]
    # Lower score = more important keyword
    search_keywords_with_scores: list[dict] | None

    # DEV-245 Phase 5.3: Conversation topic tracking for long conversations
    # Preserves main topic across many turns (industry best practice - JetBrains, Zoice AI)
    # Without this, messages[-4:] window loses topic context at Q4+
    # DEV-245 Phase 5.7: Use reducers to persist across node transitions
    # Without reducers, LangGraph REPLACES these with None on any node that doesn't return them
    conversation_topic: Annotated[str | None, preserve_conversation_topic]  # "rottamazione quinquies"
    topic_keywords: Annotated[list[str] | None, preserve_topic_keywords]  # ["rottamazione", "quinquies"]

    # Phase 9: LLM Excellence - Complexity & Routing (DEV-220, DEV-221)
    # Query complexity level: "simple" | "complex" | "multi_domain"
    query_complexity: str | None
    # Full classification result from ComplexityClassifier
    # Structure: {complexity, domains, confidence, reasoning}
    complexity_classification: dict | None

    # Phase 9: LLM Excellence - Reasoning (DEV-223, DEV-229)
    # Reasoning approach used: "cot" | "tot" | "tot_multi_domain"
    reasoning_type: str | None
    # Internal reasoning log (CoT steps or ToT summary)
    # CoT Structure: {tema, fonti_utilizzate, elementi_chiave, conclusione}
    # ToT Structure: {hypotheses, selected, selection_reasoning, confidence}
    reasoning_trace: dict | None
    # Full Tree of Thoughts analysis when ToT is used
    # Structure: {hypotheses[], selected, selection_reasoning, confidence, alternative_note}
    tot_analysis: dict | None

    # Phase 9: LLM Excellence - Dual Reasoning (DEV-229, DEV-230)
    # Technical reasoning for debugging/logging (not shown to user)
    internal_reasoning: dict | None
    # User-friendly explanation of reasoning
    # Structure: {summary, selected_scenario, why_selected, main_sources, confidence_label}
    public_reasoning: dict | None

    # Phase 9: LLM Excellence - Action Validation (DEV-215, DEV-217, DEV-218)
    # ActionValidator output with validation results
    action_validation_result: dict | None
    # Golden Loop iteration count (max 2 regenerations)
    action_regeneration_count: int | None
    # Source of actions: "unified_llm" | "fallback" | "template" | "regenerated"
    actions_source: str | None
    # Rejection reasons for debugging failed validations
    actions_validation_log: list[str] | None

    # ==========================================================================
    # End Phase 9 Fields
    # ==========================================================================

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
from app.schemas.graph import GraphState  # noqa: E402

__all__ = ["RAGState", "rag_step_log", "rag_step_timer", "GraphState", "merge_messages", "merge_attachments"]
