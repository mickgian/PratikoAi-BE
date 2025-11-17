"""Node wrapper for Step 73: Retry Same."""

from typing import (
    Any,
    Dict,
)

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.providers import step_73__retry_same

STEP = 73


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


async def node_step_73(state: RAGState) -> RAGState:
    """Node wrapper for Step 73: Retry with same provider."""
    rag_step_log(STEP, "enter", provider=state.get("provider"))
    with rag_step_timer(STEP):
        res = await step_73__retry_same(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        provider = state.setdefault("provider", {})
        decisions = state.setdefault("decisions", {})
        retries = state.setdefault("retries", {})  # Add retries tracking

        # Field mappings with name translation
        if "retry_same" in res:
            provider["retry_same"] = res["retry_same"]

        # CRITICAL: Map attempt_number to state.retries AND top-level (persistent counters)
        if "attempt_number" in res:
            retries["llm_attempts"] = res["attempt_number"]
            state["attempt_number"] = res["attempt_number"]  # Also store at top level

        # Enforce hard cap from env (safety net)
        import os

        max_retries = int(os.getenv("RAG_MAX_RETRIES", "2"))
        if retries.get("llm_attempts", 0) > max_retries:
            # Override decision - force error route
            decisions["force_error"] = True
            from app.core.logging import logger

            logger.error(
                "retry_hard_cap_exceeded",
                extra={"step": 73, "llm_attempts": retries["llm_attempts"], "max_retries": max_retries},
            )

        _merge(provider, res.get("provider_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", retry_same=provider.get("retry_same"))
    return state
