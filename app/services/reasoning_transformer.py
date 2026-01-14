"""ReasoningTransformer Service for Italian User-Friendly Explanations (DEV-230).

This service transforms internal technical reasoning into user-friendly
Italian explanations suitable for display to end users.

The transformation includes:
- Confidence score mapping to Italian labels (alta, media, bassa)
- Source reference simplification (removing technical IDs)
- Selection reasoning transformation (user-friendly language)
- Alternative note generation for ToT reasoning
- Risk warning generation for high-risk scenarios

Example:
    from app.services.reasoning_transformer import get_reasoning_transformer

    transformer = get_reasoning_transformer()
    public = transformer.transform(internal_reasoning)
    dual = transformer.transform_to_dual(internal_reasoning)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from app.schemas.reasoning import (
    DualReasoning,
    InternalReasoning,
    PublicExplanation,
    ReasoningType,
    RiskLevel,
    confidence_to_label,
)

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# =============================================================================
# Module-level singleton
# =============================================================================
_transformer_instance: ReasoningTransformer | None = None


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class TransformOptions:
    """Configuration options for reasoning transformation.

    Attributes:
        max_sources: Maximum number of sources to include (None for unlimited)
        add_source_suffix: Whether to add "e altre X fonti" when truncating
        include_alternative_note: Whether to include alternative interpretation note
        include_risk_warning: Whether to include risk warnings
    """

    max_sources: int | None = None
    add_source_suffix: bool = True
    include_alternative_note: bool = True
    include_risk_warning: bool = True


# =============================================================================
# Italian Text Templates
# =============================================================================

# Summary templates
COT_SUMMARY_NO_SOURCES = "La risposta si basa sull'analisi del tema: {theme}."
COT_SUMMARY_ONE_SOURCE = "La risposta si basa sull'analisi di una fonte normativa."
COT_SUMMARY_MULTIPLE_SOURCES = "La risposta si basa sull'analisi di {count} fonti normative."

TOT_SUMMARY_SINGLE = "La risposta è stata elaborata considerando le normative pertinenti."
TOT_SUMMARY_MULTIPLE = (
    "Abbiamo considerato {count} possibili interpretazioni "
    "e selezionato quella più supportata dalle fonti normative."
)

# Alternative note templates
ALTERNATIVE_NOTE_TEMPLATE = (
    "Sono state valutate altre {count} interpretazioni alternative, "
    "ma quella presentata risulta la più supportata dalle fonti normative."
)

# Risk warning templates
RISK_WARNING_CRITICAL = (
    "Attenzione: questa situazione comporta rischi sanzionatori "
    "significativi che potrebbero includere sanzioni penali. "
    "Si consiglia la consulenza di un professionista."
)

RISK_WARNING_HIGH = (
    "Attenzione: questa interpretazione comporta potenziali "
    "rischi sanzionatori elevati. Verificare con un professionista."
)

# Source ID pattern for removal
SOURCE_ID_PATTERN = re.compile(r"\bS\d+\b")


# =============================================================================
# ReasoningTransformer Class
# =============================================================================


class ReasoningTransformer:
    """Service for transforming internal reasoning to user-friendly Italian.

    Provides methods for:
    - Confidence score mapping
    - Source reference simplification
    - Selection reasoning transformation
    - Full pipeline transformation

    Example:
        >>> transformer = ReasoningTransformer()
        >>> public = transformer.transform(internal_reasoning)
        >>> print(public.summary)
        'La risposta si basa sull'analisi di 3 fonti normative.'
    """

    def __init__(self) -> None:
        """Initialize the transformer."""
        pass

    # =========================================================================
    # Confidence Mapping
    # =========================================================================

    def map_confidence(self, confidence: float | None) -> str:
        """Map numeric confidence score to Italian label.

        Args:
            confidence: Confidence score (0.0-1.0) or None.

        Returns:
            Italian confidence label: "alta", "media", "bassa", or "non disponibile".

        Example:
            >>> transformer.map_confidence(0.85)
            'alta'
            >>> transformer.map_confidence(0.6)
            'media'
        """
        return confidence_to_label(confidence)

    # =========================================================================
    # Source Simplification
    # =========================================================================

    def simplify_sources(
        self,
        sources: Sequence[dict | str],
        max_count: int | None = None,
        add_suffix: bool = False,
    ) -> list[str]:
        """Simplify source references for user display.

        Extracts human-readable titles from source objects, removing technical
        IDs and limiting the number of sources shown.

        Args:
            sources: List of source dictionaries or strings.
            max_count: Maximum number of sources to include (None for all).
            add_suffix: Whether to add "e altre X fonti" when truncating.

        Returns:
            List of simplified source titles.

        Example:
            >>> sources = [{"id": "S1", "title": "DPR 633/72"}]
            >>> transformer.simplify_sources(sources)
            ['DPR 633/72']
        """
        if not sources:
            return []

        simplified: list[str] = []
        for source in sources:
            title = self._extract_source_title(source)
            if title:
                simplified.append(title)

        # Apply max_count limit if specified
        if max_count is not None and len(simplified) > max_count:
            remaining_count = len(simplified) - max_count
            simplified = simplified[:max_count]
            if add_suffix and remaining_count > 0:
                simplified.append(f"e altre {remaining_count} fonti")

        return simplified

    def _extract_source_title(self, source: dict | str) -> str:
        """Extract human-readable title from a source.

        Args:
            source: Source dictionary or string.

        Returns:
            Extracted title string.
        """
        if isinstance(source, str):
            return source

        if isinstance(source, dict):
            # Try title first, then ref, then id as fallback
            title = source.get("title") or source.get("ref") or source.get("id", "")
            return str(title) if title else ""

        return ""

    # =========================================================================
    # Selection Reasoning Transformation
    # =========================================================================

    def transform_selection_reasoning(self, reasoning: str | None) -> str | None:
        """Transform technical selection reasoning to user-friendly Italian.

        Removes technical references like source IDs (S1, S2, etc.) and
        ensures the reasoning is suitable for user display.

        Args:
            reasoning: Technical selection reasoning or None.

        Returns:
            User-friendly reasoning or None/empty string.

        Example:
            >>> transformer.transform_selection_reasoning(
            ...     "Source S1 explicitly states 20%"
            ... )
            'La fonte principale indica chiaramente il 20%'
        """
        if reasoning is None:
            return None

        if not reasoning:
            return ""

        # Remove source ID references (S1, S2, etc.)
        transformed = SOURCE_ID_PATTERN.sub("", reasoning)

        # Clean up any resulting double spaces or awkward punctuation
        transformed = re.sub(r"\s+", " ", transformed)
        transformed = re.sub(r"\s*,\s*,\s*", ", ", transformed)
        transformed = re.sub(r"^\s*,\s*", "", transformed)
        transformed = transformed.strip()

        # If after cleaning it looks like Italian, keep it
        # Otherwise, just return the cleaned version
        return transformed

    # =========================================================================
    # Alternative Note Generation
    # =========================================================================

    def generate_alternative_note(self, internal: InternalReasoning) -> str | None:
        """Generate note about alternative interpretations considered.

        Only generates a note for ToT reasoning with multiple hypotheses.

        Args:
            internal: Internal reasoning data.

        Returns:
            Alternative note string or None if not applicable.

        Example:
            >>> note = transformer.generate_alternative_note(tot_reasoning)
            >>> print(note)
            'Sono state valutate altre 2 interpretazioni alternative...'
        """
        # Only for ToT reasoning
        if internal.reasoning_type == ReasoningType.COT.value:
            return None

        # Need multiple hypotheses
        hypotheses = internal.hypotheses or []
        if len(hypotheses) <= 1:
            return None

        # Count alternatives (excluding the selected one)
        alternative_count = len(hypotheses) - 1

        return ALTERNATIVE_NOTE_TEMPLATE.format(count=alternative_count)

    # =========================================================================
    # Risk Warning Generation
    # =========================================================================

    def generate_risk_warning(self, internal: InternalReasoning) -> str | None:
        """Generate risk warning message for high-risk scenarios.

        Only generates warnings for CRITICAL or HIGH risk levels.

        Args:
            internal: Internal reasoning data.

        Returns:
            Risk warning string in Italian or None.

        Example:
            >>> warning = transformer.generate_risk_warning(high_risk_reasoning)
            >>> print(warning)
            'Attenzione: questa interpretazione comporta...'
        """
        risk_level = internal.risk_level

        if risk_level == RiskLevel.CRITICAL.value:
            return RISK_WARNING_CRITICAL
        elif risk_level == RiskLevel.HIGH.value:
            return RISK_WARNING_HIGH

        return None

    # =========================================================================
    # Summary Generation
    # =========================================================================

    def generate_summary(self, internal: InternalReasoning) -> str:
        """Generate user-friendly summary of the reasoning process.

        Creates an Italian summary based on the reasoning type and
        number of sources consulted.

        Args:
            internal: Internal reasoning data.

        Returns:
            User-friendly summary in Italian.

        Example:
            >>> summary = transformer.generate_summary(internal)
            >>> print(summary)
            'La risposta si basa sull'analisi di 3 fonti normative.'
        """
        if internal.reasoning_type == ReasoningType.TOT.value:
            return self._generate_tot_summary(internal)
        else:
            return self._generate_cot_summary(internal)

    def _generate_cot_summary(self, internal: InternalReasoning) -> str:
        """Generate summary for Chain of Thought reasoning.

        Args:
            internal: Internal reasoning data.

        Returns:
            User-friendly summary in Italian.
        """
        source_count = len(internal.sources_used)

        if source_count == 0:
            theme = internal.theme or "richiesta"
            return COT_SUMMARY_NO_SOURCES.format(theme=theme)
        elif source_count == 1:
            return COT_SUMMARY_ONE_SOURCE
        else:
            return COT_SUMMARY_MULTIPLE_SOURCES.format(count=source_count)

    def _generate_tot_summary(self, internal: InternalReasoning) -> str:
        """Generate summary for Tree of Thoughts reasoning.

        Args:
            internal: Internal reasoning data.

        Returns:
            User-friendly summary in Italian.
        """
        hypothesis_count = len(internal.hypotheses or [])

        if hypothesis_count <= 1:
            return TOT_SUMMARY_SINGLE
        else:
            return TOT_SUMMARY_MULTIPLE.format(count=hypothesis_count)

    # =========================================================================
    # Full Transformation Pipeline
    # =========================================================================

    def transform(
        self,
        internal: InternalReasoning,
        options: TransformOptions | None = None,
    ) -> PublicExplanation:
        """Transform internal reasoning to public explanation.

        Full transformation pipeline that produces a user-friendly Italian
        explanation from technical internal reasoning.

        Args:
            internal: Internal technical reasoning.
            options: Optional transformation options.

        Returns:
            PublicExplanation with user-friendly content.

        Example:
            >>> public = transformer.transform(internal_reasoning)
            >>> print(public.summary)
            >>> print(public.confidence_label)
        """
        options = options or TransformOptions()

        logger.debug(
            "transforming_reasoning",
            reasoning_type=internal.reasoning_type,
            source_count=len(internal.sources_used),
        )

        # Generate summary
        summary = self.generate_summary(internal)

        # Simplify sources
        main_sources = self.simplify_sources(
            internal.sources_used,
            max_count=options.max_sources,
            add_suffix=options.add_source_suffix,
        )

        # Map confidence
        confidence_label = self.map_confidence(internal.confidence)

        # Transform selection reasoning
        why_selected = self.transform_selection_reasoning(internal.selection_reasoning)

        # Generate alternative note if applicable
        alternative_note = None
        if options.include_alternative_note:
            alternative_note = self.generate_alternative_note(internal)

        # Generate risk warning if applicable
        risk_warning = None
        if options.include_risk_warning:
            risk_warning = self.generate_risk_warning(internal)

        # Determine selected scenario for ToT
        selected_scenario = None
        if internal.reasoning_type == ReasoningType.TOT.value:
            selected_scenario = internal.selected_hypothesis

        return PublicExplanation(
            summary=summary,
            main_sources=main_sources,
            confidence_label=confidence_label,
            selected_scenario=selected_scenario,
            why_selected=why_selected,
            alternative_note=alternative_note,
            risk_warning=risk_warning,
        )

    def transform_to_dual(
        self,
        internal: InternalReasoning,
        options: TransformOptions | None = None,
    ) -> DualReasoning:
        """Transform internal reasoning and create DualReasoning container.

        Convenience method that transforms internal reasoning and wraps
        both in a DualReasoning container.

        Args:
            internal: Internal technical reasoning.
            options: Optional transformation options.

        Returns:
            DualReasoning with both internal and transformed public.

        Example:
            >>> dual = transformer.transform_to_dual(internal_reasoning)
            >>> print(dual.internal.reasoning_type)
            >>> print(dual.public.summary)
        """
        public = self.transform(internal, options)
        return DualReasoning(internal=internal, public=public)


# =============================================================================
# Factory Functions
# =============================================================================


def get_reasoning_transformer() -> ReasoningTransformer:
    """Get or create ReasoningTransformer singleton instance.

    Returns:
        ReasoningTransformer instance.

    Example:
        >>> transformer = get_reasoning_transformer()
        >>> public = transformer.transform(internal)
    """
    global _transformer_instance
    if _transformer_instance is None:
        _transformer_instance = ReasoningTransformer()
    return _transformer_instance


def reset_transformer() -> None:
    """Reset the singleton instance (for testing)."""
    global _transformer_instance
    _transformer_instance = None
