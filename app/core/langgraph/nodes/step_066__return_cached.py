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
        # Call orchestrator
        result = await step_66__return_cached(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Ensure cache value is populated for downstream
        if "cache" in state and state["cache"].get("hit"):
            # Mark that we're returning cached response
            state["returning_cached"] = True

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state