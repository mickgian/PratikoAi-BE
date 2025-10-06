"""Node wrapper for Step 52: Best Provider."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 52


def node_step_52(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 52: Best Provider.

    Delegates to the orchestrator and updates state with best provider selection.
    """
    provider = state.setdefault("provider", {})
    state.setdefault("provider_choice", None)
    state.setdefault("route_strategy", None)

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator
        result = orchestrators.step_52__best_provider(ctx=state)

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            if "provider" in result:
                provider["selected"] = result["provider"]
                state["provider_choice"] = result["provider"]  # legacy field
            provider["strategy"] = "BEST"
            state["route_strategy"] = "BEST"  # legacy field

        rag_types.rag_step_log(STEP, "exit", provider=provider, selected=provider.get("selected"))

    return state