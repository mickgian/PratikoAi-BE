"""Node wrapper for Step 40: Build Context.

Internal step - merges facts, KB docs, and optional document facts into unified context.

DEV-213: Enhanced to preserve KB documents and metadata for action grounding.
DEV-237: Uses ParagraphExtractor for query-relevant paragraph extraction.
"""

import re

from app.core.langgraph.types import RAGState
from app.core.logging import logger as step40_logger
from app.observability.rag_logging import rag_step_log_compat as rag_step_log
from app.observability.rag_logging import rag_step_timer_compat as rag_step_timer
from app.orchestrators.facts import step_40__build_context
from app.services.paragraph_extractor import ParagraphExtractor

STEP = 40

# Maximum number of KB documents to preserve (performance cap)
MAX_KB_DOCUMENTS = 20

# Italian legal document hierarchy weights for source prioritization
HIERARCHY_WEIGHTS: dict[str, float] = {
    "legge": 1.0,
    "decreto_legislativo": 1.0,
    "dpr": 1.0,
    "decreto_ministeriale": 0.8,
    "regolamento_ue": 0.8,
    "circolare": 0.6,
    "risoluzione": 0.6,
    "interpello": 0.4,
    "faq": 0.4,
    "cassazione": 0.9,
    "corte_costituzionale": 1.0,
}


def get_hierarchy_weight(doc_type: str) -> float:
    """Return Italian legal hierarchy weight for source prioritization.

    Args:
        doc_type: Document type (e.g., 'legge', 'circolare', 'dpr')

    Returns:
        Hierarchy weight between 0.0 and 1.0
    """
    if not doc_type:
        return 0.5
    return HIERARCHY_WEIGHTS.get(doc_type.lower(), 0.5)


def extract_topics(doc: dict) -> list[str]:
    """Extract key topics from document for action relevance.

    Args:
        doc: Document dictionary with title and content

    Returns:
        List of extracted topic keywords
    """
    topics = []
    title = doc.get("title", "")
    content = doc.get("content", "")

    # Extract from title - split on common separators
    if title:
        # Remove article references like "Art. 16" and legal refs
        clean_title = re.sub(r"Art\.?\s*\d+", "", title)
        clean_title = re.sub(r"D\.?Lgs\.?\s*\d+/\d+", "", clean_title)
        clean_title = re.sub(r"DPR\s*\d+/\d+", "", clean_title)
        clean_title = re.sub(r"n\.\s*\d+", "", clean_title)

        # Split on separators and filter
        words = re.split(r"[-–—,;:/()]+", clean_title)
        for word in words:
            word = word.strip()
            if len(word) > 3:  # Skip short words
                topics.append(word)

    # Extract key terms from content (first 500 chars)
    if content:
        content_preview = content[:500]
        # Look for capitalized terms (likely important)
        capitalized = re.findall(r"\b[A-Z][A-Za-z]{3,}\b", content_preview)
        topics.extend(capitalized[:5])  # Limit to 5 from content

    # Deduplicate while preserving order
    seen = set()
    unique_topics = []
    for topic in topics:
        topic_lower = topic.lower()
        if topic_lower not in seen:
            seen.add(topic_lower)
            unique_topics.append(topic)

    return unique_topics[:10]  # Cap at 10 topics


def extract_values(doc: dict) -> list[str]:
    """Extract specific values (percentages, dates, amounts) for action prompts.

    Args:
        doc: Document dictionary with content

    Returns:
        List of extracted values (percentages, euro amounts, dates)
    """
    content = doc.get("content", "")
    if not content:
        return []

    values = []

    # Extract percentages (e.g., 22%, 10,5%)
    percentages = re.findall(r"\b\d+(?:[,\.]\d+)?%", content)
    values.extend(percentages)

    # Extract euro amounts (e.g., €1.000, 5.000 euro, € 10.000)
    euro_amounts = re.findall(r"€\s*[\d.,]+|\b[\d.]+(?:,\d+)?\s*euro\b", content, re.IGNORECASE)
    values.extend(euro_amounts[:5])  # Limit euro amounts

    # Extract dates in Italian format (e.g., 15/03/2024, 15 marzo 2024)
    dates = re.findall(r"\b\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b", content)
    values.extend(dates[:3])  # Limit dates

    # Extract article numbers (e.g., Art. 16, articolo 2)
    articles = re.findall(r"Art\.?\s*\d+|articolo\s+\d+", content, re.IGNORECASE)
    values.extend(articles[:3])  # Limit articles

    # Deduplicate
    return list(dict.fromkeys(values))[:15]  # Cap at 15 values


def generate_paragraph_id(doc_id: str, paragraph_index: int) -> str:
    """Generate a unique paragraph ID for source tracking (DEV-236).

    Args:
        doc_id: Document ID
        paragraph_index: Index of the paragraph within the document

    Returns:
        Unique paragraph ID in format "doc_id_p{index}"
    """
    if not doc_id:
        return f"unknown_p{paragraph_index}"
    return f"{doc_id}_p{paragraph_index}"


def extract_paragraph_excerpt(content: str | None, max_length: int = 150) -> str:
    """Extract the first meaningful paragraph as excerpt for tooltip display (DEV-236).

    Args:
        content: Document content text
        max_length: Maximum excerpt length (default 150 for UI tooltip)

    Returns:
        First paragraph excerpt, truncated with ellipsis if needed
    """
    if not content:
        return ""

    # Strip and check for whitespace-only
    content = content.strip()
    if not content:
        return ""

    # Take the first part up to max_length
    if len(content) <= max_length:
        return content

    # Truncate at max_length and add ellipsis
    truncated = content[:max_length]

    # Try to break at word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:  # Only if we can keep 70%+ of the content
        truncated = truncated[:last_space]

    return truncated + "..."


def _build_kb_sources_metadata(
    kb_documents: list[dict],
    user_query: str | None = None,
) -> list[dict]:
    """Build structured metadata for action grounding from KB documents.

    DEV-236: Now includes paragraph_id and paragraph_excerpt for paragraph-level grounding.
    DEV-237: Uses ParagraphExtractor for query-relevant paragraph extraction.

    Args:
        kb_documents: List of KB document dictionaries
        user_query: User query for relevance-based paragraph extraction (DEV-237)

    Returns:
        List of metadata dictionaries for each document
    """
    metadata_list = []

    # DEV-237: Initialize paragraph extractor for relevance-based extraction
    extractor = ParagraphExtractor()

    for idx, doc in enumerate(kb_documents):
        if not isinstance(doc, dict):
            continue

        doc_id = doc.get("id", "")
        content = doc.get("content", "")

        # DEV-237: Extract most relevant paragraph using query
        paragraph_id = generate_paragraph_id(doc_id, 0)  # Default to first
        paragraph_excerpt = extract_paragraph_excerpt(content)
        relevance_score = 0.0

        if user_query and content:
            paragraph_result = extractor.extract_best_paragraph(
                content=content,
                query=user_query,
                doc_id=doc_id,
            )
            if paragraph_result:
                paragraph_id = paragraph_result.paragraph_id
                paragraph_excerpt = paragraph_result.excerpt
                relevance_score = paragraph_result.relevance_score

        metadata = {
            "id": doc_id,
            "title": doc.get("title", ""),
            "type": doc.get("type", ""),
            "date": doc.get("date") or "data non disponibile",
            "url": doc.get("url"),
            "key_topics": extract_topics(doc),
            "key_values": extract_values(doc),
            "hierarchy_weight": get_hierarchy_weight(doc.get("type", "")),
            # DEV-236: Paragraph-level grounding fields
            # DEV-237: Now using relevance-based extraction
            "paragraph_id": paragraph_id,
            "paragraph_excerpt": paragraph_excerpt,
            "paragraph_relevance_score": relevance_score,  # DEV-237
        }
        metadata_list.append(metadata)

    return metadata_list


async def node_step_40(state: RAGState) -> RAGState:
    """Node wrapper for Step 40: Build unified context.

    Args:
        state: Current RAG state with facts and KB docs

    Returns:
        Updated state with merged context, kb_documents, and kb_sources_metadata
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

        # DEV-213: Preserve KB documents and metadata for action grounding
        kb_results = res.get("kb_results") or []

        # Filter out malformed documents (must be dict)
        valid_kb_docs = [doc for doc in kb_results if isinstance(doc, dict)]

        # Log if documents were filtered
        if len(valid_kb_docs) < len(kb_results):
            step40_logger.warning(
                "step40_malformed_docs_skipped",
                original_count=len(kb_results),
                valid_count=len(valid_kb_docs),
                skipped_count=len(kb_results) - len(valid_kb_docs),
                request_id=state.get("request_id"),
            )

        # Cap at MAX_KB_DOCUMENTS for performance
        if len(valid_kb_docs) > MAX_KB_DOCUMENTS:
            step40_logger.info(
                "step40_kb_docs_capped",
                original_count=len(valid_kb_docs),
                capped_count=MAX_KB_DOCUMENTS,
                request_id=state.get("request_id"),
            )
            valid_kb_docs = valid_kb_docs[:MAX_KB_DOCUMENTS]

        # Store raw KB documents
        state["kb_documents"] = valid_kb_docs

        # Build and store structured metadata
        # DEV-237: Pass user_query for relevance-based paragraph extraction
        user_query = state.get("user_query")
        state["kb_sources_metadata"] = _build_kb_sources_metadata(valid_kb_docs, user_query)

        # DEV-242 FIX: Check KB-empty BEFORE prompt is built in Step 41
        # This ensures the warning is in kb_context when the system prompt is rendered
        from app.core.langgraph.nodes.step_064__llm_call import _check_kb_empty_and_inject_warning

        kb_empty = _check_kb_empty_and_inject_warning(state)
        state["kb_was_empty"] = kb_empty
        if kb_empty:
            step40_logger.warning(
                "kb_empty_detected_step40",
                user_query=(state.get("user_message") or state.get("user_query", ""))[:100],
                kb_sources_count=len(state.get("kb_sources_metadata", [])),
                kb_context_len=len(state.get("kb_context", "")),
            )

        step40_logger.debug(
            "step40_kb_preservation_complete",
            kb_documents_count=len(state["kb_documents"]),
            kb_metadata_count=len(state["kb_sources_metadata"]),
            request_id=state.get("request_id"),
        )

    # DEV-007 DIAGNOSTIC: Log context value stored in state
    context_value = state.get("context", "")
    # Count document headers to verify all documents are present
    doc_headers_count = context_value.count("[Documento:")
    expected_doc_count = state["context_metadata"].get("doc_facts_count", 0)

    # DEV-007 DIAGNOSTIC: Extract document order from context to verify current docs come first
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
            # DEV-213: KB preservation diagnostics
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
