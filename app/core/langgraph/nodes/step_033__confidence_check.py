"""Node wrapper for Step 33: Confidence Check.

Internal step - checks if classification confidence meets threshold.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.classify import step_33__confidence_check

STEP = 33


async def node_step_33(state: RAGState) -> RAGState:
    """Node wrapper for Step 33: Confidence threshold check.

    Args:
        state: Current RAG state with classification scores

    Returns:
        Updated state with confidence check result
    """
    confidence = state.get("classification", {}).get("confidence", 0.0)
    rag_step_log(STEP, "enter", confidence=confidence)

    with rag_step_timer(STEP):
        res = await step_33__confidence_check(messages=state.get("messages", []), ctx=dict(state))

        # Store confidence check result
        classification = state.setdefault("classification", {})
        classification["confidence_sufficient"] = res.get("confidence_sufficient", False)
        classification["threshold"] = res.get("threshold", 0.6)
        classification["needs_fallback"] = res.get("needs_fallback", False)

    rag_step_log(
        STEP,
        "exit",
        confidence_sufficient=classification.get("confidence_sufficient"),
        threshold=classification.get("threshold"),
    )
    return state
