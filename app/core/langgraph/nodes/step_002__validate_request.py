"""Node wrapper for Step 2: Validate Request."""

from typing import Any, Dict

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
)
from app.observability.rag_logging import (
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.platform import step_2__validate_request

STEP = 2


def _merge(d: dict[str, Any], patch: dict[str, Any]) -> None:
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


async def node_step_2(state: RAGState) -> RAGState:
    """Node wrapper for Step 2: Validate Request."""
    rag_step_log(STEP, "enter", request_id=state.get("request_id"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_2__validate_request(ctx=dict(state), messages=state.get("messages"))

        # Map orchestrator outputs to canonical state keys (additive)
        privacy = state.setdefault("privacy", {})
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation (CRITICAL mapping)
        if "request_valid" in res:
            decisions["request_valid"] = bool(res["request_valid"])
        elif "is_valid" in res:
            decisions["request_valid"] = bool(res["is_valid"])
        mirror(state, "request_valid", bool(res.get("is_valid", res.get("request_valid", False))))

        if "validation_successful" in res:
            decisions["validation_successful"] = bool(res["validation_successful"])
        if "authentication_successful" in res:
            decisions["authentication_successful"] = bool(res["authentication_successful"])

        # Copy session and user info if present
        if "session" in res:
            state["session"] = res["session"]
        if "user" in res:
            state["user"] = res["user"]
        if "validated_request" in res:
            state["validated_request"] = res["validated_request"]
        if "validation_errors" in res:
            mirror(state, "validation_errors", res["validation_errors"])

        # Merge any extra structured data
        _merge(privacy, res.get("privacy_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", request_valid=decisions.get("request_valid"))
    return state
