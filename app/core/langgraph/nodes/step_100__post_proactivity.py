"""Step 100: Post-Response Proactivity Node (DEV-245).

LangGraph node that handles post-response processing including web verification.

DEV-245: Web verification to detect contradictions and add caveats.
DEV-245 Phase 5.15: Removed suggested actions feature per user feedback.

The node:
1. Checks if pre-proactivity already triggered (skip if so)
2. Checks if chitchat route (skip if so)
3. DEV-245: Runs web verification to detect contradictions with KB answer
4. Returns proactivity state update with web verification caveats

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


def _build_proactivity_update(
    preserve_pre_response: dict | None = None,
) -> dict[str, Any]:
    """Build proactivity state update.

    Args:
        preserve_pre_response: Pre-response data to preserve

    Returns:
        Dict with proactivity field for state update
    """
    pre_response = preserve_pre_response or {"question": None, "skip_rag": False}

    return {
        "proactivity": {
            "pre_response": pre_response,
            "post_response": {
                # DEV-245 Phase 5.15: Actions removed per user feedback
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


async def node_step_100(state: RAGState) -> dict[str, Any]:
    """Post-Response Proactivity Node with Web Verification.

    Handles post-response processing including web verification for
    detecting contradictions between KB answers and web sources.

    DEV-245 Phase 5.15: Suggested actions feature removed per user feedback.

    Args:
        state: Current RAG state with llm response

    Returns:
        State update with web verification results and topic preservation
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

    # DEV-245 Phase 5.10: Debug log at step_100 entry to verify topic_keywords survived
    from app.core.logging import logger as structlog_logger

    structlog_logger.info(
        "DEV245_step100_topic_keywords",
        request_id=request_id,
        topic_keywords=state.get("topic_keywords"),
        conversation_topic=state.get("conversation_topic"),
    )

    # Check if pre-proactivity already triggered - skip post-proactivity
    if state.get("skip_rag_for_proactivity"):
        logger.debug(
            "step_100_skip_pre_proactivity_triggered",
            extra={"request_id": request_id},
        )
        existing_proactivity = state.get("proactivity", {})
        return {
            **_build_proactivity_update(
                preserve_pre_response=existing_proactivity.get("pre_response"),
            ),
            "topic_keywords": state.get("topic_keywords"),
            "conversation_topic": state.get("conversation_topic"),
        }

    # Check if chitchat route - skip post-proactivity
    routing_decision = state.get("routing_decision", {})
    is_chitchat = routing_decision.get("route") == "chitchat"
    if is_chitchat:
        logger.debug(
            "step_100_skip_chitchat_route",
            extra={"request_id": request_id},
        )
        return {
            **_build_proactivity_update(),
            "topic_keywords": state.get("topic_keywords"),
            "conversation_topic": state.get("conversation_topic"),
        }

    # =========================================================================
    # DEV-245 Phase 3.1: Web Verification
    # Detect contradictions between KB answer and web sources, add caveats
    # DEV-245: With Parallel Hybrid RAG, use existing web sources from state
    # =========================================================================
    web_verification_result = None
    try:
        from app.services.web_verification import web_verification_service

        # DEV-245 Phase 3.6: Use reformulated query for web verification
        query_variants = state.get("query_variants", {})
        user_query = query_variants.get("original_query") or state.get("user_query", "")

        response_content = _get_response_content(state)
        kb_sources = state.get("kb_sources_metadata", [])

        # DEV-245: Get existing web sources from Parallel Hybrid RAG (Step 40)
        existing_web_sources = state.get("web_sources_metadata", [])

        # Run web verification for non-chitchat routes with substantial responses
        route = routing_decision.get("route", "")
        should_verify = route != "chitchat" and response_content and len(response_content) > 100

        logger.debug(
            "step_100_web_verification_check",
            extra={
                "request_id": request_id,
                "route": route,
                "should_verify": should_verify,
                "response_length": len(response_content) if response_content else 0,
                "existing_web_sources_count": len(existing_web_sources),
            },
        )

        if should_verify:
            # DEV-246: Pass user_id and session_id for Brave API cost tracking
            web_verification_result = await web_verification_service.verify_answer(
                user_query=user_query,
                kb_answer=response_content,
                kb_sources=kb_sources,
                skip_for_chitchat=is_chitchat,
                existing_web_sources=existing_web_sources,
                messages=state.get("messages", []),
                topic_keywords=state.get("topic_keywords"),
                user_id=state.get("user_id"),
                session_id=state.get("session_id"),
            )

            if web_verification_result and web_verification_result.has_caveats:
                logger.info(
                    "step_100_caveats_found",
                    extra={
                        "request_id": request_id,
                        "caveat_count": len(web_verification_result.caveats),
                        "web_sources_checked": web_verification_result.web_sources_checked,
                        "used_existing_sources": len(existing_web_sources) > 0,
                    },
                )

    except Exception as web_error:
        logger.warning(
            "step_100_web_verification_error",
            extra={
                "request_id": request_id,
                "error": str(web_error),
                "error_type": type(web_error).__name__,
            },
        )

    # Build result
    proactivity_update = _build_proactivity_update()

    # DEV-245: Add web verification results to state
    if web_verification_result:
        proactivity_update["web_verification"] = {
            "caveats": web_verification_result.caveats,
            "has_caveats": web_verification_result.has_caveats,
            "web_sources_checked": web_verification_result.web_sources_checked,
            "verification_performed": web_verification_result.verification_performed,
            "brave_ai_summary": web_verification_result.brave_ai_summary,
            "synthesized_response": web_verification_result.synthesized_response,
            "has_synthesized_response": web_verification_result.has_synthesized_response,
        }
        logger.debug(
            "step_100_web_verification_added",
            extra={
                "request_id": request_id,
                "has_caveats": web_verification_result.has_caveats,
                "caveat_count": len(web_verification_result.caveats),
                "has_synthesized": web_verification_result.has_synthesized_response,
            },
        )

    logger.debug(
        "step_100_returning_proactivity",
        extra={
            "request_id": request_id,
            "proactivity_keys": list(proactivity_update.keys()),
        },
    )

    return {
        **proactivity_update,
        "topic_keywords": state.get("topic_keywords"),
        "conversation_topic": state.get("conversation_topic"),
    }
