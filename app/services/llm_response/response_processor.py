"""Response processing for LLM outputs.

Handles unified JSON parsing, fallback processing, and disclaimer filtering.
"""

from typing import Any

from app.core.logging import logger
from app.services.reasoning_trace_logger import log_reasoning_trace_failed

from .bold_section_formatter import BoldSectionFormatter
from .json_parser import parse_unified_response
from .section_numbering_fixer import SectionNumberingFixer
from .source_hierarchy import apply_source_hierarchy

# Type alias for RAG state dict
RAGStateDict = dict[str, Any]


def fallback_to_text(content: str, state: RAGStateDict) -> dict:
    """Fallback parsing when JSON extraction fails.

    DEV-214: Returns minimal valid response with answer only.

    Args:
        content: LLM response content
        state: Current RAG state (for logging context)

    Returns:
        Dict with answer and empty optional fields
    """
    logger.info(
        "step64_fallback_to_text",
        content_length=len(content) if content else 0,
        request_id=state.get("request_id"),
    )

    return {
        "reasoning": None,
        "answer": content or "",
        "sources_cited": [],
    }


def process_unified_response(content: str, state: RAGStateDict) -> str:
    """Process LLM response with unified JSON parsing.

    DEV-214: Extracts and stores reasoning and sources from JSON response.
    Falls back to text extraction if JSON parsing fails.

    DEV-226: Preserves ToT reasoning_type if already set (from TreeOfThoughtsReasoner).

    Args:
        content: LLM response content
        state: RAG state to update with parsed fields

    Returns:
        The answer text to use for display (from JSON or raw content)
    """
    # Try unified JSON parsing
    parsed = parse_unified_response(content)

    if parsed:
        # DEV-226: Preserve ToT reasoning if already set, otherwise use CoT
        if state.get("reasoning_type") != "tot":
            state["reasoning_type"] = "cot"
            state["reasoning_trace"] = parsed.get("reasoning")
        # If ToT, reasoning_trace is already set by _use_tree_of_thoughts

        # Store and validate sources with hierarchy
        sources = parsed.get("sources_cited", [])
        state["sources_cited"] = apply_source_hierarchy(sources)

        # Use answer for display
        answer = parsed.get("answer", content)

        # DEV-245 Phase 5.1: Filter out unauthorized disclaimers
        # LLM sometimes ignores prompt instructions and includes "consulta un esperto"
        # This is a safety net to catch those cases and remove them
        from app.services.disclaimer_filter import DisclaimerFilter

        answer, removed_disclaimers = DisclaimerFilter.filter_response(answer)
        if removed_disclaimers:
            logger.info(
                "step64_disclaimers_filtered",
                removed_count=len(removed_disclaimers),
                request_id=state.get("request_id"),
            )

        # DEV-251: Apply formatting post-processors
        # 1. Fix section numbering (1. 1. 1. → 1. 2. 3.)
        answer = SectionNumberingFixer.fix_numbering(answer)
        # 2. Add bold to plain sections (1. Title → 1. **Title**:)
        answer = BoldSectionFormatter.format_sections(answer)

        logger.info(
            "step64_unified_response_parsed",
            has_reasoning=parsed.get("reasoning") is not None,
            sources_count=len(sources),
            request_id=state.get("request_id"),
        )

        return answer
    else:
        # Fallback: JSON parsing failed
        # DEV-226: Preserve ToT reasoning_type if already set
        if state.get("reasoning_type") != "tot":
            state["reasoning_type"] = None
            state["reasoning_trace"] = None
        state["sources_cited"] = []

        logger.warning(
            "step64_json_parse_failed",
            content_length=len(content) if content else 0,
            content_preview=content[:200] if content else "",
            request_id=state.get("request_id"),
        )

        # DEV-238: Log reasoning trace parse failure with mandatory context
        log_reasoning_trace_failed(
            state=state,
            error_type="JSONParseError",
            error_message="Failed to extract unified JSON response",
            content_sample=content[:500] if content else "",
        )

        # DEV-245 Phase 5.1: Filter out unauthorized disclaimers (fallback branch)
        from app.services.disclaimer_filter import DisclaimerFilter

        filtered_content, removed_disclaimers = DisclaimerFilter.filter_response(content)
        if removed_disclaimers:
            logger.info(
                "step64_disclaimers_filtered_fallback",
                removed_count=len(removed_disclaimers),
                request_id=state.get("request_id"),
            )

        # DEV-251: Apply formatting post-processors (fallback branch)
        # 1. Fix section numbering (1. 1. 1. → 1. 2. 3.)
        filtered_content = SectionNumberingFixer.fix_numbering(filtered_content) or ""
        # 2. Add bold to plain sections (1. Title → 1. **Title**:)
        filtered_content = BoldSectionFormatter.format_sections(filtered_content) or ""

        return filtered_content
