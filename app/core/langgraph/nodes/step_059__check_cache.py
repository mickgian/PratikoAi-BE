"""Node wrapper for Step 59: Check Cache."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.cache import step_59__check_cache

STEP = 59


async def node_step_59(state: RAGState) -> RAGState:
    """Node wrapper for Step 59: Check cache for cached LLM response."""
    cache = state.setdefault("cache", {})

    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])

        # Call orchestrator (cast to dict for type compatibility)
        result = await step_59__check_cache(messages=messages, ctx=dict(state))

        # Merge result fields into state (preserving existing data)
        if isinstance(result, dict):
            # Selectively update state with known fields from result
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Populate consistent cache state keys
        cache_key = state.get("cache_key")
        cache_value = state.get("cached_response")

        cache["key"] = cache_key
        cache["hit"] = cache_value is not None
        cache["value"] = cache_value

        rag_step_log(STEP, "exit", cache=cache, cache_hit=cache.get("hit"))

        return state