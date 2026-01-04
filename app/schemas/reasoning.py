"""DualReasoning Data Structures for Internal and Public Reasoning (DEV-229).

This module provides data structures for separating internal technical
reasoning from public user-friendly explanations in Italian.

The dual reasoning pattern allows:
- Internal reasoning: Full technical trace for debugging and analysis
- Public reasoning: User-friendly Italian explanation for display

Example:
    from app.schemas.reasoning import (
        InternalReasoning,
        PublicExplanation,
        DualReasoning,
        create_public_from_internal,
    )

    internal = InternalReasoning(
        reasoning_type="cot",
        theme="Calcolo IVA",
        sources_used=[{"id": "S1", "title": "DPR 633/72"}],
        key_elements=["aliquota 22%"],
        conclusion="IVA al 22%",
        confidence=0.85,
    )
    public = create_public_from_internal(internal)
    dual = DualReasoning(internal=internal, public=public)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# Enumerations
# =============================================================================


class ReasoningType(str, Enum):
    """Type of reasoning used for the response.

    Values:
        COT: Chain of Thought - single linear reasoning path
        TOT: Tree of Thoughts - multiple hypothesis exploration
        TOT_MULTI_DOMAIN: ToT across multiple domains (fiscale, lavoro, etc.)
    """

    COT = "cot"
    TOT = "tot"
    TOT_MULTI_DOMAIN = "tot_multi_domain"


class ConfidenceLevel(str, Enum):
    """Confidence level labels in Italian.

    Values:
        ALTA: High confidence (>=80%)
        MEDIA: Medium confidence (50-79%)
        BASSA: Low confidence (<50%)
    """

    ALTA = "alta"
    MEDIA = "media"
    BASSA = "bassa"


class RiskLevel(str, Enum):
    """Risk level for sanction analysis.

    Values:
        CRITICAL: >100% tax + criminal penalties
        HIGH: 90-180% tax penalties
        MEDIUM: 30-90% tax penalties
        LOW: 0-30% tax penalties or formal errors
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# Helper Functions
# =============================================================================


def confidence_to_label(confidence: float | None) -> str:
    """Convert numeric confidence to Italian label.

    Args:
        confidence: Confidence score between 0.0 and 1.0, or None.

    Returns:
        Italian confidence label: "alta", "media", "bassa", or "non disponibile".

    Example:
        >>> confidence_to_label(0.85)
        'alta'
        >>> confidence_to_label(0.6)
        'media'
        >>> confidence_to_label(None)
        'non disponibile'
    """
    if confidence is None:
        return "non disponibile"

    if confidence >= 0.8:
        return ConfidenceLevel.ALTA.value
    elif confidence >= 0.5:
        return ConfidenceLevel.MEDIA.value
    else:
        return ConfidenceLevel.BASSA.value


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class InternalReasoning:
    """Internal technical reasoning trace for debugging and analysis.

    This structure captures the full reasoning process including:
    - Sources consulted and their hierarchy
    - Key elements extracted from sources
    - Hypotheses considered (for ToT)
    - Risk analysis results

    Attributes:
        reasoning_type: Type of reasoning ("cot", "tot", "tot_multi_domain")
        theme: Main topic/theme of the reasoning
        sources_used: List of source dicts with id, type, title
        key_elements: Key facts/rules extracted from sources
        conclusion: Final conclusion reached
        hypotheses: List of hypotheses (ToT only)
        selected_hypothesis: ID of selected hypothesis (ToT only)
        selection_reasoning: Why this hypothesis was selected (ToT only)
        confidence: Confidence score (0.0 to 1.0)
        risk_level: Risk assessment level
        risk_factors: List of identified risk factors
        latency_ms: Processing time in milliseconds
    """

    reasoning_type: str
    theme: str
    sources_used: list[dict]
    key_elements: list[str]
    conclusion: str
    hypotheses: list[dict] | None = None
    selected_hypothesis: str | None = None
    selection_reasoning: str | None = None
    confidence: float | None = None
    risk_level: str | None = None
    risk_factors: list[str] | None = None
    latency_ms: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all fields, including None values.
        """
        return {
            "reasoning_type": self.reasoning_type,
            "theme": self.theme,
            "sources_used": self.sources_used,
            "key_elements": self.key_elements,
            "conclusion": self.conclusion,
            "hypotheses": self.hypotheses,
            "selected_hypothesis": self.selected_hypothesis,
            "selection_reasoning": self.selection_reasoning,
            "confidence": self.confidence,
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "latency_ms": self.latency_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InternalReasoning:
        """Create InternalReasoning from dictionary.

        Args:
            data: Dictionary with reasoning fields.

        Returns:
            InternalReasoning instance.
        """
        return cls(
            reasoning_type=data.get("reasoning_type", "cot"),
            theme=data.get("theme", ""),
            sources_used=data.get("sources_used", []),
            key_elements=data.get("key_elements", []),
            conclusion=data.get("conclusion", ""),
            hypotheses=data.get("hypotheses"),
            selected_hypothesis=data.get("selected_hypothesis"),
            selection_reasoning=data.get("selection_reasoning"),
            confidence=data.get("confidence"),
            risk_level=data.get("risk_level"),
            risk_factors=data.get("risk_factors"),
            latency_ms=data.get("latency_ms"),
        )


@dataclass
class PublicExplanation:
    """User-friendly public explanation in Italian.

    This structure contains information suitable for display to end users,
    avoiding technical jargon and using Italian language throughout.

    Attributes:
        summary: Brief explanation of the reasoning process
        main_sources: Simplified list of main sources (titles only)
        confidence_label: Italian confidence label ("alta", "media", "bassa")
        selected_scenario: Name of selected scenario (if multiple considered)
        why_selected: User-friendly explanation of selection
        alternative_note: Note about alternative interpretations
        risk_warning: Risk warning message in Italian (if applicable)
    """

    summary: str
    main_sources: list[str]
    confidence_label: str
    selected_scenario: str | None = None
    why_selected: str | None = None
    alternative_note: str | None = None
    risk_warning: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all fields.
        """
        return {
            "summary": self.summary,
            "main_sources": self.main_sources,
            "confidence_label": self.confidence_label,
            "selected_scenario": self.selected_scenario,
            "why_selected": self.why_selected,
            "alternative_note": self.alternative_note,
            "risk_warning": self.risk_warning,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PublicExplanation:
        """Create PublicExplanation from dictionary.

        Args:
            data: Dictionary with explanation fields.

        Returns:
            PublicExplanation instance.
        """
        return cls(
            summary=data.get("summary", ""),
            main_sources=data.get("main_sources", []),
            confidence_label=data.get("confidence_label", "non disponibile"),
            selected_scenario=data.get("selected_scenario"),
            why_selected=data.get("why_selected"),
            alternative_note=data.get("alternative_note"),
            risk_warning=data.get("risk_warning"),
        )


@dataclass
class DualReasoning:
    """Container for both internal and public reasoning.

    Combines the full technical reasoning trace with the user-friendly
    public explanation, along with metadata.

    Attributes:
        internal: Full technical reasoning trace
        public: User-friendly public explanation
        created_at: Timestamp when reasoning was generated
    """

    internal: InternalReasoning
    public: PublicExplanation
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with nested internal and public dicts.
        """
        return {
            "internal": self.internal.to_dict(),
            "public": self.public.to_dict(),
            "created_at": self.created_at.isoformat(),
        }


# =============================================================================
# Factory Functions
# =============================================================================


def create_internal_from_cot(cot_data: dict[str, Any]) -> InternalReasoning:
    """Create InternalReasoning from Chain of Thought data.

    Args:
        cot_data: Dictionary with CoT fields:
            - tema: Topic/theme
            - fonti_utilizzate: Sources used (list of strings or dicts)
            - elementi_chiave: Key elements
            - conclusione: Conclusion

    Returns:
        InternalReasoning instance configured for CoT.

    Example:
        >>> cot = {"tema": "IVA", "fonti_utilizzate": ["Art. 1"], ...}
        >>> reasoning = create_internal_from_cot(cot)
    """
    # Convert sources to list of dicts if they're strings
    sources = cot_data.get("fonti_utilizzate", [])
    if sources and isinstance(sources[0], str):
        sources = [{"title": s} for s in sources]

    return InternalReasoning(
        reasoning_type=ReasoningType.COT.value,
        theme=cot_data.get("tema", ""),
        sources_used=sources,
        key_elements=cot_data.get("elementi_chiave", []),
        conclusion=cot_data.get("conclusione", ""),
        confidence=cot_data.get("confidence"),
    )


def create_internal_from_tot(tot_data: dict[str, Any], theme: str = "") -> InternalReasoning:
    """Create InternalReasoning from Tree of Thoughts data.

    Args:
        tot_data: Dictionary with ToT fields:
            - hypotheses: List of hypothesis dicts
            - selected: ID of selected hypothesis
            - selection_reasoning: Why selected
            - confidence: Overall confidence
        theme: Topic/theme for the reasoning

    Returns:
        InternalReasoning instance configured for ToT.

    Example:
        >>> tot = {"hypotheses": [...], "selected": "H1", ...}
        >>> reasoning = create_internal_from_tot(tot, theme="Deducibilità")
    """
    hypotheses = tot_data.get("hypotheses", [])
    selected_id = tot_data.get("selected")

    # Extract conclusion from selected hypothesis
    conclusion = ""
    sources_used: list[dict] = []
    for h in hypotheses:
        if h.get("id") == selected_id:
            conclusion = h.get("conclusion", "")
            sources_used = h.get("sources", [])
            break

    return InternalReasoning(
        reasoning_type=ReasoningType.TOT.value,
        theme=theme,
        sources_used=sources_used,
        key_elements=[],
        conclusion=conclusion,
        hypotheses=hypotheses,
        selected_hypothesis=selected_id,
        selection_reasoning=tot_data.get("selection_reasoning"),
        confidence=tot_data.get("confidence"),
    )


def create_public_from_internal(internal: InternalReasoning) -> PublicExplanation:
    """Create PublicExplanation from InternalReasoning.

    Transforms the technical internal reasoning into a user-friendly
    Italian explanation suitable for display.

    Args:
        internal: The internal technical reasoning.

    Returns:
        PublicExplanation with simplified, user-friendly content.

    Example:
        >>> internal = InternalReasoning(...)
        >>> public = create_public_from_internal(internal)
    """
    # Extract source titles for public display
    main_sources = []
    for source in internal.sources_used:
        if isinstance(source, dict):
            title = source.get("title") or source.get("ref") or source.get("id", "")
            if title:
                main_sources.append(str(title))
        elif isinstance(source, str):
            main_sources.append(source)

    # Generate summary based on reasoning type
    if internal.reasoning_type == ReasoningType.TOT.value:
        summary = _generate_tot_summary(internal)
    else:
        summary = _generate_cot_summary(internal)

    # Determine confidence label
    confidence_label = confidence_to_label(internal.confidence)

    # Build risk warning if applicable
    risk_warning = None
    if internal.risk_level in (RiskLevel.CRITICAL.value, RiskLevel.HIGH.value):
        risk_warning = _generate_risk_warning(internal)

    return PublicExplanation(
        summary=summary,
        main_sources=main_sources,
        confidence_label=confidence_label,
        selected_scenario=internal.selected_hypothesis,
        why_selected=internal.selection_reasoning,
        risk_warning=risk_warning,
    )


def _generate_cot_summary(internal: InternalReasoning) -> str:
    """Generate summary for Chain of Thought reasoning.

    Args:
        internal: Internal reasoning data.

    Returns:
        User-friendly summary in Italian.
    """
    source_count = len(internal.sources_used)
    if source_count == 0:
        return f"La risposta si basa sull'analisi del tema: {internal.theme}."
    elif source_count == 1:
        return "La risposta si basa sull'analisi di una fonte normativa."
    else:
        return f"La risposta si basa sull'analisi di {source_count} fonti normative."


def _generate_tot_summary(internal: InternalReasoning) -> str:
    """Generate summary for Tree of Thoughts reasoning.

    Args:
        internal: Internal reasoning data.

    Returns:
        User-friendly summary in Italian.
    """
    hypothesis_count = len(internal.hypotheses or [])
    if hypothesis_count <= 1:
        return "La risposta è stata elaborata considerando le normative pertinenti."
    else:
        return (
            f"Abbiamo considerato {hypothesis_count} possibili interpretazioni "
            f"e selezionato quella più supportata dalle fonti normative."
        )


def _generate_risk_warning(internal: InternalReasoning) -> str:
    """Generate risk warning message in Italian.

    Args:
        internal: Internal reasoning data.

    Returns:
        Risk warning message.
    """
    if internal.risk_level == RiskLevel.CRITICAL.value:
        return (
            "Attenzione: questa situazione comporta rischi sanzionatori "
            "significativi che potrebbero includere sanzioni penali. "
            "Si consiglia la consulenza di un professionista."
        )
    elif internal.risk_level == RiskLevel.HIGH.value:
        return (
            "Attenzione: questa interpretazione comporta potenziali "
            "rischi sanzionatori elevati. Verificare con un professionista."
        )
    return ""
