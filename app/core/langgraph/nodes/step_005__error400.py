"""Node wrapper for Step 5: Error400 - Return 400 Bad Request."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.orchestrators.platform import step_5__error400
from app.observability.rag_logging import rag_step_log_compat as rag_step_log, rag_step_timer_compat as rag_step_timer

STEP = 5


def _merge(d: Dict[str, Any], patch: Dict[str, Any]) -> None:
    """Recursively merge patch into d (additive)."""
    for k, v in (patch or {}).items():
        if isinstance(v, dict):
            d.setdefault(k, {})
            if isinstance(d[k], dict):
                _merge(d[k], v)
            else:
                d[k] = v
        else:
            d[k] = v


async def node_step_5(state: RAGState) -> RAGState:
    """Node wrapper for Step 5: Error400 - Return 400 Bad Request (Terminal)."""
    rag_step_log(STEP, "enter", keys=list(state.keys()))
    with rag_step_timer(STEP):
        # Extract error information from state
        decisions = state.get("decisions", {})
        error_type = decisions.get("error_type", "validation_failed")
        error_message = decisions.get("error_message")
        validation_errors = decisions.get("validation_errors", [])

        res = await step_5__error400(
            messages=state.get("messages"),
            ctx=dict(state),
            error_type=error_type,
            error_message=error_message,
            validation_errors=validation_errors,
            session_id=state.get("session_id"),
            user_id=state.get("user_id"),
            request_context={"request_id": state.get("request_id")}
        )

        # Store error response in state
        state["error_response"] = res.get("error_response", {})
        state["error_details"] = res.get("error_details", {})
        state["workflow_terminated"] = res.get("workflow_terminated", True)
        state["terminal_step"] = res.get("terminal_step", True)
        state["status_code"] = res.get("status_code", 400)

        # Set final_response to prevent fallback logic from executing
        # This ensures the workflow terminates properly without triggering provider selection
        state["final_response"] = {
            "content": error_message or "Invalid request",
            "type": "error",
            "status_code": 400,
            "error_type": error_type
        }

        # Update decisions with error info
        decisions["error_returned"] = res.get("error_returned", True)
        decisions["error_type"] = res.get("error_type", error_type)

    rag_step_log(
        STEP,
        "exit",
        error_returned=True,
        status_code=state.get("status_code"),
        workflow_terminated=True
    )
    return state
