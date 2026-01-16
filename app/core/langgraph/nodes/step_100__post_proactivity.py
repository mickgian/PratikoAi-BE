"""Step 100: Post-Response Proactivity Node (DEV-200, DEV-201, DEV-218, DEV-244).

LangGraph node that adds suggested actions AFTER LLM response. It uses template
actions for recognized document types, extracts from VERDETTO for technical_research,
or parses LLM response for contextual actions.

DEV-201d: Integrates forbidden action filtering to prevent inappropriate suggestions.
DEV-218: Integrates ActionValidator and Golden Loop regeneration.
DEV-244: Topic-anchored action generation with zero actions support.

The node:
1. Checks if pre-proactivity already triggered (skip if so)
2. Checks if chitchat route (skip if so)
3. Gets actions from Step 64 unified output or falls back to legacy sources
4. Builds topic context from user query and conversation
5. Validates actions using ActionValidator with topic filtering (DEV-244)
6. Triggers ActionRegenerator if <2 valid actions AND rejections aren't topic-based
7. Allows zero actions when none are relevant (DEV-244)
8. Stores validation results in state
9. Returns proactivity state update

Usage in graph:
    graph.add_node("PostProactivity", node_step_100)
    graph.add_edge("LLMSuccess", "PostProactivity")
    graph.add_edge("PostProactivity", "End")
"""

import logging
from typing import Any

from app.core.langgraph.types import RAGState
from app.services.action_regenerator import ActionRegenerator, ResponseContext
from app.services.action_validator import ActionValidator, action_validator

logger = logging.getLogger(__name__)

# DEV-218: Minimum valid actions before triggering regeneration
MIN_VALID_ACTIONS = 2

# DEV-218: ActionRegenerator instance (lazy loaded)
action_regenerator: ActionRegenerator | None = None

# Step 100 is Post-Response Proactivity
STEP_NUM = 100
STEP_ID = "RAG.proactivity.post_response"
NODE_LABEL = "step_100_post_proactivity"

# DEV-200: Routes that use SYNTHESIS_SYSTEM_PROMPT (VERDETTO format)
SYNTHESIS_ROUTES = {"technical_research"}

# DEV-244: Italian verb/preposition prefixes to strip when extracting topic
# These patterns at the start of a query are not the topic itself
ITALIAN_QUERY_PREFIXES = [
    "parlami della ",
    "parlami del ",
    "parlami di ",
    "dimmi della ",
    "dimmi del ",
    "dimmi di ",
    "spiegami la ",
    "spiegami il ",
    "spiegami ",
    "cosa è la ",
    "cosa è il ",
    "cos'è la ",
    "cos'è il ",
    "cos'è ",
    "che cos'è la ",
    "che cos'è il ",
    "che cos'è ",
    "informazioni sulla ",
    "informazioni sul ",
    "informazioni su ",
    "dettagli sulla ",
    "dettagli sul ",
    "dettagli su ",
    "vorrei sapere della ",
    "vorrei sapere del ",
    "vorrei sapere di ",
    "puoi spiegarmi la ",
    "puoi spiegarmi il ",
    "puoi spiegarmi ",
    "mi parli della ",
    "mi parli del ",
    "mi parli di ",
]


def _extract_topic_from_query(query: str) -> str:
    """DEV-244: Extract the actual topic from a user query.

    Strips common Italian verb phrases and prepositions from the start of the query
    to get the actual subject/topic the user is asking about.

    Examples:
        "Parlami della rottamazione quinquies" -> "rottamazione quinquies"
        "Cosa è la pensione anticipata" -> "pensione anticipata"
        "Informazioni sulla NASpI" -> "NASpI"

    Args:
        query: The user's query string

    Returns:
        The extracted topic, or the original query if no prefix matched
    """
    if not query:
        return "argomento fiscale"

    query_lower = query.lower().strip()

    # Try to match and remove prefixes
    for prefix in ITALIAN_QUERY_PREFIXES:
        if query_lower.startswith(prefix):
            # Return the remaining part with original casing
            topic = query.strip()[len(prefix) :]
            if topic:
                return topic[:50]  # Limit length
            break

    # No prefix matched, return original (truncated)
    return query[:50] if query else "argomento fiscale"


def _build_proactivity_update(
    actions: list[dict],
    source: str | None,
    preserve_pre_response: dict | None = None,
) -> dict[str, Any]:
    """Build proactivity state update.

    Args:
        actions: List of suggested action dicts
        source: Action source ("template" or "llm_parsed")
        preserve_pre_response: Pre-response data to preserve

    Returns:
        Dict with proactivity field for state update
    """
    pre_response = preserve_pre_response or {"question": None, "skip_rag": False}

    return {
        "proactivity": {
            "pre_response": pre_response,
            "post_response": {
                "actions": actions,
                "source": source,
            },
        },
    }


def _get_response_content(state: RAGState) -> str:
    """Extract LLM response content from state.

    Args:
        state: Current RAG state

    Returns:
        Response content string
    """
    llm_data = state.get("llm") or {}
    llm_response = llm_data.get("response") if isinstance(llm_data, dict) else None

    if llm_response is None:
        return ""

    if isinstance(llm_response, dict):
        return llm_response.get("content", "")
    elif hasattr(llm_response, "content"):
        return llm_response.content or ""
    elif isinstance(llm_response, str):
        return llm_response

    return ""


def _extract_values_from_text(text: str) -> list[str]:
    """Extract numeric values from text.

    Args:
        text: Text to extract values from

    Returns:
        List of extracted values (percentages, amounts, dates)
    """
    import re

    values = []

    # Percentages (e.g., 22%, 10,5%)
    percentages = re.findall(r"\b\d+(?:[,\.]\d+)?%", text)
    values.extend(percentages)

    # Euro amounts (e.g., €15.000, 5.000 euro)
    euro_amounts = re.findall(r"€\s*[\d.,]+|\b[\d.]+(?:,\d+)?\s*euro\b", text, re.IGNORECASE)
    values.extend(euro_amounts[:5])

    # Dates (e.g., 16/03/2024)
    dates = re.findall(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", text)
    values.extend(dates[:3])

    return list(dict.fromkeys(values))[:10]  # Deduplicate, max 10


def _build_response_context(state: RAGState) -> ResponseContext:
    """Build ResponseContext for action regeneration.

    Args:
        state: Current RAG state

    Returns:
        ResponseContext with answer, sources, and extracted values
    """
    response_content = _get_response_content(state)
    kb_sources = state.get("kb_sources_metadata", [])

    # Extract primary source
    primary_source = {"ref": "Fonte non specificata", "relevant_paragraph": ""}
    if kb_sources:
        first_source = kb_sources[0]
        primary_source = {
            "ref": first_source.get("ref", "Fonte non specificata"),
            "relevant_paragraph": first_source.get("relevant_paragraph", "")[:500],
        }

    # Extract topic from query (DEV-244: strip Italian verb prefixes)
    user_query = state.get("user_query", "")
    main_topic = _extract_topic_from_query(user_query)

    return ResponseContext(
        answer=response_content[:1000],
        primary_source=primary_source,
        extracted_values=_extract_values_from_text(response_content),
        main_topic=main_topic,
        kb_sources=kb_sources,
    )


def _build_topic_context(state: RAGState) -> dict | None:
    """DEV-244: Build topic context for action validation.

    Extracts topic keywords from user query and conversation history
    to filter off-topic suggested actions.

    Args:
        state: Current RAG state

    Returns:
        Dict with current_topic and topic_keywords, or None if not available
    """
    user_query = state.get("user_query", "")
    if not user_query:
        return None

    # Extract significant words from user query as keywords
    # Filter out common Italian stop words and short words
    stop_words = {
        "il",
        "lo",
        "la",
        "i",
        "gli",
        "le",
        "un",
        "una",
        "uno",
        "del",
        "della",
        "dello",
        "dei",
        "delle",
        "degli",
        "al",
        "alla",
        "allo",
        "ai",
        "alle",
        "agli",
        "da",
        "dal",
        "dalla",
        "dallo",
        "dai",
        "dalle",
        "dagli",
        "in",
        "nel",
        "nella",
        "nello",
        "nei",
        "nelle",
        "negli",
        "su",
        "sul",
        "sulla",
        "sullo",
        "sui",
        "sulle",
        "sugli",
        "con",
        "per",
        "tra",
        "fra",
        "di",
        "a",
        "e",
        "o",
        "che",
        "come",
        "cosa",
        "quale",
        "quali",
        "quanto",
        "questo",
        "questa",
        "questi",
        "queste",
        "quello",
        "quella",
        "quelli",
        "quelle",
        "sono",
        "è",
        "hai",
        "ho",
        "ha",
        "hanno",
        "essere",
        "avere",
        "fare",
        "dire",
        "parlami",
        "dimmi",
        "spiegami",
        "raccontami",
        "vorrei",
        "sapere",
        "conoscere",
        "capire",
    }

    # Extract keywords from query
    import re

    words = re.findall(r"\b\w+\b", user_query.lower())
    keywords = [w for w in words if len(w) > 2 and w not in stop_words]

    # Also add KB source topics as keywords
    kb_sources = state.get("kb_sources_metadata", [])
    for source in kb_sources:
        source_topics = source.get("key_topics", [])
        for topic in source_topics:
            if topic.lower() not in keywords:
                keywords.append(topic.lower())

    # Add keywords from conversation history (last 2 turns)
    conversation_history = state.get("conversation_history", [])
    for msg in conversation_history[-4:]:  # Last 2 exchanges
        if msg.get("role") == "user":
            msg_words = re.findall(r"\b\w+\b", msg.get("content", "").lower())
            for w in msg_words:
                if len(w) > 3 and w not in stop_words and w not in keywords:
                    keywords.append(w)

    if not keywords:
        return None

    return {
        "current_topic": user_query[:100],
        "topic_keywords": keywords[:20],  # Limit to 20 keywords
        "user_query": user_query,
    }


def _extract_previous_action_labels(state: RAGState) -> list[str]:
    """DEV-244: Extract labels of previously clicked actions from conversation history.

    When a user clicks a suggested action, the message includes ActionContext
    with selected_action_label. This function extracts all such labels to prevent
    suggesting the same action again.

    Args:
        state: Current RAG state with messages

    Returns:
        List of previously clicked action labels (empty if none)
    """
    previous_labels: list[str] = []
    messages = state.get("messages", [])

    for msg in messages:
        # Messages can be dicts or LangChain message objects
        if isinstance(msg, dict):
            action_context = msg.get("action_context")
        else:
            # LangChain message object
            action_context = getattr(msg, "action_context", None)

        if action_context:
            # action_context can be dict or ActionContext object
            if isinstance(action_context, dict):
                label = action_context.get("selected_action_label")
            else:
                label = getattr(action_context, "selected_action_label", None)

            if label and label not in previous_labels:
                previous_labels.append(label)

    if previous_labels:
        logger.debug(
            "extracted_previous_action_labels",
            extra={
                "count": len(previous_labels),
                "labels": previous_labels,
            },
        )

    return previous_labels


def _build_validation_result_state(
    validation_result: Any,
    actions_source: str,
) -> dict[str, Any]:
    """Build validation result state for storage.

    Args:
        validation_result: BatchValidationResult from validator
        actions_source: Source of actions (e.g., "regenerated")

    Returns:
        Dict with validation result fields
    """
    return {
        "validated_count": len(validation_result.validated_actions),
        "rejected_count": validation_result.rejected_count,
        "quality_score": validation_result.quality_score,
        "regeneration_used": actions_source == "regenerated",
    }


def _build_validation_log(rejection_log: list[tuple[dict, str]]) -> list[str]:
    """Build human-readable validation log.

    Args:
        rejection_log: List of (action, reason) tuples

    Returns:
        List of formatted rejection strings
    """
    return [f"{action.get('label', 'N/A')}: {reason}" for action, reason in rejection_log]


async def node_step_100(state: RAGState) -> dict[str, Any]:
    """Post-Response Proactivity Node with Validation and Golden Loop.

    Adds suggested actions after LLM response. Integrates ActionValidator
    and ActionRegenerator for quality assurance.

    DEV-218: Validates actions and triggers regeneration when <2 valid.

    Args:
        state: Current RAG state with llm response and optional attachments

    Returns:
        State update with proactivity.post_response data and validation results
    """
    request_id = state.get("request_id", "unknown")

    logger.debug(
        "step_100_post_proactivity_enter",
        extra={
            "request_id": request_id,
            "step": STEP_NUM,
            "step_id": STEP_ID,
        },
    )

    # Check if pre-proactivity already triggered - skip post-proactivity
    if state.get("skip_rag_for_proactivity"):
        logger.debug(
            "step_100_skip_pre_proactivity_triggered",
            extra={"request_id": request_id},
        )
        # Preserve existing proactivity state
        existing_proactivity = state.get("proactivity", {})
        return _build_proactivity_update(
            actions=[],
            source=None,
            preserve_pre_response=existing_proactivity.get("pre_response"),
        )

    # Check if chitchat route - skip post-proactivity
    routing_decision = state.get("routing_decision", {})
    if routing_decision.get("route") == "chitchat":
        logger.debug(
            "step_100_skip_chitchat_route",
            extra={"request_id": request_id},
        )
        return _build_proactivity_update(actions=[], source=None)

    try:
        # Lazy import to avoid database connection during module load
        from app.services.proactivity_graph_service import (
            filter_forbidden_actions,
            get_proactivity_graph_service,
        )

        service = get_proactivity_graph_service()

        # DEV-218: Get KB sources for validation context
        kb_sources = state.get("kb_sources_metadata", [])

        # =====================================================================
        # Phase 1: Collect actions from source (prioritized)
        # =====================================================================
        actions: list[dict] = []
        actions_source: str | None = None

        # Priority 0 (DEV-218): Get actions from Step 64 unified output
        suggested_actions = state.get("suggested_actions", [])
        if suggested_actions and state.get("actions_source") != "fallback_needed":
            actions = suggested_actions
            actions_source = state.get("actions_source", "llm_structured")
            logger.debug(
                "step_100_using_step64_actions",
                extra={
                    "request_id": request_id,
                    "action_count": len(actions),
                    "source": actions_source,
                },
            )

        # Priority 1: Check for document attachments with template actions
        if not actions:
            attachments = state.get("attachments", [])
            if attachments:
                for attachment in attachments:
                    doc_type = attachment.get("document_type")
                    if doc_type:
                        template_actions = service.get_document_actions(doc_type)
                        if template_actions:
                            actions = filter_forbidden_actions(template_actions)
                            actions_source = "template"
                            logger.info(
                                "step_100_template_actions",
                                extra={
                                    "request_id": request_id,
                                    "document_type": doc_type,
                                    "action_count": len(actions),
                                },
                            )
                            break

        # Priority 2: Extract from VERDETTO for technical_research routes
        if not actions:
            route = routing_decision.get("route", "")
            if route in SYNTHESIS_ROUTES:
                parsed_synthesis = state.get("parsed_synthesis", {})
                verdetto = parsed_synthesis.get("verdetto", {})
                azione = verdetto.get("azione_consigliata")

                if azione:
                    actions = [
                        {
                            "id": "azione_consigliata",
                            "label": "Segui consiglio",
                            "icon": "✅",
                            "prompt": azione,
                        }
                    ]

                    # Add scadenza action if available and not "Nessuna"
                    scadenza = verdetto.get("scadenza", "")
                    if scadenza and "Nessuna" not in scadenza:
                        actions.append(
                            {
                                "id": "scadenza",
                                "label": "Verifica scadenza",
                                "icon": "📅",
                                "prompt": f"Dettagli sulla scadenza: {scadenza}",
                            }
                        )

                    # Add rischio action if available
                    rischio = verdetto.get("analisi_rischio")
                    if rischio:
                        actions.append(
                            {
                                "id": "rischio",
                                "label": "Analisi rischio",
                                "icon": "⚠️",
                                "prompt": f"Approfondisci l'analisi del rischio: {rischio[:100]}...",
                            }
                        )

                    actions = filter_forbidden_actions(actions)
                    actions_source = "verdetto"
                    logger.info(
                        "step_100_verdetto_actions",
                        extra={
                            "request_id": request_id,
                            "action_count": len(actions),
                            "route": route,
                            "has_scadenza": bool(scadenza and "Nessuna" not in scadenza),
                            "has_rischio": bool(rischio),
                        },
                    )

        # Priority 3: Parse LLM response for suggested_actions XML tags
        if not actions:
            response_content = _get_response_content(state)
            if response_content:
                parsed_actions = service.parse_llm_actions(response_content)
                if parsed_actions:
                    actions = filter_forbidden_actions(parsed_actions)
                    actions_source = "llm_parsed"
                    logger.info(
                        "step_100_llm_parsed_actions",
                        extra={
                            "request_id": request_id,
                            "action_count": len(actions),
                        },
                    )

        # =====================================================================
        # Phase 2: Validate actions using ActionValidator (DEV-218, DEV-244)
        # =====================================================================
        response_text = _get_response_content(state)

        # DEV-244: For template actions, skip topic filtering since they're
        # already curated for specific document types. Only apply topic
        # filtering to LLM-parsed actions which may drift off-topic.
        if actions_source == "template":
            # Template actions are document-type specific, use standard validation
            validation_result = action_validator.validate_batch(
                actions=actions,
                response_text=response_text,
                kb_sources=kb_sources,
            )
            logger.debug(
                "step_100_template_validation_no_topic_filter",
                extra={
                    "request_id": request_id,
                    "action_count": len(actions),
                    "reason": "Template actions skip topic filtering",
                },
            )
        else:
            # DEV-244: Build topic context for filtering off-topic actions
            topic_context = _build_topic_context(state)

            # DEV-244: Extract previously clicked action labels to avoid repetition
            previous_action_labels = _extract_previous_action_labels(state)

            # DEV-244: Use topic-aware validation with previous action filtering
            validation_result = action_validator.validate_batch_with_topic_context(
                actions=actions,
                response_text=response_text,
                kb_sources=kb_sources,
                topic_context=topic_context,
                previous_actions_used=previous_action_labels,  # DEV-244: Filter repeated actions
            )

        logger.debug(
            "step_100_validation_complete",
            extra={
                "request_id": request_id,
                "original_count": len(actions),
                "validated_count": len(validation_result.validated_actions),
                "rejected_count": validation_result.rejected_count,
                "quality_score": validation_result.quality_score,
                "actions_source": actions_source,
                "topic_filtering_applied": actions_source != "template",
            },
        )

        # =====================================================================
        # Phase 3: Trigger regeneration if needed (DEV-218 Golden Loop)
        # DEV-244: Skip regeneration if all rejections are topic-based
        # =====================================================================
        final_actions = validation_result.validated_actions

        # DEV-244: Check if all rejections were topic-based (only relevant when topic filtering was applied)
        # If so, skip regeneration (regenerating would produce more off-topic actions)
        all_topic_rejections = False
        if actions_source != "template":
            all_topic_rejections = action_validator.all_rejections_topic_based(validation_result.rejection_log)

        should_regenerate = (
            len(validation_result.validated_actions) < MIN_VALID_ACTIONS
            and not all_topic_rejections  # DEV-244: Don't regenerate for topic-filtered
        )

        # DEV-244: Log when skipping regeneration due to topic filtering
        if all_topic_rejections and len(validation_result.validated_actions) < MIN_VALID_ACTIONS:
            logger.info(
                "step_100_regeneration_skipped_topic_filtered",
                extra={
                    "request_id": request_id,
                    "valid_count": len(validation_result.validated_actions),
                    "rejected_count": validation_result.rejected_count,
                    "reason": "All rejections were topic-based, regeneration would produce more off-topic actions",
                },
            )

        if should_regenerate:
            logger.info(
                "step_100_regeneration_triggered",
                extra={
                    "request_id": request_id,
                    "valid_count": len(validation_result.validated_actions),
                    "min_required": MIN_VALID_ACTIONS,
                },
            )

            try:
                global action_regenerator
                if action_regenerator is None:
                    # Lazy load regenerator with dependencies
                    from app.services.action_regenerator import get_action_regenerator
                    from app.services.prompt_loader import PromptLoader

                    # Use a mock LLM client for now - will be injected properly
                    prompt_loader = PromptLoader()
                    # Note: In production, inject proper LLM client
                    action_regenerator = get_action_regenerator(prompt_loader, None)

                response_context = _build_response_context(state)
                regenerated = await action_regenerator.regenerate_if_needed(
                    original_actions=actions,
                    validation_result=validation_result,
                    response_context=response_context,
                )

                if regenerated:
                    final_actions = regenerated
                    actions_source = "regenerated"
                    logger.info(
                        "step_100_regeneration_success",
                        extra={
                            "request_id": request_id,
                            "regenerated_count": len(regenerated),
                        },
                    )

            except Exception as regen_error:
                logger.warning(
                    "step_100_regeneration_error",
                    extra={
                        "request_id": request_id,
                        "error": str(regen_error),
                        "error_type": type(regen_error).__name__,
                    },
                )
                # Keep using validated actions on regeneration failure

        # =====================================================================
        # Phase 4: Build result with validation state (DEV-218)
        # =====================================================================
        if not actions and not final_actions:
            logger.debug(
                "step_100_no_actions",
                extra={"request_id": request_id},
            )

        proactivity_update = _build_proactivity_update(
            actions=final_actions,
            source=actions_source,
        )

        # DEV-218: Add validation results to state
        proactivity_update["action_validation_result"] = _build_validation_result_state(
            validation_result=validation_result,
            actions_source=actions_source or "",
        )
        proactivity_update["actions_validation_log"] = _build_validation_log(validation_result.rejection_log)

        return proactivity_update

    except Exception as e:
        # Graceful degradation: log warning with traceback and continue without actions
        import traceback

        tb_str = traceback.format_exc()
        logger.warning(
            f"step_100_post_proactivity_error: {type(e).__name__}: {e}\n{tb_str}",
            extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "traceback": tb_str,
            },
        )
        return _build_proactivity_update(actions=[], source=None)
