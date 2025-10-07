"""Node wrapper for Step 20: Golden Fast Gate."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.golden import step_20__golden_fast_gate

STEP = 20


async def node_step_20(state: RAGState) -> RAGState:
    """Node wrapper for Step 20: Golden fast-path eligible check."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()), golden=state.get("golden"))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_20__golden_fast_gate(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store golden eligibility in nested dict (additive)
        golden = state.setdefault("golden", {})
        golden["eligible"] = result.get("golden_eligible", False) if isinstance(result, dict) else False

        # Store decision for routing
        decisions = state.setdefault("decisions", {})
        decisions["golden_eligible"] = golden["eligible"]

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    golden_eligible=golden.get("eligible"),
                    decisions=decisions)
        return state
