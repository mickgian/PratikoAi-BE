"""Node wrapper for Step 24: Golden Lookup."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.preflight import step_24__golden_lookup

STEP = 24


async def node_step_24(state: RAGState) -> RAGState:
    """Node wrapper for Step 24: Match by signature or semantic search."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()), golden=state.get("golden"))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_24__golden_lookup(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store golden lookup result in nested dict (additive)
        golden = state.setdefault("golden", {})
        golden["lookup"] = result.get("lookup", {}) if isinstance(result, dict) else {}
        golden["match_found"] = result.get("match_found", False) if isinstance(result, dict) else False

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    match_found=golden.get("match_found"),
                    golden=golden)
        return state
