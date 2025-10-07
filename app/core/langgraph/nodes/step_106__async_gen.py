"""Node wrapper for Step 106: Async Generator."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_106__async_gen

STEP = 106


async def node_step_106(state: RAGState) -> RAGState:
    """Node wrapper for Step 106: Create async generator for streaming."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_106__async_gen(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store async generator metadata in streaming dict
        streaming = state.setdefault("streaming", {})
        streaming["generator_created"] = result.get("generator_created", False) if isinstance(result, dict) else False
        streaming["async_generator"] = result.get("async_generator") if isinstance(result, dict) else None
        streaming["generator_config"] = result.get("generator_config", {}) if isinstance(result, dict) else {}

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    generator_created=streaming.get("generator_created"))
        return state
