"""Node wrapper for Step 111: Collect Metrics."""

from app.core.langgraph.types import RAGState, rag_step_log, rag_step_timer
from app.orchestrators.metrics import step_111__collect_metrics

STEP = 111


async def node_step_111(state: RAGState) -> RAGState:
    """Node wrapper for Step 111: Collect usage metrics."""
    with rag_step_timer(STEP):
        rag_step_log(STEP, "enter", keys=list(state.keys()))

        # Delegate to existing orchestrator function
        messages = state.get("messages", [])
        # Call orchestrator
        result = await step_111__collect_metrics(messages=messages, ctx=dict(state))

        # Merge result back into state
        # Mutate state in place
        if isinstance(result, dict):
            for key, value in result.items():
                if key in state or key in RAGState.__annotations__:
                    state[key] = value  # type: ignore[literal-required]

        # Store metrics in metrics dict
        metrics = state.setdefault("metrics", {})
        if isinstance(result, dict):
            metrics["collected"] = result.get("metrics_collected", False)
            metrics["timestamp"] = result.get("timestamp")
            metrics["user_id"] = result.get("user_id")
            metrics["session_id"] = result.get("session_id")
            metrics["response_time_ms"] = result.get("response_time_ms")
            metrics["cache_hit"] = result.get("cache_hit", False)
            metrics["provider"] = result.get("provider")
            metrics["model"] = result.get("model")
            metrics["total_tokens"] = result.get("total_tokens", 0)
            metrics["cost"] = result.get("cost", 0.0)

        rag_step_log(STEP, "exit",
                    keys=list(state.keys()),
                    metrics_collected=metrics.get("collected"))
        return state
