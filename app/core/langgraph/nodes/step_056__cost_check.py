"""Node wrapper for Step 56: Cost Check (Decision)."""

from app.core.langgraph import types as rag_types

# Aliases for test introspection
rag_step_log = rag_types.rag_step_log
rag_step_timer = rag_types.rag_step_timer
from app.orchestrators import providers as orchestrators

STEP = 56


def node_step_56(state: rag_types.RAGState) -> rag_types.RAGState:
    """Node wrapper for Step 56: Cost Check (Decision).

    Delegates to the orchestrator and updates state with cost check decision.
    """
    provider = state.setdefault("provider", {})
    decisions = state.setdefault("decisions", {})

    with rag_types.rag_step_timer(STEP):
        rag_types.rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to the orchestrator
        result = orchestrators.step_56__cost_check(ctx=state)

        # Merge result fields into provider and decisions dicts (preserving existing data)
        if isinstance(result, dict):
            if "budget_ok" in result:
                provider["budget_ok"] = result["budget_ok"]
                decisions["cost_ok"] = bool(result["budget_ok"])
            if "cost_approved" in result:
                provider["cost_approved"] = result["cost_approved"]
                # Only set cost_ok from cost_approved if budget_ok wasn't present
                if "budget_ok" not in result:
                    decisions["cost_ok"] = bool(result["cost_approved"])

        rag_types.rag_step_log(STEP, "exit", provider=provider, decisions=decisions)

    return state