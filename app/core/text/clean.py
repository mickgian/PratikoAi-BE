"""Text cleaning utilities for Italian regulatory documents.

Handles:
- HTML extraction and cleaning
- PDF text extraction (if needed)
- Whitespace normalization
- Special character handling for Italian text
"""

import html
import re
from typing import Optional

from bs4 import BeautifulSoup


def clean_html(html_content: str) -> str:
    """Extract and clean text from HTML content.

    Args:
        html_content: Raw HTML string

    Returns:
        Cleaned plain text
    """
    # Parse HTML
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "meta", "link"]):
        element.decompose()

    # Get text with separator
    # Note: get_text() accepts separator as first positional arg in BS4 4.x
    text = soup.get_text()  # Get all text
    text = " ".join(text.split())  # Join with spaces, normalize whitespace

    # Clean up text
    text = normalize_whitespace(text)

    return text


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text.

    Args:
        text: Input text

    Returns:
        Text with normalized whitespace
    """
    # Replace multiple spaces with single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with double newline
    text = re.sub(r"\n\n+", "\n\n", text)

    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    # Remove empty lines
    lines = [line for line in text.split("\n") if line]
    text = "\n".join(lines)

    return text.strip()


def clean_italian_text(text: str) -> str:
    """Clean Italian text while preserving special characters.

    Args:
        text: Input text in Italian

    Returns:
        Cleaned text
    """
    # Decode HTML entities
    text = html.unescape(text)

    # Normalize quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace("'", "'").replace("'", "'")

    # Normalize dashes
    text = text.replace("–", "-").replace("—", "-")

    # Remove zero-width spaces and other invisible characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Normalize whitespace
    text = normalize_whitespace(text)

    return text


def extract_text_from_url_content(content: str, content_type: str | None = None) -> str:
    """Extract clean text from URL content (HTML, PDF, etc.).

    Args:
        content: Raw content string
        content_type: MIME type hint (e.g., 'text/html', 'application/pdf')

    Returns:
        Cleaned text content
    """
    # Detect if content is HTML
    if content_type and "html" in content_type.lower():
        text = clean_html(content)
    elif content.strip().startswith("<"):
        # Looks like HTML
        text = clean_html(content)
    else:
        # Assume plain text
        text = content

    # Apply Italian-specific cleaning
    text = clean_italian_text(text)

    return text


def truncate_text(text: str, max_chars: int = 50000) -> str:
    """Truncate text to maximum character length.

    Args:
        text: Input text
        max_chars: Maximum characters to keep

    Returns:
        Truncated text
    """
    if len(text) <= max_chars:
        return text

    return text[:max_chars] + "\n\n[Text truncated...]"


def is_valid_text(text: str, min_length: int = 50) -> bool:
    """Check if text is valid for processing.

    Args:
        text: Input text
        min_length: Minimum required length

    Returns:
        True if text is valid
    """
    if not text or not text.strip():
        return False

    if len(text.strip()) < min_length:
        return False

    # Check for actual content (not just special characters)
    alphanumeric = re.sub(r"[^a-zA-Z0-9À-ÿ]", "", text)
    return not len(alphanumeric) < min_length // 2
