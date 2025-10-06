"""Node wrapper for Step 55: Estimate Cost."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 55


def node_step_55(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 55: Estimate Cost.

    Delegates to the orchestrator and updates state with cost estimation.
    """
    provider = state.setdefault("provider", {})
    state.setdefault("estimated_cost", None)

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator
        result = orchestrators.step_55__estimate_cost(ctx=state)

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            if "estimated_cost" in result:
                provider["estimate"] = result["estimated_cost"]
                state["estimated_cost"] = result["estimated_cost"]  # legacy field
            if "cost_details" in result:
                provider["cost_details"] = result["cost_details"]

        rag_types.rag_step_log(STEP, "exit", provider=provider, estimate=provider.get("estimate"))

    return state