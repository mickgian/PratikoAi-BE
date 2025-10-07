"""Node wrapper for Step 109: Stream Response."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.streaming import step_109__stream_response

STEP = 109


async def node_step_109(state: RAGState) -> RAGState:
    """Node wrapper for Step 109: Create StreamingResponse with SSE chunks."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_109__stream_response(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store streaming response metadata in streaming dict
        streaming = state.setdefault("streaming", {})
        streaming["response_created"] = result.get("response_created", False) if isinstance(result, dict) else False
        streaming["streaming_response"] = result.get("streaming_response") if isinstance(result, dict) else None
        streaming["response_config"] = result.get("response_config", {}) if isinstance(result, dict) else {}

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    response_created=streaming.get("response_created"))
        return state
