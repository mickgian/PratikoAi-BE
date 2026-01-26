"""Contradiction detection for web verification.

Detects contradictions between KB answers and web search results.
"""

import re

from app.core.logging import logger

from .constants import CONTRADICTION_KEYWORDS, MIN_CAVEAT_CONFIDENCE, SENSITIVE_TOPICS
from .types import ContradictionInfo


class ContradictionDetector:
    """Detects contradictions between KB answers and web content."""

    def detect_contradictions(
        self,
        kb_answer: str,
        web_results: list[dict],
    ) -> list[ContradictionInfo]:
        """Detect contradictions between KB answer and web results.

        Args:
            kb_answer: The KB-generated answer
            web_results: Web search results (may include is_ai_synthesis flag)

        Returns:
            List of detected contradictions
        """
        contradictions = []
        kb_lower = kb_answer.lower()

        for result in web_results:
            snippet = result.get("snippet", "")
            if not snippet:
                continue

            detected = self._find_contradiction_indicators(snippet.lower(), kb_lower)
            if detected:
                contradiction = self._build_contradiction(result, detected, kb_answer)
                contradictions.append(contradiction)

        logger.debug(
            "web_verification_contradictions_detected",
            count=len(contradictions),
            topics=[c.topic for c in contradictions],
        )

        return contradictions

    def _find_contradiction_indicators(self, snippet_lower: str, kb_lower: str) -> tuple[str, str] | None:
        """Find contradiction indicators between snippet and KB answer.

        Args:
            snippet_lower: Lowercased web snippet
            kb_lower: Lowercased KB answer

        Returns:
            Tuple of (detected_topic, web_claim) or None if no contradiction
        """
        for keyword in CONTRADICTION_KEYWORDS:
            if keyword not in snippet_lower:
                continue

            # Check if this is about a topic mentioned in KB
            for sensitive_topic in SENSITIVE_TOPICS:
                if sensitive_topic in kb_lower and sensitive_topic in snippet_lower:
                    return (sensitive_topic, snippet_lower[:200])

            # Check for date/deadline contradictions
            has_date_topic = any(term in kb_lower for term in ["scadenza", "data", "termine"])
            date_keywords = ["prorogato", "prorogata", "proroga", "posticipato", "nuova scadenza"]
            if has_date_topic and keyword in date_keywords:
                return ("scadenza/data", snippet_lower[:200])

        return None

    def _build_contradiction(
        self,
        result: dict,
        detected: tuple[str, str],
        kb_answer: str,
    ) -> ContradictionInfo:
        """Build a ContradictionInfo from detection results.

        Args:
            result: Web search result dict
            detected: Tuple of (topic, web_claim)
            kb_answer: Original KB answer

        Returns:
            ContradictionInfo instance
        """
        topic, web_claim = detected
        is_ai_synthesis = result.get("is_ai_synthesis", False)

        confidence = self._calculate_contradiction_confidence(
            kb_answer, result.get("snippet", ""), topic, is_ai_synthesis
        )

        return ContradictionInfo(
            topic=topic,
            kb_claim=self._extract_kb_claim(kb_answer, topic),
            web_claim=web_claim,
            source_url=result.get("link", ""),
            source_title=result.get("title", ""),
            confidence=confidence,
        )

    def _calculate_contradiction_confidence(
        self,
        kb_answer: str,
        web_snippet: str,
        topic: str,
        is_ai_synthesis: bool = False,
    ) -> float:
        """Calculate confidence score for a contradiction.

        Args:
            kb_answer: KB answer text
            web_snippet: Web snippet text
            topic: Detected topic
            is_ai_synthesis: Whether the web snippet is from AI synthesis (Brave AI)

        Returns:
            Confidence score 0.0-1.0
        """
        # AI synthesis gets higher base confidence (0.65 vs 0.5)
        confidence = 0.65 if is_ai_synthesis else 0.5

        # Higher confidence if topic is specific
        if topic in SENSITIVE_TOPICS:
            confidence += 0.15

        # Higher confidence if web snippet has specific details
        if re.search(r"\d{1,2}/\d{1,2}/\d{4}", web_snippet):  # Contains date
            confidence += 0.1
        if re.search(r"art\.?\s*\d+", web_snippet, re.IGNORECASE):  # Contains article ref
            confidence += 0.1

        # Higher confidence if contradiction keyword is explicit
        explicit_keywords = ["non", "esclusi", "escluso", "richiede", "dipende", "accordo"]
        if any(kw in web_snippet.lower() for kw in explicit_keywords):
            confidence += 0.15

        return min(confidence, 1.0)

    def _extract_kb_claim(self, kb_answer: str, topic: str) -> str:
        """Extract the KB's claim about a topic.

        Args:
            kb_answer: Full KB answer
            topic: Topic to extract claim for

        Returns:
            Extracted claim string
        """
        # Find sentence containing the topic
        sentences = re.split(r"[.!?]", kb_answer)
        for sentence in sentences:
            if topic in sentence.lower():
                return sentence.strip()[:200]

        # Fallback: return first 100 chars
        return kb_answer[:100]


# Singleton instance
contradiction_detector = ContradictionDetector()
