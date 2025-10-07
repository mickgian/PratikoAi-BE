"""Node wrapper for Step 110: Send Done."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.platform import step_110__send_done

STEP = 110


def node_step_110(state: RAGState) -> RAGState:
    """Node wrapper for Step 110: Send DONE frame to terminate streaming."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator (synchronous)
        result = step_110__send_done(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store done frame metadata in streaming dict
        streaming = state.setdefault("streaming", {})
        streaming["done"] = True
        streaming["chunks_sent"] = result.get("chunks_sent", 0) if isinstance(result, dict) else 0
        streaming["done_sent"] = result.get("done_sent", False) if isinstance(result, dict) else False

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    done=streaming.get("done"))
        return state
