"""Node wrapper for Step 39: Knowledge Base Pre-Fetch.

Internal step - retrieves relevant KB documents using BM25, vectors, and recency boost.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.preflight import step_39__kbpre_fetch

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
        # Map user_query to user_message for orchestrator compatibility
        ctx = dict(state)
        ctx["user_message"] = user_query

        res = await step_39__kbpre_fetch(messages=state.get("messages", []), ctx=ctx)

        # Store KB results - map orchestrator response keys to state
        # Orchestrator returns: knowledge_items, total_results, search_mode
        knowledge_items_raw = res.get("knowledge_items", [])
        total_results = res.get("total_results", 0)

        # Convert SearchResult dataclass objects to dicts for serialization
        # Step 40's context builder expects dict format
        from dataclasses import (
            asdict,
            is_dataclass,
        )

        knowledge_items = []
        for item in knowledge_items_raw:
            if is_dataclass(item):
                # Convert dataclass to dict
                # Note: Keep datetime objects as-is for context builder compatibility
                item_dict = asdict(item)
                knowledge_items.append(item_dict)
            elif isinstance(item, dict):
                # Already a dict
                knowledge_items.append(item)
            else:
                # Unknown type, try to convert to dict
                knowledge_items.append(dict(item))

        kb_results = state.setdefault("kb_results", {})
        kb_results["documents"] = knowledge_items
        kb_results["doc_count"] = total_results
        kb_results["retrieval_method"] = res.get("search_mode", "hybrid")
        kb_results["timestamp"] = res.get("timestamp")

        # Store at state root level using defined RAGState field 'kb_docs'
        # Step 40 orchestrator looks for ctx.get('knowledge_items'), but we also
        # need to store in a TypedDict-compatible field
        state["kb_docs"] = knowledge_items
        # Also try storing as knowledge_items for step 40 orchestrator
        state["knowledge_items"] = knowledge_items

    rag_step_log(STEP, "exit", doc_count=kb_results.get("doc_count", 0))
    return state
