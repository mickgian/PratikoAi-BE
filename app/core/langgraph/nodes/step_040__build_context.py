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
from app.services.italian_stop_words import STOP_WORDS
from app.services.paragraph_extractor import ParagraphExtractor

STEP = 40

# Maximum number of KB documents to preserve (performance cap)
MAX_KB_DOCUMENTS = 20

# DEV-244: Minimum RRF score to display in Fonti dropdown
# Filters out low-relevance keyword matches (e.g., "Interpello prima casa" matching "agevolazione")
# RRF scores typically range from 0.001 to 0.05; 0.008 filters docs ranking below ~6th in single search
MIN_FONTI_RELEVANCE_SCORE = 0.008

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

# DEV-245: Category labels in Italian for Fonti section display
CATEGORY_LABELS_IT: dict[str, str] = {
    "regulatory_documents": "normativa",
    "legge": "legge",
    "decreto_legislativo": "decreto legislativo",
    "decreto": "decreto",
    "dpr": "DPR",
    "decreto_ministeriale": "decreto ministeriale",
    "regolamento_ue": "regolamento UE",
    "circolare": "circolare",
    "risoluzione": "risoluzione",
    "interpello": "interpello",
    "faq": "FAQ",
    "cassazione": "Cassazione",
    "corte_costituzionale": "Corte Costituzionale",
    "prassi": "prassi",
    "guida": "guida",
    "web": "web",  # DEV-245: Web sources from Brave Search
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


def get_category_label_it(category: str | None) -> str:
    """Return Italian label for category/type for Fonti display (DEV-245).

    Args:
        category: Internal category name (e.g., 'regulatory_documents', 'legge')

    Returns:
        Italian label for display, or empty string if unknown
    """
    if not category:
        return ""
    return CATEGORY_LABELS_IT.get(category.lower(), category.replace("_", " "))


def simplify_title(title: str | None) -> str:
    """Simplify document title for Fonti display (DEV-245).

    Removes article references and truncated text from titles like:
    "LEGGE 30 dicembre 2025, n. 199 - Art. 1 - guenti: «33 per c…"
    → "LEGGE 30 dicembre 2025, n. 199"

    Args:
        title: Full document title

    Returns:
        Simplified title without article details
    """
    if not title:
        return ""

    # Pattern 1: Remove " - Art. X" and everything after
    # Matches: " - Art. 1", " - Art. 16", " - Articolo 3"
    simplified = re.sub(r"\s*-\s*Art(?:icolo)?\.?\s*\d+.*$", "", title, flags=re.IGNORECASE)

    # Pattern 2: Remove truncated text (ends with "…" or "...")
    # If title was truncated mid-word, remove the partial word
    if simplified.endswith("…") or simplified.endswith("..."):
        simplified = re.sub(r"\s+\S*[…\.]{2,}$", "", simplified)

    # Pattern 3: Remove trailing " - " with partial content
    simplified = re.sub(r"\s*-\s*[^-]{0,20}$", "", simplified)

    # Clean up any trailing punctuation or whitespace
    simplified = simplified.rstrip(" -–—:")

    return simplified.strip()


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


def _extract_filter_keywords_from_query(query: str) -> list[str]:
    """DEV-245 Phase 5.13: Extract keywords using stop word list for web source filtering.

    DEV-245 Phase 5.13: Reverted from YAKE to stop word lists.
    YAKE didn't work well for short Italian fiscal queries - it prioritized
    verbs like "recepira" over domain terms like "rottamazione".

    DEV-245 Phase 5.14: Uses centralized STOP_WORDS from italian_stop_words module.
    This includes comprehensive verb conjugations (future, conditional, imperative)
    to fix the "recepira" problem where future tense verbs slipped through.

    Example:
        - User asks: "irap" (short follow-up)
        - Reformulated by step_039a: "L'IRAP può essere inclusa nella rottamazione quinquies?"
        - Extracted keywords: ["irap", "rottamazione", "quinquies", ...]

    Args:
        query: The reformulated user query (from step_039a via query_variants.original_query)

    Returns:
        List of significant keywords for filtering (lowercase), max 10 keywords
    """
    # DEV-245 Phase 5.14: Use centralized stop words module
    # Includes comprehensive verb conjugations to fix "recepira" problem

    if not query:
        return []

    # Normalize and tokenize
    query_lower = query.lower()
    # Handle Italian contractions: "dell'irap" → "dell irap"
    query_lower = re.sub(r"[''`]", " ", query_lower)
    # Split on non-alphanumeric (keep accented chars)
    words = re.findall(r"[a-zàèéìòùáéíóú]+", query_lower)

    # Filter stop words and short words
    keywords = []
    for word in words:
        if word not in STOP_WORDS and len(word) > 2:
            keywords.append(word)

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    # Return up to 10 keywords for filtering (more than search's 5)
    return unique_keywords[:10]


def _is_web_source_topic_relevant(
    doc: dict,
    query_keywords: list[str],
    topic_keywords: list[str] | None = None,
) -> bool:
    """DEV-245 Phase 5.5: Check if web source is relevant to the conversation topic.

    CRITICAL: If topic_keywords are provided (e.g., ["rottamazione", "quinquies"]),
    ALL of them must appear in the web result. This prevents "rottamazione ter"
    results from passing when the topic is "rottamazione quinquies".

    Example:
        - Topic: "rottamazione quinquies" → topic_keywords = ["rottamazione", "quinquies"]
        - Q5: "la regione sicilia recepira' la rottamazione dell'irap?"
        - Web result: "Rottamazione Ter 2024 - Sicilia" (contains "rottamazione" + "sicilia")
        - OLD behavior: PASS (any keyword matches)
        - NEW behavior: FAIL (missing "quinquies" from topic)

    Args:
        doc: Web document dict with content/title
        query_keywords: Keywords extracted from reformulated query
        topic_keywords: Core topic keywords that MUST ALL match (DEV-245 Phase 5.5)

    Returns:
        True if web source is relevant, False if it should be filtered
    """
    # Combine title and content for keyword matching
    title = doc.get("source_name", "") or doc.get("title", "") or ""
    content = doc.get("content", "") or ""
    combined_text = f"{title} {content}".lower()

    # DEV-245 Phase 5.5 FIX: Check topic_keywords FIRST (strictest filter)
    # This must happen BEFORE the early return for empty query_keywords.
    # Otherwise, if query_keywords is empty, all web sources pass through!
    # Requires 2+ topic keywords to enable strict matching (single keyword is too restrictive).
    if topic_keywords and isinstance(topic_keywords, list) and len(topic_keywords) >= 2:
        # Require ALL topic keywords to be present
        topic_match = all(kw.lower() in combined_text for kw in topic_keywords)
        if not topic_match:
            return False  # Reject: doesn't match conversation topic

    # No query keywords = allow (but only AFTER topic filter passed above)
    if not query_keywords:
        return True

    # General sanity check: at least one query keyword must match
    return any(kw in combined_text for kw in query_keywords)


def _build_kb_sources_metadata(
    kb_documents: list[dict],
    user_query: str | None = None,
    min_score: float = MIN_FONTI_RELEVANCE_SCORE,
) -> list[dict]:
    """Build structured metadata for action grounding from KB documents.

    DEV-236: Now includes paragraph_id and paragraph_excerpt for paragraph-level grounding.
    DEV-237: Uses ParagraphExtractor for query-relevant paragraph extraction.
    DEV-244: Filters out low-relevance documents to improve Fonti quality.

    Args:
        kb_documents: List of KB document dictionaries
        user_query: User query for relevance-based paragraph extraction (DEV-237)
        min_score: Minimum RRF/combined score to include in Fonti (DEV-244)

    Returns:
        List of metadata dictionaries for each document
    """
    metadata_list = []
    filtered_count = 0  # DEV-244: Track filtered docs

    # DEV-237: Initialize paragraph extractor for relevance-based extraction
    extractor = ParagraphExtractor()

    for idx, doc in enumerate(kb_documents):
        if not isinstance(doc, dict):
            continue

        # DEV-244: Filter out low-relevance documents from Fonti display
        rrf_score = doc.get("rrf_score", 0) or doc.get("combined_score", 0) or 0
        if rrf_score < min_score:
            filtered_count += 1
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

        # DEV-245: Simplify title and use Italian category labels
        raw_title = doc.get("title", "")
        raw_type = doc.get("type", "") or doc.get("category", "")

        metadata = {
            "id": doc_id,
            "title": simplify_title(raw_title),
            "type": get_category_label_it(raw_type),
            "date": doc.get("date") or "",  # DEV-245: Empty if not available (frontend handles)
            # DEV-244 FIX: parallel_retrieval stores URL in "source_url", not "url"
            # Check multiple fields for backwards compatibility
            "url": doc.get("source_url") or doc.get("url") or doc.get("metadata", {}).get("source_url"),
            "key_topics": extract_topics(doc),
            "key_values": extract_values(doc),
            "hierarchy_weight": get_hierarchy_weight(raw_type),
            # DEV-236: Paragraph-level grounding fields
            # DEV-237: Now using relevance-based extraction
            "paragraph_id": paragraph_id,
            "paragraph_excerpt": paragraph_excerpt,
            "paragraph_relevance_score": relevance_score,  # DEV-237
        }
        metadata_list.append(metadata)

    # DEV-244: Log filtering results
    if filtered_count > 0:
        step40_logger.info(
            "fonti_low_relevance_filtered",
            filtered_count=filtered_count,
            remaining_count=len(metadata_list),
            min_score=min_score,
        )

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
        # DEV-245 Phase 3.4: Pre-filter web docs BEFORE context building
        # This ensures irrelevant web content doesn't pollute the LLM context.
        # Previously, filtering only happened for Fonti display, meaning LLM still saw irrelevant content.
        query_variants = state.get("query_variants", {})
        filter_query = query_variants.get("original_query") or state.get("user_query", "")

        # DEV-245 Phase 4.2.1: Use search keywords from Step 039c if available
        # This ensures web filtering uses the SAME keywords as Brave search.
        # Without this, IRAP-specific results could be filtered out because
        # _extract_filter_keywords_from_query() may extract different keywords.
        search_keywords = state.get("search_keywords")
        # DEV-245 Phase 5.12: Get keyword scores for evaluation
        search_keywords_with_scores = state.get("search_keywords_with_scores")
        if search_keywords:
            query_keywords = search_keywords
            step40_logger.info(
                "DEV245_using_search_keywords_from_state",
                keywords=query_keywords,
                keywords_with_scores=search_keywords_with_scores,  # DEV-245 Phase 5.12
                source="step_039c_retrieval",
            )
        else:
            query_keywords = _extract_filter_keywords_from_query(filter_query)
            step40_logger.info(
                "DEV245_extracting_filter_keywords",
                keywords=query_keywords,
                source="local_extraction",
            )

        # DEV-245 Phase 5.5: Get topic_keywords for stricter web filtering
        # Topic keywords represent the core conversation topic (e.g., ["rottamazione", "quinquies"])
        # All topic keywords must match in web results to filter out wrong versions
        topic_keywords = state.get("topic_keywords")
        if topic_keywords and isinstance(topic_keywords, list):
            step40_logger.info(
                "DEV245_topic_keywords_for_filtering",
                topic_keywords=topic_keywords,
                keyword_count=len(topic_keywords),
            )
        else:
            topic_keywords = None  # Ensure clean None if invalid type

        # Get retrieval results and filter web docs BEFORE context building
        retrieval_result = state.get("retrieval_result", {})
        all_docs = retrieval_result.get("documents", [])

        # DEV-245 Phase 3.6: Debug logging for Fonti troubleshooting
        step40_logger.info(
            "DEV245_step40_retrieval_debug",
            retrieval_result_keys=list(retrieval_result.keys()) if retrieval_result else [],
            all_docs_count=len(all_docs),
            filter_query=filter_query[:100] if filter_query else "(empty)",
            query_keywords=query_keywords,
            user_query=(state.get("user_query", ""))[:50],
        )

        filtered_docs = []
        web_prefiltered_count = 0
        for doc in all_docs:
            if not isinstance(doc, dict):
                continue
            metadata = doc.get("metadata") or {}
            source_type = doc.get("source_type", "") or ""
            is_web = (
                metadata.get("is_web_result", False)
                or source_type == "web"
                or source_type == "web_ai_summary"
                or doc.get("document_id", "").startswith("web_")
            )

            if is_web:
                # DEV-245 Phase 5.5: Apply topic filter to web docs BEFORE context building
                # Pass topic_keywords for stricter filtering (ALL topic keywords must match)
                if _is_web_source_topic_relevant(doc, query_keywords, topic_keywords):
                    filtered_docs.append(doc)
                else:
                    web_prefiltered_count += 1
                    step40_logger.info(
                        "web_doc_prefiltered",
                        title=(doc.get("source_name", "") or doc.get("title", ""))[:50],
                        keywords=query_keywords,
                        topic_keywords=topic_keywords,
                    )
            else:
                # KB docs always included
                filtered_docs.append(doc)

        # DEV-245 Phase 3.6: Enhanced debug logging for Fonti troubleshooting
        kb_doc_count = sum(
            1
            for d in filtered_docs
            if not (
                (d.get("metadata") or {}).get("is_web_result", False)
                or d.get("source_type", "") in ("web", "web_ai_summary")
                or d.get("document_id", "").startswith("web_")
            )
        )
        web_doc_count = len(filtered_docs) - kb_doc_count

        step40_logger.info(
            "DEV245_step40_filter_complete",
            original_count=len(all_docs),
            web_prefiltered_count=web_prefiltered_count,
            remaining_total=len(filtered_docs),
            remaining_kb_docs=kb_doc_count,
            remaining_web_docs=web_doc_count,
            keywords=query_keywords,
        )

        # Update retrieval_result with filtered docs for context building
        filtered_retrieval = {**retrieval_result, "documents": filtered_docs}
        filtered_ctx = {**dict(state), "retrieval_result": filtered_retrieval}

        # NOW call context builder with filtered docs (irrelevant web content removed)
        res = await step_40__build_context(messages=state.get("messages", []), ctx=filtered_ctx)

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
        # DEV-245: Separate KB documents from web results for proper attribution
        kb_results = res.get("kb_results") or []

        # DEV-245 Phase 3: Debug logging to trace web doc detection
        if kb_results:
            sample_doc = kb_results[0]
            step40_logger.info(
                "step40_kb_results_debug",
                total_docs=len(kb_results),
                sample_keys=list(sample_doc.keys()) if isinstance(sample_doc, dict) else [],
                sample_source_type=sample_doc.get("source_type") if isinstance(sample_doc, dict) else None,
                sample_metadata_keys=list((sample_doc.get("metadata") or {}).keys())
                if isinstance(sample_doc, dict)
                else [],
                sample_is_web_result=sample_doc.get("metadata", {}).get("is_web_result")
                if isinstance(sample_doc, dict)
                else None,
                sample_document_id=(sample_doc.get("document_id", "") or "")[:30]
                if isinstance(sample_doc, dict)
                else None,
            )

        # Filter out malformed documents (must be dict)
        valid_kb_docs = []
        web_docs = []
        for doc in kb_results:
            if not isinstance(doc, dict):
                continue
            # DEV-245 Phase 3: More robust web result detection
            # Check multiple fields since serialization may vary
            metadata = doc.get("metadata") or {}
            source_type = doc.get("source_type", "") or ""

            is_web = (
                metadata.get("is_web_result", False)
                or source_type == "web"
                or source_type == "web_ai_summary"
                or doc.get("document_id", "").startswith("web_")
            )
            if is_web:
                web_docs.append(doc)
            else:
                valid_kb_docs.append(doc)

        # DEV-245: Log document separation results
        step40_logger.info(
            "step40_docs_separated",
            kb_docs_count=len(valid_kb_docs),
            web_docs_count=len(web_docs),
            total_retrieval_count=len(kb_results),
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

        # DEV-245: Store web sources separately for proper attribution
        state["web_documents"] = web_docs

        # Build and store structured metadata
        # DEV-237: Pass user_query for relevance-based paragraph extraction
        user_query = state.get("user_query")
        kb_sources_metadata = _build_kb_sources_metadata(valid_kb_docs, user_query)

        # DEV-245 Phase 5.5: Reuse query_keywords and topic_keywords from pre-filter
        # (Already extracted at the start of node_step_40, no need to re-extract)

        # DEV-245: Merge web sources into kb_sources_metadata for unified Fonti display
        # Web sources appear alongside KB sources with "web" label
        # DEV-245 Phase 5.5: Filter to only topic-relevant web sources
        web_filtered_count = 0
        for doc in web_docs:
            # DEV-245 Phase 5.5: Skip web sources that don't match conversation topic
            # Pass topic_keywords for stricter filtering (ALL topic keywords must match)
            if not _is_web_source_topic_relevant(doc, query_keywords, topic_keywords):
                web_filtered_count += 1
                step40_logger.info(
                    "web_source_filtered_off_topic",
                    title=(doc.get("source_name", "") or doc.get("title", ""))[:50],
                    query_keywords=query_keywords,
                    topic_keywords=topic_keywords,
                )
                continue

            content = doc.get("content", "")
            excerpt = content[:500] if content else ""
            kb_sources_metadata.append(
                {
                    "id": doc.get("document_id", ""),
                    "title": doc.get("source_name", "") or doc.get("title", ""),
                    "url": doc.get("source_url") or doc.get("metadata", {}).get("source_url"),
                    "type": "web",  # DEV-245: "web" label in Fonti section
                    "date": "",
                    "excerpt": excerpt,
                    "is_ai_synthesis": doc.get("metadata", {}).get("is_ai_synthesis", False),
                    # Standard fields for compatibility
                    "key_topics": [],
                    "key_values": [],
                    "hierarchy_weight": 0.3,  # Lower than legal sources
                    "paragraph_id": "",
                    "paragraph_excerpt": excerpt,
                    "paragraph_relevance_score": 0.0,
                }
            )

        # DEV-245 Phase 5.5: Log filtering results with topic keywords
        if web_filtered_count > 0:
            step40_logger.info(
                "web_sources_topic_filtered",
                filtered_count=web_filtered_count,
                remaining_count=len(web_docs) - web_filtered_count,
                query_keywords=query_keywords,
                topic_keywords=topic_keywords,
            )

        state["kb_sources_metadata"] = kb_sources_metadata

        # DEV-245: Keep web_sources_metadata for backwards compatibility but mark deprecated
        # TODO: Remove in future release once frontend is updated
        state["web_sources_metadata"] = []  # Empty - sources are now in kb_sources_metadata

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
            web_documents_count=len(state.get("web_documents", [])),  # DEV-245
            web_metadata_count=len(state.get("web_sources_metadata", [])),  # DEV-245
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
