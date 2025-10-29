"""Node wrapper for Step 64: LLM Call."""

from typing import Dict, Any
from app.core.langgraph.types import RAGState
from app.core.langgraph.node_utils import ns, mirror
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)
from app.orchestrators.providers import step_64__llmcall

STEP = 64


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


async def node_step_64(state: RAGState) -> RAGState:
    """Node wrapper for Step 64: LLM Call."""
    rag_step_log(STEP, "enter", provider=state.get("provider", {}).get("selected"))
    with rag_step_timer(STEP):
        # Call orchestrator with business inputs only
        res = await step_64__llmcall(
            messages=state.get("messages"),
            ctx=dict(state)
        )

        # Map orchestrator outputs to canonical state keys (additive)
        llm = ns(state, "llm")
        decisions = state.setdefault("decisions", {})

        # Map fields with name translation if needed
        if "llm_request" in res:
            llm["request"] = res["llm_request"]

        # Always set llm["success"]
        if "error" in res and res["error"] not in ["", None]:
            llm["error"] = res["error"]
            llm["success"] = False
            # Track error type for retryability check
            if "error_type" in res:
                llm["error_type"] = res["error_type"]
        elif "llm_call_successful" in res:
            # Explicitly check for llm_call_successful from orchestrator
            llm["success"] = res["llm_call_successful"]
            if "response" in res or "llm_response" in res:
                response = res.get("response", res.get("llm_response"))
                llm["response"] = response
                mirror(state, "llm_response", response)
        elif "response" in res or "llm_response" in res:
            response = res.get("response", res.get("llm_response"))
            llm["response"] = response
            llm["success"] = True
            mirror(state, "llm_response", response)
        elif "llm_success" in res:
            llm["success"] = res["llm_success"]
        else:
            llm.setdefault("success", False)

        # Merge any extra structured data
        _merge(llm, res.get("llm_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", llm_success=llm.get("success"))
    return state