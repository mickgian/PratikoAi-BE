"""LLM Response Processing Service module.

This module provides utilities for processing LLM responses,
including JSON extraction, source hierarchy ranking, PII restoration,
KB empty detection, citation validation, and query complexity classification.

All public API is re-exported here for backward compatibility.
"""

from .citation_validator import (
    validate_citations_in_response,
)
from .complexity_classifier import (
    classify_query_complexity,
    extract_user_message,
    get_llm_orchestrator,
)
from .constants import SOURCE_HIERARCHY
from .json_parser import (
    extract_json_from_content,
    extract_xml_response,
    parse_unified_response,
)
from .kb_empty_detector import (
    check_kb_empty_and_inject_warning,
)
from .pii_restorer import deanonymize_response
from .response_processor import (
    fallback_to_text,
    process_unified_response,
)
from .source_hierarchy import apply_source_hierarchy
from .tot_orchestrator import (
    get_tot_reasoner,
    use_tree_of_thoughts,
)
from .types import ParsedResponse

__all__ = [
    # Types
    "ParsedResponse",
    # Constants
    "SOURCE_HIERARCHY",
    # JSON/XML parsing
    "extract_json_from_content",
    "extract_xml_response",
    "parse_unified_response",
    # Source hierarchy
    "apply_source_hierarchy",
    # PII restoration
    "deanonymize_response",
    # KB empty detection
    "check_kb_empty_and_inject_warning",
    # Response processing
    "fallback_to_text",
    "process_unified_response",
    # Citation validation
    "validate_citations_in_response",
    # Complexity classification
    "classify_query_complexity",
    "extract_user_message",
    "get_llm_orchestrator",
    # ToT orchestration
    "get_tot_reasoner",
    "use_tree_of_thoughts",
]
