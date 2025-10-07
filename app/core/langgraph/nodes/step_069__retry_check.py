"""Node wrapper for Step 69: Retry Check."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_69__retry_check

STEP = 69


async def node_step_69(state: RAGState) -> RAGState:
    """Node wrapper for Step 69: Retry check decision node."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_69__retry_check(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Decision logic based on orchestrator result
        # The orchestrator should set retry_allowed flag
        retry_allowed = state.get("retry_allowed", False)

        # Update llm state for retry tracking
        if "llm" not in state:
            state["llm"] = {}
        state["llm"]["retry_allowed"] = retry_allowed

        # Set retry count
        retry_count = state.get("llm", {}).get("retry_count", 0)
        state["llm"]["retry_count"] = retry_count + 1

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state