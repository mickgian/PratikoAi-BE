"""Node wrapper for Step 100: Post-Response Proactivity. DEV-250: Thin wrapper using web_verification service."""

import logging
from typing import Any

from app.core.langgraph.types import RAGState
from app.core.logging import logger as structlog_logger
from app.services.web_verification import build_proactivity_update, get_response_content

logger = logging.getLogger(__name__)

STEP_NUM = 100
STEP_ID = "RAG.proactivity.post_response"
NODE_LABEL = "step_100_post_proactivity"


async def node_step_100(state: RAGState) -> dict[str, Any]:
    """Post-Response Proactivity Node with Web Verification.

    Handles post-response processing including web verification for
    detecting contradictions between KB answers and web sources.
    """
    request_id = state.get("request_id", "unknown")
    logger.debug(
        "step_100_post_proactivity_enter", extra={"request_id": request_id, "step": STEP_NUM, "step_id": STEP_ID}
    )

    structlog_logger.info(
        "DEV245_step100_topic_keywords",
        request_id=request_id,
        topic_keywords=state.get("topic_keywords"),
        conversation_topic=state.get("conversation_topic"),
    )

    # Check if pre-proactivity already triggered
    if state.get("skip_rag_for_proactivity"):
        logger.debug("step_100_skip_pre_proactivity_triggered", extra={"request_id": request_id})
        existing_proactivity = state.get("proactivity", {})
        return {
            **build_proactivity_update(preserve_pre_response=existing_proactivity.get("pre_response")),
            "topic_keywords": state.get("topic_keywords"),
            "conversation_topic": state.get("conversation_topic"),
        }

    # Check if chitchat route
    routing_decision = state.get("routing_decision", {})
    is_chitchat = routing_decision.get("route") == "chitchat"
    if is_chitchat:
        logger.debug("step_100_skip_chitchat_route", extra={"request_id": request_id})
        return {
            **build_proactivity_update(),
            "topic_keywords": state.get("topic_keywords"),
            "conversation_topic": state.get("conversation_topic"),
        }

    # DEV-245: Web Verification
    web_verification_result = None
    try:
        from app.services.web_verification import web_verification_service

        query_variants = state.get("query_variants", {})
        user_query = query_variants.get("original_query") or state.get("user_query", "")
        response_content = get_response_content(state)
        kb_sources = state.get("kb_sources_metadata", [])
        existing_web_sources = state.get("web_sources_metadata", [])

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
            extra={"request_id": request_id, "error": str(web_error), "error_type": type(web_error).__name__},
        )

    proactivity_update = build_proactivity_update()

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
        extra={"request_id": request_id, "proactivity_keys": list(proactivity_update.keys())},
    )

    return {
        **proactivity_update,
        "topic_keywords": state.get("topic_keywords"),
        "conversation_topic": state.get("conversation_topic"),
    }
