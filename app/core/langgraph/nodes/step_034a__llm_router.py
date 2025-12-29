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

# Lazy import to avoid database connection during module load
if TYPE_CHECKING:
    from app.services.llm_router_service import LLMRouterService

logger = logging.getLogger(__name__)

# Step 34a is a sub-step of Step 34 (Agentic RAG Router)
STEP_NUM = 34
STEP_ID = "RAG.routing.llm_router"
NODE_LABEL = "step_034a_llm_router"


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

    # Return updated state with routing_decision
    return {
        **state,
        "routing_decision": routing_decision,
    }
