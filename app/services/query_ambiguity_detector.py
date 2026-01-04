"""QueryAmbiguityDetector Service for Identifying Vague Queries (DEV-234).

This service detects ambiguous queries that may require multi-variant HyDE
or conversation context to generate relevant hypothetical documents.

Ambiguity Indicators:
- Very short queries (<5 words)
- Pronouns without clear antecedent ("questo", "quello")
- Generic follow-ups ("E per...", "E se...")
- Missing key fiscal terms

Example:
    from app.services.query_ambiguity_detector import get_query_ambiguity_detector

    detector = get_query_ambiguity_detector()
    result = detector.detect("E per l'IVA?")
    print(result.is_ambiguous)  # True
    print(result.recommended_strategy)  # "multi_variant"
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# =============================================================================
# Module-level singleton
# =============================================================================
_detector_instance: QueryAmbiguityDetector | None = None


# =============================================================================
# Ambiguity Configuration
# =============================================================================

# Ambiguous pronouns (Italian)
AMBIGUOUS_PRONOUNS = [
    "questo",
    "questa",
    "questi",
    "queste",
    "quello",
    "quella",
    "quelli",
    "quelle",
    "ciò",
    "esso",
    "essa",
    "essi",
    "esse",
]

# Follow-up patterns (Italian)
FOLLOWUP_PATTERNS = [
    r"^e\s+per\b",  # "E per..."
    r"^e\s+se\b",  # "E se..."
    r"^invece\b",  # "Invece..."
    r"\banche\b",  # "...anche..."
    r"\bla\s+stessa\s+cosa\b",  # "la stessa cosa"
    r"\bcome\s+prima\b",  # "come prima"
    r"\bcome\s+sopra\b",  # "come sopra"
    r"\bidem\b",  # "idem"
]

# Key fiscal/legal terms (Italian)
FISCAL_TERMS = [
    "irpef",
    "iva",
    "irap",
    "ires",
    "imu",
    "tasi",
    "tari",
    "imposta",
    "imposte",
    "tassa",
    "tasse",
    "tributo",
    "tributi",
    "aliquota",
    "aliquote",
    "detrazione",
    "detrazioni",
    "deduzione",
    "deduzioni",
    "scadenza",
    "scadenze",
    "dichiarazione",
    "fattura",
    "fatture",
    "fatturazione",
    "contributo",
    "contributi",
    "inps",
    "inail",
    "pensione",
    "pensioni",
    "reddito",
    "redditi",
    "cedolare",
    "partita iva",
    "codice fiscale",
    "f24",
    "730",
    "unico",
    "modello",
    "ravvedimento",
    "sanzione",
    "sanzioni",
    "interessi",
    "mora",
]

# Score weights for indicators
INDICATOR_WEIGHTS = {
    "short_query": 0.25,
    "pronoun_ambiguity": 0.30,
    "followup_pattern": 0.25,
    "missing_fiscal_terms": 0.20,
}

# Thresholds for strategy recommendation
AMBIGUITY_THRESHOLD_HIGH = 0.5  # Above this = multi_variant
AMBIGUITY_THRESHOLD_LOW = 0.3  # Below this = standard


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class AmbiguityResult:
    """Result of query ambiguity detection.

    Attributes:
        is_ambiguous: Whether the query is considered ambiguous
        score: Ambiguity score from 0.0 (clear) to 1.0 (very ambiguous)
        indicators: List of detected ambiguity indicators
        recommended_strategy: Recommended HyDE strategy
            - "standard": Normal single HyDE generation
            - "conversational": Use conversation context
            - "multi_variant": Generate multiple HyDE variants
    """

    is_ambiguous: bool
    score: float
    indicators: list[str] = field(default_factory=list)
    recommended_strategy: str = "standard"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all fields.
        """
        return {
            "is_ambiguous": self.is_ambiguous,
            "score": self.score,
            "indicators": self.indicators,
            "recommended_strategy": self.recommended_strategy,
        }


# =============================================================================
# QueryAmbiguityDetector Class
# =============================================================================


class QueryAmbiguityDetector:
    """Service for detecting ambiguous queries in Italian fiscal/legal context.

    Detects queries that may require special handling:
    - Multi-variant HyDE for very ambiguous queries
    - Conversational HyDE for follow-up queries
    - Standard HyDE for clear, specific queries

    Example:
        >>> detector = QueryAmbiguityDetector()
        >>> result = detector.detect("E per l'IVA?")
        >>> print(result.is_ambiguous)
        True
        >>> print(result.indicators)
        ['short_query', 'followup_pattern']
    """

    def __init__(self) -> None:
        """Initialize the detector."""
        logger.debug("query_ambiguity_detector_initialized")

    def detect(
        self,
        query: str,
        conversation_history: list[dict] | None = None,
    ) -> AmbiguityResult:
        """Detect ambiguity in a query.

        Args:
            query: User query to analyze
            conversation_history: Optional conversation history for context
                Format: [{"role": "user"|"assistant", "content": str}, ...]

        Returns:
            AmbiguityResult with detection results and recommended strategy.
        """
        # Normalize query
        query_lower = query.strip().lower()
        indicators: list[str] = []

        # Handle empty/whitespace queries
        if not query_lower:
            return AmbiguityResult(
                is_ambiguous=True,
                score=1.0,
                indicators=["empty_query"],
                recommended_strategy="multi_variant",
            )

        # Check for short query
        if self._is_short_query(query_lower):
            indicators.append("short_query")

        # Check for pronoun ambiguity
        if self._has_pronoun_ambiguity(query_lower):
            indicators.append("pronoun_ambiguity")

        # Check for follow-up patterns
        if self._has_followup_pattern(query_lower):
            indicators.append("followup_pattern")

        # Check for missing fiscal terms
        if self._is_missing_fiscal_terms(query_lower):
            indicators.append("missing_fiscal_terms")

        # Calculate score
        score = self._calculate_score(indicators, query_lower)

        # Determine if ambiguous
        is_ambiguous = score >= AMBIGUITY_THRESHOLD_LOW

        # Determine recommended strategy
        recommended_strategy = self._determine_strategy(score, indicators, conversation_history)

        logger.debug(
            "query_ambiguity_detected",
            query_length=len(query),
            is_ambiguous=is_ambiguous,
            score=score,
            indicators=indicators,
            strategy=recommended_strategy,
        )

        return AmbiguityResult(
            is_ambiguous=is_ambiguous,
            score=score,
            indicators=indicators,
            recommended_strategy=recommended_strategy,
        )

    def _is_short_query(self, query: str) -> bool:
        """Check if query is too short (<5 words).

        Args:
            query: Normalized query string.

        Returns:
            True if query has fewer than 5 words.
        """
        # Split by whitespace and filter empty strings
        words = [w for w in query.split() if w]
        return len(words) < 5

    def _has_pronoun_ambiguity(self, query: str) -> bool:
        """Check if query contains ambiguous pronouns.

        Args:
            query: Normalized query string.

        Returns:
            True if query contains ambiguous pronouns.
        """
        for pronoun in AMBIGUOUS_PRONOUNS:
            # Match as whole word
            pattern = rf"\b{re.escape(pronoun)}\b"
            if re.search(pattern, query):
                return True
        return False

    def _has_followup_pattern(self, query: str) -> bool:
        """Check if query matches follow-up patterns.

        Args:
            query: Normalized query string.

        Returns:
            True if query matches a follow-up pattern.
        """
        return any(re.search(pattern, query, re.IGNORECASE) for pattern in FOLLOWUP_PATTERNS)

    def _is_missing_fiscal_terms(self, query: str) -> bool:
        """Check if query is missing key fiscal terms.

        Args:
            query: Normalized query string.

        Returns:
            True if query lacks any fiscal/legal terms.
        """
        return all(term not in query for term in FISCAL_TERMS)

    def _calculate_score(self, indicators: list[str], query: str) -> float:
        """Calculate ambiguity score based on indicators.

        Args:
            indicators: List of detected indicators.
            query: Normalized query string.

        Returns:
            Ambiguity score between 0.0 and 1.0.
        """
        if not indicators:
            return 0.0

        # Sum weighted scores for each indicator
        score = 0.0
        for indicator in indicators:
            weight = INDICATOR_WEIGHTS.get(indicator, 0.1)
            score += weight

        # Apply modifiers based on query characteristics
        # Very short queries get extra penalty
        words = [w for w in query.split() if w]
        if len(words) <= 2:
            score += 0.2

        # Multiple indicators compound the ambiguity
        if len(indicators) >= 3:
            score += 0.15

        # Ensure score is bounded
        return min(max(score, 0.0), 1.0)

    def _determine_strategy(
        self,
        score: float,
        indicators: list[str],
        conversation_history: list[dict] | None,
    ) -> str:
        """Determine recommended HyDE strategy.

        Args:
            score: Calculated ambiguity score.
            indicators: Detected ambiguity indicators.
            conversation_history: Optional conversation context.

        Returns:
            Strategy string: "standard", "conversational", or "multi_variant".
        """
        # High ambiguity always needs multi-variant
        if score >= AMBIGUITY_THRESHOLD_HIGH:
            return "multi_variant"

        # Follow-up patterns benefit from conversational context
        if "followup_pattern" in indicators and conversation_history:
            return "conversational"

        # Pronoun ambiguity with history can use conversational
        if "pronoun_ambiguity" in indicators and conversation_history:
            return "conversational"

        # Medium ambiguity - depends on context availability
        if score >= AMBIGUITY_THRESHOLD_LOW:
            if conversation_history:
                return "conversational"
            return "multi_variant"

        # Low ambiguity - standard is fine
        return "standard"


# =============================================================================
# Factory Functions
# =============================================================================


def get_query_ambiguity_detector() -> QueryAmbiguityDetector:
    """Get or create QueryAmbiguityDetector singleton instance.

    Returns:
        QueryAmbiguityDetector instance.

    Example:
        >>> detector = get_query_ambiguity_detector()
        >>> result = detector.detect("E per l'IVA?")
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = QueryAmbiguityDetector()
    return _detector_instance


def reset_detector() -> None:
    """Reset the singleton instance (for testing)."""
    global _detector_instance
    _detector_instance = None
