"""Node wrapper for Step 50: Strategy Type (Decision)."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import platform as orchestrators

STEP = 50


def node_step_50(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 50: Strategy Type (Decision).

    Delegates to the orchestrator and updates state with strategy type decision.
    """
    decisions = state.setdefault("decisions", {})
    provider = state.setdefault("provider", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator (cast to dict for type compatibility)
        result = orchestrators.step_50__strategy_type(ctx=dict(state))

        # Merge result fields into decisions dict (preserving existing data)
        if isinstance(result, dict) and "strategy_type" in result:
            decisions["strategy_type"] = result["strategy_type"]
            provider["strategy_type"] = result["strategy_type"]

        rag_types.rag_step_log(STEP, "exit", provider=provider, decisions=decisions)

    return state