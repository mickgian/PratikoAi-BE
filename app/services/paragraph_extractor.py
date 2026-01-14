"""Paragraph Extractor Service (DEV-237).

Extracts and scores relevant paragraphs from retrieved documents for
paragraph-level grounding in suggested actions.

This service:
1. Splits documents into paragraphs
2. Scores relevance of each paragraph to the user query
3. Returns the most relevant paragraphs with metadata

Coverage Target: 90%+ for new code.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Paragraph:
    """A paragraph extracted from a document."""

    text: str
    index: int


@dataclass
class ParagraphResult:
    """Result of paragraph extraction with relevance scoring."""

    paragraph_id: str
    paragraph_index: int
    relevance_score: float
    excerpt: str
    full_text: str

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "paragraph_id": self.paragraph_id,
            "paragraph_index": self.paragraph_index,
            "relevance_score": self.relevance_score,
            "excerpt": self.excerpt,
            "full_text": self.full_text,
        }


class ParagraphExtractor:
    """Extracts and scores relevant paragraphs from documents.

    This service provides functionality for:
    - Splitting documents into paragraphs
    - Scoring paragraph relevance to a query
    - Extracting the best matching paragraphs

    Example:
        extractor = ParagraphExtractor()
        result = extractor.extract_best_paragraph(
            content="Document text...",
            query="aliquota IVA 22%",
            doc_id="doc_001"
        )
    """

    # Maximum excerpt length for tooltips
    MAX_EXCERPT_LENGTH = 200

    def split_paragraphs(
        self,
        content: str | None,
        min_length: int = 0,
    ) -> list[Paragraph]:
        """Split document content into paragraphs.

        Args:
            content: The document text to split
            min_length: Minimum paragraph length to include (default: 0)

        Returns:
            List of Paragraph objects with text and index
        """
        if not content:
            return []

        # Split by double newlines (paragraph breaks)
        raw_paragraphs = re.split(r"\n\n+", content)

        paragraphs = []
        for i, text in enumerate(raw_paragraphs):
            text = text.strip()
            if not text:
                continue

            # Filter by minimum length if specified
            if min_length > 0 and len(text) < min_length:
                continue

            paragraphs.append(Paragraph(text=text, index=i))

        # Re-index paragraphs after filtering
        for new_index, para in enumerate(paragraphs):
            para.index = new_index

        return paragraphs

    def score_relevance(self, paragraph: str, query: str) -> float:
        """Score the relevance of a paragraph to a query.

        Uses term overlap scoring normalized to 0-1 range.

        Args:
            paragraph: The paragraph text
            query: The user query

        Returns:
            Relevance score between 0.0 and 1.0
        """
        if not paragraph or not query:
            return 0.0

        # Normalize to lowercase for matching
        para_lower = paragraph.lower()
        query_lower = query.lower()

        # Extract query terms (words)
        query_terms = set(re.findall(r"\b\w+\b", query_lower))
        if not query_terms:
            return 0.0

        # Count matching terms
        matches = sum(1 for term in query_terms if term in para_lower)

        # Normalize to 0-1 range
        score = matches / len(query_terms)
        return min(1.0, max(0.0, score))

    def extract_best_paragraph(
        self,
        content: str | None,
        query: str,
        doc_id: str,
    ) -> ParagraphResult | None:
        """Extract the most relevant paragraph from content.

        Args:
            content: The document text
            query: The user query for relevance scoring
            doc_id: Document ID for generating paragraph_id

        Returns:
            ParagraphResult with best matching paragraph, or None if empty
        """
        if not content:
            return None

        paragraphs = self.split_paragraphs(content)
        if not paragraphs:
            return None

        # Score each paragraph
        scored = [(para, self.score_relevance(para.text, query)) for para in paragraphs]

        # Find best match
        best_para, best_score = max(scored, key=lambda x: x[1])

        return ParagraphResult(
            paragraph_id=f"{doc_id}_p{best_para.index}",
            paragraph_index=best_para.index,
            relevance_score=best_score,
            excerpt=self._truncate_excerpt(best_para.text),
            full_text=best_para.text,
        )

    def extract_top_paragraphs(
        self,
        content: str | None,
        query: str,
        doc_id: str,
        top_n: int = 3,
    ) -> list[ParagraphResult]:
        """Extract the top N most relevant paragraphs.

        Args:
            content: The document text
            query: The user query for relevance scoring
            doc_id: Document ID for generating paragraph_ids
            top_n: Number of top paragraphs to return

        Returns:
            List of ParagraphResult sorted by relevance descending
        """
        if not content:
            return []

        paragraphs = self.split_paragraphs(content)
        if not paragraphs:
            return []

        # Score each paragraph
        scored = [(para, self.score_relevance(para.text, query)) for para in paragraphs]

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        results = []
        for para, score in scored[:top_n]:
            results.append(
                ParagraphResult(
                    paragraph_id=f"{doc_id}_p{para.index}",
                    paragraph_index=para.index,
                    relevance_score=score,
                    excerpt=self._truncate_excerpt(para.text),
                    full_text=para.text,
                )
            )

        return results

    def _truncate_excerpt(self, text: str) -> str:
        """Truncate text to max excerpt length with ellipsis.

        Args:
            text: The text to truncate

        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= self.MAX_EXCERPT_LENGTH:
            return text

        # Truncate at word boundary
        truncated = text[: self.MAX_EXCERPT_LENGTH]
        last_space = truncated.rfind(" ")
        if last_space > self.MAX_EXCERPT_LENGTH * 0.7:
            truncated = truncated[:last_space]

        return truncated + "..."
