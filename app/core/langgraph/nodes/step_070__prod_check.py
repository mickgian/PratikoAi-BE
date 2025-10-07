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
        # Call orchestrator
        result = await step_70__prod_check(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Decision logic based on environment
        is_production = state.get("is_production", False)
        should_failover = state.get("should_failover", False)

        # Update state for routing decision
        if "llm" not in state:
            state["llm"] = {}
        state["llm"]["is_production"] = is_production
        state["llm"]["should_failover"] = should_failover

        rag_step_log(STEP, "exit",
                    keys=list(state.keys())
                                )
        return state