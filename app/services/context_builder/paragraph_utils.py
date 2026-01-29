"""Paragraph utilities for source tracking.

Contains functions for generating paragraph IDs and extracting excerpts.
"""


def generate_paragraph_id(doc_id: str, paragraph_index: int) -> str:
    """Generate a unique paragraph ID for source tracking (DEV-236).

    Args:
        doc_id: Document ID
        paragraph_index: Index of the paragraph within the document

    Returns:
        Unique paragraph ID in format "doc_id_p{index}"
    """
    if not doc_id:
        return f"unknown_p{paragraph_index}"
    return f"{doc_id}_p{paragraph_index}"


def extract_paragraph_excerpt(content: str | None, max_length: int = 150) -> str:
    """Extract the first meaningful paragraph as excerpt for tooltip display (DEV-236).

    Args:
        content: Document content text
        max_length: Maximum excerpt length (default 150 for UI tooltip)

    Returns:
        First paragraph excerpt, truncated with ellipsis if needed
    """
    if not content:
        return ""

    # Strip and check for whitespace-only
    content = content.strip()
    if not content:
        return ""

    # Take the first part up to max_length
    if len(content) <= max_length:
        return content

    # Truncate at max_length and add ellipsis
    truncated = content[:max_length]

    # Try to break at word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_length * 0.7:  # Only if we can keep 70%+ of the content
        truncated = truncated[:last_space]

    return truncated + "..."
