"""Node wrapper for Step 108: Write SSE."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.streaming import step_108__write_sse

STEP = 108


async def node_step_108(state: RAGState) -> RAGState:
    """Node wrapper for Step 108: Format chunks into SSE format."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_108__write_sse(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store SSE formatting metadata in streaming dict
        streaming = state.setdefault("streaming", {})
        streaming["chunks_formatted"] = result.get("chunks_formatted", False) if isinstance(result, dict) else False
        streaming["sse_formatted_stream"] = result.get("sse_formatted_stream") if isinstance(result, dict) else None
        streaming["format_config"] = result.get("format_config", {}) if isinstance(result, dict) else {}

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    chunks_formatted=streaming.get("chunks_formatted"))
        return state
