"""Node wrapper for Step 66: Return Cached."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.cache import step_66__return_cached

STEP = 66


async def node_step_66(state: RAGState) -> RAGState:
    """Node wrapper for Step 66: Return cached response."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_66__return_cached(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Ensure cache value is populated for downstream
        if "cache" in new_state and new_state["cache"].get("hit"):
            # Mark that we're returning cached response
            new_state["returning_cached"] = True

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state