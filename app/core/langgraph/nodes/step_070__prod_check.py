"""Node wrapper for Step 70: Prod Check."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_70__prod_check

STEP = 70


async def node_step_70(state: RAGState) -> RAGState:
    """Node wrapper for Step 70: Production environment check decision node."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        ctx = dict(state)  # Pass full state as context

        # Call orchestrator
        result = await step_70__prod_check(messages=messages, ctx=ctx)

        # Merge result back into state
        new_state = state.copy()
        if isinstance(result, dict):
            new_state.update(result)

        # Decision logic based on environment
        is_production = new_state.get("is_production", False)
        should_failover = new_state.get("should_failover", False)

        # Update state for routing decision
        if "llm" not in new_state:
            new_state["llm"] = {}
        new_state["llm"]["is_production"] = is_production
        new_state["llm"]["should_failover"] = should_failover

        rag_step_log(STEP, "exit",
                    changed_keys=[k for k in new_state.keys()
                                if new_state.get(k) != state.get(k)])
        return new_state