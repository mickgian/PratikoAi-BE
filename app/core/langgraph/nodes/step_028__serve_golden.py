"""Node wrapper for Step 28: Serve Golden."""

from typing import Any, Dict

from langchain_core.messages import AIMessage

from app.core.langgraph.node_utils import mirror
from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.golden import step_28__serve_golden

STEP = 28


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


async def node_step_28(state: RAGState) -> RAGState:
    """Node wrapper for Step 28: Serve Golden answer with citations."""
    rag_step_log(STEP, "enter", golden=state.get("golden"))
    with rag_step_timer(STEP):
        res = await step_28__serve_golden(
            messages=state.get("messages"),
            ctx=dict(state),
        )

        # Map to canonical state keys
        golden = state.setdefault("golden", {})
        decisions = state.setdefault("decisions", {})

        # Field mappings with name translation
        # Note: orchestrator returns answer nested under "response" key
        response_data = res.get("response", {})
        answer = response_data.get("answer")
        citations = response_data.get("citations")

        if answer:
            golden["answer"] = answer
            # CRITICAL: Set golden_answer at top level for streaming response handler
            # This key is declared in RAGState and will be persisted by LangGraph
            state["golden_answer"] = answer
            # CRITICAL: Add golden answer to messages for chat history persistence
            # Without this, golden answers are lost on page refresh because
            # GET /messages endpoint reads from state["messages"], not query_history
            messages = state.get("messages", [])
            messages.append(AIMessage(content=answer))
            state["messages"] = messages
        if citations:
            golden["citations"] = citations
        golden["served"] = True
        mirror(state, "golden_served", True)
        # CRITICAL: Set golden_hit at top level to signal golden answer was served
        state["golden_hit"] = True
        if "complete" in res:
            mirror(state, "complete", bool(res["complete"]))

        _merge(golden, res.get("golden_extra", {}))
        _merge(decisions, res.get("decisions", {}))

    rag_step_log(STEP, "exit", served=golden.get("served"))
    return state
