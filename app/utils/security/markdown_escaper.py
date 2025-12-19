"""Markdown escaping utilities for security hardening.

This module provides functions to escape markdown special characters
to prevent markdown injection attacks when writing user-provided content
to markdown files (e.g., task files, reports).

Security vulnerabilities addressed:
- V-001: Markdown injection in task generation
- Prevents heading injection (# characters)
- Prevents link/image injection ([text](url))
- Prevents code injection (backticks)
- Prevents formatting injection (bold, italic)
- Prevents table injection (pipes)
- Prevents HTML injection (angle brackets)
"""

import re

# Markdown special characters that need escaping
# Order matters: backslash must be first to avoid double-escaping
MARKDOWN_ESCAPE_CHARS = [
    "\\",  # Backslash first (escape character itself)
    "`",  # Code blocks and inline code
    "*",  # Bold and italic
    "_",  # Bold and italic (alternative)
    "{",  # Curly braces (some parsers use for macros)
    "}",
    "[",  # Links and references
    "]",
    "(",  # Link URLs
    ")",
    "#",  # Headings
    "+",  # Unordered lists
    "-",  # Unordered lists and horizontal rules
    ".",  # Ordered lists (after numbers)
    "!",  # Images
    "|",  # Tables
    "<",  # HTML tags
    ">",  # Block quotes and HTML tags
]

# Precompiled regex for null byte removal
NULL_BYTE_PATTERN = re.compile(r"\x00")

# Precompiled regex for detecting already-escaped content
ALREADY_ESCAPED_PATTERN = re.compile(r"\\([\\`*_{}\[\]()#+\-.!|<>])")


def escape_markdown(text: str) -> str:
    r"""Escape markdown special characters in text.

    This function escapes all markdown formatting characters to prevent
    them from being interpreted as markdown syntax when the text is
    rendered in a markdown file.

    Args:
        text: The text to escape. Must be a string.

    Returns:
        str: The escaped text with all markdown special characters
             prefixed with backslash.

    Examples:
        >>> escape_markdown("**bold**")
        '\\*\\*bold\\*\\*'
        >>> escape_markdown("# Heading")
        '\\# Heading'
        >>> escape_markdown("[link](url)")
        '\\[link\\]\\(url\\)'
    """
    if not text:
        return ""

    result = text

    # Check for already-escaped content to avoid double-escaping
    # If we find patterns like \*, \_, etc., we need to handle them specially
    # Strategy: temporarily replace already-escaped sequences, escape, then restore
    placeholder_map = {}
    placeholder_counter = [0]

    def make_placeholder(match: re.Match) -> str:
        placeholder = f"\x00ESCAPED_{placeholder_counter[0]}\x00"
        placeholder_map[placeholder] = match.group(0)
        placeholder_counter[0] += 1
        return placeholder

    # Protect already-escaped sequences
    result = ALREADY_ESCAPED_PATTERN.sub(make_placeholder, result)

    # Escape each special character
    for char in MARKDOWN_ESCAPE_CHARS:
        # Skip backslash if we've already handled it via placeholder
        if char == "\\":
            # Only escape backslashes that are not part of escape sequences
            # This is tricky - we escape standalone backslashes
            result = re.sub(r"\\(?![\\`*_{}\[\]()#+\-.!|<>])", r"\\\\", result)
        else:
            result = result.replace(char, f"\\{char}")

    # Restore already-escaped sequences
    for placeholder, original in placeholder_map.items():
        result = result.replace(placeholder, original)

    return result


def escape_markdown_code_block(text: str) -> str:
    r"""Escape content that will be placed inside a markdown code block.

    When user content is placed inside a code block (```...```), we need
    to escape any triple backticks within the content to prevent the
    user from "breaking out" of the code block.

    Args:
        text: The text to be placed in a code block.

    Returns:
        str: The text with triple backticks escaped.

    Examples:
        >>> escape_markdown_code_block("```python\ncode\n```")
        "\\`\\`\\`python\ncode\n\\`\\`\\`"
    """
    if not text:
        return ""

    # Replace triple backticks with escaped version
    # We use a unique replacement to avoid issues with partial matches
    result = text.replace("```", "\\`\\`\\`")

    # Also escape single backticks at the start/end of lines that could
    # potentially be combined with surrounding backticks
    result = re.sub(r"^`", "\\`", result, flags=re.MULTILINE)
    result = re.sub(r"`$", "\\`", result, flags=re.MULTILINE)

    return result


def sanitize_for_markdown_file(
    text: str,
    max_length: int | None = None,
    preserve_newlines: bool = True,
) -> str:
    r"""Sanitize user-provided text for safe inclusion in markdown files.

    This is the main entry point for sanitizing content before writing
    to markdown files like QUERY_ISSUES_ROADMAP.md. It combines multiple
    security measures:
    1. Removes null bytes
    2. Escapes markdown special characters
    3. Optionally truncates to max_length
    4. Normalizes whitespace

    Args:
        text: The text to sanitize. Must be a string (not None).
        max_length: Optional maximum length. If provided, text will be
                   truncated to this length (with "..." suffix if truncated).
        preserve_newlines: If True, newlines are preserved. If False,
                          they are converted to spaces.

    Returns:
        str: The sanitized text safe for markdown inclusion.

    Raises:
        TypeError: If text is None.
        ValueError: If text is not a string.

    Examples:
        >>> sanitize_for_markdown_file("# Heading")
        '\\# Heading'
        >>> sanitize_for_markdown_file("Safe text")
        'Safe text'
    """
    if text is None:
        raise TypeError("text cannot be None")

    if not isinstance(text, str):
        raise ValueError(f"text must be a string, got {type(text).__name__}")

    # Step 1: Remove null bytes (security measure)
    result = NULL_BYTE_PATTERN.sub("", text)

    # Step 2: Handle newlines
    if not preserve_newlines:
        result = result.replace("\n", " ").replace("\r", " ")

    # Step 3: Normalize excessive whitespace (but preserve single newlines)
    # Replace multiple spaces with single space
    result = re.sub(r" {2,}", " ", result)
    # Replace multiple newlines with double newline (preserve paragraph breaks)
    if preserve_newlines:
        result = re.sub(r"\n{3,}", "\n\n", result)

    # Step 4: Escape markdown special characters
    result = escape_markdown(result)

    # Step 5: Truncate if needed
    if max_length is not None and len(result) > max_length:
        # Truncate with ellipsis, accounting for ellipsis length
        truncate_at = max_length - 3
        if truncate_at > 0:
            result = result[:truncate_at] + "..."
        else:
            result = result[:max_length]

    # Step 6: Strip leading/trailing whitespace
    result = result.strip()

    return result


def escape_for_markdown_table_cell(text: str) -> str:
    """Escape text for safe inclusion in a markdown table cell.

    Table cells have additional restrictions:
    - Pipes (|) must be escaped to not break table structure
    - Newlines must be removed (tables don't support multiline cells)

    Args:
        text: The text to escape for table cell.

    Returns:
        str: Text safe for markdown table cell.
    """
    if not text:
        return ""

    # Remove newlines (tables don't support them)
    result = text.replace("\n", " ").replace("\r", " ")

    # Escape markdown characters
    result = escape_markdown(result)

    return result
