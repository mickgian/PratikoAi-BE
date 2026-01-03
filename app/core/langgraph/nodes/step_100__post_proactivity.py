"""Step 100: Post-Response Proactivity Node (DEV-200, DEV-201, DEV-218).

LangGraph node that adds suggested actions AFTER LLM response. It uses template
actions for recognized document types, extracts from VERDETTO for technical_research,
or parses LLM response for contextual actions.

DEV-201d: Integrates forbidden action filtering to prevent inappropriate suggestions.
DEV-218: Integrates ActionValidator and Golden Loop regeneration.

The node:
1. Checks if pre-proactivity already triggered (skip if so)
2. Checks if chitchat route (skip if so)
3. Gets actions from Step 64 unified output or falls back to legacy sources
4. Validates actions using ActionValidator (DEV-215)
5. Triggers ActionRegenerator if <2 valid actions (DEV-217 Golden Loop)
6. Stores validation results in state
7. Returns proactivity state update

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

    # Extract topic from query
    user_query = state.get("user_query", "")
    main_topic = user_query[:50] if user_query else "argomento fiscale"

    return ResponseContext(
        answer=response_content[:1000],
        primary_source=primary_source,
        extracted_values=_extract_values_from_text(response_content),
        main_topic=main_topic,
        kb_sources=kb_sources,
    )


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
        # Phase 2: Validate actions using ActionValidator (DEV-218)
        # =====================================================================
        response_text = _get_response_content(state)

        validation_result = action_validator.validate_batch(
            actions=actions,
            response_text=response_text,
            kb_sources=kb_sources,
        )

        logger.debug(
            "step_100_validation_complete",
            extra={
                "request_id": request_id,
                "original_count": len(actions),
                "validated_count": len(validation_result.validated_actions),
                "rejected_count": validation_result.rejected_count,
                "quality_score": validation_result.quality_score,
            },
        )

        # =====================================================================
        # Phase 3: Trigger regeneration if needed (DEV-218 Golden Loop)
        # =====================================================================
        final_actions = validation_result.validated_actions

        if len(validation_result.validated_actions) < MIN_VALID_ACTIONS:
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
