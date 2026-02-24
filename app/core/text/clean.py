"""Text cleaning utilities for Italian regulatory documents.

Handles:
- HTML extraction and cleaning with intelligent content detection
- Automatic main content extraction using Trafilatura
- Quality validation to detect navigation/boilerplate content
- Whitespace normalization
- Special character handling for Italian text
"""

import html
import re
from typing import Tuple

from bs4 import BeautifulSoup

from app.core.logging import logger

# Trafilatura for intelligent content extraction
try:
    import trafilatura

    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning("trafilatura_not_available", message="Install trafilatura for better content extraction")


# Navigation/boilerplate patterns that indicate extraction failed
NAVIGATION_PATTERNS = [
    "vai al menu",
    "vai al contenuto",
    "cookie policy",
    "accedi a myinps",
    "cedolino pensione",
    "mappa del sito",
    "privacy policy",
    "seguici su",
    "contatti",
    "cambia lingua",
    "cerca nel sito",
    "menu principale",
    "skip to content",
    "skip to main",
    "area riservata",
    "cassetto fiscale",
    "fatture e corrispettivi",
    "amministrazione trasparente",
    "note legali",
    "dipartimento delle finanze",
]


_HTML_ENTITY_PATTERN = re.compile(r"&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);")


def sanitize_html_entities(text: str) -> str:
    """Decode any residual HTML entities in text.

    Safety net for content that passed through HTML extraction but still
    contains encoded entities like &amp;, &lt;, &#8217;, &#xE0;.

    Args:
        text: Input text that may contain HTML entities

    Returns:
        Text with all HTML entities decoded
    """
    if _HTML_ENTITY_PATTERN.search(text):
        return html.unescape(text)
    return text


def chunk_contains_navigation(text: str, threshold: int = 2) -> bool:
    """Check if a chunk contains navigation boilerplate text.

    Used to filter out chunks contaminated with web scraping artifacts
    (e.g. "vai al menu", "cookie policy", "area riservata").

    Args:
        text: Chunk text content
        threshold: Minimum pattern matches to flag as navigation

    Returns:
        True if chunk is navigation boilerplate and should be dropped
    """
    text_lower = text.lower()
    matches = sum(1 for p in NAVIGATION_PATTERNS if p in text_lower)

    if matches >= threshold:
        return True

    # Single match in a short chunk — too small to have meaningful content
    if matches >= 1 and len(text) < 300:
        return True

    return False


def validate_extracted_content(text: str, url: str = "") -> tuple[bool, str]:
    """Check if extracted content looks valid (not navigation/boilerplate).

    Args:
        text: Extracted text content
        url: Source URL for logging

    Returns:
        Tuple of (is_valid, reason)
    """
    if not text or not text.strip():
        return False, "Empty content"

    text_lower = text.lower()

    # Check 1: Contains too many navigation keywords
    nav_matches = sum(1 for p in NAVIGATION_PATTERNS if p in text_lower)
    if nav_matches >= 3:
        return False, f"Contains {nav_matches} navigation patterns"

    # Check 2: Too short (likely extraction failed)
    if len(text.strip()) < 200:
        return False, f"Content too short ({len(text.strip())} chars)"

    # Check 3: Content starts with common navigation text
    first_50 = text_lower[:50] if len(text_lower) >= 50 else text_lower
    nav_starts = ["vai al", "menu", "home", "accedi", "skip to"]
    if any(first_50.startswith(p) for p in nav_starts):
        return False, "Starts with navigation text"

    # Check 4: High ratio of navigation to content
    nav_char_count = sum(len(p) for p in NAVIGATION_PATTERNS if p in text_lower)
    if len(text) > 0 and nav_char_count / len(text) > 0.1:
        return False, "High navigation content ratio"

    return True, "OK"


def clean_html(html_content: str, url: str = "") -> str:
    """Extract and clean main text from HTML content.

    Uses trafilatura for intelligent content extraction that automatically:
    - Removes navigation, headers, footers, sidebars
    - Identifies and extracts main content area
    - Works across any website without site-specific configuration

    Falls back to BeautifulSoup if trafilatura unavailable or fails.
    Validates extracted content to detect garbage.

    Args:
        html_content: Raw HTML string
        url: Source URL (for logging)

    Returns:
        Cleaned plain text (main content only)
    """
    if not html_content or not html_content.strip():
        return ""

    extracted_text = ""
    extraction_method = "none"

    # Try trafilatura first (intelligent extraction)
    if TRAFILATURA_AVAILABLE:
        try:
            extracted = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=True,
                no_fallback=False,
                favor_precision=True,
            )
            if extracted and len(extracted.strip()) > 100:
                extracted_text = normalize_whitespace(extracted)
                extraction_method = "trafilatura"
        except Exception as e:
            logger.warning("trafilatura_extraction_failed", url=url, error=str(e))

    # Fallback: BeautifulSoup with enhanced removal
    if not extracted_text:
        extracted_text = _fallback_clean_html(html_content)
        extraction_method = "beautifulsoup_fallback"

    # Validate extracted content
    is_valid, reason = validate_extracted_content(extracted_text, url)

    if not is_valid:
        logger.warning(
            "content_extraction_quality_warning",
            url=url,
            extraction_method=extraction_method,
            reason=reason,
            content_length=len(extracted_text),
            first_100_chars=extracted_text[:100] if extracted_text else "",
        )
    else:
        logger.debug(
            "content_extraction_success",
            url=url,
            extraction_method=extraction_method,
            content_length=len(extracted_text),
        )

    return extracted_text


def _fallback_clean_html(html_content: str) -> str:
    """Fallback HTML cleaning using BeautifulSoup.

    Used when trafilatura is unavailable or fails.
    """
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove non-content elements (expanded list)
    for element in soup(
        [
            "script",
            "style",
            "meta",
            "link",
            "nav",
            "header",
            "footer",
            "aside",
            "noscript",
            "iframe",
            "form",
        ]
    ):
        element.decompose()

    # Remove common non-content classes
    for selector in [".cookie", ".banner", ".menu", ".sidebar", ".breadcrumb", ".navigation"]:
        for el in soup.select(selector):
            el.decompose()

    # Try to find main content area
    for selector in ["main", "article", "[role='main']", "#content", ".content", "#main-content"]:
        main = soup.select_one(selector)
        if main:
            text = main.get_text()
            if len(text.strip()) > 200:
                return normalize_whitespace(text)

    # Last resort: body text
    body = soup.find("body")
    if body:
        return normalize_whitespace(body.get_text())

    return normalize_whitespace(soup.get_text())


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

    # Normalize quotes (curly to straight)
    text = text.replace("\u201c", '"').replace("\u201d", '"')  # left/right double quotes
    text = text.replace("\u2018", "'").replace("\u2019", "'")  # left/right single quotes

    # Normalize dashes (en-dash and em-dash to regular hyphen)
    text = text.replace("\u2013", "-").replace("\u2014", "-")

    # Remove zero-width spaces and other invisible characters
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)

    # Normalize whitespace
    text = normalize_whitespace(text)

    return text


def extract_text_from_url_content(
    content: str,
    content_type: str | None = None,
    url: str = "",
) -> str:
    """Extract clean text from URL content (HTML, PDF, etc.).

    Args:
        content: Raw content string
        content_type: MIME type hint (e.g., 'text/html', 'application/pdf')
        url: Source URL (for logging quality warnings)

    Returns:
        Cleaned text content
    """
    # Detect if content is HTML
    if content_type and "html" in content_type.lower():
        text = clean_html(content, url=url)
    elif content.strip().startswith("<"):
        # Looks like HTML
        text = clean_html(content, url=url)
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


# ---------------------------------------------------------------------------
# E.7: Preamble / signature removal for Italian legal documents
# ---------------------------------------------------------------------------

# Matches the dispositional keyword that ends a preamble block.
# The preamble runs from the start of text (or from an institutional header
# like "IL DIRETTORE...") up to and including one of these keywords.
_PREAMBLE_END_RE = re.compile(
    r"(?m)^[ \t]*(?:DISPONE|DECRETA|DETERMINA|DELIBERA|ORDINA|EMANA)\b[^\n]*\n?",
)

# Institutional header that typically starts a preamble.
_INSTITUTIONAL_HEADER_RE = re.compile(
    r"(?m)^[ \t]*IL\s+(?:DIRETTORE|PRESIDENTE|MINISTRO|SEGRETARIO|CAPO|COMMISSARIO)\b"
)


def strip_preamble(text: str) -> str:
    """Remove institutional preamble from Italian legal documents.

    Strips the block from "IL DIRETTORE/PRESIDENTE/..." through the
    dispositional keyword (DISPONE/DECRETA/EMANA/...), keeping everything
    after that keyword.

    Args:
        text: Full document text.

    Returns:
        Text with preamble removed. Unchanged if no preamble detected.
    """
    match = _PREAMBLE_END_RE.search(text)
    if not match:
        return text

    # Only strip if an institutional header precedes the keyword
    header = _INSTITUTIONAL_HEADER_RE.search(text[: match.start()])
    if not header:
        return text

    return text[match.end() :].strip()


# Signature block patterns (appear at the end of documents).
_SIGNATURE_BLOCK_RE = re.compile(
    r"(?m)"
    r"(?:"
    r"(?:Roma|Milano|Napoli|Torino|Firenze|Bologna|Palermo),\s+\d{1,2}\s+\w+\s+\d{4}\s*\n"
    r"[ \t]*IL\s+(?:DIRETTORE|PRESIDENTE|MINISTRO|SEGRETARIO|CAPO|RESPONSABILE)\b"
    r"|Firmato\s+digitalmente(?:\s+da)?"
    r")"
    r"[\s\S]*$"
)


def strip_signature_block(text: str) -> str:
    """Remove trailing signature block from Italian legal documents.

    Detects patterns like:
        Roma, 15 gennaio 2024
        IL DIRETTORE DELL'AGENZIA
        Ernesto Maria Ruffini
    or:
        Firmato digitalmente da ...

    Args:
        text: Full document text.

    Returns:
        Text with signature block removed. Unchanged if not detected.
    """
    result = _SIGNATURE_BLOCK_RE.sub("", text)
    return result.strip()


# ---------------------------------------------------------------------------
# E.11: Table of Contents detection
# ---------------------------------------------------------------------------

# Dotted leader pattern: "something ......... 123"
_DOTTED_LEADER_RE = re.compile(r"\.{3,}\s*\d+")

# TOC header keywords
_TOC_HEADERS = ["indice", "sommario", "table of contents"]


def detect_toc_section(text: str) -> bool:
    """Detect whether a text block is a Table of Contents.

    A TOC is identified by:
    - A header keyword (INDICE, SOMMARIO) AND dotted leaders, OR
    - Multiple lines with dotted leaders (>=3 lines)

    Args:
        text: Text block to check.

    Returns:
        True if the text looks like a TOC section.
    """
    lines = text.strip().split("\n")
    if not lines:
        return False

    first_line_lower = lines[0].strip().lower()
    has_toc_header = any(h in first_line_lower for h in _TOC_HEADERS)

    dotted_lines = sum(1 for line in lines if _DOTTED_LEADER_RE.search(line))

    # TOC header + at least one dotted leader
    if has_toc_header and dotted_lines >= 1:
        return True

    # No header but many dotted leaders (standalone TOC)
    return dotted_lines >= 3
