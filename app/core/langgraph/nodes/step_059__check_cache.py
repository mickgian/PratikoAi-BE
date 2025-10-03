"""Node wrapper for Step 59: Check Cache."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.cache import step_59__check_cache

STEP = 59


async def node_step_59(state: RAGState) -> RAGState:
    """Node wrapper for Step 59: Check cache for cached LLM response."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        # Convert RAGState to the format expected by orchestrator
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_59__check_cache(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Populate consistent cache state keys
        cache_key = new_state.get("cache_key")
        cache_value = new_state.get("cached_response")

        # Initialize cache state structure
        if "cache" not in new_state:
            new_state["cache"] = {}

        new_state["cache"]["key"] = cache_key
        new_state["cache"]["hit"] = cache_value is not None
        new_state["cache"]["value"] = cache_value

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state