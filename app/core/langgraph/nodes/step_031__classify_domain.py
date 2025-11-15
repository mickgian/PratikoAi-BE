"""Node wrapper for Step 31: Classify Domain.

This node delegates to the orchestrator step_31__classify_domain() and maps
the results to RAGState under the 'classification' key.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.classify import step_31__classify_domain

STEP = 31


async def node_step_31(state: RAGState) -> RAGState:
    """Node wrapper for Step 31: Classify Domain.

    Delegates to step_31__classify_domain orchestrator and maps classification
    results to state['classification'].

    Args:
        state: Current RAG state containing messages and user_query

    Returns:
        Updated state with classification data
    """
    domain = state.get("classification", {}).get("domain", "unknown")
    rag_step_log(STEP, "enter", domain=domain)

    with rag_step_timer(STEP):
        # Call orchestrator with context from state
        res = await step_31__classify_domain(messages=state.get("messages", []), ctx=dict(state))

        # Map orchestrator output to canonical state key
        state["classification"] = {
            "timestamp": res.get("timestamp"),
            "domain": res.get("domain"),
            "action": res.get("action"),
            "confidence": res.get("confidence", 0.0),
            "fallback_used": res.get("fallback_used", False),
            "query_length": res.get("query_length", 0),
            "error": res.get("error"),
        }

        # Also store the nested classification dict if present and valid
        if "classification" in res and isinstance(res["classification"], dict):
            state["classification"].update(res["classification"])

    rag_step_log(
        STEP,
        "exit",
        domain=state["classification"].get("domain"),
        confidence=state["classification"].get("confidence"),
    )
    return state
