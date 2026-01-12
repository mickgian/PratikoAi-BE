"""Document Classifier for Tiered Ingestion (ADR-023).

Classifies documents into tiers based on rules and content analysis.
Determines parsing strategy: article_level, standard_chunking, or light_indexing.

Usage:
    from app.services.document_classifier import DocumentClassifier

    classifier = DocumentClassifier()
    result = classifier.classify(
        title="LEGGE 30 dicembre 2025, n. 199",
        source="gazzetta_ufficiale",
    )
    print(f"Tier: {result.tier}, Strategy: {result.parsing_strategy}")
"""

import re
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import yaml

from app.core.logging import logger


class DocumentTier(IntEnum):
    """Document importance tiers."""

    CRITICAL = 1  # Article-level parsing for laws
    IMPORTANT = 2  # Standard chunking for circolars
    REFERENCE = 3  # Light indexing for news


class ParsingStrategy:
    """Parsing strategies for each tier."""

    ARTICLE_LEVEL = "article_level"
    STANDARD_CHUNKING = "standard_chunking"
    LIGHT_INDEXING = "light_indexing"


@dataclass
class ClassificationResult:
    """Result of document classification."""

    tier: DocumentTier
    parsing_strategy: str
    confidence: float
    matched_pattern: str | None
    detected_topics: list[str]
    is_explicit_match: bool


class DocumentClassifier:
    """Classifies documents into tiers for appropriate ingestion.

    The classifier uses a priority-based approach:
    1. Explicit document list (highest priority, confidence=1.0)
    2. Regex pattern matching (confidence=0.9)
    3. Source-based classification (confidence=0.7)
    4. Default to Tier 3 (confidence=0.5)

    Example:
        classifier = DocumentClassifier()

        # Classify a critical law
        result = classifier.classify("LEGGE 30 dicembre 2025, n. 199")
        assert result.tier == DocumentTier.CRITICAL
        assert result.parsing_strategy == ParsingStrategy.ARTICLE_LEVEL

        # Classify a circular
        result = classifier.classify("Circolare n. 19/E del 2025")
        assert result.tier == DocumentTier.IMPORTANT
    """

    def __init__(self, config_path: str | None = None):
        """Initialize the classifier.

        Args:
            config_path: Path to config YAML. Defaults to config/document_tiers.yaml
        """
        if config_path is None:
            # Use default path relative to project root
            config_path = "config/document_tiers.yaml"

        self._config = self._load_config(config_path)
        self._compile_patterns()

    def _load_config(self, path: str) -> dict[str, Any]:
        """Load tier configuration from YAML."""
        config_path = Path(path)
        if not config_path.exists():
            logger.warning(f"Tier config not found at {path}, using defaults")
            return self._default_config()

        with open(config_path) as f:
            return yaml.safe_load(f)

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        self._compiled_patterns: dict[DocumentTier, list[tuple[re.Pattern, str]]] = {}
        self._exact_patterns: dict[DocumentTier, list[str]] = {}

        for tier_name, tier_config in self._config.get("tiers", {}).items():
            tier = self._tier_from_name(tier_name)
            patterns = []
            exact = []

            for pattern_def in tier_config.get("patterns", []):
                if "regex" in pattern_def:
                    try:
                        compiled = re.compile(pattern_def["regex"], re.IGNORECASE)
                        patterns.append((compiled, pattern_def["regex"]))
                    except re.error as e:
                        logger.warning(f"Invalid regex pattern: {pattern_def['regex']}: {e}")
                elif "exact" in pattern_def:
                    exact.append(pattern_def["exact"].lower())

            self._compiled_patterns[tier] = patterns
            self._exact_patterns[tier] = exact

    def classify(
        self,
        title: str,
        source: str | None = None,
        content_preview: str | None = None,
    ) -> ClassificationResult:
        """Classify a document into a tier.

        Args:
            title: Document title (e.g., "LEGGE 30 dicembre 2025, n. 199")
            source: Source identifier (e.g., "gazzetta_ufficiale", "inps_circolari")
            content_preview: First ~500 chars of content for topic detection

        Returns:
            ClassificationResult with tier, strategy, confidence, and detected topics
        """
        # 1. Check explicit document list (highest priority)
        explicit_result = self._check_explicit_documents(title)
        if explicit_result:
            explicit_result.detected_topics = self._detect_topics(title, content_preview)
            return explicit_result

        # 2. Check regex patterns
        pattern_result = self._check_patterns(title)
        if pattern_result:
            pattern_result.detected_topics = self._detect_topics(title, content_preview)
            return pattern_result

        # 3. Check exact match patterns (case-insensitive)
        exact_result = self._check_exact_patterns(title)
        if exact_result:
            exact_result.detected_topics = self._detect_topics(title, content_preview)
            return exact_result

        # 4. Check source-based classification
        source_result = self._check_source(source)
        if source_result:
            source_result.detected_topics = self._detect_topics(title, content_preview)
            return source_result

        # 5. Default to Tier 3 (Reference)
        return ClassificationResult(
            tier=DocumentTier.REFERENCE,
            parsing_strategy=ParsingStrategy.LIGHT_INDEXING,
            confidence=0.5,
            matched_pattern=None,
            detected_topics=self._detect_topics(title, content_preview),
            is_explicit_match=False,
        )

    def _check_explicit_documents(self, title: str) -> ClassificationResult | None:
        """Check if title matches explicit document list."""
        # Empty titles should not match
        if not title or not title.strip():
            return None

        tier_1_config = self._config.get("tiers", {}).get("tier_1_critical", {})
        explicit_docs = tier_1_config.get("explicit_documents", [])

        title_lower = title.lower()
        for doc_title in explicit_docs:
            doc_lower = doc_title.lower()
            # Check both directions for flexible matching
            if doc_lower in title_lower or title_lower in doc_lower:
                return ClassificationResult(
                    tier=DocumentTier.CRITICAL,
                    parsing_strategy=ParsingStrategy.ARTICLE_LEVEL,
                    confidence=1.0,
                    matched_pattern=f"explicit:{doc_title}",
                    detected_topics=[],
                    is_explicit_match=True,
                )
        return None

    def _check_patterns(self, title: str) -> ClassificationResult | None:
        """Check title against compiled regex patterns."""
        for tier, patterns in self._compiled_patterns.items():
            for compiled, pattern_str in patterns:
                if compiled.search(title):
                    strategy = self._strategy_for_tier(tier)
                    return ClassificationResult(
                        tier=tier,
                        parsing_strategy=strategy,
                        confidence=0.9,
                        matched_pattern=pattern_str,
                        detected_topics=[],
                        is_explicit_match=False,
                    )
        return None

    def _check_exact_patterns(self, title: str) -> ClassificationResult | None:
        """Check title against exact match patterns (case-insensitive)."""
        title_lower = title.lower()
        for tier, exact_patterns in self._exact_patterns.items():
            for pattern in exact_patterns:
                if pattern in title_lower:
                    strategy = self._strategy_for_tier(tier)
                    return ClassificationResult(
                        tier=tier,
                        parsing_strategy=strategy,
                        confidence=0.85,
                        matched_pattern=f"exact:{pattern}",
                        detected_topics=[],
                        is_explicit_match=False,
                    )
        return None

    def _check_source(self, source: str | None) -> ClassificationResult | None:
        """Check source-based classification."""
        if not source:
            return None

        for tier_name, tier_config in self._config.get("tiers", {}).items():
            sources = tier_config.get("sources", [])
            if source in sources:
                tier = self._tier_from_name(tier_name)
                return ClassificationResult(
                    tier=tier,
                    parsing_strategy=self._strategy_for_tier(tier),
                    confidence=0.7,
                    matched_pattern=f"source:{source}",
                    detected_topics=[],
                    is_explicit_match=False,
                )
        return None

    def _detect_topics(
        self,
        title: str,
        content_preview: str | None = None,
    ) -> list[str]:
        """Detect topics from title and content preview.

        Args:
            title: Document title
            content_preview: First ~500 chars of content

        Returns:
            List of detected topic names
        """
        text = f"{title} {content_preview or ''}".lower()
        detected = []

        topic_keywords = self._config.get("topic_keywords", {})
        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    detected.append(topic)
                    break

        return list(set(detected))

    def _tier_from_name(self, name: str) -> DocumentTier:
        """Convert tier name to enum."""
        if "critical" in name.lower() or "tier_1" in name.lower():
            return DocumentTier.CRITICAL
        elif "important" in name.lower() or "tier_2" in name.lower():
            return DocumentTier.IMPORTANT
        return DocumentTier.REFERENCE

    def _strategy_for_tier(self, tier: DocumentTier) -> str:
        """Get parsing strategy for tier."""
        return {
            DocumentTier.CRITICAL: ParsingStrategy.ARTICLE_LEVEL,
            DocumentTier.IMPORTANT: ParsingStrategy.STANDARD_CHUNKING,
            DocumentTier.REFERENCE: ParsingStrategy.LIGHT_INDEXING,
        }[tier]

    def _default_config(self) -> dict[str, Any]:
        """Return default configuration if YAML not found."""
        return {
            "tiers": {
                "tier_1_critical": {
                    "patterns": [
                        {"regex": r"LEGGE\s+\d+.*n\.\s*\d+"},
                        {"regex": r"Decreto.*Legge"},
                    ],
                    "explicit_documents": [
                        "LEGGE 30 dicembre 2025, n. 199",
                    ],
                },
                "tier_2_important": {
                    "patterns": [
                        {"regex": r"Circolare.*n\.\s*\d+"},
                        {"regex": r"Interpello.*n\.\s*\d+"},
                    ],
                    "sources": [
                        "agenzia_entrate_normativa",
                        "inps_circolari",
                    ],
                },
                "tier_3_reference": {
                    "patterns": [
                        {"regex": r"Comunicato\s+stampa"},
                    ],
                    "sources": [
                        "ministero_economia_documenti",
                    ],
                },
            },
            "topic_keywords": {
                "rottamazione": ["rottamazione", "definizione agevolata"],
                "irpef": ["IRPEF", "imposta sul reddito"],
                "iva": ["IVA", "imposta sul valore aggiunto"],
            },
        }
