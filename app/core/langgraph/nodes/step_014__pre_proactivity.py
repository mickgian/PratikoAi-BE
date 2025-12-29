"""Step 14: Pre-Response Proactivity Node (DEV-200).

LangGraph node that checks if a calculable intent (IRPEF, IVA, INPS, etc.)
has missing parameters BEFORE RAG execution. If missing, it returns an
InteractiveQuestion and sets skip_rag_for_proactivity=True to bypass RAG.

The node:
1. Extracts user query from state
2. Calls ProactivityGraphService.check_calculable_intent()
3. If missing params: stores InteractiveQuestion and sets skip_rag=True
4. If all params present or non-calculable: continues to RAG

Usage in graph:
    graph.add_node("PreProactivity", node_step_14)
    graph.add_conditional_edges("PreProactivity", route_pre_proactivity, {...})
"""

import logging
from typing import Any

from app.core.langgraph.types import RAGState

logger = logging.getLogger(__name__)

# Step 14 is Pre-Response Proactivity
STEP_NUM = 14
STEP_ID = "RAG.proactivity.pre_response"
NODE_LABEL = "step_014_pre_proactivity"


def _build_proactivity_state(
    question: dict | None,
    skip_rag: bool,
) -> dict[str, Any]:
    """Build proactivity state update.

    Args:
        question: InteractiveQuestion dict or None
        skip_rag: Whether to skip RAG execution

    Returns:
        Dict with proactivity field for state update
    """
    return {
        "proactivity": {
            "pre_response": {
                "question": question,
                "skip_rag": skip_rag,
            },
            "post_response": {
                "actions": [],
                "source": None,
            },
        },
    }


async def node_step_14(state: RAGState) -> dict[str, Any]:
    """Pre-Response Proactivity Node.

    Checks if the user query is a calculable intent (IRPEF, IVA, INPS, etc.)
    with missing required parameters. If so, generates an InteractiveQuestion
    and signals to skip RAG execution.

    Args:
        state: Current RAG state with user_query

    Returns:
        State update with proactivity data and optional skip_rag_for_proactivity flag
    """
    request_id = state.get("request_id", "unknown")
    user_query = state.get("user_query", "")

    logger.debug(
        "step_14_pre_proactivity_enter",
        extra={
            "request_id": request_id,
            "step": STEP_NUM,
            "step_id": STEP_ID,
            "query_preview": user_query[:50] if user_query else "N/A",
        },
    )

    # Empty query - skip proactivity
    if not user_query or not user_query.strip():
        logger.debug(
            "step_14_empty_query_skip",
            extra={"request_id": request_id},
        )
        return _build_proactivity_state(question=None, skip_rag=False)

    try:
        # Lazy import to avoid database connection during module load
        from app.services.proactivity_graph_service import get_proactivity_graph_service

        service = get_proactivity_graph_service()
        routing_decision = state.get("routing_decision")

        needs_question, question = service.check_calculable_intent(
            query=user_query,
            routing_decision=routing_decision,
        )

        if needs_question and question:
            logger.info(
                "step_14_question_generated",
                extra={
                    "request_id": request_id,
                    "question_id": question.get("id"),
                    "field_count": len(question.get("fields", [])),
                },
            )
            result = _build_proactivity_state(question=question, skip_rag=True)
            result["skip_rag_for_proactivity"] = True
            return result

        # No question needed - continue to RAG
        logger.debug(
            "step_14_no_question_continue",
            extra={
                "request_id": request_id,
                "needs_question": needs_question,
            },
        )
        return _build_proactivity_state(question=None, skip_rag=False)

    except Exception as e:
        # Graceful degradation: log warning and continue without proactivity
        logger.warning(
            "step_14_pre_proactivity_error",
            extra={
                "request_id": request_id,
                "error": str(e),
            },
        )
        return _build_proactivity_state(question=None, skip_rag=False)


def route_pre_proactivity(state: RAGState) -> str:
    """Route from PreProactivity - skip RAG if InteractiveQuestion needed.

    Args:
        state: Current RAG state

    Returns:
        "skip_rag" if should bypass RAG, "continue" otherwise
    """
    if state.get("skip_rag_for_proactivity"):
        return "skip_rag"
    return "continue"
