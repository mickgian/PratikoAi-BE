"""Node wrapper for Step 68: Cache Response."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.cache import step_68__cache_response

STEP = 68


async def node_step_68(state: RAGState) -> RAGState:
    """Node wrapper for Step 68: Cache LLM response."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_68__cache_response(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Mark that response has been cached
        if "cache" not in new_state:
            new_state["cache"] = {}
        new_state["cache"]["response_cached"] = True

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state