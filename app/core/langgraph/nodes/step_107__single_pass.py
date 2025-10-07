"""Node wrapper for Step 107: Single Pass Stream."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.preflight import step_107__single_pass

STEP = 107


async def node_step_107(state: RAGState) -> RAGState:
    """Node wrapper for Step 107: Wrap stream with single-pass protection."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_107__single_pass(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store stream protection metadata in streaming dict
        streaming = state.setdefault("streaming", {})
        streaming["stream_protected"] = result.get("stream_protected", False) if isinstance(result, dict) else False
        streaming["wrapped_stream"] = result.get("wrapped_stream") if isinstance(result, dict) else None
        streaming["protection_config"] = result.get("protection_config", {}) if isinstance(result, dict) else {}

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    stream_protected=streaming.get("stream_protected"))
        return state
