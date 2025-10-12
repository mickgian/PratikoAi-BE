"""Node wrapper for Step 42: Classification Confidence Check.

This node delegates to the orchestrator step_42__class_confidence() and maps
the results to RAGState under the 'confidence_check' key.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.classify import step_42__class_confidence
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 42


async def node_step_42(state: RAGState) -> RAGState:
    """Node wrapper for Step 42: Classification Confidence Check.

    Delegates to step_42__class_confidence orchestrator and maps confidence
    check results to state['confidence_check'].

    Args:
        state: Current RAG state containing classification data

    Returns:
        Updated state with confidence check data
    """
    confidence = state.get("classification", {}).get("confidence", 0.0)
    rag_step_log(STEP, "enter", confidence=confidence)

    with rag_step_timer(STEP):
        # Call orchestrator with context from state
        res = await step_42__class_confidence(
            classification=state.get("classification"),
            ctx=dict(state)
        )

        # Map orchestrator output to canonical state key
        state["confidence_check"] = {
            "timestamp": res.get("timestamp"),
            "classification_exists": res.get("classification_exists", False),
            "confidence_sufficient": res.get("confidence_sufficient", False),
            "confidence_value": res.get("confidence_value", 0.0),
            "threshold": res.get("threshold", 0.6),
            "domain": res.get("domain"),
            "action": res.get("action"),
            "fallback_used": res.get("fallback_used", False),
            "reasoning": res.get("reasoning")
        }

    rag_step_log(
        STEP,
        "exit",
        confidence_sufficient=state["confidence_check"]["confidence_sufficient"],
        confidence_value=state["confidence_check"]["confidence_value"]
    )
    return state
