"""Node wrapper for Step 40: Build Context.

Internal step - merges facts, KB docs, and optional document facts into unified context.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.facts import step_40__build_context
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 40


async def node_step_40(state: RAGState) -> RAGState:
    """Node wrapper for Step 40: Build unified context.

    Args:
        state: Current RAG state with facts and KB docs

    Returns:
        Updated state with merged context
    """
    rag_step_log(STEP, "enter")

    with rag_step_timer(STEP):
        res = await step_40__build_context(
            messages=state.get("messages", []),
            ctx=dict(state)
        )

        # Store merged context
        state["context"] = res.get("context", "")
        state["context_metadata"] = {
            "facts_count": res.get("facts_count", 0),
            "kb_docs_count": res.get("kb_docs_count", 0),
            "doc_facts_count": res.get("doc_facts_count", 0),
            "total_chars": len(res.get("context", "")),
            "timestamp": res.get("timestamp")
        }

    rag_step_log(
        STEP,
        "exit",
        context_length=len(state.get("context", "")),
        facts_count=state["context_metadata"].get("facts_count", 0)
    )
    return state
