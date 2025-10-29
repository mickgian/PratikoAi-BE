"""Node wrapper for Step 39: Knowledge Base Pre-Fetch.

Internal step - retrieves relevant KB documents using BM25, vectors, and recency boost.
"""

from app.core.langgraph.types import RAGState
from app.orchestrators.preflight import step_39__kbpre_fetch
from app.observability.rag_logging import (
    rag_step_log_compat as rag_step_log,
    rag_step_timer_compat as rag_step_timer,
)

STEP = 39


async def node_step_39(state: RAGState) -> RAGState:
    """Node wrapper for Step 39: KB pre-fetch.

    Args:
        state: Current RAG state with user query

    Returns:
        Updated state with KB documents
    """
    user_query = state.get("user_query", "")
    rag_step_log(STEP, "enter", query_length=len(user_query))

    with rag_step_timer(STEP):
        res = await step_39__kbpre_fetch(
            messages=state.get("messages", []),
            ctx=dict(state)
        )

        # Store KB results
        kb_results = state.setdefault("kb_results", {})
        kb_results["documents"] = res.get("documents", [])
        kb_results["doc_count"] = res.get("doc_count", 0)
        kb_results["retrieval_method"] = res.get("method", "hybrid")
        kb_results["timestamp"] = res.get("timestamp")

    rag_step_log(
        STEP,
        "exit",
        doc_count=kb_results.get("doc_count", 0)
    )
    return state
