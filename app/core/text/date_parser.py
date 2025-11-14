"""
Date extraction utilities for Italian documents.

Provides functions to extract publication dates from Italian regulatory documents
and parse years from search queries.
"""

import re
from datetime import date
from typing import Optional

# Italian month name to number mapping
ITALIAN_MONTHS = {
    "gennaio": 1,
    "febbraio": 2,
    "marzo": 3,
    "aprile": 4,
    "maggio": 5,
    "giugno": 6,
    "luglio": 7,
    "agosto": 8,
    "settembre": 9,
    "ottobre": 10,
    "novembre": 11,
    "dicembre": 12,
}


def extract_publication_date(content: str, title: str = "") -> Optional[date]:
    """
    Extract publication date from Italian document content.

    Looks for common Italian date patterns like:
    - "Roma, 13 ottobre 2025"
    - "del 13 ottobre 2025"
    - "13 ottobre 2025"
    - "30/10/2025 (ottobre)" (after text normalization)

    Args:
        content: Document content
        title: Document title (optional)

    Returns:
        date object or None if not found
    """
    # Search in title + first 500 chars of content
    search_text = f"{title} {content[:500]}"

    # Italian date patterns (ordered by specificity)
    date_patterns = [
        # "Roma, 13 ottobre 2025"
        r"Roma,?\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        # "del 13 ottobre 2025"
        r"del\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        # "13 ottobre 2025"
        r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        # "n. 62 del 13 ottobre 2025"
        r"n\.\s*\d+\s+del\s+(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
        # "30/10/2025 (ottobre)" - after text normalization
        r"(\d{1,2})/(\d{1,2})/(\d{4})\s*\((gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\)",
    ]

    for pattern in date_patterns:
        match = re.search(pattern, search_text, re.IGNORECASE)
        if match:
            groups = match.groups()

            # Handle DD/MM/YYYY (month_name) format
            if len(groups) == 4:
                day, month_num, year, month_name = groups
                month = int(month_num)
            # Handle "DD month_name YYYY" format
            else:
                day, month_name, year = groups
                month = ITALIAN_MONTHS.get(month_name.lower())

            if month:
                try:
                    return date(int(year), month, int(day))
                except ValueError:
                    # Invalid date (e.g., Feb 30) - continue to next pattern
                    continue

    return None


def extract_year_from_query(query: str) -> Optional[int]:
    """
    Extract 4-digit year from search query.

    Looks for years in format 201X or 202X (2010-2029 range).

    Args:
        query: User search query

    Returns:
        Year (int) or None if not found

    Examples:
        >>> extract_year_from_query("risoluzioni ottobre 2025")
        2025
        >>> extract_year_from_query("risoluzioni ottobre")
        None
    """
    match = re.search(r"\b(202[0-9]|201[0-9])\b", query)
    return int(match.group(1)) if match else None


def strip_years_from_text(text: str) -> str:
    """
    Remove 4-digit years from text (for FTS preprocessing).

    PostgreSQL FTS doesn't index numbers, so we strip years from queries
    to prevent false negatives. Year filtering is done via SQL WHERE clause.

    Args:
        text: Input text

    Returns:
        Text with years removed and whitespace normalized

    Examples:
        >>> strip_years_from_text("risoluzioni ottobre 2025")
        "risoluzioni ottobre"
        >>> strip_years_from_text("documenti 2024 e 2025")
        "documenti e"
    """
    # Remove 4-digit years
    text = re.sub(r"\b(202[0-9]|201[0-9])\b", "", text)

    # Normalize whitespace
    text = " ".join(text.split())

    return text.strip()
