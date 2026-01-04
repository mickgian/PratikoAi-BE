"""RiskAnalyzer Service for Italian Tax/Legal Sanction Risk Analysis (DEV-231).

This service analyzes hypotheses for sanction risk based on Italian tax law
categories. It assigns risk levels, extracts risk factors, and generates
mitigation actions.

Risk Categories (from Italian tax law):
| Level    | Sanction Range        | Examples                              |
|----------|----------------------|---------------------------------------|
| CRITICAL | >100% tax + criminal | Frode fiscale, falsa fatturazione     |
| HIGH     | 90-180% tax          | Omessa dichiarazione                  |
| MEDIUM   | 30-90% tax           | Errori formali sostanziali            |
| LOW      | 0-30% tax            | Ritardi, errori formali minori        |

Example:
    from app.services.risk_analyzer import get_risk_analyzer

    analyzer = get_risk_analyzer()
    result = analyzer.analyze_hypothesis(hypothesis)
    print(result.risk_level)  # 'critical'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import structlog

from app.schemas.reasoning import RiskLevel

if TYPE_CHECKING:
    from app.services.tree_of_thoughts_reasoner import ToTHypothesis

logger = structlog.get_logger(__name__)

# =============================================================================
# Module-level singleton
# =============================================================================
_analyzer_instance: RiskAnalyzer | None = None


# =============================================================================
# Risk Keywords (Italian)
# =============================================================================

# CRITICAL risk keywords (>100% tax + criminal penalties)
CRITICAL_KEYWORDS = [
    "frode fiscale",
    "frode",
    "evasione fiscale",
    "evasione",
    "falsa fatturazione",
    "fatture false",
    "fattura falsa",
    "reato tributario",
    "reato penale",
    "occultamento",
    "sottrazione fraudolenta",
    "dichiarazione fraudolenta",
    "emissione di fatture",  # for false invoices
    "utilizzo di fatture",  # for false invoices
    "penale",
]

# HIGH risk keywords (90-180% tax penalties)
HIGH_KEYWORDS = [
    "omessa dichiarazione",
    "dichiarazione omessa",
    "dichiarazione infedele",
    "omesso versamento",
    "versamento omesso",
    "indebita compensazione",
    "compensazione indebita",
    "infedele",
    "omissione",
    "omessa",
    "120%",
    "180%",
    "240%",
]

# MEDIUM risk keywords (30-90% tax penalties)
MEDIUM_KEYWORDS = [
    "errori formali",
    "errore formale",
    "violazione formale",
    "irregolarità",
    "sanzione amministrativa",
    "rettifica",
    "30%",
    "90%",
]

# LOW risk keywords (0-30% tax penalties)
LOW_KEYWORDS = [
    "ritardo",
    "ritardi",
    "lieve",
    "minore",
    "minori",
    "errore minore",
    "ravvedimento sprint",
]


# =============================================================================
# Mitigation Action Templates
# =============================================================================

CRITICAL_MITIGATION_ACTIONS = [
    "Consultare immediatamente un avvocato tributarista o penalista",
    "Non procedere con l'operazione senza parere legale",
    "Valutare la possibilità di autodenuncia (disclosure)",
]

HIGH_MITIGATION_ACTIONS = [
    "Valutare il ravvedimento operoso per ridurre le sanzioni",
    "Consultare un commercialista per la regolarizzazione",
    "Verificare i termini per la sanatoria",
]

MEDIUM_MITIGATION_ACTIONS = [
    "Correggere gli errori formali tramite dichiarazione integrativa",
    "Valutare il ravvedimento operoso",
]

LOW_MITIGATION_ACTIONS = [
    "Regolarizzare tempestivamente per minimizzare le sanzioni",
]


# =============================================================================
# Sanction Ranges
# =============================================================================

SANCTION_RANGES = {
    RiskLevel.CRITICAL.value: ">100% dell'imposta + sanzioni penali",
    RiskLevel.HIGH.value: "90%-240% dell'imposta evasa",
    RiskLevel.MEDIUM.value: "30%-90% dell'imposta",
    RiskLevel.LOW.value: "0%-30% dell'imposta o sanzioni fisse minime",
}


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class RiskResult:
    """Result of risk analysis for a single hypothesis.

    Attributes:
        hypothesis_id: ID of the analyzed hypothesis
        risk_level: Detected risk level (critical, high, medium, low)
        risk_factors: List of detected risk factors
        mitigation_actions: Suggested mitigation actions
        should_flag: Whether this risk should be flagged to user
        sanction_range: Expected sanction range description
    """

    hypothesis_id: str
    risk_level: str
    risk_factors: list[str] = field(default_factory=list)
    mitigation_actions: list[str] | None = None
    should_flag: bool = False
    sanction_range: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with all fields.
        """
        return {
            "hypothesis_id": self.hypothesis_id,
            "risk_level": self.risk_level,
            "risk_factors": self.risk_factors,
            "mitigation_actions": self.mitigation_actions,
            "should_flag": self.should_flag,
            "sanction_range": self.sanction_range,
        }


# =============================================================================
# RiskAnalyzer Class
# =============================================================================


class RiskAnalyzer:
    """Service for analyzing sanction risk in Italian tax/legal hypotheses.

    Detects risk levels based on Italian tax law categories and generates
    appropriate mitigation actions.

    Example:
        >>> analyzer = RiskAnalyzer()
        >>> result = analyzer.analyze_hypothesis({
        ...     "id": "H1",
        ...     "conclusion": "Potrebbe configurare frode fiscale"
        ... })
        >>> print(result.risk_level)
        'critical'
    """

    def __init__(self) -> None:
        """Initialize the RiskAnalyzer."""
        logger.debug("risk_analyzer_initialized")

    def analyze_hypothesis(self, hypothesis: dict) -> RiskResult:
        """Analyze a single hypothesis for risk.

        Args:
            hypothesis: Hypothesis dict with 'id', 'conclusion', 'sources_used'

        Returns:
            RiskResult with risk assessment.

        Example:
            >>> result = analyzer.analyze_hypothesis({
            ...     "id": "H1",
            ...     "conclusion": "Omessa dichiarazione"
            ... })
        """
        hypothesis_id = hypothesis.get("id", "unknown")
        conclusion = hypothesis.get("conclusion", "")
        reasoning_path = hypothesis.get("reasoning_path", "")

        # Combine text for analysis
        text = f"{conclusion} {reasoning_path}".lower()

        # Detect risk level
        risk_level = self._detect_risk_level(text)

        # Extract risk factors
        risk_factors = self._extract_risk_factors(text, risk_level)

        # Generate mitigation actions
        mitigation_actions = self._get_mitigation_actions(risk_level)

        # Determine if should flag
        should_flag = risk_level in (RiskLevel.CRITICAL.value, RiskLevel.HIGH.value)

        # Get sanction range
        sanction_range = SANCTION_RANGES.get(risk_level)

        logger.debug(
            "hypothesis_risk_analyzed",
            hypothesis_id=hypothesis_id,
            risk_level=risk_level,
            should_flag=should_flag,
        )

        return RiskResult(
            hypothesis_id=hypothesis_id,
            risk_level=risk_level,
            risk_factors=risk_factors,
            mitigation_actions=mitigation_actions,
            should_flag=should_flag,
            sanction_range=sanction_range,
        )

    def analyze_tot_hypothesis(self, hypothesis: ToTHypothesis) -> RiskResult:
        """Analyze a ToTHypothesis object for risk.

        Args:
            hypothesis: ToTHypothesis object from TreeOfThoughtsReasoner

        Returns:
            RiskResult with risk assessment.
        """
        return self.analyze_hypothesis(
            {
                "id": hypothesis.id,
                "conclusion": hypothesis.conclusion,
                "reasoning_path": hypothesis.reasoning_path,
                "sources_used": hypothesis.sources_used,
            }
        )

    def analyze_hypotheses(self, hypotheses: list[dict]) -> list[RiskResult]:
        """Analyze multiple hypotheses for risk.

        Args:
            hypotheses: List of hypothesis dicts

        Returns:
            List of RiskResult objects.
        """
        return [self.analyze_hypothesis(h) for h in hypotheses]

    def enrich_hypotheses(self, hypotheses: list[ToTHypothesis]) -> list[ToTHypothesis]:
        """Enrich ToTHypothesis objects with risk analysis.

        Modifies the hypothesis objects in place to add risk_level and risk_factors.

        Args:
            hypotheses: List of ToTHypothesis objects

        Returns:
            The same list with risk fields populated.
        """
        for hypothesis in hypotheses:
            result = self.analyze_tot_hypothesis(hypothesis)
            hypothesis.risk_level = result.risk_level
            hypothesis.risk_factors = result.risk_factors

        return hypotheses

    def get_highest_risk(self, results: list[RiskResult]) -> RiskResult:
        """Get the highest risk result from a list.

        Args:
            results: List of RiskResult objects

        Returns:
            RiskResult with highest risk level.
        """
        if not results:
            raise ValueError("No results to analyze")

        # Risk level priority (lower index = higher priority)
        priority = {
            RiskLevel.CRITICAL.value: 0,
            RiskLevel.HIGH.value: 1,
            RiskLevel.MEDIUM.value: 2,
            RiskLevel.LOW.value: 3,
        }

        return min(results, key=lambda r: priority.get(r.risk_level, 99))

    def get_risk_summary(self, results: list[RiskResult]) -> dict[str, Any]:
        """Get aggregate risk summary for multiple results.

        Args:
            results: List of RiskResult objects

        Returns:
            Summary dict with counts and flags.
        """
        critical_count = sum(1 for r in results if r.risk_level == RiskLevel.CRITICAL.value)
        high_count = sum(1 for r in results if r.risk_level == RiskLevel.HIGH.value)
        medium_count = sum(1 for r in results if r.risk_level == RiskLevel.MEDIUM.value)
        low_count = sum(1 for r in results if r.risk_level == RiskLevel.LOW.value)

        has_flagged = any(r.should_flag for r in results)

        return {
            "critical_count": critical_count,
            "high_count": high_count,
            "medium_count": medium_count,
            "low_count": low_count,
            "total_count": len(results),
            "has_flagged_risks": has_flagged,
            "highest_risk": self.get_highest_risk(results).risk_level if results else None,
        }

    def _detect_risk_level(self, text: str) -> str:
        """Detect risk level from text content.

        Args:
            text: Lowercase text to analyze

        Returns:
            Risk level string (critical, high, medium, low)
        """
        # Check for CRITICAL keywords first
        for keyword in CRITICAL_KEYWORDS:
            if keyword in text:
                return RiskLevel.CRITICAL.value

        # Check for HIGH keywords
        for keyword in HIGH_KEYWORDS:
            if keyword in text:
                return RiskLevel.HIGH.value

        # Check for MEDIUM keywords
        for keyword in MEDIUM_KEYWORDS:
            if keyword in text:
                return RiskLevel.MEDIUM.value

        # Check for explicit LOW keywords
        for keyword in LOW_KEYWORDS:
            if keyword in text:
                return RiskLevel.LOW.value

        # Default to LOW
        return RiskLevel.LOW.value

    def _extract_risk_factors(self, text: str, risk_level: str) -> list[str]:
        """Extract risk factors from text.

        Args:
            text: Lowercase text to analyze
            risk_level: Detected risk level

        Returns:
            List of risk factor descriptions.
        """
        factors = []

        # Extract matched keywords as factors
        if risk_level == RiskLevel.CRITICAL.value:
            for keyword in CRITICAL_KEYWORDS:
                if keyword in text:
                    factors.append(f"Rilevato: {keyword}")

        elif risk_level == RiskLevel.HIGH.value:
            for keyword in HIGH_KEYWORDS:
                if keyword in text:
                    factors.append(f"Rilevato: {keyword}")

        elif risk_level == RiskLevel.MEDIUM.value:
            for keyword in MEDIUM_KEYWORDS:
                if keyword in text:
                    factors.append(f"Rilevato: {keyword}")

        # Extract sanction percentages
        percentage_matches = re.findall(r"\d+%", text)
        for pct in percentage_matches:
            if pct not in str(factors):
                factors.append(f"Sanzione indicata: {pct}")

        # Deduplicate while preserving order
        seen = set()
        unique_factors = []
        for f in factors:
            if f not in seen:
                seen.add(f)
                unique_factors.append(f)

        return unique_factors

    def _get_mitigation_actions(self, risk_level: str) -> list[str] | None:
        """Get mitigation actions for risk level.

        Args:
            risk_level: Risk level string

        Returns:
            List of mitigation action strings or None.
        """
        if risk_level == RiskLevel.CRITICAL.value:
            return CRITICAL_MITIGATION_ACTIONS.copy()
        elif risk_level == RiskLevel.HIGH.value:
            return HIGH_MITIGATION_ACTIONS.copy()
        elif risk_level == RiskLevel.MEDIUM.value:
            return MEDIUM_MITIGATION_ACTIONS.copy()
        elif risk_level == RiskLevel.LOW.value:
            return None  # No actions for low risk
        return None


# =============================================================================
# Factory Functions
# =============================================================================


def get_risk_analyzer() -> RiskAnalyzer:
    """Get or create RiskAnalyzer singleton instance.

    Returns:
        RiskAnalyzer instance.

    Example:
        >>> analyzer = get_risk_analyzer()
        >>> result = analyzer.analyze_hypothesis(hypothesis)
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = RiskAnalyzer()
    return _analyzer_instance


def reset_analyzer() -> None:
    """Reset the singleton instance (for testing)."""
    global _analyzer_instance
    _analyzer_instance = None
