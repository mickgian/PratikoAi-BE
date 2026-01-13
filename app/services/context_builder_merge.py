"""RAG STEP 40 — ContextBuilder.merge facts and KB docs and optional doc facts

This module implements the context building logic that merges canonical facts,
KB search results, and optional document facts into a unified context for LLM processing.
It handles token budgets, content prioritization, and deduplication.

Based on Mermaid diagram: BuildContext (ContextBuilder.merge facts and KB docs and optional doc facts)
"""

import re
import time
from dataclasses import dataclass
from datetime import (
    UTC,
    datetime,
    timezone,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from app.core.logging import logger
from app.observability.rag_logging import (
    rag_step_log,
    rag_step_timer,
)
from app.services.knowledge_search_service import SearchResult

# DEV-007 Issue 9: Import QueryComposition for type hints (lazy import to avoid circular)
# Actual enum imported in get_composition_priority_weights() to avoid import cycles


# =============================================================================
# DEV-007 Issue 9: Adaptive Priority Weights by Query Composition
# =============================================================================
# When user attaches a document, LLM classifies their intent and we adjust
# priority weights accordingly. This ensures document content is prioritized
# when user wants document analysis, and KB docs when they want regulatory info.
#
# Priority weights determine how token budget is allocated:
# - Higher weight = more tokens allocated to that source
# - Weights are normalized during budget allocation

COMPOSITION_PRIORITY_WEIGHTS = {
    # PURE_DOCUMENT: User wants document analysis only
    # e.g., "calcola la mia pensione" + fondo_pensione.xlsx
    "pure_doc": {"facts": 0.2, "kb_docs": 0.2, "document_facts": 0.6},
    # HYBRID: User wants document analysis + regulatory context
    # e.g., "verifica se rispetta la normativa" + bilancio.xlsx
    "hybrid": {"facts": 0.25, "kb_docs": 0.5, "document_facts": 0.5},
    # PURE_KB: No attachments or query unrelated to document
    # e.g., "aliquote IVA 2024?" (no attachment)
    "pure_kb": {"facts": 0.3, "kb_docs": 0.6, "document_facts": 0.1},
    # CONVERSATIONAL: Greetings, chitchat - minimal retrieval needed
    # e.g., "ciao!"
    "chat": {"facts": 0.5, "kb_docs": 0.3, "document_facts": 0.2},
}


def get_composition_priority_weights(query_composition: str | None) -> dict[str, float]:
    """Get priority weights based on query composition type.

    DEV-007 Issue 9: Returns appropriate weights for context source prioritization.

    Args:
        query_composition: QueryComposition value as string (or None for default)

    Returns:
        Dict with priority weights for facts, kb_docs, and document_facts
    """
    if query_composition and query_composition in COMPOSITION_PRIORITY_WEIGHTS:
        weights = COMPOSITION_PRIORITY_WEIGHTS[query_composition]
        logger.info(
            "composition_weights_applied",
            composition=query_composition,
            weights=weights,
        )
        return weights

    # Default: PURE_KB behavior (backward compatible)
    return COMPOSITION_PRIORITY_WEIGHTS["pure_kb"]


@dataclass
class ContextPart:
    """Individual piece of context from a source."""

    type: str  # "facts", "kb_docs", "document_facts"
    content: str
    tokens: int
    priority_score: float
    metadata: dict[str, Any]


def extract_publication_date(content: str, title: str = "") -> str | None:
    """Extract publication date from document content.

    Looks for common Italian date patterns like:
    - "Roma, 13 ottobre 2025"
    - "del 13 ottobre 2025"
    - "13 ottobre 2025"

    Args:
        content: Document content
        title: Document title (optional)

    Returns:
        Formatted date string or None if not found
    """
    # Combine title and first 500 chars of content for date search
    search_text = f"{title} {content[:500]}"

    # Italian date patterns
    date_patterns = [
        r"Roma,?\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        r"del\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        r"n\.\s*\d+\s+del\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            day, month, year = match.groups()
            return f"{day} {month} {year}"

    return None


@dataclass
class MergedContext:
    """Result of context merging operation."""

    merged_context: str
    context_parts: list[dict[str, Any]]
    token_count: int
    source_distribution: dict[str, int]
    context_quality_score: float
    deduplication_applied: bool = False
    content_truncated: bool = False
    budget_exceeded: bool = False


class ContextBuilderMerge:
    """RAG STEP 40 — ContextBuilder for merging facts, KB docs, and document facts.

    This class handles the merging of different types of content into a unified
    context that will be passed to the LLM for response generation.
    """

    def __init__(self):
        self.STEP_NUM = 40
        self.STEP_ID = "RAG.facts.contextbuilder.merge.facts.and.kb.docs.and.optional.doc.facts"
        self.NODE_LABEL = "BuildContext"

        # Default configuration
        # Base budget: 3500 tokens (efficient for most queries)
        # Dynamic scaling: increases in 500-token steps up to 30000 based on content needs
        # DEV-007: Increased from 8000 to 30000 to support 5 documents at ~5000 tokens each
        self.default_max_tokens = 3500
        self.max_budget_limit = 30000
        self.budget_step_size = 500
        self.default_priority_weights = {"facts": 0.3, "kb_docs": 0.5, "document_facts": 0.2}

    def calculate_optimal_budget(self, kb_results: list, base_budget: int | None = None) -> int:
        """Dynamically calculate optimal token budget based on search results.

        Uses smart heuristics to balance cost and quality:
        - Small result sets: use base budget (3500 tokens)
        - Large result sets: scale up in 500-token increments
        - Maximum: 8000 tokens

        Args:
            kb_results: List of search results (chunks)
            base_budget: Base budget to use (defaults to self.default_max_tokens)

        Returns:
            Optimal token budget (multiple of 500 between base and 8000)
        """
        if base_budget is None:
            base_budget = self.default_max_tokens

        if not kb_results:
            return base_budget

        num_chunks = len(kb_results)

        # Heuristic: Each chunk averages ~500 tokens (including title, formatting, metadata)
        # Add 500 token buffer for section headers and structure
        estimated_tokens = (num_chunks * 500) + 500

        # Round up to nearest 500 (our step size)
        optimal = ((estimated_tokens + self.budget_step_size - 1) // self.budget_step_size) * self.budget_step_size

        # Clamp between base and max
        final_budget = max(base_budget, min(optimal, self.max_budget_limit))

        # Log decision for transparency
        if final_budget > base_budget:
            logger.info(
                "dynamic_budget_calculated",
                num_chunks=num_chunks,
                estimated_tokens=estimated_tokens,
                base_budget=base_budget,
                calculated_budget=final_budget,
                increase=final_budget - base_budget,
                reason="scaled_up_for_content_size",
            )

        return final_budget

    def merge_context(self, context_data: dict[str, Any]) -> dict[str, Any]:
        """Merge facts, KB docs, and optional document facts into unified context.

        Args:
            context_data: Dictionary containing:
                - canonical_facts: List of extracted canonical facts
                - kb_results: List of SearchResult from KB search
                - document_facts: Optional list of document-extracted facts
                - query: Original user query
                - trace_id: Trace identifier for logging
                - user_id: User identifier
                - session_id: Session identifier
                - max_context_tokens: Token budget limit (optional)
                - priority_weights: Weights for different content types (optional)

        Returns:
            Dict with merged context:
                - merged_context: Final context text
                - context_parts: List of individual context parts
                - token_count: Total tokens used
                - source_distribution: Distribution of content by type
                - context_quality_score: Quality assessment
        """
        start_time = time.perf_counter()

        # Extract parameters
        canonical_facts = context_data.get("canonical_facts", [])
        kb_results = context_data.get("kb_results", [])
        document_facts = context_data.get("document_facts", [])
        query = context_data.get("query", "")
        trace_id = context_data.get("trace_id")
        user_id = context_data.get("user_id")
        session_id = context_data.get("session_id")
        base_max_tokens = context_data.get("max_context_tokens", self.default_max_tokens)
        priority_weights = context_data.get("priority_weights", self.default_priority_weights)

        # DEV-007 FIX: Dynamic budget increase for multiple document_facts
        # Each document (payslip, invoice, etc.) can be 1500-2500 tokens
        # Without this fix, second+ documents get truncated due to budget exhaustion
        if document_facts and len(document_facts) > 1:
            # Add 2500 tokens per additional document (conservative estimate for payslips)
            additional_budget = (len(document_facts) - 1) * 2500
            max_tokens = min(base_max_tokens + additional_budget, self.max_budget_limit)
            logger.info(
                "multi_document_budget_increase",
                document_count=len(document_facts),
                base_budget=base_max_tokens,
                additional_budget=additional_budget,
                final_budget=max_tokens,
                max_limit=self.max_budget_limit,
            )
        else:
            max_tokens = base_max_tokens

        try:
            # Use timer context manager for performance tracking
            with rag_step_timer(self.STEP_NUM, self.STEP_ID, self.NODE_LABEL, query=query, trace_id=trace_id):
                # Initial logging
                rag_step_log(
                    step=self.STEP_NUM,
                    step_id=self.STEP_ID,
                    node_label=self.NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    facts_count=len(canonical_facts),
                    kb_results_count=len(kb_results),
                    document_facts_count=len(document_facts) if document_facts else 0,
                    max_tokens=max_tokens,
                    processing_stage="started",
                )

                # Handle empty inputs
                if not canonical_facts and not kb_results and not document_facts:
                    return self._create_empty_context_result(trace_id, user_id, session_id)

                # Convert inputs to ContextPart objects
                context_parts = self._create_context_parts(
                    canonical_facts, kb_results, document_facts, priority_weights
                )

                # Apply deduplication
                deduplicated_parts, deduplication_applied = self._deduplicate_content(context_parts)

                # Apply token budget and prioritization with adaptive retry
                selected_parts, content_truncated, budget_exceeded = self._apply_token_budget_with_retry(
                    deduplicated_parts, max_tokens, kb_results
                )

                # Generate final merged context text
                merged_text = self._generate_merged_context_text(selected_parts, query)

                # Calculate metrics
                total_tokens = sum(part.tokens for part in selected_parts)
                source_distribution = self._calculate_source_distribution(selected_parts)
                quality_score = self._calculate_context_quality(selected_parts, query, total_tokens, max_tokens)

                # Create result
                result = MergedContext(
                    merged_context=merged_text,
                    context_parts=self._context_parts_to_dict(selected_parts),
                    token_count=total_tokens,
                    source_distribution=source_distribution,
                    context_quality_score=quality_score,
                    deduplication_applied=deduplication_applied,
                    content_truncated=content_truncated,
                    budget_exceeded=budget_exceeded,
                )

                # Log completion
                rag_step_log(
                    step=self.STEP_NUM,
                    step_id=self.STEP_ID,
                    node_label=self.NODE_LABEL,
                    query=query,
                    trace_id=trace_id,
                    user_id=user_id,
                    session_id=session_id,
                    token_count=total_tokens,
                    max_tokens=max_tokens,
                    source_distribution=source_distribution,
                    context_quality_score=quality_score,
                    deduplication_applied=deduplication_applied,
                    content_truncated=content_truncated,
                    processing_stage="completed",
                )

                return self._convert_to_dict(result)

        except Exception as exc:
            # Calculate latency even on error
            end_time = time.perf_counter()
            latency_ms = round((end_time - start_time) * 1000.0, 2)

            # Log error
            rag_step_log(
                step=self.STEP_NUM,
                step_id=self.STEP_ID,
                node_label=self.NODE_LABEL,
                level="ERROR",
                query=query,
                error=str(exc),
                latency_ms=latency_ms,
                trace_id=trace_id,
                user_id=user_id,
                session_id=session_id,
                processing_stage="error",
            )

            # Return empty context on error (graceful degradation)
            logger.error("context_builder_merge_error", error=str(exc), trace_id=trace_id)
            return {
                "merged_context": "",
                "context_parts": [],
                "token_count": 0,
                "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
                "context_quality_score": 0.0,
                "deduplication_applied": False,
                "content_truncated": False,
                "budget_exceeded": False,
            }

    def _create_context_parts(
        self,
        canonical_facts: list[str],
        kb_results: list[SearchResult],
        document_facts: list[str] | None,
        priority_weights: dict[str, float],
    ) -> list[ContextPart]:
        """Convert inputs to ContextPart objects."""
        parts = []

        # Process canonical facts
        for i, fact in enumerate(canonical_facts):
            if fact and fact.strip():
                tokens = self._estimate_tokens(fact)
                priority = priority_weights.get("facts", 0.3) + (
                    0.1 / (i + 1)
                )  # Earlier facts slightly higher priority

                parts.append(
                    ContextPart(
                        type="facts",
                        content=fact.strip(),
                        tokens=tokens,
                        priority_score=priority,
                        metadata={"index": i, "source": "canonical_facts"},
                    )
                )

        # Process KB results
        for i, result in enumerate(kb_results):
            # Handle both dict and object formats for content access
            if isinstance(result, dict):
                content = result.get("content", "")
                title = result.get("title", "")
                score = result.get("score", 0.0)
                updated_at = result.get("updated_at")
                document_source = result.get("document_source")
                source_url = result.get("source_url")
                category = result.get("category")
                subcategory = result.get("subcategory")
            else:
                content = result.content if hasattr(result, "content") else ""
                title = result.title if hasattr(result, "title") else ""
                score = result.score if hasattr(result, "score") else 0.0
                updated_at = result.updated_at if hasattr(result, "updated_at") else None
                document_source = getattr(result, "document_source", None)
                source_url = getattr(result, "source_url", None)
                category = getattr(result, "category", None)
                subcategory = getattr(result, "subcategory", None)

            if content and content.strip():
                # Use title + content for KB results
                kb_content = f"{title}: {content}"
                tokens = self._estimate_tokens(kb_content)

                # Priority based on weight, relevance score, and recency
                base_priority = priority_weights.get("kb_docs", 0.5)
                score_boost = score * 0.2 if score else 0.0
                recency_boost = self._calculate_recency_boost(updated_at) * 0.1
                priority = base_priority + score_boost + recency_boost - (0.05 * i)  # Slight penalty for lower rank

                parts.append(
                    ContextPart(
                        type="kb_docs",
                        content=kb_content,
                        tokens=tokens,
                        priority_score=priority,
                        metadata={
                            "kb_id": result.id if hasattr(result, "id") else result.get("id"),
                            "title": result.title if hasattr(result, "title") else result.get("title"),
                            "score": result.score if hasattr(result, "score") else result.get("score"),
                            "category": category,
                            "source": result.source if hasattr(result, "source") else result.get("source"),
                            "document_source": document_source,
                            "source_url": source_url,
                            "subcategory": subcategory,
                            "updated_at": (
                                result.updated_at.isoformat()
                                if hasattr(result, "updated_at") and result.updated_at
                                else None
                            ),
                            "publication_date": (
                                result.publication_date
                                if hasattr(result, "publication_date")
                                else result.get("publication_date")
                            ),
                            "rank": i,
                        },
                    )
                )

        # Process document facts
        if document_facts:
            # DEV-007 FIX: Give ALL document_facts equal high priority
            # Previously: priority decreased with index (0.15 / (i + 1))
            # This caused later documents (Payslip 9) to be deprioritized/truncated
            # Now: All document_facts get the same high priority to ensure inclusion
            base_doc_priority = priority_weights.get("document_facts", 0.2) + 0.15
            for i, doc_fact in enumerate(document_facts):
                if doc_fact and doc_fact.strip():
                    tokens = self._estimate_tokens(doc_fact)

                    parts.append(
                        ContextPart(
                            type="document_facts",
                            content=doc_fact.strip(),
                            tokens=tokens,
                            priority_score=base_doc_priority,  # Equal priority for all docs
                            metadata={"index": i, "source": "document_facts"},
                        )
                    )

        return parts

    def _deduplicate_content(self, context_parts: list[ContextPart]) -> tuple[list[ContextPart], bool]:
        """Remove duplicate or highly similar content."""
        if len(context_parts) <= 1:
            return context_parts, False

        deduplicated = []
        seen_content = []
        deduplication_applied = False

        # Sort by priority (highest first) to keep best content
        sorted_parts = sorted(context_parts, key=lambda x: x.priority_score, reverse=True)

        for part in sorted_parts:
            is_duplicate = False

            # Check for exact matches or high similarity
            for seen in seen_content:
                similarity = self._calculate_content_similarity(part.content, seen)
                if similarity > 0.8:  # 80% similarity threshold
                    is_duplicate = True
                    deduplication_applied = True
                    break

            if not is_duplicate:
                deduplicated.append(part)
                seen_content.append(part.content)

        return deduplicated, deduplication_applied

    def _apply_token_budget_with_retry(
        self, context_parts: list[ContextPart], initial_budget: int, kb_results: list
    ) -> tuple[list[ContextPart], bool, bool]:
        """Apply token budget with adaptive retry if content doesn't fit.

        Tries initial budget, then increases in 500-token steps up to max (8000) if needed.

        Args:
            context_parts: Context parts to fit
            initial_budget: Starting token budget
            kb_results: Search results (for logging)

        Returns:
            Tuple of (selected_parts, content_truncated, budget_exceeded)
        """
        current_budget = initial_budget
        max_attempts = (self.max_budget_limit - initial_budget) // self.budget_step_size + 1

        for attempt in range(max_attempts):
            selected_parts, content_truncated, budget_exceeded = self._apply_token_budget(
                context_parts, current_budget
            )

            # If everything fits, we're done
            if not budget_exceeded:
                if attempt > 0:  # Only log if we actually retried
                    logger.info(
                        "adaptive_retry_succeeded",
                        initial_budget=initial_budget,
                        final_budget=current_budget,
                        attempts=attempt + 1,
                        parts_included=len(selected_parts),
                        content_truncated=content_truncated,
                    )
                return selected_parts, content_truncated, budget_exceeded

            # Budget exceeded - can we retry with more budget?
            if current_budget >= self.max_budget_limit:
                # Already at max, can't increase further
                logger.warning(
                    "max_budget_reached_content_still_truncated",
                    max_budget=self.max_budget_limit,
                    parts_included=len(selected_parts),
                    total_parts=len(context_parts),
                    kb_results_count=len(kb_results),
                )
                return selected_parts, content_truncated, budget_exceeded

            # Increase budget by step size and retry
            old_budget = current_budget
            current_budget = min(current_budget + self.budget_step_size, self.max_budget_limit)

            logger.info(
                "adaptive_budget_increase",
                attempt=attempt + 1,
                old_budget=old_budget,
                new_budget=current_budget,
                reason="content_exceeded_budget",
            )

        # Shouldn't reach here, but return last attempt if we do
        return selected_parts, content_truncated, budget_exceeded

    def _apply_token_budget(
        self, context_parts: list[ContextPart], max_tokens: int
    ) -> tuple[list[ContextPart], bool, bool]:
        """Apply token budget constraints with priority-based selection.

        DEV-007 FIX: Removed `break` statement that was silently dropping remaining
        documents after truncation. Now continues loop to track all excluded parts.
        """
        if not context_parts:
            return [], False, False

        # Sort by priority score (descending)
        sorted_parts = sorted(context_parts, key=lambda x: x.priority_score, reverse=True)

        selected_parts = []
        excluded_parts = []  # DEV-007: Track excluded parts for logging
        total_tokens = 0
        content_truncated = False
        budget_exceeded = False

        for idx, part in enumerate(sorted_parts):
            if total_tokens + part.tokens <= max_tokens:
                selected_parts.append(part)
                total_tokens += part.tokens
            else:
                # Try to fit truncated content
                remaining_tokens = max_tokens - total_tokens
                part_included = False

                if remaining_tokens > 50:  # Minimum meaningful content
                    truncated_content = self._truncate_content(part.content, remaining_tokens)
                    if truncated_content:
                        truncated_part = ContextPart(
                            type=part.type,
                            content=truncated_content,
                            tokens=remaining_tokens,
                            priority_score=part.priority_score,
                            metadata={**part.metadata, "truncated": True},
                        )
                        selected_parts.append(truncated_part)
                        content_truncated = True
                        total_tokens = max_tokens
                        part_included = True
                        # DEV-007 FIX: REMOVED `break` - continue to track excluded parts

                # DEV-007: Track and log excluded parts
                if not part_included:
                    excluded_parts.append(part)

                    # Log exclusion with details
                    logger.warning(
                        "context_part_excluded_budget",
                        extra={
                            "part_index": idx,
                            "part_type": part.type,
                            "part_content_preview": part.content[:100] if part.content else "",
                            "tokens_needed": part.tokens,
                            "tokens_available": remaining_tokens,
                            "priority_score": part.priority_score,
                            "exclusion_reason": "insufficient_budget",
                        },
                    )

                budget_exceeded = True

        # DEV-007: Log budget summary
        if excluded_parts:
            doc_parts_excluded = sum(1 for p in excluded_parts if p.type == "document_facts")
            logger.info(
                "token_budget_application_complete",
                extra={
                    "parts_received": len(context_parts),
                    "parts_included": len(selected_parts),
                    "parts_excluded": len(excluded_parts),
                    "doc_parts_excluded": doc_parts_excluded,
                    "total_tokens_used": total_tokens,
                    "max_tokens": max_tokens,
                    "budget_utilization_pct": round(total_tokens / max_tokens * 100, 1) if max_tokens > 0 else 0,
                    "content_truncated": content_truncated,
                    "budget_exceeded": budget_exceeded,
                },
            )

        return selected_parts, content_truncated, budget_exceeded

    def _generate_merged_context_text(self, context_parts: list[ContextPart], query: str) -> str:
        """Generate final merged context text with document type labels and source links.

        NOW GROUPS CHUNKS BY DOCUMENT: Multiple chunks from the same document are
        combined under a single document header, improving readability and token efficiency.
        """
        if not context_parts:
            return "No specific context available for this query."

        # Group parts by type
        facts_parts = [p for p in context_parts if p.type == "facts"]
        kb_parts = [p for p in context_parts if p.type == "kb_docs"]
        doc_parts = [p for p in context_parts if p.type == "document_facts"]

        sections = []

        # Facts section
        if facts_parts:
            facts_text = " ".join([p.content for p in facts_parts])
            sections.append(facts_text)

        # KB docs section - NOW GROUPS CHUNKS BY DOCUMENT
        if kb_parts:
            # Group chunks by document title (since chunks from same doc share same title)
            # DEV-242 Phase 54: Track ALL source_urls to avoid losing links during grouping
            docs_by_title = {}
            for part in kb_parts:
                doc_title = part.metadata.get("title", "Untitled")
                if doc_title not in docs_by_title:
                    docs_by_title[doc_title] = {
                        "chunks": [],
                        "metadata": part.metadata,
                        "source_urls": set(),  # Track ALL unique source URLs from all chunks
                    }
                docs_by_title[doc_title]["chunks"].append(part)
                # Collect source_url from EVERY chunk (DEV-242 Phase 54 fix)
                chunk_url = part.metadata.get("source_url")
                if chunk_url:
                    docs_by_title[doc_title]["source_urls"].add(chunk_url)

            kb_items = []
            for doc_title, doc_data in docs_by_title.items():
                chunks = doc_data["chunks"]
                metadata = doc_data["metadata"]

                # Sort chunks by chunk_index to maintain document flow
                chunks.sort(key=lambda c: c.metadata.get("chunk_index", 0))

                # Extract metadata
                document_source = metadata.get("document_source", "")
                # Note: source_url now comes from doc_data["source_urls"] set (DEV-242 Phase 54)

                # Determine document type label
                if document_source and "news" in document_source.lower():
                    doc_type_label = "[NEWS - AGENZIAENTRATE]"
                elif document_source and "normativa" in document_source.lower():
                    doc_type_label = "[NORMATIVA/PRASSI - AGENZIAENTRATE]"
                elif document_source and "inps" in document_source.lower():
                    doc_type_label = "[CIRCOLARI - INPS]"
                elif document_source and "gazzetta" in document_source.lower():
                    doc_type_label = "[GAZZETTA UFFICIALE]"
                elif document_source and "governo" in document_source.lower():
                    doc_type_label = "[DECRETI LEGGE]"
                else:
                    doc_type_label = f"[{document_source.upper()}]" if document_source else "[KNOWLEDGE BASE]"

                # Get publication date from database metadata (more reliable than content parsing)
                publication_date_obj = metadata.get("publication_date")
                publication_date = None
                if publication_date_obj:
                    # Format date for Italian display: "30 ottobre 2025"
                    try:
                        from datetime import (
                            date,
                            datetime,
                        )

                        # Handle ISO string format (from cache/JSON serialization)
                        if isinstance(publication_date_obj, str):
                            try:
                                # Try parsing ISO date string: "2025-10-30"
                                publication_date_obj = datetime.fromisoformat(publication_date_obj).date()
                            except Exception:
                                # Already formatted string like "30 ottobre 2025"
                                publication_date = publication_date_obj

                        # Format date object to Italian
                        if hasattr(publication_date_obj, "strftime") and publication_date is None:
                            # It's a date object
                            day = publication_date_obj.strftime("%d").lstrip("0")
                            year = publication_date_obj.strftime("%Y")
                            month_map = {
                                1: "gennaio",
                                2: "febbraio",
                                3: "marzo",
                                4: "aprile",
                                5: "maggio",
                                6: "giugno",
                                7: "luglio",
                                8: "agosto",
                                9: "settembre",
                                10: "ottobre",
                                11: "novembre",
                                12: "dicembre",
                            }
                            month_name = month_map.get(publication_date_obj.month, "")
                            if month_name:
                                publication_date = f"{day} {month_name} {year}"
                    except Exception:
                        # Fallback to content extraction if date formatting fails
                        first_chunk_content = chunks[0].content
                        publication_date = extract_publication_date(first_chunk_content, doc_title)

                # Build document section with header
                kb_item = f"{doc_type_label}\n"
                kb_item += f"**{doc_title}**\n"

                # Add publication date prominently if found
                if publication_date:
                    kb_item += f"Publication Date: {publication_date}\n"

                # Concatenate all chunk texts, removing redundant title prefixes
                chunk_texts = []
                for chunk in chunks:
                    # Remove "Title: " prefix added by context builder (line 304)
                    chunk_content = chunk.content
                    if chunk_content.startswith(f"{doc_title}: "):
                        chunk_content = chunk_content[len(doc_title) + 2 :]
                    chunk_texts.append(chunk_content)

                kb_item += "\n".join(chunk_texts)

                # DEV-242 Phase 54: Add ALL source URLs collected from chunks
                source_urls = doc_data.get("source_urls", set())
                if source_urls:
                    for url in sorted(source_urls):  # Sorted for consistency
                        kb_item += f"\nSource URL: {url}"

                kb_items.append(kb_item)

            kb_text = "\n\nRelevant documents from knowledge base:\n\n" + "\n\n---\n\n".join(kb_items)
            sections.append(kb_text)

            # Diagnostic logging for KB context quality
            total_chunks = len(kb_parts)
            logger.info(
                "kb_context_built",
                num_documents=len(docs_by_title),
                num_chunks=total_chunks,
                total_chars=len(kb_text),
                has_dates=any("Publication Date:" in item for item in kb_items),
                has_links=any("Source URL:" in item for item in kb_items),
                first_doc_preview=kb_items[0][:200] if kb_items else None,
                message=f"Built KB context with {len(docs_by_title)} document(s) from {total_chunks} chunks, {len(kb_text)} chars",
            )

        # Document facts section
        # DEV-007 FIX: Use clear document separators (---) instead of spaces
        # This ensures the LLM can clearly distinguish between multiple uploaded documents
        if doc_parts:
            # DEV-007 DIAGNOSTIC: Log document part order before joining
            import re

            doc_part_order = []
            current_uploads = []
            prior_context = []

            for i, p in enumerate(doc_parts):
                # Extract marker and filename from content
                match = re.search(
                    r"\[(DOCUMENTI ALLEGATI ORA|CONTESTO PRECEDENTE)\] \[Documento: ([^\]]+)\]", p.content
                )
                if match:
                    marker, filename = match.groups()
                    doc_part_order.append({"index": i, "marker": marker, "filename": filename})
                    if marker == "DOCUMENTI ALLEGATI ORA":
                        current_uploads.append(filename)
                    else:
                        prior_context.append(filename)

            logger.info(
                "doc_parts_order_before_joining",
                doc_parts_count=len(doc_parts),
                doc_part_order=doc_part_order,
                current_uploads=current_uploads,
                prior_context=prior_context,
                first_part_preview=doc_parts[0].content[:200] if doc_parts else None,
            )

            # DEV-007 FIX: Add VERY PROMINENT header listing current uploads
            # This helps the LLM understand which documents to analyze
            doc_header_parts = ["From your documents:"]

            if current_uploads:
                upload_count = len(current_uploads)
                upload_list = ", ".join(current_uploads)
                doc_header_parts.append(
                    f"\n\n**>>> NUOVI DOCUMENTI APPENA CARICATI ({upload_count}): {upload_list} <<<**"
                )
                doc_header_parts.append(
                    "**ANALIZZA QUESTI DOCUMENTI - sono quelli che l'utente vuole analizzare ORA.**"
                )

            if prior_context:
                doc_header_parts.append(f"\n(Documenti dal contesto precedente: {len(prior_context)})")

            doc_header = "\n".join(doc_header_parts)
            doc_text = "\n\n" + doc_header + "\n\n" + "\n\n---\n\n".join([p.content for p in doc_parts])
            sections.append(doc_text)

        return "\n".join(sections).strip()

    def _calculate_source_distribution(self, context_parts: list[ContextPart]) -> dict[str, int]:
        """Calculate distribution of content by source type."""
        distribution = {"facts": 0, "kb_docs": 0, "document_facts": 0}

        for part in context_parts:
            if part.type in distribution:
                distribution[part.type] += 1

        return distribution

    def _calculate_context_quality(
        self, context_parts: list[ContextPart], query: str, total_tokens: int, max_tokens: int
    ) -> float:
        """Calculate context quality score based on various factors."""
        if not context_parts:
            return 0.0

        # Base quality from priority scores
        avg_priority = sum(p.priority_score for p in context_parts) / len(context_parts)

        # Diversity bonus (having multiple types)
        types_present = len({p.type for p in context_parts})
        diversity_bonus = min(types_present * 0.1, 0.2)

        # Token utilization efficiency
        utilization = total_tokens / max_tokens if max_tokens > 0 else 0
        utilization_score = min(utilization * 0.15, 0.15)

        # Content relevance (simple keyword matching)
        query_keywords = set(query.lower().split())
        relevance_scores = []

        for part in context_parts:
            content_words = set(part.content.lower().split())
            overlap = len(query_keywords.intersection(content_words))
            relevance = overlap / len(query_keywords) if query_keywords else 0
            relevance_scores.append(relevance)

        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        relevance_bonus = avg_relevance * 0.25

        # Final quality score (0.0 to 1.0)
        quality = min(avg_priority + diversity_bonus + utilization_score + relevance_bonus, 1.0)

        return round(quality, 2)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)."""
        if not text:
            return 0

        # Simple estimation: ~4 characters per token on average
        char_count = len(text)
        token_estimate = max(1, char_count // 4)

        return token_estimate

    def _calculate_recency_boost(self, updated_at: datetime | None) -> float:
        """Calculate recency boost for content."""
        if not updated_at:
            return 0.0

        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=UTC)

        now = datetime.now(UTC)
        age_days = (now - updated_at).total_seconds() / 86400

        # Exponential decay: newer content gets higher boost
        if age_days <= 7:
            return 1.0  # Very recent
        elif age_days <= 30:
            return 0.7  # Recent
        elif age_days <= 90:
            return 0.4  # Somewhat recent
        else:
            return 0.1  # Old

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two pieces of content."""
        if not content1 or not content2:
            return 0.0

        # Simple word-based similarity
        words1 = set(re.findall(r"\w+", content1.lower()))
        words2 = set(re.findall(r"\w+", content2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = words1.intersection(words2)
        union = words1.union(words2)

        similarity = len(intersection) / len(union) if union else 0.0
        return similarity

    def _truncate_content(self, content: str, max_tokens: int) -> str:
        """Truncate content to fit within token budget."""
        if not content:
            return ""

        # Rough truncation based on character count
        max_chars = max_tokens * 4  # ~4 chars per token

        if len(content) <= max_chars:
            return content

        # Try to truncate at sentence boundaries
        sentences = re.split(r"[.!?]+", content[:max_chars])
        if len(sentences) > 1:
            # Keep all but the last (potentially incomplete) sentence
            truncated = ". ".join(sentences[:-1]) + "."
            if len(truncated) > 10:  # Ensure meaningful content
                return truncated + "..."

        # Fallback to character truncation
        return content[: max_chars - 3] + "..."

    def _context_parts_to_dict(self, context_parts: list[ContextPart]) -> list[dict[str, Any]]:
        """Convert ContextPart objects to dictionaries."""
        return [
            {
                "type": part.type,
                "content": part.content,
                "tokens": part.tokens,
                "priority_score": part.priority_score,
                **part.metadata,
            }
            for part in context_parts
        ]

    def _create_empty_context_result(
        self, trace_id: str | None, user_id: str | None, session_id: str | None
    ) -> dict[str, Any]:
        """Create result for empty input scenario."""
        rag_step_log(
            step=self.STEP_NUM,
            step_id=self.STEP_ID,
            node_label=self.NODE_LABEL,
            trace_id=trace_id,
            user_id=user_id,
            session_id=session_id,
            token_count=8,
            source_distribution={"facts": 0, "kb_docs": 0, "document_facts": 0},
            context_quality_score=0.0,
            processing_stage="empty_inputs",
        )

        return {
            "merged_context": "No specific context available for this query.",
            "context_parts": [],
            "token_count": 8,
            "source_distribution": {"facts": 0, "kb_docs": 0, "document_facts": 0},
            "context_quality_score": 0.0,
            "deduplication_applied": False,
            "content_truncated": False,
            "budget_exceeded": False,
        }

    def _convert_to_dict(self, result: MergedContext) -> dict[str, Any]:
        """Convert MergedContext to dictionary."""
        return {
            "merged_context": result.merged_context,
            "context_parts": result.context_parts,
            "token_count": result.token_count,
            "source_distribution": result.source_distribution,
            "context_quality_score": result.context_quality_score,
            "deduplication_applied": result.deduplication_applied,
            "content_truncated": result.content_truncated,
            "budget_exceeded": result.budget_exceeded,
        }


# Convenience function for direct usage
def merge_context(context_data: dict[str, Any]) -> dict[str, Any]:
    """Convenience function to merge context from facts, KB docs, and document facts.

    Args:
        context_data: Context data dictionary

    Returns:
        Dict with merged context result
    """
    service = ContextBuilderMerge()
    return service.merge_context(context_data)
