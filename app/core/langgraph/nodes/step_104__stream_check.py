"""Node wrapper for Step 104: Stream Check."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.streaming import step_104__stream_check

STEP = 104


async def node_step_104(state: RAGState) -> RAGState:
    """Node wrapper for Step 104: Determine if streaming is requested."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_104__stream_check(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store streaming decision in nested dict
        streaming = state.setdefault("streaming", {})
        streaming["requested"] = result.get("streaming_requested", False) if isinstance(result, dict) else False
        streaming["decision"] = result.get("decision", "no") if isinstance(result, dict) else "no"
        streaming["decision_source"] = result.get("decision_source", "default") if isinstance(result, dict) else "default"

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    streaming_requested=streaming.get("requested"))
        return state
