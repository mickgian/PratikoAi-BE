"""Title simplification for Fonti display.

Simplifies document titles by removing article references and truncated text.
"""

import re


def simplify_title(title: str | None) -> str:
    """Simplify document title for Fonti display (DEV-245).

    Removes article references and truncated text from titles like:
    "LEGGE 30 dicembre 2025, n. 199 - Art. 1 - guenti: «33 per c…"
    → "LEGGE 30 dicembre 2025, n. 199"

    Args:
        title: Full document title

    Returns:
        Simplified title without article details
    """
    if not title:
        return ""

    # Pattern 1: Remove " - Art. X" and everything after
    simplified = re.sub(r"\s*-\s*Art(?:icolo)?\.?\s*\d+.*$", "", title, flags=re.IGNORECASE)

    # Pattern 2: Remove truncated text (ends with "…" or "...")
    if simplified.endswith("…") or simplified.endswith("..."):
        simplified = re.sub(r"\s+\S*[…\.]{2,}$", "", simplified)

    # Pattern 3: Remove trailing " - " with partial content
    simplified = re.sub(r"\s*-\s*[^-]{0,20}$", "", simplified)

    # Clean up any trailing punctuation or whitespace
    simplified = simplified.rstrip(" -–—:")

    return simplified.strip()
