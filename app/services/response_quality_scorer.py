"""ResponseQualityScorer Service for Response Quality Evaluation (DEV-232).

This service evaluates response quality across multiple dimensions:
- Source citation accuracy (based on SourceHierarchy weights)
- Reasoning coherence (completeness of reasoning trace)
- Action relevance (grounding of suggested actions)
- Risk coverage (presence and completeness of risk analysis)

The quality score enables A/B testing, model comparison, and continuous
improvement of the RAG pipeline.

Example:
    from app.services.response_quality_scorer import get_response_quality_scorer

    scorer = get_response_quality_scorer()
    result = scorer.score(
        response="L'IVA è del 22%",
        reasoning_trace={"steps": ["analysis"]},
        sources_cited=[{"type": "legge", "title": "DPR 633/72"}],
        suggested_actions=[],
        kb_sources=[{"type": "legge", "title": "DPR 633/72"}],
        query="Quale aliquota IVA?",
    )
    print(result.overall_score)  # 0.75
    print(result.recommendation)  # "good"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from app.services.source_hierarchy import SourceHierarchy

logger = structlog.get_logger(__name__)

# =============================================================================
# Module-level singleton
# =============================================================================
_scorer_instance: ResponseQualityScorer | None = None


# =============================================================================
# Default Weights
# =============================================================================
DEFAULT_WEIGHTS: dict[str, float] = {
    "source_citation": 0.30,
    "reasoning_coherence": 0.25,
    "action_relevance": 0.25,
    "risk_coverage": 0.20,
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class QualityDimension:
    """Single quality dimension score.

    Attributes:
        name: Dimension name (e.g., "source_citation")
        score: Score between 0.0 and 1.0
        weight: Weight for overall score calculation
        details: Optional explanation of the score
    """

    name: str
    score: float
    weight: float
    details: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all fields.
        """
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "details": self.details,
        }


@dataclass
class QualityScore:
    """Complete quality assessment for a response.

    Attributes:
        overall_score: Weighted average of all dimensions (0.0 to 1.0)
        dimensions: List of individual dimension scores
        flags: Quality warning flags (e.g., "no_sources_cited")
        recommendation: Quality recommendation ("good", "review", "poor")
    """

    overall_score: float
    dimensions: list[QualityDimension]
    flags: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with nested dimension dicts.
        """
        return {
            "overall_score": self.overall_score,
            "dimensions": [d.to_dict() for d in self.dimensions],
            "flags": self.flags,
            "recommendation": self.recommendation,
        }


# =============================================================================
# ResponseQualityScorer Class
# =============================================================================


class ResponseQualityScorer:
    """Evaluates response quality across multiple dimensions.

    Dimensions:
    - source_citation (30%): Quality and authority of cited sources
    - reasoning_coherence (25%): Completeness of reasoning trace
    - action_relevance (25%): Grounding of suggested actions
    - risk_coverage (20%): Presence and completeness of risk analysis

    Example:
        >>> from app.services.source_hierarchy import SourceHierarchy
        >>> hierarchy = SourceHierarchy()
        >>> scorer = ResponseQualityScorer(source_hierarchy=hierarchy)
        >>> result = scorer.score(...)
        >>> print(result.recommendation)
        'good'
    """

    def __init__(
        self,
        source_hierarchy: SourceHierarchy,
        weights: dict[str, float] | None = None,
    ) -> None:
        """Initialize the scorer.

        Args:
            source_hierarchy: SourceHierarchy instance for source weighting.
            weights: Optional custom weights for dimensions.
        """
        self.source_hierarchy = source_hierarchy
        self.weights = weights or DEFAULT_WEIGHTS.copy()

    def score(
        self,
        response: str,
        reasoning_trace: dict | None,
        sources_cited: list[dict],
        suggested_actions: list[dict],
        kb_sources: list[dict],
        query: str,
    ) -> QualityScore:
        """Score response quality.

        Args:
            response: Generated response text
            reasoning_trace: Reasoning trace dictionary from LLM
            sources_cited: List of source dicts with 'type' and 'title'
            suggested_actions: List of action dicts with 'label' and optional 'grounded'
            kb_sources: Knowledge base sources available for grounding
            query: Original user query

        Returns:
            QualityScore with overall score, dimensions, flags, and recommendation.
        """
        flags: list[str] = []
        dimensions: list[QualityDimension] = []

        # Handle None reasoning_trace
        if reasoning_trace is None:
            reasoning_trace = {}

        # Score each dimension
        source_dim = self._score_source_citation(sources_cited, kb_sources, flags)
        dimensions.append(source_dim)

        reasoning_dim = self._score_reasoning_coherence(reasoning_trace, flags)
        dimensions.append(reasoning_dim)

        action_dim = self._score_action_relevance(suggested_actions, flags)
        dimensions.append(action_dim)

        risk_dim = self._score_risk_coverage(reasoning_trace, suggested_actions, flags)
        dimensions.append(risk_dim)

        # Check for empty response
        if not response or not response.strip():
            flags.append("empty_response")

        # Calculate overall score
        overall_score = sum(d.score * d.weight for d in dimensions)

        # Determine recommendation
        recommendation = self._determine_recommendation(overall_score, flags)

        logger.debug(
            "response_quality_scored",
            overall_score=overall_score,
            recommendation=recommendation,
            flags=flags,
        )

        return QualityScore(
            overall_score=overall_score,
            dimensions=dimensions,
            flags=flags,
            recommendation=recommendation,
        )

    def _score_source_citation(
        self,
        sources_cited: list[dict],
        kb_sources: list[dict],
        flags: list[str],
    ) -> QualityDimension:
        """Score source citation quality.

        Evaluates:
        - Presence of sources
        - Authority level of sources (via SourceHierarchy)
        - Grounding of sources in knowledge base

        Args:
            sources_cited: Sources cited in response
            kb_sources: Available KB sources
            flags: Mutable flags list to append warnings

        Returns:
            QualityDimension for source citation.
        """
        weight = self.weights.get("source_citation", 0.30)

        if not sources_cited:
            flags.append("no_sources_cited")
            return QualityDimension(
                name="source_citation",
                score=0.0,
                weight=weight,
                details="No sources cited",
            )

        # Calculate average source authority
        total_weight = 0.0
        for source in sources_cited:
            source_type = source.get("type", "unknown")
            total_weight += self.source_hierarchy.get_weight(source_type)

        avg_authority = total_weight / len(sources_cited)

        # Check if sources are grounded in KB
        kb_titles = {s.get("title", "").lower() for s in kb_sources if s.get("title")}
        cited_titles = {s.get("title", "").lower() for s in sources_cited if s.get("title")}

        if cited_titles and not cited_titles.intersection(kb_titles):
            flags.append("sources_not_grounded")

        return QualityDimension(
            name="source_citation",
            score=avg_authority,
            weight=weight,
            details=f"Average source authority: {avg_authority:.2f}",
        )

    def _score_reasoning_coherence(
        self,
        reasoning_trace: dict,
        flags: list[str],
    ) -> QualityDimension:
        """Score reasoning coherence.

        Evaluates:
        - Presence of reasoning steps
        - Completeness of reasoning trace
        - Type-specific scoring (CoT vs ToT)

        Args:
            reasoning_trace: Reasoning trace dictionary
            flags: Mutable flags list to append warnings

        Returns:
            QualityDimension for reasoning coherence.
        """
        weight = self.weights.get("reasoning_coherence", 0.25)
        default_score = 0.5

        if not reasoning_trace:
            flags.append("empty_reasoning_trace")
            return QualityDimension(
                name="reasoning_coherence",
                score=default_score,
                weight=weight,
                details="Empty reasoning trace, using default score",
            )

        score = 0.0
        score_components: list[str] = []

        # Check for steps
        steps = reasoning_trace.get("steps", [])
        if steps:
            step_score = min(len(steps) / 3.0, 1.0)  # 3+ steps = full score
            score += step_score * 0.3
            score_components.append(f"steps: {step_score:.2f}")

        # Check for conclusion
        if reasoning_trace.get("conclusion"):
            score += 0.2
            score_components.append("conclusion present")

        # Check for theme
        if reasoning_trace.get("theme"):
            score += 0.1
            score_components.append("theme present")

        # Type-specific scoring
        reasoning_type = reasoning_trace.get("type", "cot")

        if reasoning_type == "tot":
            # ToT-specific scoring - hypotheses are the main component
            hypotheses = reasoning_trace.get("hypotheses", [])
            if hypotheses:
                # More hypotheses = more thorough analysis
                hyp_score = min(len(hypotheses) / 2.0, 1.0) * 0.4
                score += hyp_score
                score_components.append(f"{len(hypotheses)} hypotheses")

            if reasoning_trace.get("selected"):
                score += 0.2
                score_components.append("selected hypothesis")

            if reasoning_trace.get("selection_reasoning"):
                score += 0.2
                score_components.append("selection reasoning")
        else:
            # CoT-specific scoring - steps matter more
            if steps:
                score += 0.2
                score_components.append("cot with steps")
            else:
                score += 0.1

        # Ensure score is in bounds
        score = min(max(score, 0.0), 1.0)

        # If score is 0, use default
        if score == 0.0:
            flags.append("empty_reasoning_trace")
            return QualityDimension(
                name="reasoning_coherence",
                score=default_score,
                weight=weight,
                details="Minimal reasoning trace, using default score",
            )

        return QualityDimension(
            name="reasoning_coherence",
            score=score,
            weight=weight,
            details=", ".join(score_components),
        )

    def _score_action_relevance(
        self,
        suggested_actions: list[dict],
        flags: list[str],
    ) -> QualityDimension:
        """Score action relevance.

        Evaluates:
        - Presence of actions
        - Grounding of actions (explicit grounded flag)

        Args:
            suggested_actions: List of suggested action dicts
            flags: Mutable flags list to append warnings

        Returns:
            QualityDimension for action relevance.
        """
        weight = self.weights.get("action_relevance", 0.25)

        if not suggested_actions:
            # No actions is acceptable for informational queries
            return QualityDimension(
                name="action_relevance",
                score=0.0,
                weight=weight,
                details="No actions suggested",
            )

        # Check grounding
        grounded_count = sum(1 for action in suggested_actions if action.get("grounded", False))
        total_count = len(suggested_actions)

        grounding_ratio = grounded_count / total_count

        if grounding_ratio == 0.0:
            flags.append("actions_not_grounded")

        # Score based on grounding ratio
        # Also add bonus for having actions
        score = 0.3 + (grounding_ratio * 0.7)

        return QualityDimension(
            name="action_relevance",
            score=score,
            weight=weight,
            details=f"{grounded_count}/{total_count} actions grounded",
        )

    def _score_risk_coverage(
        self,
        reasoning_trace: dict,
        suggested_actions: list[dict],
        flags: list[str],
    ) -> QualityDimension:
        """Score risk coverage.

        Evaluates:
        - Presence of risk analysis
        - Risk level assignment
        - Risk factors identified
        - Mitigation actions for high risks

        Args:
            reasoning_trace: Reasoning trace with potential risk fields
            suggested_actions: Actions that may include mitigations
            flags: Mutable flags list to append warnings

        Returns:
            QualityDimension for risk coverage.
        """
        weight = self.weights.get("risk_coverage", 0.20)
        default_score = 0.5

        risk_level = reasoning_trace.get("risk_level")
        risk_factors = reasoning_trace.get("risk_factors", [])

        if not risk_level:
            flags.append("no_risk_analysis")
            return QualityDimension(
                name="risk_coverage",
                score=default_score,
                weight=weight,
                details="No risk analysis present",
            )

        score = 0.0
        score_components: list[str] = []

        # Risk level present
        score += 0.4
        score_components.append(f"risk_level: {risk_level}")

        # Risk factors identified
        if risk_factors:
            factor_score = min(len(risk_factors) / 2.0, 0.3)  # 2+ factors = full
            score += factor_score
            score_components.append(f"{len(risk_factors)} risk factors")

        # Check for mitigation actions for high/critical risk
        if risk_level in ("critical", "high"):
            mitigation_actions = [a for a in suggested_actions if a.get("is_mitigation", False)]
            if mitigation_actions:
                score += 0.3
                score_components.append("mitigation actions present")
            else:
                # Still good but not perfect
                score += 0.15
                score_components.append("no explicit mitigation")
        else:
            # Low/medium risk doesn't need mitigation
            score += 0.3
            score_components.append("acceptable risk level")

        score = min(max(score, 0.0), 1.0)

        return QualityDimension(
            name="risk_coverage",
            score=score,
            weight=weight,
            details=", ".join(score_components),
        )

    def _determine_recommendation(
        self,
        overall_score: float,
        flags: list[str],
    ) -> str:
        """Determine quality recommendation.

        Args:
            overall_score: Weighted average score
            flags: Quality warning flags

        Returns:
            "good", "review", or "poor"
        """
        # Critical flags that force review regardless of score
        critical_flags = {"no_sources_cited", "empty_response"}

        if any(f in critical_flags for f in flags):
            return "poor" if overall_score < 0.3 else "review"

        if overall_score >= 0.7:
            return "good"
        elif overall_score >= 0.4:
            return "review"
        else:
            return "poor"


# =============================================================================
# Factory Functions
# =============================================================================


def get_response_quality_scorer() -> ResponseQualityScorer:
    """Get or create ResponseQualityScorer singleton instance.

    Returns:
        ResponseQualityScorer instance.

    Example:
        >>> scorer = get_response_quality_scorer()
        >>> result = scorer.score(...)
    """
    global _scorer_instance
    if _scorer_instance is None:
        from app.services.source_hierarchy import get_source_hierarchy

        hierarchy = get_source_hierarchy()
        _scorer_instance = ResponseQualityScorer(source_hierarchy=hierarchy)
    return _scorer_instance


def reset_scorer() -> None:
    """Reset the singleton instance (for testing)."""
    global _scorer_instance
    _scorer_instance = None
