"""Citation grader for evaluating citation accuracy and hallucination.

Evaluates Step 64 of the LangGraph RAG pipeline - final response generation
with proper citations from retrieved documents.

Metrics:
- Hallucination rate: Fraction of citations not found in sources
- Valid citation ratio: Fraction of citations that are grounded
- Expected citation recall: Fraction of expected citations present
"""

import re
from dataclasses import dataclass
from typing import Any

from evals.schemas.test_case import GradeResult, TestCase


@dataclass
class CitationMatch:
    """Result of validating a citation against source documents.

    Attributes:
        citation_text: The citation text (e.g., "Legge 104/1992")
        found_in_sources: Whether the citation was found in source docs
        source_id: ID of the source document containing the citation
        is_hallucinated: Whether this is a hallucinated citation
    """

    citation_text: str
    found_in_sources: bool
    source_id: str | None
    is_hallucinated: bool


@dataclass
class CitationMetrics:
    """Metrics from citation evaluation.

    Attributes:
        hallucination_rate: Fraction of citations not grounded in sources
        valid_citation_ratio: Fraction of citations that are valid
        total_citations: Total number of citations in response
        valid_citations: Number of valid citations
        hallucinated_citations: Number of hallucinated citations
        citation_matches: Detailed match results for each citation
    """

    hallucination_rate: float
    valid_citation_ratio: float
    total_citations: int
    valid_citations: int
    hallucinated_citations: int
    citation_matches: list[CitationMatch]


# Italian legal citation patterns
ITALIAN_CITATION_PATTERNS = [
    r"Legge\s+\d+/\d{4}",  # Legge 104/1992
    r"L\.\s*\d+/\d{4}",  # L. 234/2021
    r"D\.Lgs\.\s*\d+/\d{4}",  # D.Lgs. 446/1997
    r"D\.L\.\s*\d+/\d{4}",  # D.L. 18/2020
    r"D\.P\.R\.\s*\d+/\d{4}",  # D.P.R. 633/1972
    r"D\.M\.\s*\d+/\d{4}",  # D.M. 123/2020
    r"Art\.\s*\d+(?:\s+comma\s+\d+)?(?:\s+(?:L\.|Legge|D\.Lgs\.)\s*\d+/\d{4})?",  # Art. 3 comma 2 L. 104/1992
    r"Circolare\s+(?:INPS|INAIL|ADE|Agenzia\s+Entrate)\s+n\.\s*\d+/\d{4}",  # Circolare INPS n. 12/2024
]


class CitationGrader:
    """Grader for evaluating citation accuracy.

    Evaluates:
    1. Hallucination rate - Are citations grounded in source documents?
    2. Valid citation ratio - What fraction of citations are valid?
    3. Expected citation recall - Are expected citations present?

    Score weighting:
    - Valid citation ratio: 50% (inverse of hallucination)
    - Expected citation recall: 30%
    - No hallucinations bonus: 20%
    """

    # Score weights
    VALID_RATIO_WEIGHT = 0.50
    RECALL_WEIGHT = 0.30
    NO_HALLUCINATION_BONUS = 0.20

    def grade(
        self,
        test_case: TestCase,
        response: dict[str, Any] | None,
        source_docs: list[dict[str, Any]] | None,
    ) -> GradeResult:
        """Grade citation accuracy in a response.

        Args:
            test_case: Test case with expected citations
            response: Response containing text and/or citations list
            source_docs: Source documents used for the response

        Returns:
            GradeResult with score, pass/fail, reasoning, and metrics
        """
        if response is None:
            return GradeResult(
                score=0.0,
                passed=False,
                reasoning="Response is missing.",
                metrics={
                    "hallucination_rate": 1.0,
                    "valid_citation_ratio": 0.0,
                    "total_citations": 0,
                    "valid_citations": 0,
                    "hallucinated_citations": 0,
                    "expected_citation_recall": 0.0,
                    "citation_matches": [],
                },
            )

        source_docs = source_docs or []

        # Extract citations from response
        citations = self._extract_citations(response)

        # Validate each citation against source documents
        metrics = self._compute_metrics(
            citations=citations,
            source_docs=source_docs,
            expected_citations=test_case.expected_citations,
        )

        score = self._compute_score(metrics, test_case.expected_citations)
        passed = score >= test_case.pass_threshold
        reasoning = self._generate_reasoning(metrics)

        return GradeResult(
            score=score,
            passed=passed,
            reasoning=reasoning,
            metrics={
                "hallucination_rate": metrics.hallucination_rate,
                "valid_citation_ratio": metrics.valid_citation_ratio,
                "total_citations": metrics.total_citations,
                "valid_citations": metrics.valid_citations,
                "hallucinated_citations": metrics.hallucinated_citations,
                "expected_citation_recall": getattr(metrics, "expected_citation_recall", 0.0),
                "citation_matches": [
                    {
                        "citation_text": m.citation_text,
                        "found_in_sources": m.found_in_sources,
                        "source_id": m.source_id,
                        "is_hallucinated": m.is_hallucinated,
                    }
                    for m in metrics.citation_matches
                ],
            },
        )

    def _extract_citations(self, response: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract citations from response.

        Looks for citations in:
        1. response["citations"] list
        2. Italian legal citation patterns in response["text"]

        Args:
            response: Response dictionary

        Returns:
            List of citation dicts with text and optional source_id
        """
        citations = []

        # Get explicit citations list
        explicit_citations = response.get("citations", [])
        citations.extend(explicit_citations)

        # Extract from text if no explicit citations
        text = response.get("text", "")
        if text and not explicit_citations:
            extracted = self._extract_citations_from_text(text)
            citations.extend(extracted)

        return citations

    def _extract_citations_from_text(self, text: str) -> list[dict[str, Any]]:
        """Extract Italian legal citation patterns from text.

        Args:
            text: Response text

        Returns:
            List of extracted citation dicts
        """
        citations = []
        seen = set()

        for pattern in ITALIAN_CITATION_PATTERNS:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                citation_text = match.group()
                normalized = citation_text.lower().strip()
                if normalized not in seen:
                    seen.add(normalized)
                    citations.append(
                        {
                            "text": citation_text,
                            "source_id": None,  # Unknown source
                        }
                    )

        return citations

    def _compute_metrics(
        self,
        citations: list[dict[str, Any]],
        source_docs: list[dict[str, Any]],
        expected_citations: list[str] | None,
    ) -> CitationMetrics:
        """Compute citation validation metrics.

        Args:
            citations: List of citations from response
            source_docs: Source documents
            expected_citations: Expected citations from test case

        Returns:
            CitationMetrics with validation results
        """
        if not citations:
            return CitationMetrics(
                hallucination_rate=0.0,
                valid_citation_ratio=1.0,  # No citations = no hallucinations
                total_citations=0,
                valid_citations=0,
                hallucinated_citations=0,
                citation_matches=[],
            )

        # Build searchable content from source docs
        source_content = self._build_source_content(source_docs)

        # Validate each citation
        citation_matches = []
        valid_count = 0
        hallucinated_count = 0

        for citation in citations:
            citation_text = citation.get("text", "")
            source_id = citation.get("source_id")

            # Check if citation is grounded in sources
            is_grounded = self._is_citation_grounded(
                citation_text=citation_text,
                source_id=source_id,
                source_content=source_content,
                source_docs=source_docs,
            )

            match = CitationMatch(
                citation_text=citation_text,
                found_in_sources=is_grounded,
                source_id=source_id if is_grounded else None,
                is_hallucinated=not is_grounded,
            )
            citation_matches.append(match)

            if is_grounded:
                valid_count += 1
            else:
                hallucinated_count += 1

        total = len(citations)
        hallucination_rate = hallucinated_count / total if total > 0 else 0.0
        valid_ratio = valid_count / total if total > 0 else 1.0

        metrics = CitationMetrics(
            hallucination_rate=hallucination_rate,
            valid_citation_ratio=valid_ratio,
            total_citations=total,
            valid_citations=valid_count,
            hallucinated_citations=hallucinated_count,
            citation_matches=citation_matches,
        )

        # Add expected citation recall if expected citations provided
        if expected_citations:
            recall = self._compute_expected_recall(citations, expected_citations)
            metrics.expected_citation_recall = recall  # type: ignore

        return metrics

    def _build_source_content(self, source_docs: list[dict[str, Any]]) -> dict[str, str]:
        """Build a mapping of source ID to lowercase content.

        Args:
            source_docs: List of source documents

        Returns:
            Dict mapping source ID to lowercase content
        """
        content_map = {}
        for doc in source_docs:
            doc_id = doc.get("id", "")
            content = doc.get("content", "")
            content_map[doc_id.lower()] = content.lower()
        return content_map

    def _is_citation_grounded(
        self,
        citation_text: str,
        source_id: str | None,
        source_content: dict[str, str],
        source_docs: list[dict[str, Any]],
    ) -> bool:
        """Check if a citation is grounded in source documents.

        Args:
            citation_text: The citation text
            source_id: Claimed source document ID
            source_content: Map of source ID to content
            source_docs: Original source documents

        Returns:
            True if citation is grounded, False if hallucinated
        """
        citation_lower = citation_text.lower()

        # If source_id is provided, check that specific source
        if source_id:
            source_id_lower = source_id.lower()
            if source_id_lower in source_content:
                content = source_content[source_id_lower]
                # Return whether citation appears in the claimed source
                return self._citation_in_content(citation_lower, content)

        # No source_id or source not found - search all sources
        return any(self._citation_in_content(citation_lower, content) for content in source_content.values())

    def _citation_in_content(self, citation: str, content: str) -> bool:
        """Check if a citation reference appears in content.

        Uses fuzzy matching for Italian legal citations, handling
        common format variations (e.g., "Legge 104/1992" vs "n. 104"
        + "1992", "c.c." vs "codice civile").

        Args:
            citation: Lowercase citation text
            content: Lowercase source content

        Returns:
            True if citation appears in content
        """
        # Direct substring match
        if citation in content:
            return True

        # Normalize and try again
        normalized_citation = self._normalize_citation(citation)
        normalized_content = self._normalize_citation(content)

        if normalized_citation in normalized_content:
            return True

        # Extract key identifiers (numbers, law types)
        # e.g., "legge 104/1992" -> check for "104/1992"
        numbers = re.findall(r"\d+/\d{4}", citation)
        if any(num in content for num in numbers):
            return True

        # Decomposed number matching: "104/1992" -> check both "104" and "1992"
        # Handles Italian format "n. 104" + "1992" in source content
        for num in numbers:
            law_num, year = num.split("/")
            if law_num in content and year in content:
                return True

        # Handle "c.c." / "codice civile" / "cod. civ." equivalence
        cc_variants = ("c.c.", "codice civile", "cod. civ.")
        citation_has_cc = any(v in citation for v in cc_variants)
        content_has_cc = any(v in content for v in cc_variants)
        if citation_has_cc and content_has_cc:
            # Extract article number and check if it appears in content
            art_match = re.search(r"art\.?\s*(\d+)", citation)
            if art_match and art_match.group(1) in content:
                return True

        # Handle standalone article references: "art. N" in both citation and content
        art_match = re.search(r"art\.?\s*(\d+)", citation)
        if art_match:
            art_pattern = rf"art\.?\s*{re.escape(art_match.group(1))}\b"
            if re.search(art_pattern, content):
                return True

        return False

    def _normalize_citation(self, text: str) -> str:
        """Normalize citation text for comparison.

        Args:
            text: Text to normalize

        Returns:
            Normalized text
        """
        # Remove extra spaces
        text = re.sub(r"\s+", " ", text)
        # Remove punctuation variations
        text = text.replace(".", "").replace(",", "")
        return text.strip()

    def _compute_expected_recall(
        self,
        citations: list[dict[str, Any]],
        expected_citations: list[str],
    ) -> float:
        """Compute recall of expected citations.

        Args:
            citations: Actual citations in response
            expected_citations: Expected citations from test case

        Returns:
            Recall score (0.0 to 1.0)
        """
        if not expected_citations:
            return 1.0

        actual_texts = {c.get("text", "").lower() for c in citations}
        found = 0

        for expected in expected_citations:
            expected_lower = expected.lower()
            # Check for exact or partial match
            for actual in actual_texts:
                if expected_lower in actual or actual in expected_lower:
                    found += 1
                    break

        return found / len(expected_citations)

    def _compute_score(
        self,
        metrics: CitationMetrics,
        expected_citations: list[str] | None,
    ) -> float:
        """Compute weighted score from metrics.

        Args:
            metrics: Computed citation metrics
            expected_citations: Expected citations (if any)

        Returns:
            Weighted score between 0.0 and 1.0
        """
        # Base score from valid citation ratio
        score = self.VALID_RATIO_WEIGHT * metrics.valid_citation_ratio

        # Add expected citation recall if applicable
        if expected_citations:
            recall = getattr(metrics, "expected_citation_recall", 0.0)
            score += self.RECALL_WEIGHT * recall
        else:
            # No expected citations - redistribute weight
            score += self.RECALL_WEIGHT * metrics.valid_citation_ratio

        # Bonus for no hallucinations
        if metrics.hallucination_rate == 0.0:
            score += self.NO_HALLUCINATION_BONUS

        return min(1.0, max(0.0, score))

    def _generate_reasoning(self, metrics: CitationMetrics) -> str:
        """Generate human-readable reasoning from metrics.

        Args:
            metrics: Computed citation metrics

        Returns:
            Reasoning string
        """
        parts = []

        if metrics.total_citations == 0:
            parts.append("No citations found in response")
        else:
            parts.append(f"{metrics.valid_citations}/{metrics.total_citations} citations valid")

        if metrics.hallucinated_citations > 0:
            parts.append(f"{metrics.hallucinated_citations} hallucinated citation(s) detected")

        if hasattr(metrics, "expected_citation_recall"):
            recall = getattr(metrics, "expected_citation_recall", 0.0)
            if recall < 1.0:
                parts.append(f"Expected citation recall: {recall:.0%}")

        return ". ".join(parts) + "."
