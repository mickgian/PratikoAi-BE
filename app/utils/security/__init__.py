"""Security utilities for input sanitization and validation.

This module provides comprehensive security hardening for user inputs:
- Markdown escaping for safe file generation
- Prompt injection detection for chat inputs
- Field length validation with Italian error messages
- XSS sanitization for data exports
- Log message escaping for injection prevention

Security vulnerabilities addressed:
- V-001: Markdown injection in task generation
- V-002: Missing field-level length limits
- V-003: Prompt injection in chat flow
- V-004: XSS in data exports
- V-005: Log injection
- V-006: Unvalidated improvement suggestions

Usage:
    from app.utils.security import (
        escape_markdown,
        sanitize_for_markdown_file,
        detect_prompt_injection,
        validate_field_length,
        sanitize_for_export,
        escape_log_message,
    )
"""

from app.utils.security.markdown_escaper import (
    escape_for_markdown_table_cell,
    escape_markdown,
    escape_markdown_code_block,
    sanitize_for_markdown_file,
)
from app.utils.security.prompt_guard import (
    PromptInjectionResult,
    detect_prompt_injection,
    get_injection_patterns,
    log_injection_attempt,
    normalize_text_for_detection,
)
from app.utils.security.validators import (
    FIELD_LENGTH_LIMITS,
    escape_log_message,
    get_field_max_length,
    sanitize_for_export,
    validate_field_length,
)

__all__ = [
    # Markdown escaping
    "escape_markdown",
    "escape_markdown_code_block",
    "sanitize_for_markdown_file",
    "escape_for_markdown_table_cell",
    # Prompt injection detection
    "detect_prompt_injection",
    "PromptInjectionResult",
    "get_injection_patterns",
    "normalize_text_for_detection",
    "log_injection_attempt",
    # Field validation
    "validate_field_length",
    "get_field_max_length",
    "FIELD_LENGTH_LIMITS",
    # Export sanitization
    "sanitize_for_export",
    # Log escaping
    "escape_log_message",
]
