"""Node wrapper for Step 28: Serve Golden."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.golden import step_28__serve_golden

STEP = 28


async def node_step_28(state: RAGState) -> RAGState:
    """Node wrapper for Step 28: Serve Golden answer with citations."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()), golden=state.get("golden"))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        result = await step_28__serve_golden(messages=messages, ctx=dict(state))

        # Merge result back into state additively
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store golden answer in nested dict (additive)
        golden = state.setdefault("golden", {})
        golden["answer"] = result.get("answer", {}) if isinstance(result, dict) else {}
        golden["served"] = True

        # Log metric for golden hit tracking
        rag_step_log(STEP, "metric",
                    metric="golden_hit",
                    signature=state.get("query_signature"),
                    hit=True,
                    faq_id=golden["answer"].get("faq_id") if isinstance(golden.get("answer"), dict) else None)

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    answer_length=len(str(golden.get("answer", {}))),
                    golden=golden)
        return state
