"""Node wrapper for Step 34a: LLM Router. DEV-250: Thin wrapper using topic_extraction service."""

import logging
from typing import TYPE_CHECKING

from app.core.langgraph.types import RAGState
from app.core.logging import logger as structlog_logger
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.services.topic_extraction import (
    create_fallback_decision,
    decision_to_dict,
    extract_topic_keywords,
)

if TYPE_CHECKING:
    from app.services.llm_router_service import LLMRouterService

logger = logging.getLogger(__name__)

STEP_NUM = 34
STEP_ID = "RAG.routing.llm_router"
NODE_LABEL = "step_034a_llm_router"


async def node_step_34a(state: RAGState) -> RAGState:
    """LLM Router node for semantic query classification.

    Classifies user queries into semantic categories for intelligent routing:
    - CHITCHAT: Casual conversation, handled directly
    - CALCULATOR: Calculation requests, routed to calculator tools
    - THEORETICAL_DEFINITION: Definition requests, RAG retrieval
    - TECHNICAL_RESEARCH: Complex queries, full RAG retrieval
    - GOLDEN_SET: Known high-value patterns, golden set lookup
    """
    user_query = state.get("user_query", "")
    messages = state.get("messages", [])

    if not user_query and messages:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_query = msg.get("content", "")
                break

    rag_step_log(STEP_NUM, STEP_ID, f"{NODE_LABEL}.enter", query_length=len(user_query) if user_query else 0)

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        try:
            from app.core.llm.model_config import get_model_config
            from app.services.llm_router_service import LLMRouterService

            config = get_model_config()
            router_service = LLMRouterService(config=config)
            decision = await router_service.route(query=user_query, history=messages)
            routing_decision = decision_to_dict(decision)
            logger.info(
                f"Step {NODE_LABEL}: Routed to {routing_decision['route']} "
                f"with confidence {routing_decision['confidence']:.2f}"
            )

        except Exception as e:
            logger.warning(f"Step {NODE_LABEL}: LLM router error, falling back to TECHNICAL_RESEARCH: {e}")
            routing_decision = create_fallback_decision()

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        route=routing_decision["route"],
        confidence=routing_decision["confidence"],
        needs_retrieval=routing_decision["needs_retrieval"],
    )

    # DEV-245 Phase 5.3: Extract and persist conversation topic on first query
    conversation_topic = state.get("conversation_topic")
    topic_keywords = state.get("topic_keywords")

    # DEV-245 Phase 5.4: Type safety - validate topic_keywords is a valid list
    if topic_keywords and not isinstance(topic_keywords, list):
        logger.warning(
            f"Step {NODE_LABEL}: topic_keywords has invalid type {type(topic_keywords).__name__}, resetting"
        )
        topic_keywords = None

    structlog_logger.info(
        "DEV245_step034a_topic_keywords",
        topic_keywords_from_state=topic_keywords,
        is_followup=routing_decision.get("is_followup", False),
        will_extract_new=not topic_keywords,
    )

    # DEV-245 Phase 5.11: Extract topic_keywords whenever missing
    if not topic_keywords:
        topic_keywords = extract_topic_keywords(user_query)
        conversation_topic = user_query
        if topic_keywords:
            logger.info(f"Step {NODE_LABEL}: Extracted topic keywords: {topic_keywords}")

    return {
        **state,
        "routing_decision": routing_decision,
        "conversation_topic": conversation_topic,
        "topic_keywords": topic_keywords,
    }
