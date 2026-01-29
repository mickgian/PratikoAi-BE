"""Article Extractor Service for DEV-245.

Extracts Italian legal article references (articolo, comma, lettera) from text.
This enables accurate citation of specific legal provisions in responses.

Usage:
    from app.services.article_extractor import article_extractor

    refs = article_extractor.extract_references(text)
    for ref in refs:
        print(f"Found: {ref}")  # "Art. 1, comma 231, lettera a)"

    # Or extract chunk metadata for storage
    metadata = article_extractor.extract_chunk_metadata(chunk_text)
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger


@dataclass
class ArticleReference:
    """A reference to an Italian legal article.

    Represents patterns like:
    - "Art. 1"
    - "Art. 1, comma 231"
    - "Art. 1, comma 231, lettera a)"
    - "Art. 1, commi 231-252"
    """

    article: str
    comma: str | None = None
    lettera: str | None = None
    comma_range: tuple[str, str] | None = None
    source_law: str | None = None

    def __str__(self) -> str:
        """Format as Italian legal citation."""
        parts = [f"Art. {self.article}"]

        if self.comma_range:
            parts.append(f"commi {self.comma_range[0]}-{self.comma_range[1]}")
        elif self.comma:
            parts.append(f"comma {self.comma}")

        if self.lettera:
            parts.append(f"lettera {self.lettera})")

        result = ", ".join(parts)

        if self.source_law:
            result += f", {self.source_law}"

        return result

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "article": self.article,
            "comma": self.comma,
            "lettera": self.lettera,
            "comma_range": self.comma_range,
            "source_law": self.source_law,
        }

    def __eq__(self, other: object) -> bool:
        """Check equality."""
        if not isinstance(other, ArticleReference):
            return False
        return (
            self.article == other.article
            and self.comma == other.comma
            and self.lettera == other.lettera
            and self.comma_range == other.comma_range
        )


# Regex patterns for Italian legal article references
# Matches: Art. 1, art. 1, ARTICOLO 1, articolo 1
ARTICLE_PATTERN = re.compile(
    r"""
    (?:
        (?:[Aa]rt(?:icolo|\.)?|ARTICOLO|artt\.?)  # Article prefix
        \s*
        (\d+(?:-[a-z]+)?)                          # Article number (e.g., 1, 2-bis, 36-ter)
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Matches: comma 231, c. 231, co. 231, COMMA 231
COMMA_PATTERN = re.compile(
    r"""
    (?:[Cc]omma|[Cc]o?\.)\s*(\d+)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Matches: commi da 231 a 252, commi 231-252
COMMA_RANGE_PATTERN = re.compile(
    r"""
    [Cc]ommi\s+
    (?:da\s+)?
    (\d+)
    \s*
    (?:a|-)\s*
    (\d+)
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Matches: lettera a), lett. a), LETTERA A)
LETTERA_PATTERN = re.compile(
    r"""
    (?:[Ll]ett(?:era)?\.?)\s*([a-zA-Z])(?:\))?
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Matches Italian law references for context
LAW_PATTERN = re.compile(
    r"""
    (?:
        (?:della\s+)?
        (?:
            [Ll]egge\s+(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}
            |
            D\.?Lgs\.?\s*(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}
            |
            D\.?P\.?R\.?\s*(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}
        )
    )
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Combined pattern for full article citation
# Matches: Art. 1, comma 231, lettera a) della Legge 199/2025
FULL_CITATION_PATTERN = re.compile(
    r"""
    (?:[Aa]rt(?:icolo|\.)?|ARTICOLO|artt\.?)\s*
    (\d+(?:-[a-z]+)?)                            # Article number
    (?:
        \s*,?\s*
        (?:[Cc]omma|[Cc]o?\.)\s*(\d+)            # Comma number (optional)
    )?
    (?:
        \s*,?\s*
        (?:[Ll]ett(?:era)?\.?)\s*([a-zA-Z])(?:\))?  # Lettera (optional)
    )?
    (?:
        \s*
        (?:della?\s+)?
        (
            [Ll]egge\s+(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}
            |
            D\.?Lgs\.?\s*(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}
            |
            D\.?P\.?R\.?\s*(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}
        )
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
)


class ArticleExtractor:
    """Service to extract Italian legal article references from text.

    Extracts patterns like:
    - "Art. 1" -> ArticleReference(article="1")
    - "Art. 1, comma 231" -> ArticleReference(article="1", comma="231")
    - "Art. 1, comma 231, lettera a)" -> ArticleReference(article="1", comma="231", lettera="a")
    - "Art. 1, commi 231-252" -> ArticleReference(article="1", comma_range=("231", "252"))

    Example:
        extractor = ArticleExtractor()
        refs = extractor.extract_references("Art. 1, comma 231 della Legge 199/2025")
        # refs[0] = ArticleReference(article="1", comma="231", source_law="Legge 199/2025")
    """

    def extract_references(self, text: str) -> list[ArticleReference]:
        """Extract all article references from text.

        Args:
            text: Text to extract references from

        Returns:
            List of ArticleReference objects
        """
        if not text:
            return []

        references: list[ArticleReference] = []
        seen: set[tuple[Any, ...]] = set()  # Track unique references

        # First, try to extract comma ranges
        for match in COMMA_RANGE_PATTERN.finditer(text):
            start, end = match.groups()

            # Find the article this range belongs to (look before and after)
            article = self._find_preceding_article(text, match.start())

            # If no preceding article, try to find one after the range
            if not article:
                remaining = text[match.end() : match.end() + 100]
                article_match = ARTICLE_PATTERN.search(remaining)
                if article_match:
                    article = article_match.group(1)

            # Create reference even without explicit article (use "N/A" as placeholder)
            ref = ArticleReference(
                article=article or "N/A",
                comma_range=(start, end),
            )
            key: tuple[Any, ...] = (ref.article, None, None, ref.comma_range)
            if key not in seen:
                references.append(ref)
                seen.add(key)

        # Extract full citations with article + comma + lettera + law
        for match in FULL_CITATION_PATTERN.finditer(text):
            article, comma, lettera, law = match.groups()

            if not article:
                continue

            # Normalize article (remove leading zeros, etc.)
            article = article.strip()

            # Normalize lettera
            if lettera:
                lettera = lettera.lower()

            # Clean up law reference
            if law:
                law = law.strip()

            ref = ArticleReference(
                article=article,
                comma=comma,
                lettera=lettera,
                source_law=law,
            )

            # Avoid duplicates
            key = (ref.article, ref.comma, ref.lettera, None)
            if key not in seen:
                references.append(ref)
                seen.add(key)

        # If no full citations found, try simpler article extraction
        if not references:
            for match in ARTICLE_PATTERN.finditer(text):
                article = match.group(1)
                if article:
                    article = article.strip()

                    # Look for nearby comma and lettera
                    remaining_text = text[match.end() : match.end() + 100]

                    comma = None
                    comma_match = COMMA_PATTERN.search(remaining_text)
                    if comma_match and comma_match.start() < 30:
                        comma = comma_match.group(1)

                    lettera = None
                    lettera_match = LETTERA_PATTERN.search(remaining_text)
                    if lettera_match and lettera_match.start() < 50:
                        lettera = lettera_match.group(1).lower()

                    # Look for law context
                    law = None
                    law_match = LAW_PATTERN.search(remaining_text)
                    if law_match and law_match.start() < 80:
                        law = law_match.group(0).strip()

                    ref = ArticleReference(
                        article=article,
                        comma=comma,
                        lettera=lettera,
                        source_law=law,
                    )

                    key = (ref.article, ref.comma, ref.lettera, None)
                    if key not in seen:
                        references.append(ref)
                        seen.add(key)

        logger.debug(
            "article_extraction_complete",
            text_length=len(text),
            references_found=len(references),
        )

        return references

    def _find_preceding_article(self, text: str, position: int) -> str | None:
        """Find the article number that precedes a given position.

        Args:
            text: Full text
            position: Position to search before

        Returns:
            Article number if found, None otherwise
        """
        # Look in the 100 characters before the position
        search_start = max(0, position - 100)
        preceding_text = text[search_start:position]

        # Find the last article reference
        matches = list(ARTICLE_PATTERN.finditer(preceding_text))
        if matches:
            return matches[-1].group(1)

        return None

    def extract_chunk_metadata(self, chunk_text: str) -> dict[str, Any]:
        """Extract article metadata from a document chunk.

        This is used during document ingestion to store article structure
        in chunk metadata for better retrieval and citation.

        Args:
            chunk_text: Text of the chunk

        Returns:
            Dictionary with:
            - article_references: List of ArticleReference dicts
            - primary_article: The main article referenced (if any)
            - has_definitions: Whether chunk contains "Definizioni" section
            - comma_count: Number of comma references found
        """
        references = self.extract_references(chunk_text)

        # Determine primary article (most common or first)
        primary_article = None
        if references:
            article_counts: dict[str, int] = {}
            for ref in references:
                article_counts[ref.article] = article_counts.get(ref.article, 0) + 1

            # Get most common article
            primary_article = max(article_counts, key=lambda k: article_counts.get(k, 0)) if article_counts else None

        # Check for special sections
        has_definitions = bool(re.search(r"[Dd]efinizion[ie]", chunk_text))

        # Count comma references
        comma_count = len(COMMA_PATTERN.findall(chunk_text))

        metadata = {
            "article_references": [ref.to_dict() for ref in references],
            "primary_article": primary_article,
            "has_definitions": has_definitions,
            "comma_count": comma_count,
        }

        logger.debug(
            "chunk_metadata_extracted",
            primary_article=primary_article,
            reference_count=len(references),
            comma_count=comma_count,
        )

        return metadata


# Singleton instance for convenience
article_extractor = ArticleExtractor()
