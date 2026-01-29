"""Query Reformulation Service module.

This module provides utilities for reformulating and expanding user queries,
including short query expansion using LLM and result builders for query variants.

All public API is re-exported here for backward compatibility.
"""

from .constants import SHORT_QUERY_THRESHOLD, SKIP_EXPANSION_ROUTES
from .llm_reformulator import reformulate_short_query_llm
from .result_builders import (
    create_fallback_result,
    create_skip_result,
    variants_to_dict,
)

__all__ = [
    # Constants
    "SHORT_QUERY_THRESHOLD",
    "SKIP_EXPANSION_ROUTES",
    # LLM reformulation
    "reformulate_short_query_llm",
    # Result builders
    "variants_to_dict",
    "create_skip_result",
    "create_fallback_result",
]
