"""Node wrapper for Step 34: Track Classification Metrics.

Internal step - records classification metrics for monitoring.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.metrics import step_34__track_metrics

STEP = 34


async def node_step_34(state: RAGState) -> RAGState:
    """Node wrapper for Step 34: Track classification metrics.

    Args:
        state: Current RAG state with classification data

    Returns:
        Updated state with metrics tracking confirmation
    """
    domain = state.get("classification", {}).get("domain")
    rag_step_log(STEP, "enter", domain=domain)

    with rag_step_timer(STEP):
        res = await step_34__track_metrics(messages=state.get("messages", []), ctx=dict(state))

        # Store metrics tracking result
        metrics = state.setdefault("metrics", {})
        metrics["classification_tracked"] = res.get("tracked", False)
        metrics["tracking_timestamp"] = res.get("timestamp")
        if "metric_id" in res:
            metrics["metric_id"] = res["metric_id"]

    rag_step_log(STEP, "exit", tracked=metrics.get("classification_tracked"))
    return state
