"""Node wrapper for Step 32: Calculate Scores.

Internal step - calculates domain and action scores using Italian keyword matching.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.classify import step_32__calc_scores
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 32


async def node_step_32(state: RAGState) -> RAGState:
    """Node wrapper for Step 32: Calculate domain and action scores.

    Args:
        state: Current RAG state

    Returns:
        Updated state with score data
    """
    rag_step_log(STEP, "enter")

    with rag_step_timer(STEP):
        res = await step_32__calc_scores(
            messages=state.get("messages", []),
            ctx=dict(state)
        )

        # Update classification with scores
        classification = state.setdefault("classification", {})
        if "domain_scores" in res:
            classification["domain_scores"] = res["domain_scores"]
        if "action_scores" in res:
            classification["action_scores"] = res["action_scores"]
        if "matched_keywords" in res:
            classification["matched_keywords"] = res["matched_keywords"]

    rag_step_log(STEP, "exit", scores_calculated=True)
    return state
