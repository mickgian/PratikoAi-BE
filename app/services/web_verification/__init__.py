"""Web Verification Service module.

This module provides web search verification for KB answers,
detecting contradictions and adding caveats when needed.

All public API is re-exported here for backward compatibility.
"""

from .constants import (
    CONTRADICTION_KEYWORDS,
    EXCLUSION_KEYWORDS,
    MIN_CAVEAT_CONFIDENCE,
    SENSITIVE_TOPICS,
)
from .exclusion_detector import _web_has_genuine_exclusions
from .service import WebVerificationService, web_verification_service
from .types import ContradictionInfo, WebVerificationResult

__all__ = [
    # Types
    "ContradictionInfo",
    "WebVerificationResult",
    # Service
    "WebVerificationService",
    "web_verification_service",
    # Functions
    "_web_has_genuine_exclusions",
    # Constants
    "EXCLUSION_KEYWORDS",
    "CONTRADICTION_KEYWORDS",
    "SENSITIVE_TOPICS",
    "MIN_CAVEAT_CONFIDENCE",
]
