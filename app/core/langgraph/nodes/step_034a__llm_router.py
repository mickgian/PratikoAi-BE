"""Node wrapper for Step 34a: LLM Router.

DEV-250: Thin wrapper using topic_extraction service.
DEV-251: HuggingFace zero-shot classifier integration for cost reduction.
"""

from typing import TYPE_CHECKING

from app.core.langgraph.types import RAGState
from app.core.logging import logger
from app.observability.rag_logging import rag_step_log, rag_step_timer
from app.services.topic_extraction import (
    create_fallback_decision,
    decision_to_dict,
    extract_topic_keywords,
    hf_result_to_decision_dict,
)

if TYPE_CHECKING:
    from app.services.llm_router_service import LLMRouterService

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
            # DEV-251: Try HuggingFace zero-shot classifier first (fast, free)
            from app.services.hf_intent_classifier import get_hf_intent_classifier

            hf_classifier = get_hf_intent_classifier()
            hf_result = await hf_classifier.classify_async(user_query)

            if not hf_classifier.should_fallback_to_gpt(hf_result):
                # High confidence - use HF result
                # DEV-251 Part 3.1: Pass query for follow-up detection
                routing_decision = hf_result_to_decision_dict(hf_result, query=user_query)
                logger.info(
                    "DEV251_hf_classification_used",
                    step=NODE_LABEL,
                    route=routing_decision["route"],
                    confidence=hf_result.confidence,
                    is_followup=routing_decision.get("is_followup", False),
                    all_scores=hf_result.all_scores,
                )
            else:
                # Low confidence - fall back to GPT-4o-mini router
                logger.info(
                    "DEV251_gpt_fallback_triggered",
                    step=NODE_LABEL,
                    hf_intent=hf_result.intent,
                    hf_confidence=hf_result.confidence,
                    threshold=hf_classifier.confidence_threshold,
                )

                from app.core.llm.model_config import get_model_config
                from app.services.llm_router_service import LLMRouterService

                config = get_model_config()
                router_service = LLMRouterService(config=config)
                decision = await router_service.route(query=user_query, history=messages)
                routing_decision = decision_to_dict(decision)
                logger.info(
                    "DEV251_gpt_fallback_complete",
                    step=NODE_LABEL,
                    route=routing_decision["route"],
                    confidence=routing_decision["confidence"],
                )

        except Exception as e:
            logger.error(
                "llm_router_failed",
                step=NODE_LABEL,
                operation="classify_intent",
                query_length=len(user_query) if user_query else 0,
                error_type=type(e).__name__,
                error_message=str(e),
            )
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
            "topic_keywords_invalid_type",
            step=NODE_LABEL,
            actual_type=type(topic_keywords).__name__,
            action="resetting_to_none",
        )
        topic_keywords = None

    logger.info(
        "DEV245_step034a_topic_keywords",
        step=NODE_LABEL,
        topic_keywords_from_state=topic_keywords,
        is_followup=routing_decision.get("is_followup", False),
        will_extract_new=not topic_keywords,
    )

    # DEV-245 Phase 5.11: Extract topic_keywords whenever missing
    if not topic_keywords:
        topic_keywords = extract_topic_keywords(user_query)
        conversation_topic = user_query
        if topic_keywords:
            logger.info(
                "topic_keywords_extracted",
                step=NODE_LABEL,
                keywords=topic_keywords,
            )

    return {
        **state,
        "routing_decision": routing_decision,
        "conversation_topic": conversation_topic,
        "topic_keywords": topic_keywords,
    }
