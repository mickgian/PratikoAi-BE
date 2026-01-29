"""Node wrapper for Step 40: Build Context. DEV-250: Thin wrapper using context_builder service."""

from app.core.langgraph.types import RAGState
from app.core.logging import logger
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.facts import step_40__build_context
from app.services.context_builder import (
    MAX_KB_DOCUMENTS,
    build_kb_sources_metadata,
    build_web_metadata_entry,
    extract_filter_keywords_from_query,
    is_web_document,
    is_web_source_topic_relevant,
    separate_kb_and_web_docs,
)

STEP = 40


async def node_step_40(state: RAGState) -> RAGState:
    """Node wrapper for Step 40: Build unified context."""
    rag_step_log(STEP, "enter")
    with rag_step_timer(STEP):
        qv = state.get("query_variants", {})
        filter_query = qv.get("original_query") or state.get("user_query", "")
        query_keywords = state.get("search_keywords") or extract_filter_keywords_from_query(filter_query)
        topic_keywords = state.get("topic_keywords") if isinstance(state.get("topic_keywords"), list) else None

        # Pre-filter web docs
        retrieval_result = state.get("retrieval_result", {})
        all_docs = retrieval_result.get("documents", [])
        filtered_docs = [
            d
            for d in all_docs
            if isinstance(d, dict)
            and (not is_web_document(d) or is_web_source_topic_relevant(d, query_keywords, topic_keywords))
        ]
        logger.info("DEV245_step40_filter_complete", original_count=len(all_docs), remaining_total=len(filtered_docs))

        filtered_ctx = {**dict(state), "retrieval_result": {**retrieval_result, "documents": filtered_docs}}
        res = await step_40__build_context(messages=state.get("messages", []), ctx=filtered_ctx)

        state["context"] = res.get("merged_context", "")
        sd = res.get("source_distribution", {})
        state["context_metadata"] = {
            "facts_count": sd.get("facts", 0),
            "kb_docs_count": sd.get("kb_docs", 0),
            "doc_facts_count": sd.get("document_facts", 0),
            "total_chars": len(state["context"]),
            "token_count": res.get("token_count", 0),
            "quality_score": res.get("context_quality_score", 0.0),
            "timestamp": res.get("timestamp"),
        }

        if dmap := res.get("document_deanonymization_map", {}):
            priv = state.get("privacy") or {}
            priv["document_deanonymization_map"], priv["document_pii_placeholders_count"] = dmap, len(dmap)
            state["privacy"] = priv

        valid_kb_docs, web_docs = separate_kb_and_web_docs(res.get("kb_results") or [])
        if len(valid_kb_docs) > MAX_KB_DOCUMENTS:
            valid_kb_docs = valid_kb_docs[:MAX_KB_DOCUMENTS]
        state["kb_documents"], state["web_documents"] = valid_kb_docs, web_docs

        kb_sources_metadata = build_kb_sources_metadata(valid_kb_docs, state.get("user_query"))
        # DEV-250: Build web_sources_metadata from web_docs for PostProactivity
        # This prevents redundant web search + LLM synthesis in step_100
        web_sources_metadata = []
        for doc in web_docs:
            if is_web_source_topic_relevant(doc, query_keywords, topic_keywords):
                web_entry = build_web_metadata_entry(doc)
                kb_sources_metadata.append(web_entry)
                web_sources_metadata.append(web_entry)
        state["kb_sources_metadata"] = kb_sources_metadata
        state["web_sources_metadata"] = web_sources_metadata
        logger.info("DEV250_web_sources_preserved", web_sources_count=len(web_sources_metadata))

        from app.services.llm_response import check_kb_empty_and_inject_warning

        state["kb_was_empty"] = check_kb_empty_and_inject_warning(state)
        if state["kb_was_empty"]:
            logger.warning(
                "kb_empty_detected_step40", user_query=(state.get("user_message") or state.get("user_query", ""))[:100]
            )

    logger.info(
        "DEV007_step40_context_stored_in_state",
        extra={
            "context_length": len(state.get("context", "")),
            "kb_documents_preserved": len(state.get("kb_documents", [])),
            "kb_metadata_preserved": len(state.get("kb_sources_metadata", [])),
        },
    )
    rag_step_log(
        STEP,
        "exit",
        context_length=len(state.get("context", "")),
        facts_count=state["context_metadata"].get("facts_count", 0),
        kb_documents_count=len(state.get("kb_documents", [])),
    )
    return state
