"""Prompt injection detection for security hardening.

This module provides functions to detect potential prompt injection attacks
in user input. It is designed for MONITORING mode - it detects and logs
suspicious patterns but does NOT block requests.

Security vulnerabilities addressed:
- V-003: Prompt injection in chat flow
- Detects instruction override attempts
- Detects role hijacking attempts
- Detects system prompt extraction attempts
- Detects jailbreak keywords

IMPORTANT: This module is in monitoring phase. It logs detected patterns
at WARNING level but allows requests to proceed. This approach:
1. Prevents false positives from blocking legitimate users
2. Allows us to tune patterns based on real-world data
3. Provides audit trail for security analysis
"""

import re
import unicodedata
from typing import NamedTuple

# Cached compiled patterns for performance
_COMPILED_PATTERNS: list[tuple[re.Pattern, str]] | None = None


class PromptInjectionResult(NamedTuple):
    """Result of prompt injection detection.

    Attributes:
        detected: True if a potential injection pattern was found.
        pattern: The pattern that matched, or None if not detected.
    """

    detected: bool
    pattern: str | None


def get_injection_patterns() -> list[str]:
    """Get list of prompt injection detection patterns.

    These patterns are designed to detect common prompt injection
    techniques while minimizing false positives on Italian legal/tax
    queries.

    Returns:
        List of regex patterns (strings) for injection detection.
    """
    return [
        # Instruction override patterns (English)
        r"\bignore\s+(all\s+)?previous\s+instructions?\b",
        r"\bforget\s+(all\s+)?previous\s+instructions?\b",
        r"\bdisregard\s+(all\s+)?previous\s+instructions?\b",
        r"\boverride\s+(all\s+)?previous\s+instructions?\b",
        r"\bforget\s+everything\b",
        r"\bstart\s+(over|fresh|anew)\b",
        # Role hijacking patterns
        r"\byou\s+are\s+now\b",
        r"\bfrom\s+now\s+on[,\s]+act\s+as\b",
        r"\bact\s+as\s+(an?\s+)?(evil|unrestricted|unfiltered)\b",
        r"\bpretend\s+(you\s+are|to\s+be)\b",
        r"\bimpersonate\b",
        r"\broleplay\s+as\b",
        # System prompt extraction
        r"\bwhat\s+is\s+your\s+system\s+prompt\b",
        r"\bshow\s+(me\s+)?your\s+(system\s+)?prompt\b",
        r"\breveal\s+(your\s+)?(initial\s+)?instructions?\b",
        r"\brepeat\s+(your\s+)?instructions?\s+verbatim\b",
        r"\bprint\s+(your\s+)?(system\s+)?prompt\b",
        r"\boutput\s+(your\s+)?(system\s+)?prompt\b",
        # Jailbreak keywords
        r"\bjailbreak\b",
        r"\benable\s+jailbreak\b",
        r"\bbypass\s+(all\s+)?filters?\b",
        r"\bdeveloper\s+mode\b",
        r"\bdebug\s+mode\b",
        r"\bsudo\s+mode\b",
        r"\badmin\s+mode\b",
        # DAN and similar jailbreaks
        r"\bdan\s+mode\b",
        r"\bdo\s+anything\s+now\b",
        # Safety bypass attempts
        r"\bignore\s+(all\s+)?safety\b",
        r"\bdisable\s+(all\s+)?restrictions?\b",
        r"\bremove\s+(all\s+)?limitations?\b",
        r"\bno\s+(ethical\s+)?guidelines?\b",
        r"\bwithout\s+(any\s+)?(ethical\s+)?constraints?\b",
    ]


def _get_compiled_patterns() -> list[tuple[re.Pattern, str]]:
    """Get compiled regex patterns (cached for performance).

    Returns:
        List of tuples: (compiled_pattern, pattern_name)
    """
    global _COMPILED_PATTERNS
    if _COMPILED_PATTERNS is None:
        patterns = get_injection_patterns()
        _COMPILED_PATTERNS = [(re.compile(pattern, re.IGNORECASE | re.MULTILINE), pattern) for pattern in patterns]
    return _COMPILED_PATTERNS


def normalize_text_for_detection(text: str) -> str:
    """Normalize text for prompt injection detection.

    This function prepares text for pattern matching by:
    1. Converting to lowercase
    2. Normalizing Unicode (NFKC form)
    3. Normalizing whitespace
    4. Removing zero-width characters

    Args:
        text: The text to normalize.

    Returns:
        Normalized text ready for pattern matching.
    """
    if not text:
        return ""

    # Unicode normalization (NFKC decomposes and recomposes)
    # This helps with look-alike characters (e.g., Cyrillic 'o' vs Latin 'o')
    normalized = unicodedata.normalize("NFKC", text)

    # Lowercase for case-insensitive matching
    normalized = normalized.lower()

    # Remove zero-width characters that could be used for obfuscation
    zero_width = "\u200b\u200c\u200d\ufeff"
    for char in zero_width:
        normalized = normalized.replace(char, "")

    # Normalize whitespace (multiple spaces/newlines to single space)
    normalized = re.sub(r"\s+", " ", normalized)

    return normalized.strip()


def detect_prompt_injection(text: str) -> PromptInjectionResult:
    """Detect potential prompt injection in text.

    This function checks the input text against known prompt injection
    patterns. It is designed for MONITORING mode - it detects and returns
    information about suspicious patterns but does NOT modify the input.

    The function is optimized for performance:
    - Uses pre-compiled regex patterns (cached)
    - Returns early on first match
    - Normalizes text once before all checks

    Args:
        text: The text to check for prompt injection.

    Returns:
        PromptInjectionResult with:
        - detected: True if a potential injection was found
        - pattern: The pattern that matched (for logging), or None

    Examples:
        >>> result = detect_prompt_injection("ignore previous instructions")
        >>> result.detected
        True
        >>> result.pattern is not None
        True

        >>> result = detect_prompt_injection("Come calcolo l'IVA?")
        >>> result.detected
        False
        >>> result.pattern is None
        True
    """
    # Handle empty/whitespace input
    if not text or not text.strip():
        return PromptInjectionResult(detected=False, pattern=None)

    # Normalize text for detection
    normalized = normalize_text_for_detection(text)

    # Check against all patterns
    compiled_patterns = _get_compiled_patterns()

    for pattern, pattern_str in compiled_patterns:
        if pattern.search(normalized):
            return PromptInjectionResult(detected=True, pattern=pattern_str)

    return PromptInjectionResult(detected=False, pattern=None)


def log_injection_attempt(
    text: str,
    pattern: str,
    user_id: int | None = None,
    request_id: str | None = None,
) -> None:
    """Log a detected prompt injection attempt.

    This function is called when a prompt injection pattern is detected.
    It logs the event at WARNING level with relevant context for
    security analysis.

    Args:
        text: The original text (will be truncated for logging).
        pattern: The pattern that matched.
        user_id: Optional user ID for attribution.
        request_id: Optional request ID for correlation.
    """
    # Import here to avoid circular dependencies
    from app.core.logging import logger

    # Truncate text for logging (don't log full potentially malicious content)
    truncated_text = text[:200] + "..." if len(text) > 200 else text

    # Hash the full text for correlation without exposing full content
    import hashlib

    text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

    logger.warning(
        "prompt_injection_detected",
        pattern_matched=pattern,
        text_preview=truncated_text,
        text_hash=text_hash,
        text_length=len(text),
        user_id=user_id,
        request_id=request_id,
    )
