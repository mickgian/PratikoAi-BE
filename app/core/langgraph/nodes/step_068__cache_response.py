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
        # Call orchestrator
        result = await step_68__cache_response(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Mark that response has been cached
        if "cache" not in state:
            state["cache"] = {}
        state["cache"]["response_cached"] = True

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state