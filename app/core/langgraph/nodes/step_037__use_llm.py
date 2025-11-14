"""Node wrapper for Step 37: Use LLM Classification.

Internal step - adopts LLM classification as final result.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.llm import step_37__use_llm
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 37


async def node_step_37(state: RAGState) -> RAGState:
    """Node wrapper for Step 37: Use LLM classification.

    Args:
        state: Current RAG state with LLM classification

    Returns:
        Updated state with LLM classification as final
    """
    rag_step_log(STEP, "enter", using_llm=True)

    with rag_step_timer(STEP):
        res = await step_37__use_llm(
            messages=state.get("messages", []),
            ctx=dict(state)
        )

        # Set LLM classification as final
        classification = state.setdefault("classification", {})
        classification["domain"] = res.get("domain")
        classification["action"] = res.get("action")
        classification["confidence"] = res.get("confidence", 0.0)
        classification["method_used"] = "llm"
        classification["fallback_used"] = True

    rag_step_log(
        STEP,
        "exit",
        domain=classification.get("domain"),
        confidence=classification.get("confidence")
    )
    return state
