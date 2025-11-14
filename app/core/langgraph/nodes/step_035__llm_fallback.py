"""Node wrapper for Step 35: LLM Fallback.

Internal step - uses LLM classification when rule-based confidence is low.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.classify import step_35__llm_fallback
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 35


async def node_step_35(state: RAGState) -> RAGState:
    """Node wrapper for Step 35: LLM classification fallback.

    Args:
        state: Current RAG state with low-confidence classification

    Returns:
        Updated state with LLM classification result
    """
    rag_step_log(STEP, "enter", fallback_triggered=True)

    with rag_step_timer(STEP):
        res = await step_35__llm_fallback(
            ctx=dict(state)
        )

        # Update classification with LLM results
        classification = state.setdefault("classification", {})
        if "llm_domain" in res:
            classification["llm_domain"] = res["llm_domain"]
        if "llm_action" in res:
            classification["llm_action"] = res["llm_action"]
        if "llm_confidence" in res:
            classification["llm_confidence"] = res["llm_confidence"]
        classification["llm_fallback_used"] = res.get("fallback_used", True)

    rag_step_log(
        STEP,
        "exit",
        llm_confidence=classification.get("llm_confidence", 0.0)
    )
    return state
