"""Local rule-based query complexity classifier.

DEV-251 Phase 3: Replaces GPT-4o-mini classifier with fast, cost-free local classification.

Uses heuristics based on:
- Query length and structure
- Detected domains
- Conversation history
- Keyword patterns

Performance: <1ms vs 300-500ms for GPT-4o-mini
Cost: $0 vs ~$0.00015 per classification
"""

import re
from dataclasses import dataclass
from enum import Enum

from app.core.logging import logger


class LocalComplexity(str, Enum):
    """Local complexity classification results."""

    SIMPLE = "simple"
    COMPLEX = "complex"
    MULTI_DOMAIN = "multi_domain"


@dataclass
class ClassificationResult:
    """Result of local classification with confidence."""

    complexity: LocalComplexity
    confidence: float  # 0.0-1.0
    reasons: list[str]


# Keyword patterns for classification
SIMPLE_KEYWORDS = {
    # Direct questions about rates/deadlines
    "aliquota",
    "scadenza",
    "termine",
    "quanto costa",
    "quanto è",
    "qual è",
    "quale è",
    "quando",
    "dove",
    "chi",
    # Basic definitions
    "cos'è",
    "cosa significa",
    "definizione",
    # Yes/no questions
    "è possibile",
    "si può",
    "bisogna",
    "devo",
    "serve",
}

COMPLEX_KEYWORDS = {
    # Procedural questions
    "come",
    "come si fa",
    "procedura",
    "modalità",
    "passaggi",
    # Specific case scenarios
    "nel caso",
    "se",
    "qualora",
    "ipotesi",
    "situazione",
    # Comparisons
    "differenza",
    "confronto",
    "meglio",
    "conviene",
    # Legal interpretations
    "interpretazione",
    "applicazione",
    "calcolo",
    "determinazione",
}

MULTI_DOMAIN_KEYWORDS = {
    # Cross-domain terms
    "contributivo",
    "previdenziale",
    "fiscale",
    "tributario",
    "lavoro",
    "dipendente",
    "autonomo",
    "partita iva",
    # Combined scenarios
    "assunzione",
    "cessazione",
    "trasformazione",
    "licenziamento",
    "dimissioni",
}


class LocalClassifier:
    """Rule-based query complexity classifier.

    DEV-251: Provides fast, cost-free classification for query routing.
    Falls back to GPT-4o-mini only when confidence is low.

    Example:
        classifier = LocalClassifier()
        result = classifier.classify(
            query="Qual è l'aliquota IVA?",
            domains=["fiscale"],
            has_history=False,
            has_documents=True,
        )
        # result.complexity = SIMPLE, result.confidence = 0.9
    """

    def __init__(self, confidence_threshold: float = 0.7):
        """Initialize classifier.

        Args:
            confidence_threshold: Minimum confidence to use local result.
                                  Below this, GPT fallback is recommended.
        """
        self.confidence_threshold = confidence_threshold
        logger.debug("local_classifier_initialized", threshold=confidence_threshold)

    def classify(
        self,
        query: str,
        domains: list[str] | None = None,
        has_history: bool = False,
        has_documents: bool = False,
    ) -> ClassificationResult:
        """Classify query complexity using rule-based heuristics.

        Args:
            query: User query to classify
            domains: Detected domains (fiscale, lavoro, legale)
            has_history: Whether conversation has history
            has_documents: Whether KB documents are available

        Returns:
            ClassificationResult with complexity, confidence, and reasons
        """
        query_lower = query.lower().strip()
        domains = domains or []
        reasons: list[str] = []

        # Initialize scores
        simple_score = 0.0
        complex_score = 0.0
        multi_domain_score = 0.0

        # Factor 1: Query length
        query_length = len(query)
        if query_length < 50:
            simple_score += 0.3
            reasons.append("short_query")
        elif query_length < 150:
            simple_score += 0.1
            complex_score += 0.1
        else:
            complex_score += 0.3
            reasons.append("long_query")

        # Factor 2: Number of domains
        num_domains = len(domains)
        if num_domains >= 2:
            multi_domain_score += 0.5
            reasons.append(f"multi_domain_{num_domains}")
        elif num_domains == 1:
            simple_score += 0.1

        # Factor 3: Conversation history
        if has_history:
            complex_score += 0.15
            reasons.append("has_history")

        # Factor 4: Question type analysis
        if self._is_simple_question(query_lower):
            simple_score += 0.35
            reasons.append("simple_question_pattern")
        elif self._is_complex_question(query_lower):
            complex_score += 0.35
            reasons.append("complex_question_pattern")

        # Factor 5: Keyword matching
        simple_keywords_found = self._count_keywords(query_lower, SIMPLE_KEYWORDS)
        complex_keywords_found = self._count_keywords(query_lower, COMPLEX_KEYWORDS)
        multi_domain_keywords_found = self._count_keywords(query_lower, MULTI_DOMAIN_KEYWORDS)

        if simple_keywords_found > 0:
            simple_score += 0.2 * min(simple_keywords_found, 2)
            reasons.append(f"simple_keywords_{simple_keywords_found}")

        if complex_keywords_found > 0:
            complex_score += 0.2 * min(complex_keywords_found, 2)
            reasons.append(f"complex_keywords_{complex_keywords_found}")

        if multi_domain_keywords_found >= 2:
            multi_domain_score += 0.3
            reasons.append(f"multi_domain_keywords_{multi_domain_keywords_found}")

        # Factor 6: Question complexity indicators
        if self._has_conditional_clauses(query_lower):
            complex_score += 0.2
            reasons.append("conditional_clauses")

        if self._has_multiple_questions(query_lower):
            complex_score += 0.45  # High weight - multiple questions indicate complexity
            simple_score -= 0.2  # Reduce simple score for multi-question queries
            reasons.append("multiple_questions")

        # Factor 6b: Comparison/difference questions
        if self._is_comparison_question(query_lower):
            complex_score += 0.35
            reasons.append("comparison_question")

        # Factor 7: Specific legal complexity
        if self._mentions_specific_case(query_lower):
            complex_score += 0.25
            reasons.append("specific_case")

        # Determine final classification
        scores = {
            LocalComplexity.SIMPLE: simple_score,
            LocalComplexity.COMPLEX: complex_score,
            LocalComplexity.MULTI_DOMAIN: multi_domain_score,
        }

        # Multi-domain takes precedence if score is significant
        if multi_domain_score >= 0.5:
            complexity = LocalComplexity.MULTI_DOMAIN
            confidence = min(multi_domain_score / 1.0, 0.95)
        elif complex_score >= simple_score and complex_score >= 0.4:
            # Complex wins ties if it has significant score
            # This handles cases where both simple and complex indicators are present
            complexity = LocalComplexity.COMPLEX
            confidence = min(complex_score / 1.0, 0.95)
        else:
            complexity = LocalComplexity.SIMPLE
            # Higher confidence for clearly simple queries
            confidence = min((simple_score + 0.2) / 1.0, 0.95)

        logger.info(
            "local_classification_complete",
            complexity=complexity.value,
            confidence=round(confidence, 2),
            scores={k.value: round(v, 2) for k, v in scores.items()},
            query_length=query_length,
            num_domains=num_domains,
        )

        return ClassificationResult(
            complexity=complexity,
            confidence=confidence,
            reasons=reasons,
        )

    def should_use_gpt_fallback(self, result: ClassificationResult) -> bool:
        """Check if GPT fallback is recommended due to low confidence.

        Args:
            result: Local classification result

        Returns:
            True if GPT fallback is recommended
        """
        return result.confidence < self.confidence_threshold

    def _is_simple_question(self, query: str) -> bool:
        """Check if query matches simple question patterns."""
        simple_patterns = [
            r"^qual[ei]?\s+(è|sono)",  # Qual è, Quali sono
            r"^quanto\s+(è|costa|dura)",  # Quanto è, costa, dura
            r"^quando\s+(scade|si\s+deve)",  # Quando scade
            r"^(cos'è|cosa\s+significa)",  # Cos'è
            r"^(è|sono)\s+(?:possibile|obbligatori)",  # È possibile
            r"^\s*(?:si|no)\s*[?]?\s*$",  # Yes/no
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in simple_patterns)

    def _is_complex_question(self, query: str) -> bool:
        """Check if query matches complex question patterns."""
        complex_patterns = [
            r"^come\s+(?:si\s+fa|devo|posso|calcol)",  # Come si fa, come calcolare
            r"(?:nel\s+caso|nell'ipotesi)\s+(?:in\s+cui|che)",  # Nel caso in cui
            r"qual[ei]?\s+(?:procedura|modalità|passaggi)",  # Quale procedura
            r"(?:differenza|confronto)\s+(?:tra|fra)",  # Differenza tra
            r"(?:se|qualora|laddove)\s+.{10,}",  # Conditional with content
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in complex_patterns)

    def _count_keywords(self, query: str, keywords: set[str]) -> int:
        """Count how many keywords from set appear in query."""
        count = 0
        for keyword in keywords:
            if keyword in query:
                count += 1
        return count

    def _has_conditional_clauses(self, query: str) -> bool:
        """Check for conditional language indicating complexity."""
        conditional_patterns = [
            r"\bse\s+(?!stesso)",  # se (but not "se stesso")
            r"\bqualora\b",
            r"\bnel\s+caso\b",
            r"\bladdove\b",
            r"\bquando\s+.{20,}",  # quando with substantial following text
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in conditional_patterns)

    def _has_multiple_questions(self, query: str) -> bool:
        """Check if query contains multiple questions."""
        question_marks = query.count("?")
        return question_marks >= 2

    def _mentions_specific_case(self, query: str) -> bool:
        """Check if query mentions a specific case or scenario."""
        case_patterns = [
            r"(?:mio|nostro|suo)\s+(?:caso|situazione)",  # Mio caso
            r"(?:azienda|società|ditta)\s+(?:che|con)",  # Azienda che
            r"(?:dipendente|lavoratore)\s+(?:che|con|a)",  # Dipendente che
            r"(?:cliente|fornitore)\s+(?:che|con)",  # Cliente che
            r"\b(?:esempio|caso\s+specifico)\b",  # Esempio, caso specifico
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in case_patterns)

    def _is_comparison_question(self, query: str) -> bool:
        """Check if query is asking for a comparison between options."""
        comparison_patterns = [
            r"differenza\s+(?:tra|fra)",  # Differenza tra
            r"(?:qual\s+è\s+la|quale)\s+differenza",  # Qual è la differenza
            r"confronto\s+(?:tra|fra)",  # Confronto tra
            r"(?:meglio|conviene)\s+.{3,}\s+o\s+",  # Meglio X o Y
            r"(?:vantaggi|svantaggi)\s+(?:del|della|di)",  # Vantaggi/svantaggi
            r"\bvs\.?\b",  # X vs Y
            r"(?:rispetto|comparato)\s+(?:a|al|alla)",  # Rispetto a
        ]
        return any(re.search(p, query, re.IGNORECASE) for p in comparison_patterns)


# Singleton instance
_classifier_instance: LocalClassifier | None = None


def get_local_classifier() -> LocalClassifier:
    """Get singleton LocalClassifier instance."""
    global _classifier_instance
    if _classifier_instance is None:
        _classifier_instance = LocalClassifier()
    return _classifier_instance


def reset_local_classifier() -> None:
    """Reset singleton instance (for testing)."""
    global _classifier_instance
    _classifier_instance = None
