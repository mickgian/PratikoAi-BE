"""Unit tests for DocumentClassifier service (ADR-023).

Tests document tier classification with various document types:
- Tier 1 (CRITICAL): Leggi, Decreti, DPR
- Tier 2 (IMPORTANT): Circolari, Interpelli, Risoluzioni
- Tier 3 (REFERENCE): News, Comunicati, FAQ
"""

import pytest

from app.services.document_classifier import (
    ClassificationResult,
    DocumentClassifier,
    DocumentTier,
    ParsingStrategy,
)


class TestDocumentClassifierTier1Critical:
    """Tests for Tier 1 (CRITICAL) document classification."""

    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        """Create classifier with project config."""
        return DocumentClassifier()

    def test_explicit_legge_bilancio_2026(self, classifier: DocumentClassifier) -> None:
        """Legge di Bilancio 2026 is explicitly listed as CRITICAL."""
        result = classifier.classify("LEGGE 30 dicembre 2025, n. 199")

        assert result.tier == DocumentTier.CRITICAL
        assert result.parsing_strategy == ParsingStrategy.ARTICLE_LEVEL
        assert result.confidence == 1.0
        assert result.is_explicit_match is True
        assert "explicit:" in result.matched_pattern

    def test_explicit_match_partial_title(self, classifier: DocumentClassifier) -> None:
        """Explicit match works with partial title containing the law."""
        result = classifier.classify("LEGGE 30 dicembre 2025, n. 199 - Legge di Bilancio 2026")

        assert result.tier == DocumentTier.CRITICAL
        assert result.is_explicit_match is True

    def test_regex_legge_pattern(self, classifier: DocumentClassifier) -> None:
        """Generic LEGGE pattern matches as CRITICAL."""
        result = classifier.classify("LEGGE 15 marzo 2024, n. 47")

        assert result.tier == DocumentTier.CRITICAL
        assert result.parsing_strategy == ParsingStrategy.ARTICLE_LEVEL
        assert result.confidence == 0.9
        assert result.is_explicit_match is False

    def test_decreto_legge_pattern(self, classifier: DocumentClassifier) -> None:
        """Decreto-Legge matches as CRITICAL."""
        result = classifier.classify("Decreto-Legge 34/2020 (Decreto Rilancio)")

        assert result.tier == DocumentTier.CRITICAL
        assert result.parsing_strategy == ParsingStrategy.ARTICLE_LEVEL

    def test_dl_abbreviation_pattern(self, classifier: DocumentClassifier) -> None:
        """DL abbreviation matches as CRITICAL."""
        result = classifier.classify("DL 34/2020")

        assert result.tier == DocumentTier.CRITICAL

    def test_decreto_legislativo_pattern(self, classifier: DocumentClassifier) -> None:
        """Decreto Legislativo matches as CRITICAL."""
        result = classifier.classify("Decreto Legislativo 241/1997")

        assert result.tier == DocumentTier.CRITICAL

    def test_dlgs_abbreviation_pattern(self, classifier: DocumentClassifier) -> None:
        """D.Lgs. abbreviation matches as CRITICAL."""
        result = classifier.classify("D.Lgs. 241/1997")

        assert result.tier == DocumentTier.CRITICAL

    def test_dpr_pattern(self, classifier: DocumentClassifier) -> None:
        """DPR matches as CRITICAL."""
        result = classifier.classify("DPR 633/1972")

        assert result.tier == DocumentTier.CRITICAL

    def test_exact_decreto_rilancio(self, classifier: DocumentClassifier) -> None:
        """Named law 'Decreto Rilancio' matches as CRITICAL."""
        result = classifier.classify("Il Decreto Rilancio introduce nuove misure")

        assert result.tier == DocumentTier.CRITICAL
        assert "exact:" in result.matched_pattern or "Decreto" in result.matched_pattern


class TestDocumentClassifierTier2Important:
    """Tests for Tier 2 (IMPORTANT) document classification."""

    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        return DocumentClassifier()

    def test_circolare_pattern(self, classifier: DocumentClassifier) -> None:
        """Circolare matches as IMPORTANT."""
        result = classifier.classify("Circolare n. 19/E del 2025")

        assert result.tier == DocumentTier.IMPORTANT
        assert result.parsing_strategy == ParsingStrategy.STANDARD_CHUNKING

    def test_interpello_pattern(self, classifier: DocumentClassifier) -> None:
        """Interpello matches as IMPORTANT."""
        result = classifier.classify("Interpello n. 280/2025")

        assert result.tier == DocumentTier.IMPORTANT

    def test_risoluzione_pattern(self, classifier: DocumentClassifier) -> None:
        """Risoluzione matches as IMPORTANT."""
        result = classifier.classify("Risoluzione n. 56/E")

        assert result.tier == DocumentTier.IMPORTANT

    def test_risposta_pattern(self, classifier: DocumentClassifier) -> None:
        """Risposta matches as IMPORTANT."""
        result = classifier.classify("Risposta n. 297")

        assert result.tier == DocumentTier.IMPORTANT

    def test_source_agenzia_entrate(self, classifier: DocumentClassifier) -> None:
        """Source 'agenzia_entrate_normativa' classifies as IMPORTANT."""
        result = classifier.classify(
            "Documento fiscale",
            source="agenzia_entrate_normativa",
        )

        assert result.tier == DocumentTier.IMPORTANT
        assert result.confidence == 0.7


class TestDocumentClassifierTier3Reference:
    """Tests for Tier 3 (REFERENCE) document classification."""

    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        return DocumentClassifier()

    def test_comunicato_stampa_pattern(self, classifier: DocumentClassifier) -> None:
        """Comunicato stampa matches as REFERENCE."""
        result = classifier.classify("Comunicato stampa del 15 gennaio 2025")

        assert result.tier == DocumentTier.REFERENCE
        assert result.parsing_strategy == ParsingStrategy.LIGHT_INDEXING

    def test_default_unknown_document(self, classifier: DocumentClassifier) -> None:
        """Unknown document type defaults to REFERENCE."""
        result = classifier.classify("Random document title")

        assert result.tier == DocumentTier.REFERENCE
        assert result.confidence == 0.5


class TestDocumentClassifierTopicDetection:
    """Tests for topic detection functionality."""

    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        return DocumentClassifier()

    def test_detect_rottamazione_topic(self, classifier: DocumentClassifier) -> None:
        """Detects 'rottamazione' topic from title."""
        result = classifier.classify(
            "LEGGE 30 dicembre 2025, n. 199",
            content_preview="Art. 1 - Definizione agevolata dei carichi (rottamazione quinquies)",
        )

        assert "rottamazione" in result.detected_topics

    def test_detect_irpef_topic(self, classifier: DocumentClassifier) -> None:
        """Detects 'irpef' topic from content."""
        result = classifier.classify(
            "Circolare n. 1/E",
            content_preview="Le nuove aliquote IRPEF per il 2025 prevedono...",
        )

        assert "irpef" in result.detected_topics

    def test_detect_multiple_topics(self, classifier: DocumentClassifier) -> None:
        """Detects multiple topics from content."""
        result = classifier.classify(
            "LEGGE 30 dicembre 2025, n. 199",
            content_preview="Disposizioni su IRPEF, IVA e bonus edilizi per il 2026",
        )

        assert "irpef" in result.detected_topics
        assert "iva" in result.detected_topics
        assert "bonus" in result.detected_topics

    def test_no_topics_detected(self, classifier: DocumentClassifier) -> None:
        """Returns empty list when no topics match."""
        result = classifier.classify(
            "Documento generico",
            content_preview="Testo senza parole chiave rilevanti",
        )

        assert result.detected_topics == []


class TestDocumentClassifierEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.fixture
    def classifier(self) -> DocumentClassifier:
        return DocumentClassifier()

    def test_empty_title(self, classifier: DocumentClassifier) -> None:
        """Empty title returns REFERENCE tier."""
        result = classifier.classify("")

        assert result.tier == DocumentTier.REFERENCE

    def test_none_source(self, classifier: DocumentClassifier) -> None:
        """None source is handled gracefully."""
        result = classifier.classify("Document title", source=None)

        # Should not raise, should use pattern or default
        assert result.tier in [
            DocumentTier.CRITICAL,
            DocumentTier.IMPORTANT,
            DocumentTier.REFERENCE,
        ]

    def test_none_content_preview(self, classifier: DocumentClassifier) -> None:
        """None content_preview is handled gracefully."""
        result = classifier.classify(
            "LEGGE 30 dicembre 2025, n. 199",
            content_preview=None,
        )

        assert result.tier == DocumentTier.CRITICAL

    def test_case_insensitive_pattern_matching(self, classifier: DocumentClassifier) -> None:
        """Pattern matching is case-insensitive."""
        result1 = classifier.classify("CIRCOLARE N. 19/E")
        result2 = classifier.classify("circolare n. 19/e")
        result3 = classifier.classify("Circolare N. 19/E")

        assert result1.tier == result2.tier == result3.tier == DocumentTier.IMPORTANT


class TestDocumentClassifierWithDefaultConfig:
    """Tests for classifier with default/fallback config."""

    def test_default_config_when_file_missing(self) -> None:
        """Uses default config when YAML file doesn't exist."""
        classifier = DocumentClassifier(config_path="/nonexistent/path.yaml")

        # Should still work with default patterns
        result = classifier.classify("LEGGE 30 dicembre 2025, n. 199")

        assert result.tier == DocumentTier.CRITICAL

    def test_default_config_has_essential_patterns(self) -> None:
        """Default config includes essential patterns."""
        classifier = DocumentClassifier(config_path="/nonexistent/path.yaml")

        # Test essential patterns
        assert classifier.classify("Decreto Legge 34/2020").tier == DocumentTier.CRITICAL
        assert classifier.classify("Circolare n. 1/E").tier == DocumentTier.IMPORTANT


class TestClassificationResultDataclass:
    """Tests for ClassificationResult dataclass."""

    def test_classification_result_attributes(self) -> None:
        """ClassificationResult has all required attributes."""
        result = ClassificationResult(
            tier=DocumentTier.CRITICAL,
            parsing_strategy=ParsingStrategy.ARTICLE_LEVEL,
            confidence=1.0,
            matched_pattern="explicit:test",
            detected_topics=["irpef", "iva"],
            is_explicit_match=True,
        )

        assert result.tier == DocumentTier.CRITICAL
        assert result.parsing_strategy == "article_level"
        assert result.confidence == 1.0
        assert result.matched_pattern == "explicit:test"
        assert result.detected_topics == ["irpef", "iva"]
        assert result.is_explicit_match is True

    def test_document_tier_enum_values(self) -> None:
        """DocumentTier enum has correct integer values."""
        assert DocumentTier.CRITICAL == 1
        assert DocumentTier.IMPORTANT == 2
        assert DocumentTier.REFERENCE == 3

    def test_parsing_strategy_constants(self) -> None:
        """ParsingStrategy has correct string values."""
        assert ParsingStrategy.ARTICLE_LEVEL == "article_level"
        assert ParsingStrategy.STANDARD_CHUNKING == "standard_chunking"
        assert ParsingStrategy.LIGHT_INDEXING == "light_indexing"
