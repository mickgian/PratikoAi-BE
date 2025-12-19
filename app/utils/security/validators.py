"""Input validation utilities for security hardening.

This module provides functions for:
- Field length validation with Italian error messages
- XSS sanitization for data exports
- Log message escaping to prevent log injection

Security vulnerabilities addressed:
- V-002: Missing field-level length limits
- V-004: XSS in data exports
- V-005: Log injection
"""

import re
from typing import Any

# Precompiled patterns for XSS sanitization
_SCRIPT_TAG_PATTERN = re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL)
_SCRIPT_OPEN_TAG_PATTERN = re.compile(r"<script[^>]*>", re.IGNORECASE)
_SCRIPT_CLOSE_TAG_PATTERN = re.compile(r"</script>", re.IGNORECASE)
_EVENT_HANDLER_PATTERN = re.compile(r'\s*on\w+\s*=\s*["\']?[^"\'>\s]*["\']?', re.IGNORECASE)
_JAVASCRIPT_URL_PATTERN = re.compile(r"javascript\s*:", re.IGNORECASE)
_DATA_URL_SCRIPT_PATTERN = re.compile(r"data\s*:[^,]*,\s*<script", re.IGNORECASE)

# Control characters to remove from logs (except common whitespace)
_CONTROL_CHAR_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# ANSI escape codes pattern
_ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")


def validate_field_length(
    text: str,
    max_length: int,
    field_name: str,
) -> str:
    """Validate that text does not exceed maximum length.

    This function enforces field-level length limits to prevent
    denial of service attacks and ensure database field compatibility.

    Args:
        text: The text to validate.
        max_length: Maximum allowed length (character count).
        field_name: Name of the field (for error messages).

    Returns:
        str: The original text if valid.

    Raises:
        ValueError: If text exceeds max_length, with Italian error message.

    Examples:
        >>> validate_field_length("short", 100, "test")
        'short'
        >>> validate_field_length("x" * 101, 100, "test")
        ValueError: Campo 'test' troppo lungo: massimo 100 caratteri
    """
    if len(text) > max_length:
        raise ValueError(f"Campo '{field_name}' troppo lungo: massimo {max_length} caratteri")
    return text


def sanitize_for_export(data: dict[str, Any]) -> dict[str, Any]:
    """Sanitize dictionary data for safe export.

    This function removes XSS-vulnerable content from data that will
    be exported to JSON/CSV files. It recursively processes nested
    dictionaries and lists.

    Sanitization includes:
    - Removing script tags
    - Removing event handlers (onclick, onerror, etc.)
    - Removing javascript: URLs
    - Removing dangerous data: URLs

    Args:
        data: Dictionary data to sanitize.

    Returns:
        dict: Sanitized copy of the data.

    Examples:
        >>> sanitize_for_export({"content": "<script>alert(1)</script>text"})
        {'content': 'text'}
    """
    return _sanitize_value(data)


def _sanitize_value(value: Any) -> Any:
    """Recursively sanitize a value.

    Args:
        value: Value to sanitize (can be dict, list, str, or other).

    Returns:
        Sanitized value.
    """
    if value is None:
        return None

    if isinstance(value, dict):
        return {k: _sanitize_value(v) for k, v in value.items()}

    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]

    if isinstance(value, str):
        return _sanitize_string(value)

    # Preserve other types (int, float, bool, etc.)
    return value


def _sanitize_string(text: str) -> str:
    """Sanitize a string by removing XSS-vulnerable content.

    Args:
        text: String to sanitize.

    Returns:
        Sanitized string.
    """
    if not text:
        return text

    result = text

    # Remove complete script tags and their content
    result = _SCRIPT_TAG_PATTERN.sub("", result)

    # Remove orphan script open tags (e.g., just "<script>")
    result = _SCRIPT_OPEN_TAG_PATTERN.sub("", result)

    # Remove orphan script close tags
    result = _SCRIPT_CLOSE_TAG_PATTERN.sub("", result)

    # Remove event handlers (onclick, onerror, onload, etc.)
    result = _EVENT_HANDLER_PATTERN.sub("", result)

    # Remove javascript: URLs
    result = _JAVASCRIPT_URL_PATTERN.sub("", result)

    # Remove dangerous data: URLs
    result = _DATA_URL_SCRIPT_PATTERN.sub("", result)

    # Clean up any resulting double spaces
    result = re.sub(r" {2,}", " ", result)

    return result.strip() if result != text else result


def escape_log_message(text: str) -> str:
    r"""Escape text for safe inclusion in log messages.

    This function prevents log injection attacks by:
    - Escaping newlines (prevents fake log entries)
    - Escaping carriage returns
    - Escaping tabs
    - Removing null bytes and control characters
    - Removing ANSI escape codes

    Args:
        text: Text to escape for logging.

    Returns:
        str: Escaped text safe for log output.

    Examples:
        >>> escape_log_message("Line 1\nLine 2")
        'Line 1\\nLine 2'
        >>> escape_log_message("Before\x00After")
        'BeforeAfter'
    """
    if not text:
        return ""

    result = text

    # Remove ANSI escape codes (could be used to hide log content)
    result = _ANSI_ESCAPE_PATTERN.sub("", result)

    # Remove control characters (except common ones we'll escape)
    result = _CONTROL_CHAR_PATTERN.sub("", result)

    # Escape newlines to prevent log injection
    result = result.replace("\n", "\\n")
    result = result.replace("\r", "\\r")

    # Escape tabs for consistent log formatting
    result = result.replace("\t", "\\t")

    return result


# Field length limits as defined in ARCHITECTURE_ROADMAP.md
FIELD_LENGTH_LIMITS = {
    "query_text": 2000,
    "original_answer": 5000,
    "additional_details": 2000,
    "expert_answer": 5000,
    "improvement_suggestions": 500,  # Per suggestion
    "regulatory_references": 500,  # Per reference
}


def get_field_max_length(field_name: str) -> int:
    """Get the maximum length for a field.

    Args:
        field_name: Name of the field.

    Returns:
        int: Maximum allowed length, or 1000 as default.
    """
    return FIELD_LENGTH_LIMITS.get(field_name, 1000)
