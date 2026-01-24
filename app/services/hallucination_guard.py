"""Hallucination Guard Service for DEV-245.

Validates that law citations in LLM responses actually exist in the KB context.
This prevents the LLM from hallucinating non-existent laws like "Legge 197/2022".

Usage:
    from app.services.hallucination_guard import HallucinationGuard

    guard = HallucinationGuard()
    result = guard.validate_citations(response_text, kb_context)

    if result.has_hallucinations:
        logger.warning(f"Hallucinated citations: {result.hallucinated}")
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger

# Regex patterns for Italian law citations
# Matches patterns like:
# - "Legge n. 199/2025", "Legge 199/2025", "L. 199/2025"
# - "Legge 30 dicembre 2025 n. 199" (full date format)
# - "D.Lgs. 81/2008", "D.Lgs. n. 81/2008", "Decreto Legislativo 81/2008"
# - "DPR 633/72", "D.P.R. 633/1972"
# - "Art. 16", "Art. 1, comma 231"
LAW_CITATION_PATTERNS = [
    # Legge patterns with number/year format
    r"[Ll]egge\s+(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}",
    r"L\.\s*\d{1,4}[/\-]\d{2,4}",
    # Legge patterns with full date format (e.g., "Legge 30 dicembre 2025 n. 199")
    r"[Ll]egge\s+\d{1,2}\s+\w+\s+\d{4}[,]?\s*n\.\s*\d{1,4}",
    # Decreto Legislativo patterns
    r"D\.?\s*Lgs\.?\s*(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}",
    r"[Dd]ecreto\s+[Ll]egislativo\s+(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}",
    # DPR patterns
    r"D\.?P\.?R\.?\s*(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}",
    r"[Dd]ecreto\s+del\s+[Pp]residente\s+della\s+[Rr]epubblica\s+(?:n\.\s*)?\d{1,4}[/\-]\d{2,4}",
    # Circolare patterns
    r"[Cc]ircolare\s+(?:AdE\s+)?(?:n\.\s*)?\d{1,4}[/\-]?[A-Z]?\s*(?:del\s+)?\d{2,4}",
    # Generic law number pattern (for cross-reference)
    r"(?:della\s+)?[Ll]egge\s+di\s+[Bb]ilancio\s+\d{4}",
]

# Combined pattern for extraction
COMBINED_LAW_PATTERN = re.compile("|".join(f"({p})" for p in LAW_CITATION_PATTERNS), re.IGNORECASE)

# Pattern to normalize citations for comparison
NORMALIZE_PATTERN = re.compile(r"[^a-z0-9/]", re.IGNORECASE)


@dataclass
class CitationValidationResult:
    """Result of citation validation."""

    # Citations found in the response
    extracted_citations: list[str] = field(default_factory=list)

    # Citations that exist in the KB context
    valid_citations: list[str] = field(default_factory=list)

    # Citations that do NOT exist in the KB context (potential hallucinations)
    hallucinated_citations: list[str] = field(default_factory=list)

    # Citations in the KB context (for reference)
    context_citations: list[str] = field(default_factory=list)

    @property
    def has_hallucinations(self) -> bool:
        """Check if any hallucinated citations were found."""
        return len(self.hallucinated_citations) > 0

    @property
    def hallucination_rate(self) -> float:
        """Calculate the hallucination rate (0.0 to 1.0)."""
        if not self.extracted_citations:
            return 0.0
        return len(self.hallucinated_citations) / len(self.extracted_citations)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        return {
            "extracted_citations": self.extracted_citations,
            "valid_citations": self.valid_citations,
            "hallucinated_citations": self.hallucinated_citations,
            "context_citations": self.context_citations,
            "has_hallucinations": self.has_hallucinations,
            "hallucination_rate": self.hallucination_rate,
        }


class HallucinationGuard:
    """Service to detect hallucinated law citations in LLM responses.

    This service extracts law citations from LLM responses and validates
    them against the KB context that was provided to the LLM.

    Example:
        guard = HallucinationGuard()
        result = guard.validate_citations(
            response_text="La rottamazione è disciplinata dalla Legge 197/2022...",
            kb_context="...Legge n. 199/2025 disciplina la definizione agevolata..."
        )

        if result.has_hallucinations:
            # "Legge 197/2022" would be flagged as hallucinated
            # because only "Legge 199/2025" exists in context
    """

    def __init__(self, strict_mode: bool = False):
        """Initialize the hallucination guard.

        Args:
            strict_mode: If True, only exact matches count as valid.
                        If False (default), normalized matches are accepted.
        """
        self._strict_mode = strict_mode

    def extract_citations(self, text: str) -> list[str]:
        """Extract law citations from text.

        Args:
            text: Text to extract citations from

        Returns:
            List of unique citations found
        """
        if not text:
            return []

        matches = COMBINED_LAW_PATTERN.findall(text)

        # Flatten matches (each match is a tuple of groups)
        citations = []
        for match in matches:
            # Get the non-empty group from the match tuple
            citation = next((g for g in match if g), None)
            if citation and citation not in citations:
                citations.append(citation)

        return citations

    def _normalize_citation(self, citation: str) -> str:
        """Normalize a citation for comparison.

        Removes punctuation and extra spaces, lowercases, and extracts
        the core number/year pattern.

        Args:
            citation: Citation string to normalize

        Returns:
            Normalized citation string
        """
        # Remove common prefixes and normalize
        normalized = citation.lower()

        # Extract just the number/year part for comparison
        # e.g., "Legge n. 199/2025" -> "199/2025"
        number_match = re.search(r"(\d{1,4})[/\-](\d{2,4})", normalized)
        if number_match:
            num, year = number_match.groups()
            # Normalize 2-digit years to 4-digit
            if len(year) == 2:
                year = "20" + year if int(year) < 50 else "19" + year
            return f"{num}/{year}"

        # Handle full date format: "Legge 30 dicembre 2025 n. 199" -> "199/2025"
        full_date_match = re.search(r"(\d{4})[,]?\s*n\.\s*(\d{1,4})", normalized)
        if full_date_match:
            year, num = full_date_match.groups()
            return f"{num}/{year}"

        # For citations without year (like "Art. 16"), keep more context
        return NORMALIZE_PATTERN.sub("", normalized)

    def _citation_exists_in_context(self, citation: str, context: str, context_citations: list[str]) -> bool:
        """Check if a citation exists in the KB context.

        Args:
            citation: Citation to check
            context: Full KB context text
            context_citations: Pre-extracted citations from context

        Returns:
            True if citation exists in context
        """
        if self._strict_mode:
            # Strict mode: citation must appear exactly in context
            return citation in context

        # Normalized comparison
        normalized_citation = self._normalize_citation(citation)

        # Check against extracted context citations
        for ctx_citation in context_citations:
            if self._normalize_citation(ctx_citation) == normalized_citation:
                return True

        # Also check if the number pattern appears in context
        # This handles cases where the format differs slightly
        if normalized_citation in context.lower():
            return True

        # Check for the number/year pattern in context
        number_match = re.search(r"(\d{1,4})[/\-](\d{2,4})", normalized_citation)
        if number_match:
            pattern = f"{number_match.group(1)}/{number_match.group(2)}"
            alt_pattern = f"{number_match.group(1)}-{number_match.group(2)}"
            if pattern in context or alt_pattern in context:
                return True

        return False

    def validate_citations(
        self,
        response_text: str,
        kb_context: str,
    ) -> CitationValidationResult:
        """Validate law citations in a response against KB context.

        Args:
            response_text: The LLM-generated response text
            kb_context: The KB context that was provided to the LLM

        Returns:
            CitationValidationResult with validation details
        """
        result = CitationValidationResult()

        # Extract citations from both response and context
        result.extracted_citations = self.extract_citations(response_text)
        result.context_citations = self.extract_citations(kb_context)

        if not result.extracted_citations:
            # No citations to validate
            logger.debug(
                "hallucination_guard_no_citations",
                response_length=len(response_text),
            )
            return result

        # Validate each extracted citation
        for citation in result.extracted_citations:
            if self._citation_exists_in_context(citation, kb_context, result.context_citations):
                result.valid_citations.append(citation)
            else:
                result.hallucinated_citations.append(citation)

        # Log the validation result
        if result.has_hallucinations:
            logger.warning(
                "DEV245_hallucination_detected",
                hallucinated_citations=result.hallucinated_citations,
                valid_citations=result.valid_citations,
                context_citations=result.context_citations,
                hallucination_rate=result.hallucination_rate,
            )
        else:
            logger.info(
                "DEV245_citations_validated",
                citation_count=len(result.extracted_citations),
                all_valid=True,
            )

        return result

    def get_correction_suggestion(self, result: CitationValidationResult) -> str | None:
        """Get a suggestion for correcting hallucinated citations.

        Args:
            result: Validation result with hallucinations

        Returns:
            Suggestion string or None if no hallucinations
        """
        if not result.has_hallucinations:
            return None

        suggestions = []
        for hallucinated in result.hallucinated_citations:
            # Find the most similar context citation
            best_match = self._find_similar_citation(hallucinated, result.context_citations)
            if best_match:
                suggestions.append(f"'{hallucinated}' → '{best_match}'")
            else:
                suggestions.append(f"'{hallucinated}' → (rimuovere o usare 'normativa vigente')")

        return "; ".join(suggestions)

    def _find_similar_citation(self, citation: str, context_citations: list[str]) -> str | None:
        """Find the most similar citation in context.

        Args:
            citation: Hallucinated citation
            context_citations: Citations found in context

        Returns:
            Most similar context citation or None
        """
        if not context_citations:
            return None

        normalized = self._normalize_citation(citation)

        # Look for citations with similar numbers but different years
        # e.g., "197/2022" vs "199/2025"
        for ctx_citation in context_citations:
            ctx_normalized = self._normalize_citation(ctx_citation)

            # Check if they share the same type (Legge, D.Lgs., etc.)
            citation_type = self._extract_citation_type(citation)
            ctx_type = self._extract_citation_type(ctx_citation)

            if citation_type and ctx_type and citation_type.lower() == ctx_type.lower():
                return ctx_citation

        # Return the first context citation as a fallback
        return context_citations[0] if context_citations else None

    def _extract_citation_type(self, citation: str) -> str | None:
        """Extract the type of law citation (Legge, D.Lgs., etc.).

        Args:
            citation: Citation string

        Returns:
            Citation type or None
        """
        lower = citation.lower()
        if "legge" in lower or lower.startswith("l."):
            return "Legge"
        elif "d.lgs" in lower or "decreto legislativo" in lower:
            return "D.Lgs."
        elif "dpr" in lower or "d.p.r" in lower or "decreto del presidente" in lower:
            return "DPR"
        elif "circolare" in lower:
            return "Circolare"
        return None


# Singleton instance for convenience
hallucination_guard = HallucinationGuard()
