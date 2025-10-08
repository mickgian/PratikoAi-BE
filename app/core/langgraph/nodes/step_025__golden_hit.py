"""Node wrapper for Step 25: Golden Hit (Decision)."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.golden import step_25__golden_hit

STEP = 25


async def node_step_25(state: RAGState) -> RAGState:
    """Node wrapper for Step 25: High confidence match decision (score >= 0.90)."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()), golden=state.get("golden"))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_25__golden_hit(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store golden hit decision in nested dict (additive)
        golden = state.setdefault("golden", {})
        golden["hit"] = result.get("high_confidence_match", False) if isinstance(result, dict) else False
        golden["similarity_score"] = result.get("similarity_score") if isinstance(result, dict) else None

        # CRITICAL: Set routing decision for graph edges
        decisions = state.setdefault("decisions", {})
        decisions["golden_hit"] = bool(golden["hit"])

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    golden_hit=golden.get("hit"),
                    similarity_score=golden.get("similarity_score"),
                    decisions=decisions)
        return state
