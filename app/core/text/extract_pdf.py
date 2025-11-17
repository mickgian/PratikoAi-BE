"""PDF text extraction quality metrics (shared utilities).

This module provides text quality metrics used by PDF extractors.
The actual extraction logic has moved to extract_pdf_plumber.py (pdfplumber + Tesseract).

PyMuPDF/fitz (AGPL license) has been replaced with MIT/Apache-2.0 licensed stack.

Usage:
    from app.core.text.extract_pdf import text_metrics
    metrics = text_metrics("some text content")
    # Returns: {
    #   "length": int,
    #   "printable_ratio": float,
    #   "alpha_ratio": float,
    #   "word_count": int,
    #   "looks_junk": bool,
    #   "quality_score": float (0.0-1.0)
    # }
"""

import logging
from typing import (
    Any,
    Dict,
)

from app.core.config import (
    CLEAN_ALPHA_RATIO,
    CLEAN_MIN_LEN,
    CLEAN_MIN_WORDS,
    CLEAN_PRINTABLE_RATIO,
)

logger = logging.getLogger(__name__)


def text_metrics(text: str) -> dict[str, Any]:
    """Compute quality metrics for text content.

    Args:
        text: Text content to analyze

    Returns:
        Dictionary with metrics:
        - length: Character count
        - printable_ratio: Ratio of printable characters
        - alpha_ratio: Ratio of alphabetic characters
        - word_count: Number of words with alphabetic characters
        - looks_junk: Boolean indicating likely corrupted text
        - quality_score: 0.0-1.0 quality score
    """
    length = len(text or "")

    if length == 0:
        return {
            "length": 0,
            "printable_ratio": 0.0,
            "alpha_ratio": 0.0,
            "word_count": 0,
            "looks_junk": True,
            "quality_score": 0.0,
        }

    # Count printable characters (alphanumeric, space, and common punctuation)
    printable = sum(c.isalnum() or c.isspace() or c in ",.;:%()[]-–—€'\"/" for c in text)

    # Count alphabetic characters
    alpha = sum(c.isalpha() for c in text)

    # Count words (tokens with at least one alphabetic character)
    words = sum(1 for w in text.split() if any(ch.isalpha() for ch in w))

    # Calculate ratios
    printable_ratio = printable / max(length, 1)
    alpha_ratio = alpha / max(length, 1)

    # Determine if text looks like junk
    looks_junk = (
        length < CLEAN_MIN_LEN
        or printable_ratio < CLEAN_PRINTABLE_RATIO
        or alpha_ratio < CLEAN_ALPHA_RATIO
        or words < CLEAN_MIN_WORDS
    )

    # Calculate quality score (weighted average of ratios)
    quality_score = 0.5 * min(printable_ratio, 1.0) + 0.5 * min(alpha_ratio, 1.0)

    return {
        "length": length,
        "printable_ratio": round(printable_ratio, 3),
        "alpha_ratio": round(alpha_ratio, 3),
        "word_count": words,
        "looks_junk": looks_junk,
        "quality_score": round(quality_score, 3),
    }
