"""Repair broken hyphenation from PDF text extraction.

Italian regulatory PDFs frequently contain line-break hyphenation artifacts
like "contri- buto" (should be "contributo"). This module provides a regex
to rejoin those while preserving legitimate compound words ("decreto-legge").
"""

import re

# Matches a lowercase letter (including Italian accented vowels) followed by
# "- " and another lowercase letter — the hallmark of a broken line-break
# hyphenation.  Legitimate compounds like "decreto-legge" have NO space after
# the hyphen, so they are unaffected.
_BROKEN_HYPHEN_RE = re.compile(
    r"([a-z\u00e0\u00e8\u00e9\u00ec\u00f2\u00f9])- ([a-z\u00e0\u00e8\u00e9\u00ec\u00f2\u00f9])"
)


def repair_broken_hyphenation(text: str) -> str:
    """Rejoin words broken by PDF line-break hyphenation.

    Converts "contri- buto" → "contributo" while leaving legitimate
    compounds like "decreto-legge" and "socio-economico" intact.

    Args:
        text: Raw text possibly containing broken hyphenation.

    Returns:
        Text with broken hyphenation repaired.
    """
    if not text:
        return text
    return _BROKEN_HYPHEN_RE.sub(r"\1\2", text)
