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
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_72__get_failover_provider(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Update provider information for retry
        if "llm" not in new_state:
            new_state["llm"] = {}
        new_state["llm"]["failover_provider_selected"] = True
        new_state["llm"]["retry_strategy"] = "failover"

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state