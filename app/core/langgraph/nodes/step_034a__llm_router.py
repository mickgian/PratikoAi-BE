"""Step 34a: LLM Router Node (DEV-194).

LangGraph node wrapper that integrates LLMRouterService for semantic query
classification. This replaces regex-based routing with LLM-powered semantic
understanding.

The node:
1. Extracts user query and conversation history from state
2. Calls LLMRouterService.route() for semantic classification
3. Stores the RouterDecision as a serializable dict in state["routing_decision"]
4. Falls back to TECHNICAL_RESEARCH on any error

Usage in graph:
    graph.add_node("step_34a_llm_router", node_step_34a)
"""

import logging
from typing import TYPE_CHECKING, Any

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log,
    rag_step_timer,
)
from app.schemas.router import RouterDecision, RoutingCategory
from app.services.italian_stop_words import STOP_WORDS_MINIMAL

# Lazy import to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.llm_router_service import LLMRouterService

logger = logging.getLogger(__name__)

# Step 34a is a sub-step of Step 34 (Agentic RAG Router)
STEP_NUM = 34
STEP_ID = "RAG.routing.llm_router"
NODE_LABEL = "step_034a_llm_router"

# DEV-245 Phase 5.14: _TOPIC_STOP_WORDS replaced by centralized STOP_WORDS_MINIMAL
# from app.services.italian_stop_words (imported at top of file)


def _extract_topic_keywords(query: str) -> list[str]:
    """DEV-245 Phase 5.3: Extract topic keywords from first query.

    Extracts significant keywords that represent the conversation topic.
    These keywords persist across all turns to prevent context loss.

    DEV-245 Phase 5.14: Uses centralized STOP_WORDS_MINIMAL from italian_stop_words module.

    Example:
        "parlami della rottamazione quinquies"
        → ["rottamazione", "quinquies"]

    Args:
        query: The first user query (natural language)

    Returns:
        List of significant keywords (lowercase), max 5 keywords
    """
    import re

    # Normalize: lowercase, remove punctuation
    text = query.lower()
    text = re.sub(r"[^\w\s]", " ", text)

    # Tokenize and filter using centralized stop words
    # DEV-245 Phase 5.14: Use STOP_WORDS_MINIMAL for topic extraction
    words = text.split()
    keywords = [w for w in words if len(w) >= 3 and w not in STOP_WORDS_MINIMAL]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    # Cap at 5 keywords
    return unique_keywords[:5]


def _decision_to_dict(decision: RouterDecision) -> dict[str, Any]:
    """Convert RouterDecision to a serializable dict for state storage.

    Args:
        decision: RouterDecision from LLMRouterService

    Returns:
        Dict representation with all fields serialized
    """
    return {
        "route": decision.route.value,  # Convert enum to string
        "confidence": decision.confidence,
        "reasoning": decision.reasoning,
        "entities": [
            {
                "text": entity.text,
                "type": entity.type,
                "confidence": entity.confidence,
            }
            for entity in decision.entities
        ],
        "requires_freshness": decision.requires_freshness,
        "suggested_sources": decision.suggested_sources,
        "needs_retrieval": decision.needs_retrieval,
        "is_followup": decision.is_followup,  # DEV-245: Follow-up detection
    }


def _create_fallback_decision() -> dict[str, Any]:
    """Create a fallback routing decision for error cases.

    Falls back to TECHNICAL_RESEARCH which will trigger full RAG retrieval.

    Returns:
        Fallback routing decision dict
    """
    return {
        "route": RoutingCategory.TECHNICAL_RESEARCH.value,
        "confidence": 0.3,
        "reasoning": "Fallback: LLM router service unavailable, defaulting to technical research",
        "entities": [],
        "requires_freshness": False,
        "suggested_sources": [],
        "needs_retrieval": True,
        "is_followup": False,  # DEV-245: Default to not follow-up
    }


async def node_step_34a(state: RAGState) -> RAGState:
    """LLM Router node for semantic query classification.

    This node integrates the LLMRouterService to classify user queries
    into semantic categories for intelligent routing:
    - CHITCHAT: Casual conversation, handled directly
    - CALCULATOR: Calculation requests, routed to calculator tools
    - THEORETICAL_DEFINITION: Definition requests, RAG retrieval
    - TECHNICAL_RESEARCH: Complex queries, full RAG retrieval
    - GOLDEN_SET: Known high-value patterns, golden set lookup

    Args:
        state: Current RAG state containing user_query and messages

    Returns:
        Updated state with routing_decision dict
    """
    user_query = state.get("user_query", "")
    messages = state.get("messages", [])

    # Extract query from last message if user_query not set
    if not user_query and messages:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_query = msg.get("content", "")
                break

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.enter",
        query_length=len(user_query) if user_query else 0,
    )

    with rag_step_timer(STEP_NUM, STEP_ID, NODE_LABEL):
        try:
            # Lazy import to avoid database connection during module load
            from app.core.llm.model_config import get_model_config
            from app.services.llm_router_service import LLMRouterService

            # Initialize router service with config and get routing decision
            config = get_model_config()
            router_service = LLMRouterService(config=config)
            decision = await router_service.route(
                query=user_query,
                history=messages,
            )

            routing_decision = _decision_to_dict(decision)

            logger.info(
                f"Step {NODE_LABEL}: Routed to {routing_decision['route']} "
                f"with confidence {routing_decision['confidence']:.2f}"
            )

        except Exception as e:
            logger.warning(f"Step {NODE_LABEL}: LLM router error, falling back to TECHNICAL_RESEARCH: {e}")
            routing_decision = _create_fallback_decision()

    rag_step_log(
        STEP_NUM,
        STEP_ID,
        f"{NODE_LABEL}.exit",
        route=routing_decision["route"],
        confidence=routing_decision["confidence"],
        needs_retrieval=routing_decision["needs_retrieval"],
    )

    # DEV-245 Phase 5.3: Extract and persist conversation topic on first query
    # Topic keywords are preserved across all turns to prevent context loss at Q4+
    conversation_topic = state.get("conversation_topic")
    topic_keywords = state.get("topic_keywords")

    # DEV-245 Phase 5.4: Type safety - validate topic_keywords is a valid list
    # If corrupted (e.g., string or dict), reset to None and re-extract
    if topic_keywords and not isinstance(topic_keywords, list):
        logger.warning(
            f"Step {NODE_LABEL}: topic_keywords has invalid type {type(topic_keywords).__name__}, resetting"
        )
        topic_keywords = None

    # DEV-245 Phase 5.10: Debug log at step_034a before topic extraction decision
    # Use structlog for debug logging (supports kwargs)
    from app.core.logging import logger as structlog_logger

    structlog_logger.info(
        "DEV245_step034a_topic_keywords",
        topic_keywords_from_state=topic_keywords,
        is_followup=routing_decision.get("is_followup", False),
        will_extract_new=not topic_keywords,  # Phase 5.11: Extract whenever missing
    )

    # DEV-245 Phase 5.11: Extract topic_keywords whenever missing
    # Don't rely solely on is_followup - it can be incorrectly True for first queries
    # The LLM Router may misclassify the first query as a follow-up, which would
    # prevent topic extraction and cause all downstream steps to have topic_keywords=None
    if not topic_keywords:
        # No topic keywords yet: extract from current query
        topic_keywords = _extract_topic_keywords(user_query)
        conversation_topic = user_query  # Store original query as topic reference

        if topic_keywords:
            logger.info(f"Step {NODE_LABEL}: Extracted topic keywords: {topic_keywords}")

    # Return updated state with routing_decision and topic tracking
    return {
        **state,
        "routing_decision": routing_decision,
        "conversation_topic": conversation_topic,
        "topic_keywords": topic_keywords,
    }
