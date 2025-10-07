"""Node wrapper for Step 72: Failover Provider."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.providers import step_72__get_failover_provider

STEP = 72


async def node_step_72(state: RAGState) -> RAGState:
    """Node wrapper for Step 72: Get failover provider."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_72__get_failover_provider(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Update provider information for retry
        if "llm" not in state:
            state["llm"] = {}
        state["llm"]["failover_provider_selected"] = True
        state["llm"]["retry_strategy"] = "failover"

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state