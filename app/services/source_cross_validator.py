"""SourceCrossValidator service for validating LLM source citations.

DEV-242: Validates that sources cited by LLM exist in KB and flags
when no KB sources are available (requiring web search fallback).
"""

import re
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger


@dataclass
class SourceValidationResult:
    """Result of validating a single source citation."""

    is_valid: bool
    matched_kb_doc: dict | None = None
    warning: str | None = None


@dataclass
class CrossValidationResult:
    """Result of cross-validating all sources in a response."""

    is_valid: bool
    validated_sources: list[dict]  # Sources that matched KB
    unmatched_sources: list[dict]  # Sources not found in KB
    warnings: list[str] = field(default_factory=list)
    requires_web_fallback: bool = False
    kb_was_empty: bool = False


class SourceCrossValidator:
    """Validates LLM source citations against KB sources.

    DEV-242: Implements cross-validation to ensure:
    1. Cited sources actually exist in KB context
    2. Dates and references match KB documents
    3. When KB is empty, flags for web search fallback
    """

    def validate_sources(
        self,
        sources_cited: list[dict],
        kb_sources_metadata: list[dict],
        response_text: str | None = None,
    ) -> CrossValidationResult:
        """Cross-validate sources cited against KB sources metadata.

        Args:
            sources_cited: List of source dicts from LLM response
            kb_sources_metadata: List of KB source metadata dicts
            response_text: Optional response text for context

        Returns:
            CrossValidationResult with validation status and warnings
        """
        warnings: list[str] = []
        validated_sources: list[dict] = []
        unmatched_sources: list[dict] = []

        # Check if KB is empty
        kb_was_empty = not kb_sources_metadata or len(kb_sources_metadata) == 0
        if kb_was_empty:
            logger.warning(
                "source_validation_kb_empty",
                sources_cited_count=len(sources_cited) if sources_cited else 0,
            )
            warnings.append(
                "Nessun documento ufficiale trovato nel database. "
                "Le informazioni potrebbero richiedere verifica con fonti aggiornate."
            )

        # If no sources cited, that's okay if KB was empty
        if not sources_cited:
            return CrossValidationResult(
                is_valid=kb_was_empty,  # Valid only if KB was also empty
                validated_sources=[],
                unmatched_sources=[],
                warnings=warnings,
                requires_web_fallback=kb_was_empty,
                kb_was_empty=kb_was_empty,
            )

        # Validate each cited source
        for source in sources_cited:
            result = self._validate_single_source(source, kb_sources_metadata)
            if result.is_valid:
                validated_sources.append(source)
            else:
                unmatched_sources.append(source)
                if result.warning:
                    warnings.append(result.warning)

        # Log validation results
        logger.info(
            "source_cross_validation_complete",
            total_cited=len(sources_cited),
            validated_count=len(validated_sources),
            unmatched_count=len(unmatched_sources),
            kb_was_empty=kb_was_empty,
        )

        # Determine overall validity
        # Invalid if: KB had sources but none matched, OR all sources are unmatched
        all_unmatched = len(validated_sources) == 0 and len(sources_cited) > 0
        is_valid = not (all_unmatched and not kb_was_empty)

        return CrossValidationResult(
            is_valid=is_valid,
            validated_sources=validated_sources,
            unmatched_sources=unmatched_sources,
            warnings=warnings,
            requires_web_fallback=kb_was_empty or all_unmatched,
            kb_was_empty=kb_was_empty,
        )

    def _validate_single_source(
        self,
        source: dict,
        kb_sources: list[dict],
    ) -> SourceValidationResult:
        """Validate a single source citation against KB sources.

        Args:
            source: Source dict with 'ref' field
            kb_sources: List of KB source metadata dicts

        Returns:
            SourceValidationResult with match status
        """
        source_ref = source.get("ref", "")
        if not source_ref:
            return SourceValidationResult(
                is_valid=False,
                warning="Fonte citata senza riferimento",
            )

        # Extract key components from source reference
        ref_components = self._extract_ref_components(source_ref)

        # Try to match against KB sources
        for kb_source in kb_sources:
            if self._matches_kb_source(ref_components, kb_source):
                return SourceValidationResult(
                    is_valid=True,
                    matched_kb_doc=kb_source,
                )

        # No match found
        return SourceValidationResult(
            is_valid=False,
            warning=f"Fonte '{source_ref[:50]}' non trovata nel contesto KB",
        )

    def _extract_ref_components(self, ref: str) -> dict[str, Any]:
        """Extract components from a source reference string.

        Args:
            ref: Reference string like "Art. 16 DPR 633/72"

        Returns:
            Dict with extracted components (article, law_type, number, year)
        """
        components: dict[str, Any] = {"original": ref}

        # Extract article number
        article_match = re.search(r"Art\.?\s*(\d+)", ref, re.IGNORECASE)
        if article_match:
            components["article"] = article_match.group(1)

        # Extract law type (DPR, D.Lgs, Legge, etc.)
        law_types = ["DPR", "D\\.Lgs\\.?", "Legge", "L\\.", "D\\.L\\.", "TUIR", "TUS"]
        for law_type in law_types:
            if re.search(law_type, ref, re.IGNORECASE):
                components["law_type"] = law_type.replace("\\.", ".").replace("\\", "")
                break

        # Extract law number
        number_match = re.search(r"(?:n\.?\s*)?(\d+)/(\d{2,4})", ref)
        if number_match:
            components["law_number"] = number_match.group(1)
            components["year"] = number_match.group(2)

        # Extract year from various formats
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", ref)
        if year_match and "year" not in components:
            components["year"] = year_match.group(1)

        # Extract circolare/comunicato references
        circ_match = re.search(r"Circolare.*?n\.?\s*(\d+)[/E]*", ref, re.IGNORECASE)
        if circ_match:
            components["circolare_number"] = circ_match.group(1)
            components["is_circolare"] = True

        return components

    def _matches_kb_source(
        self,
        ref_components: dict[str, Any],
        kb_source: dict,
    ) -> bool:
        """Check if reference components match a KB source.

        Args:
            ref_components: Extracted components from source reference
            kb_source: KB source metadata dict

        Returns:
            True if components match the KB source
        """
        kb_title = kb_source.get("title", "").lower()
        kb_ref = kb_source.get("reference", "").lower()
        kb_type = kb_source.get("doc_type", "").lower()
        original_ref = ref_components.get("original", "").lower()

        # Direct title/reference match
        if original_ref in kb_title or original_ref in kb_ref:
            return True

        # Match by law number and year
        law_number = ref_components.get("law_number")
        year = ref_components.get("year")
        if law_number and year:
            pattern = f"{law_number}/{year}"
            if pattern in kb_title or pattern in kb_ref:
                return True

        # Match by article reference in content
        article = ref_components.get("article")
        if article:
            article_pattern = f"art.? {article}"
            if re.search(article_pattern, kb_title, re.IGNORECASE):
                return True
            if re.search(article_pattern, kb_ref, re.IGNORECASE):
                return True

        # Match circolari
        if ref_components.get("is_circolare"):
            circ_num = ref_components.get("circolare_number")
            if circ_num and "circolare" in kb_type:
                if circ_num in kb_title or circ_num in kb_ref:
                    return True

        # Match key topics
        key_topics = kb_source.get("key_topics", [])
        for topic in key_topics:
            if topic.lower() in original_ref:
                return True

        return False

    def validate_dates_in_response(
        self,
        response_text: str,
        kb_sources: list[dict],
        current_year: int,
    ) -> list[str]:
        """Validate dates mentioned in response against KB sources.

        DEV-242: Detect potentially hallucinated dates not grounded in KB.

        Args:
            response_text: LLM response text
            kb_sources: KB source metadata
            current_year: Current year for context

        Returns:
            List of warnings about suspicious dates
        """
        warnings: list[str] = []

        # Extract all years from response
        years_in_response = set(re.findall(r"\b(19\d{2}|20\d{2})\b", response_text))

        # Extract years from KB sources
        kb_years: set[str] = set()
        for source in kb_sources:
            title = source.get("title", "")
            ref = source.get("reference", "")
            kb_years.update(re.findall(r"\b(19\d{2}|20\d{2})\b", f"{title} {ref}"))

        # Flag suspicious years (in response but not in KB and not current/next year)
        for year in years_in_response:
            year_int = int(year)
            # Allow current year, next year, and previous year
            if abs(year_int - current_year) <= 1:
                continue
            # Check if year is grounded in KB
            if year not in kb_years:
                warnings.append(
                    f"Anno {year} menzionato nella risposta ma non presente nelle fonti KB - verificare accuratezza"
                )

        return warnings


# Singleton instance
source_cross_validator = SourceCrossValidator()
