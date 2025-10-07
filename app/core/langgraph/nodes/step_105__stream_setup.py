"""Node wrapper for Step 105: Stream Setup."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.streaming import step_105__stream_setup

STEP = 105


async def node_step_105(state: RAGState) -> RAGState:
    """Node wrapper for Step 105: Setup SSE streaming infrastructure."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_105__stream_setup(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store streaming setup in nested dict
        streaming = state.setdefault("streaming", {})
        streaming["setup"] = True
        streaming["sse_headers"] = result.get("sse_headers", {}) if isinstance(result, dict) else {}
        streaming["stream_context"] = result.get("stream_context", {}) if isinstance(result, dict) else {}
        streaming["mode"] = "sse"

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    streaming_setup=streaming.get("setup"))
        return state
