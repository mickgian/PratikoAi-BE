"""Topic Extraction Service module.

This module provides utilities for extracting topic keywords from queries
and building routing decision results.

All public API is re-exported here for backward compatibility.
"""

from .result_builders import create_fallback_decision, decision_to_dict
from .topic_extractor import extract_topic_keywords

__all__ = [
    # Topic extraction
    "extract_topic_keywords",
    # Result builders
    "decision_to_dict",
    "create_fallback_decision",
]
