"""Node wrapper for Step 49: Route Strategy."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import facts as orchestrators

STEP = 49


def node_step_49(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 49: Route Strategy.

    Delegates to the orchestrator and updates state with routing strategy.
    """
    provider = state.setdefault("provider", {})
    decisions = state.setdefault("decisions", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator
        result = orchestrators.step_49__route_strategy(ctx=state)

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            # Handle both "strategy" and "routing_strategy" keys
            route = result.get("routing_strategy") or result.get("strategy")
            if route:
                provider["routing_strategy"] = route
                state["route_strategy"] = route

        rag_types.rag_step_log(STEP, "exit", provider=provider)

    return state