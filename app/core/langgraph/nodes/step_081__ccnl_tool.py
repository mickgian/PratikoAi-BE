"""Node wrapper for Step 81: CCNL Tool."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.ccnl import step_81__ccnlquery

STEP = 81


async def node_step_81(state: RAGState) -> RAGState:
    """Node wrapper for Step 81: Execute CCNL query tool."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_81__ccnlquery(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Store tool results
        if "tools" not in new_state:
            new_state["tools"] = {}
        new_state["tools"]["ccnl_results"] = result
        new_state["tools"]["executed"] = "ccnl"

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state