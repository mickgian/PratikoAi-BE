"""Node wrapper for Step 51: Cheap Provider."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 51


def node_step_51(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 51: Cheap Provider.

    Delegates to the orchestrator and updates state with cheap provider selection.
    """
    provider = state.setdefault("provider", {})
    state.setdefault("provider_choice", None)
    state.setdefault("route_strategy", None)

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = orchestrators.step_51__cheap_provider(ctx=dict(state))

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            if "provider" in result:
                provider["selected"] = result["provider"]
                state["provider_choice"] = result["provider"]  # legacy field
            provider["strategy"] = "CHEAP"
            state["route_strategy"] = "CHEAP"  # legacy field

        rag_types.rag_step_log(STEP, "exit", provider=provider, selected=provider.get("selected"))

    return state