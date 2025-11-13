"""Node wrapper for Step 40: Build Context.

Internal step - merges facts, KB docs, and optional document facts into unified context.
"""

from app.core.langgraph.types import RAGState
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.facts import step_40__build_context

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
        res = await step_40__build_context(messages=state.get("messages", []), ctx=dict(state))

        # Store merged context - orchestrator returns "merged_context" key
        merged_context = res.get("merged_context", "")
        state["context"] = merged_context

        # Extract source distribution from orchestrator response
        source_dist = res.get("source_distribution", {})

        state["context_metadata"] = {
            "facts_count": source_dist.get("facts", 0),
            "kb_docs_count": source_dist.get("kb_docs", 0),
            "doc_facts_count": source_dist.get("document_facts", 0),
            "total_chars": len(merged_context),
            "token_count": res.get("token_count", 0),
            "quality_score": res.get("context_quality_score", 0.0),
            "timestamp": res.get("timestamp"),
        }

    rag_step_log(
        STEP,
        "exit",
        context_length=len(state.get("context", "")),
        facts_count=state["context_metadata"].get("facts_count", 0),
    )
    return state
