"""Context Builder Service module.

This module provides utilities for building context from KB documents,
including hierarchy utilities, title simplification, topic extraction,
paragraph utilities, keyword extraction, web source filtering, and
KB metadata building.

All public API is re-exported here for backward compatibility.
"""

from .constants import (
    CATEGORY_LABELS_IT,
    HIERARCHY_WEIGHTS,
    MAX_KB_DOCUMENTS,
    MIN_FONTI_RELEVANCE_SCORE,
)
from .doc_classifier import (
    build_web_metadata_entry,
    is_web_document,
    separate_kb_and_web_docs,
)
from .hierarchy_utils import get_category_label_it, get_hierarchy_weight
from .kb_metadata_builder import build_kb_sources_metadata
from .keyword_extractor import extract_filter_keywords_from_query
from .paragraph_utils import extract_paragraph_excerpt, generate_paragraph_id
from .title_simplifier import simplify_title
from .topic_extractor import extract_topics, extract_values
from .web_source_filter import is_web_source_topic_relevant

__all__ = [
    # Constants
    "HIERARCHY_WEIGHTS",
    "CATEGORY_LABELS_IT",
    "MAX_KB_DOCUMENTS",
    "MIN_FONTI_RELEVANCE_SCORE",
    # Doc classification
    "is_web_document",
    "separate_kb_and_web_docs",
    "build_web_metadata_entry",
    # Hierarchy utilities
    "get_hierarchy_weight",
    "get_category_label_it",
    # Title simplification
    "simplify_title",
    # Topic extraction
    "extract_topics",
    "extract_values",
    # Paragraph utilities
    "generate_paragraph_id",
    "extract_paragraph_excerpt",
    # Keyword extraction
    "extract_filter_keywords_from_query",
    # Web source filtering
    "is_web_source_topic_relevant",
    # KB metadata building
    "build_kb_sources_metadata",
]
