"""Node wrapper for Step 48: Select Provider."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 48


def node_step_48(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 48: Select Provider.

    Delegates to the orchestrator and updates state with provider selection results.
    """
    provider = state.setdefault("provider", {})
    decisions = state.setdefault("decisions", {})
    # Initialize route_strategy if not present (for enter log keys)
    state.setdefault("route_strategy", None)

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator
        result = orchestrators.step_48__select_provider(ctx=state)

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            if "strategy" in result:
                provider["strategy"] = result["strategy"]
                state["route_strategy"] = result["strategy"]  # Update legacy field
            if "provider" in result:
                provider["selected"] = result["provider"]
                state["provider_choice"] = result["provider"]  # Update legacy field

        rag_types.rag_step_log(STEP, "exit", provider=provider)

    return state