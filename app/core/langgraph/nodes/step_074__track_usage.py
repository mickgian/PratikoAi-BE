"""Node wrapper for Step 74: Track Usage."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.metrics import step_74__track_usage

STEP = 74


async def node_step_74(state: RAGState) -> RAGState:
    """Node wrapper for Step 74: Track LLM usage metrics."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_74__track_usage(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Update metrics tracking status
        if "metrics" not in state:
            state["metrics"] = {}
        state["metrics"]["usage_tracked"] = True

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state