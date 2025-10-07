"""Node wrapper for Step 30: Return Complete."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.response import step_30__return_complete

STEP = 30


async def node_step_30(state: RAGState) -> RAGState:
    """Node wrapper for Step 30: Return ChatResponse."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_30__return_complete(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store response in state (additive)
        if isinstance(result, dict):
            state.setdefault("response", result.get("response", {}))
            state.setdefault("complete", result.get("complete", True))

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    complete=state.get("complete", True))
        return state
