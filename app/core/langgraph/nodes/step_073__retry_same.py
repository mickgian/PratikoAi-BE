"""Node wrapper for Step 73: Retry Same."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.providers import step_73__retry_same

STEP = 73


async def node_step_73(state: RAGState) -> RAGState:
    """Node wrapper for Step 73: Retry with same provider."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_73__retry_same(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Update retry strategy information
        if "llm" not in state:
            state["llm"] = {}
        state["llm"]["retry_strategy"] = "same_provider"

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state