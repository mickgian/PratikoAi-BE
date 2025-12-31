"""Step 100: Post-Response Proactivity Node (DEV-200, DEV-201).

LangGraph node that adds suggested actions AFTER LLM response. It uses template
actions for recognized document types, extracts from VERDETTO for technical_research,
or parses LLM response for contextual actions.

DEV-201d: Integrates forbidden action filtering to prevent inappropriate suggestions.

The node:
1. Checks if pre-proactivity already triggered (skip if so)
2. Checks if chitchat route (skip if so)
3. Checks for document attachments → template actions
4. Checks for VERDETTO in technical_research responses → extract AZIONE CONSIGLIATA
5. Falls back to parsing LLM response for suggested_actions XML tags
6. Filters out forbidden actions (DEV-201d)
7. Returns proactivity state update

Usage in graph:
    graph.add_node("PostProactivity", node_step_100)
    graph.add_edge("LLMSuccess", "PostProactivity")
    graph.add_edge("PostProactivity", "End")
"""

import logging
from typing import Any

from app.core.langgraph.types import RAGState

logger = logging.getLogger(__name__)

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


async def node_step_100(state: RAGState) -> dict[str, Any]:
    """Post-Response Proactivity Node.

    Adds suggested actions after LLM response. Checks document type for
    template actions first, then falls back to parsing LLM response.

    Args:
        state: Current RAG state with llm response and optional attachments

    Returns:
        State update with proactivity.post_response data
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

        # Priority 1: Check for document attachments with template actions
        attachments = state.get("attachments", [])
        if attachments:
            for attachment in attachments:
                doc_type = attachment.get("document_type")
                if doc_type:
                    actions = service.get_document_actions(doc_type)
                    if actions:
                        # DEV-201d: Filter forbidden actions
                        actions = filter_forbidden_actions(actions)
                        logger.info(
                            "step_100_template_actions",
                            extra={
                                "request_id": request_id,
                                "document_type": doc_type,
                                "action_count": len(actions),
                            },
                        )
                        return _build_proactivity_update(
                            actions=actions,
                            source="template",
                        )

        # Priority 2: Extract from VERDETTO for technical_research routes
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

                # DEV-201d: Filter forbidden actions
                actions = filter_forbidden_actions(actions)
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
                return _build_proactivity_update(
                    actions=actions,
                    source="verdetto",
                )

        # Priority 3: Parse LLM response for suggested_actions XML tags
        llm_data = state.get("llm") or {}
        llm_response = llm_data.get("response") if isinstance(llm_data, dict) else None

        # Handle both dict and LangChain message objects
        response_content = ""
        if llm_response is not None:
            if isinstance(llm_response, dict):
                response_content = llm_response.get("content", "")
            elif hasattr(llm_response, "content"):
                # LangChain AIMessage or similar object
                response_content = llm_response.content or ""
            elif isinstance(llm_response, str):
                # Direct string response
                response_content = llm_response

        if response_content:
            actions = service.parse_llm_actions(response_content)
            if actions:
                # DEV-201d: Filter forbidden actions
                actions = filter_forbidden_actions(actions)
                logger.info(
                    "step_100_llm_parsed_actions",
                    extra={
                        "request_id": request_id,
                        "action_count": len(actions),
                    },
                )
                return _build_proactivity_update(
                    actions=actions,
                    source="llm_parsed",
                )

        # No actions found
        logger.debug(
            "step_100_no_actions",
            extra={"request_id": request_id},
        )
        return _build_proactivity_update(actions=[], source=None)

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
