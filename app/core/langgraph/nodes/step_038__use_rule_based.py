"""Node wrapper for Step 38: Use Rule-Based Classification.

Internal step - adopts rule-based classification as final result.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_38__use_rule_based
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 38


async def node_step_38(state: RAGState) -> RAGState:
    """Node wrapper for Step 38: Use rule-based classification.

    Args:
        state: Current RAG state with rule-based classification

    Returns:
        Updated state with rule-based classification as final
    """
    rag_step_log(STEP, "enter", using_rule_based=True)

    with rag_step_timer(STEP):
        res = await step_38__use_rule_based(
            messages=state.get("messages", []),
            ctx=dict(state)
        )

        # Keep rule-based classification as final
        classification = state.setdefault("classification", {})
        classification["domain"] = res.get("domain")
        classification["action"] = res.get("action")
        classification["confidence"] = res.get("confidence", 0.0)
        classification["method_used"] = "rule_based"
        classification["fallback_used"] = False

    rag_step_log(
        STEP,
        "exit",
        domain=classification.get("domain"),
        confidence=classification.get("confidence")
    )
    return state
