"""Node wrapper for Step 58: Cheaper Provider."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 58


def node_step_58(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 58: Cheaper Provider.

    Delegates to the orchestrator and updates state with cheaper provider selection.
    """
    provider = state.setdefault("provider", {})
    state.setdefault("provider_choice", None)

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = orchestrators.step_58__cheaper_provider(ctx=dict(state))

        # Merge result fields into provider dict (preserving existing data)
        if isinstance(result, dict):
            if "provider" in result:
                provider["selected"] = result["provider"]
                state["provider_choice"] = result["provider"]  # legacy field
            if "cheaper_found" in result:
                provider["cheaper_found"] = result["cheaper_found"]
            if "fallback_strategy" in result:
                provider["fallback_strategy"] = result["fallback_strategy"]

        rag_types.rag_step_log(STEP, "exit", provider=provider, cheaper_found=provider.get("cheaper_found"))

    return state