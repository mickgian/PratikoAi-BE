"""Italian Law Parser for Article-Level Ingestion (ADR-023).

Parses Italian legal documents (Leggi, Decreti, DPR) into structured
articles with cross-references and topic detection.

Handles:
- Article extraction (Art. 1, Art. 2, Art. 2-bis, ...)
- Comma extraction within articles
- Cross-references (comma 3 dell'articolo 12)
- Title/Capo structure
- Allegati (attachments/tables)

Usage:
    from app.services.italian_law_parser import ItalianLawParser

    parser = ItalianLawParser()
    result = parser.parse(law_text, "LEGGE 30 dicembre 2025, n. 199")
    for article in result.articles:
        print(f"{article.article_number}: {article.title}")
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger


@dataclass
class LawComma:
    """A single comma (paragraph) within an article.

    In Italian law, a "comma" is a numbered paragraph within an article.
    Example: "1. Il presente decreto entra in vigore..."
    """

    number: int
    text: str
    cross_references: list[str] = field(default_factory=list)


@dataclass
class LawArticle:
    """A parsed article from an Italian law.

    Attributes:
        article_number: Full article identifier (e.g., "Art. 1", "Art. 2-bis")
        article_number_int: Numeric part for sorting (1, 2, etc.)
        title: Article title if present (e.g., "Revisione dell'IRPEF")
        full_text: Complete article text including all commi
        commi: List of parsed commi (paragraphs)
        cross_references: References to other articles
        topics: Detected topics based on content
        titolo: Parent Titolo name if applicable
        capo: Parent Capo name if applicable
    """

    article_number: str
    article_number_int: int
    title: str | None
    full_text: str
    commi: list[LawComma]
    cross_references: list[str]
    topics: list[str]
    titolo: str | None
    capo: str | None

    @property
    def display_title(self) -> str:
        """Human-readable title for display and search."""
        if self.title:
            return f"{self.article_number} - {self.title}"
        return self.article_number


@dataclass
class ParsedLaw:
    """Complete parsed law structure.

    Attributes:
        title: Full law title (e.g., "LEGGE 30 dicembre 2025, n. 199")
        law_number: Extracted law number (e.g., "199/2025")
        publication_date: Extracted publication date if found
        articles: List of parsed articles
        allegati: List of allegati (attachments/tables)
        metadata: Additional parsing metadata
    """

    title: str
    law_number: str
    publication_date: str | None
    articles: list[LawArticle]
    allegati: list[dict[str, Any]]
    metadata: dict[str, Any]


class ItalianLawParser:
    """Parser for Italian legal document structure.

    Extracts structured content from Italian laws including:
    - Articles (Art. 1, Art. 2, Art. 2-bis, ...)
    - Commi (numbered paragraphs within articles)
    - Titoli and Capi (structural sections)
    - Cross-references between articles
    - Allegati (attachments/tables)

    Example:
        parser = ItalianLawParser(topic_keywords={"irpef": ["IRPEF", "aliquote"]})
        result = parser.parse(law_text, "LEGGE 30 dicembre 2025, n. 199")

        for article in result.articles:
            print(f"{article.display_title}")
            print(f"  Topics: {article.topics}")
            print(f"  Cross-refs: {article.cross_references}")
    """

    # Regex patterns for Italian law structure
    PATTERNS = {
        # Article start pattern - captures article number and optional title
        # Matches: "Art. 1", "Art. 2-bis", "Articolo 10", "ART. 1."
        # Note: Handles both line-start and mid-line patterns (for PDF extraction)
        "article_start": re.compile(
            r"(?:^|\n|\s{2,})(?:Art\.?|Articolo)\s*(\d+(?:-\w+)?)\s*[\.\-]?\s*[-–]?\s*([^\n]*)?",
            re.IGNORECASE | re.MULTILINE,
        ),
        # Alternative pattern for PDF-extracted text where articles appear mid-line
        # with distinctive "Art. N." pattern (period after number)
        "article_start_pdf": re.compile(
            r"Art\.\s*(\d+(?:-\w+)?)\.",
            re.IGNORECASE,
        ),
        # Comma pattern - matches numbered paragraphs
        # Matches: "1. Testo...", "2. Altro testo..."
        "comma": re.compile(
            r"(?:^|\n)\s*(\d+)\.\s+(.+?)(?=(?:^|\n)\s*\d+\.\s+|\Z)",
            re.MULTILINE | re.DOTALL,
        ),
        # Titolo pattern - major structural division
        # Matches: "Titolo I - NOME", "TITOLO II", "Titolo 1"
        "titolo": re.compile(
            r"(?:^|\n)\s*(?:TITOLO|Titolo)\s+([IVX]+|\d+)\s*[-–]?\s*([^\n]*)",
            re.IGNORECASE | re.MULTILINE,
        ),
        # Capo pattern - subdivision within Titolo
        # Matches: "Capo I - Nome", "CAPO II"
        "capo": re.compile(
            r"(?:^|\n)\s*(?:CAPO|Capo)\s+([IVX]+|\d+)\s*[-–]?\s*([^\n]*)",
            re.IGNORECASE | re.MULTILINE,
        ),
        # Cross-reference pattern
        # Matches: "articolo 12", "art. 3, comma 2", "articoli 1 e 2"
        "cross_ref": re.compile(
            r"(?:articol[oi]|art\.?)\s*(\d+(?:-\w+)?)" r"(?:\s*,?\s*(?:comma|commi)\s*(\d+(?:\s*[,e]\s*\d+)*))?",
            re.IGNORECASE,
        ),
        # Law number pattern - extracts number/year
        # Matches: "n. 199/2025", "n. 199 del 2025", "2025, n. 199", "numero 199"
        "law_number": re.compile(
            r"(?:n\.?\s*(\d+)(?:\s*/\s*|\s+del\s+)(\d{4})|(\d{4})[,\s]+n\.?\s*(\d+))",
            re.IGNORECASE,
        ),
        # Publication date pattern
        # Matches: "30 dicembre 2025", "15 gennaio 2024"
        "publication_date": re.compile(
            r"(\d{1,2})\s+(gennaio|febbraio|marzo|aprile|maggio|giugno|"
            r"luglio|agosto|settembre|ottobre|novembre|dicembre)\s+(\d{4})",
            re.IGNORECASE,
        ),
        # Allegati pattern
        # Matches: "ALLEGATO A", "Allegato 1", "ALLEGATI"
        "allegato": re.compile(
            r"(?:^|\n)\s*(?:ALLEGAT[OI]|Allegat[oi])\s*([A-Z]|\d+)?\s*[-–]?\s*([^\n]*)",
            re.IGNORECASE | re.MULTILINE,
        ),
    }

    def __init__(self, topic_keywords: dict[str, list[str]] | None = None):
        """Initialize the parser.

        Args:
            topic_keywords: Dict mapping topics to keywords for detection.
                If None, loads from config/document_tiers.yaml.
        """
        self._topic_keywords = topic_keywords or self._load_default_topics()

    def _load_default_topics(self) -> dict[str, list[str]]:
        """Load default topic keywords from config."""
        try:
            from pathlib import Path

            import yaml

            config_path = Path("config/document_tiers.yaml")
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)
                    return config.get("topic_keywords", {})
        except Exception as e:
            logger.warning(f"Could not load topic keywords from config: {e}")

        # Fallback to basic keywords
        return {
            "rottamazione": ["rottamazione", "definizione agevolata"],
            "irpef": ["IRPEF", "imposta sul reddito"],
            "iva": ["IVA", "imposta sul valore aggiunto"],
        }

    def parse(self, text: str, title: str) -> ParsedLaw:
        """Parse a complete Italian law into structured articles.

        Args:
            text: Full law text content
            title: Law title (e.g., "LEGGE 30 dicembre 2025, n. 199")

        Returns:
            ParsedLaw with articles, allegati, and metadata
        """
        logger.info(
            "italian_law_parser_start",
            title=title[:100],
            text_length=len(text),
        )

        # Extract law number from title or text
        law_number = self._extract_law_number(title, text)

        # Extract publication date
        publication_date = self._extract_publication_date(title, text)

        # Parse structural elements (Titoli, Capi)
        structure = self._parse_structure(text)

        # Parse articles
        articles = self._parse_articles(text, structure)

        # Parse allegati
        allegati = self._parse_allegati(text)

        logger.info(
            "italian_law_parser_complete",
            title=title[:100],
            law_number=law_number,
            articles_found=len(articles),
            allegati_found=len(allegati),
        )

        return ParsedLaw(
            title=title,
            law_number=law_number,
            publication_date=publication_date,
            articles=articles,
            allegati=allegati,
            metadata={
                "structure": structure,
                "text_length": len(text),
                "titoli_count": len(structure.get("titoli", [])),
                "capi_count": len(structure.get("capi", [])),
            },
        )

    def _extract_law_number(self, title: str, text: str) -> str:
        """Extract law number like '199/2025' from title or text."""
        # Try title first (most reliable)
        match = self.PATTERNS["law_number"].search(title)
        if match:
            # Pattern has two alternatives:
            # Groups 1,2: "n. 199/2025" or "n. 199 del 2025"
            # Groups 3,4: "2025, n. 199"
            if match.group(1) and match.group(2):
                return f"{match.group(1)}/{match.group(2)}"
            elif match.group(3) and match.group(4):
                return f"{match.group(4)}/{match.group(3)}"

        # Try beginning of text (first 1000 chars)
        match = self.PATTERNS["law_number"].search(text[:1000])
        if match:
            if match.group(1) and match.group(2):
                return f"{match.group(1)}/{match.group(2)}"
            elif match.group(3) and match.group(4):
                return f"{match.group(4)}/{match.group(3)}"

        return "unknown"

    def _extract_publication_date(self, title: str, text: str) -> str | None:
        """Extract publication date from title or text."""
        # Try title first
        match = self.PATTERNS["publication_date"].search(title)
        if match:
            day, month, year = match.groups()
            return f"{day} {month} {year}"

        # Try beginning of text
        match = self.PATTERNS["publication_date"].search(text[:500])
        if match:
            day, month, year = match.groups()
            return f"{day} {month} {year}"

        return None

    def _parse_structure(self, text: str) -> dict[str, list[dict]]:
        """Parse Titoli and Capi structure from the law text.

        Returns:
            Dict with 'titoli' and 'capi' lists, each containing
            number, title, and position information.
        """
        structure: dict[str, list[dict]] = {
            "titoli": [],
            "capi": [],
        }

        # Find all Titoli
        for match in self.PATTERNS["titolo"].finditer(text):
            structure["titoli"].append(
                {
                    "number": match.group(1),
                    "title": match.group(2).strip() if match.group(2) else "",
                    "position": match.start(),
                }
            )

        # Find all Capi
        for match in self.PATTERNS["capo"].finditer(text):
            structure["capi"].append(
                {
                    "number": match.group(1),
                    "title": match.group(2).strip() if match.group(2) else "",
                    "position": match.start(),
                }
            )

        return structure

    def _parse_articles(
        self,
        text: str,
        structure: dict[str, list[dict]],
    ) -> list[LawArticle]:
        """Parse all articles from the law text.

        Args:
            text: Full law text
            structure: Parsed Titoli/Capi structure

        Returns:
            List of LawArticle objects sorted by article number
        """
        articles = []

        # Find all article start positions - try primary pattern first
        article_matches = list(self.PATTERNS["article_start"].finditer(text))

        # If no matches, try PDF-specific pattern (for PDF-extracted text)
        if not article_matches:
            logger.info("italian_law_parser_trying_pdf_pattern", text_length=len(text))
            article_matches = list(self.PATTERNS["article_start_pdf"].finditer(text))

        if not article_matches:
            logger.warning("italian_law_parser_no_articles", text_length=len(text))
            return articles

        logger.info(
            "italian_law_parser_articles_found",
            count=len(article_matches),
            pattern_used="pdf" if not list(self.PATTERNS["article_start"].finditer(text)) else "standard",
        )

        for i, match in enumerate(article_matches):
            # Determine article text boundaries
            start = match.start()
            if i + 1 < len(article_matches):
                end = article_matches[i + 1].start()
            else:
                end = len(text)

            # Check for allegati within article range and truncate if needed
            allegato_match = self.PATTERNS["allegato"].search(text[start:end])
            if allegato_match:
                end = start + allegato_match.start()

            article_text = text[start:end].strip()

            # Skip very short matches (likely false positives)
            if len(article_text) < 30:
                continue

            # Extract article number and title
            article_number = match.group(1)
            # PDF pattern only has 1 group, standard pattern has 2
            try:
                article_title = match.group(2).strip() if match.lastindex >= 2 and match.group(2) else None
            except IndexError:
                article_title = None

            # Clean up article title (remove artifacts)
            if article_title:
                # Remove leading dashes, dots, or parentheses
                article_title = re.sub(r"^[-–.\s(]+", "", article_title)
                # Remove trailing artifacts
                article_title = re.sub(r"[-–.\s)]+$", "", article_title)
                # If it's too short or looks like continuation, set to None
                if len(article_title) < 3 or article_title.isdigit():
                    article_title = None

            # For PDF patterns, try to extract title from parentheses in article text
            # Italian law article titles often appear as: "Art. 1. (Title here)"
            if not article_title:
                title_in_parens = re.search(r"\(([A-Z][^)]{5,100})\)", article_text[:500])
                if title_in_parens:
                    article_title = title_in_parens.group(1).strip()

            # Parse commi within article
            commi = self._parse_commi(article_text)

            # Extract cross-references
            cross_refs = self._extract_cross_references(article_text)

            # Detect topics
            topics = self._detect_topics(article_text)

            # Find parent Titolo and Capo
            titolo, capo = self._find_parent_structure(start, structure)

            articles.append(
                LawArticle(
                    article_number=f"Art. {article_number}",
                    article_number_int=self._parse_article_int(article_number),
                    title=article_title,
                    full_text=article_text,
                    commi=commi,
                    cross_references=cross_refs,
                    topics=topics,
                    titolo=titolo,
                    capo=capo,
                )
            )

        # Sort by article number
        articles.sort(key=lambda a: (a.article_number_int, a.article_number))

        return articles

    def _parse_commi(self, article_text: str) -> list[LawComma]:
        """Parse individual commi (paragraphs) from article text.

        Args:
            article_text: Text of a single article

        Returns:
            List of LawComma objects
        """
        commi = []

        for match in self.PATTERNS["comma"].finditer(article_text):
            comma_num = int(match.group(1))
            comma_text = match.group(2).strip()

            # Extract cross-references within this comma
            cross_refs = self._extract_cross_references(comma_text)

            commi.append(
                LawComma(
                    number=comma_num,
                    text=comma_text,
                    cross_references=cross_refs,
                )
            )

        return commi

    def _extract_cross_references(self, text: str) -> list[str]:
        """Extract cross-references to other articles.

        Args:
            text: Text to search for references

        Returns:
            List of unique references like "Art. 12, comma 3"
        """
        refs = []

        for match in self.PATTERNS["cross_ref"].finditer(text):
            article = match.group(1)
            commi = match.group(2)

            if commi:
                refs.append(f"Art. {article}, comma {commi}")
            else:
                refs.append(f"Art. {article}")

        return list(set(refs))

    def _detect_topics(self, text: str) -> list[str]:
        """Detect topics from article text based on keyword matching.

        Args:
            text: Article text to analyze

        Returns:
            List of detected topic names
        """
        text_lower = text.lower()
        detected = []

        for topic, keywords in self._topic_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    detected.append(topic)
                    break

        return list(set(detected))

    def _find_parent_structure(
        self,
        position: int,
        structure: dict[str, list[dict]],
    ) -> tuple[str | None, str | None]:
        """Find parent Titolo and Capo for an article at given position.

        Args:
            position: Character position of the article in text
            structure: Parsed structure with titoli and capi

        Returns:
            Tuple of (titolo_name, capo_name) or None values
        """
        titolo = None
        capo = None

        # Find closest preceding Titolo
        for t in reversed(structure.get("titoli", [])):
            if t["position"] < position:
                titolo = f"Titolo {t['number']} - {t['title']}" if t["title"] else f"Titolo {t['number']}"
                break

        # Find closest preceding Capo
        for c in reversed(structure.get("capi", [])):
            if c["position"] < position:
                capo = f"Capo {c['number']} - {c['title']}" if c["title"] else f"Capo {c['number']}"
                break

        return titolo, capo

    def _parse_article_int(self, article_number: str) -> int:
        """Parse article number to int for sorting.

        Handles variants like "2-bis", "2-ter", "10" etc.

        Args:
            article_number: String article number

        Returns:
            Integer for sorting (base number only)
        """
        match = re.match(r"(\d+)", article_number)
        if match:
            return int(match.group(1))
        return 0

    def _parse_allegati(self, text: str) -> list[dict[str, Any]]:
        """Parse allegati (attachments/tables) from the law text.

        Args:
            text: Full law text

        Returns:
            List of allegato dictionaries with id, title, position
        """
        allegati = []

        for match in self.PATTERNS["allegato"].finditer(text):
            allegato_id = match.group(1) or "A"
            allegato_title = match.group(2).strip() if match.group(2) else ""

            allegati.append(
                {
                    "id": allegato_id,
                    "title": allegato_title,
                    "position": match.start(),
                }
            )

        return allegati
