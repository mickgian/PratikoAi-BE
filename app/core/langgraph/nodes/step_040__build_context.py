"""Node wrapper for Step 40: Build Context.

Internal step - merges facts, KB docs, and optional document facts into unified context.
"""

from app.core.langgraph.types import RAGState
from app.core.logging import logger as step40_logger
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

        # DEV-007 PII: Store document deanonymization map in privacy state
        # This enables reversing PII placeholders after LLM response
        deanonymization_map = res.get("document_deanonymization_map", {})
        if deanonymization_map:
            privacy = state.get("privacy") or {}
            privacy["document_deanonymization_map"] = deanonymization_map
            privacy["document_pii_placeholders_count"] = len(deanonymization_map)
            state["privacy"] = privacy

    # DEV-007 DIAGNOSTIC: Log context value stored in state
    context_value = state.get("context", "")
    # Count document headers to verify all documents are present
    doc_headers_count = context_value.count("[Documento:")
    expected_doc_count = state["context_metadata"].get("doc_facts_count", 0)

    # DEV-007 DIAGNOSTIC: Extract document order from context to verify current docs come first
    import re

    doc_header_pattern = r"\[(DOCUMENTI ALLEGATI ORA|CONTESTO PRECEDENTE)\] \[Documento: ([^\]]+)\]"
    doc_matches = re.findall(doc_header_pattern, context_value)
    doc_order = [(marker, filename) for marker, filename in doc_matches]

    # Check if current documents come before prior documents
    first_prior_idx = next((i for i, (m, _) in enumerate(doc_order) if m == "CONTESTO PRECEDENTE"), len(doc_order))
    last_current_idx = max((i for i, (m, _) in enumerate(doc_order) if m == "DOCUMENTI ALLEGATI ORA"), default=-1)
    current_before_prior = last_current_idx < first_prior_idx if doc_order else True

    step40_logger.info(
        "DEV007_step40_context_stored_in_state",
        extra={
            "context_length": len(context_value),
            "context_preview": context_value[:1000] if len(context_value) > 1000 else context_value,
            "context_contains_payslip_8": "Payslip 8" in context_value or "PAYSLIP_8" in context_value,
            "context_contains_payslip_9": "Payslip 9" in context_value or "PAYSLIP_9" in context_value,
            "doc_facts_count": expected_doc_count,
            "doc_headers_in_context": doc_headers_count,
            "header_count_matches": doc_headers_count == expected_doc_count,
            # NEW: Document order diagnostics
            "doc_order": doc_order,
            "current_docs_before_prior": current_before_prior,
            "first_prior_doc_index": first_prior_idx,
            "last_current_doc_index": last_current_idx,
        },
    )

    rag_step_log(
        STEP,
        "exit",
        context_length=len(state.get("context", "")),
        facts_count=state["context_metadata"].get("facts_count", 0),
    )
    return state
