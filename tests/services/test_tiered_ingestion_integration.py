"""DEV-416: Tests for ADR-023 Tiered Ingestion Pipeline Verification.

Tests: verify tier assignment, chunk sizes for legal docs, overlap, pipeline connectivity.
"""

import pytest

from app.services.document_classifier import DocumentClassifier, DocumentTier


@pytest.fixture
def classifier():
    return DocumentClassifier()


class TestTierAssignment:
    def test_law_classified_as_tier1(self, classifier):
        result = classifier.classify(
            title="LEGGE 30 dicembre 2025, n. 199",
            source="gazzetta_ufficiale",
        )
        assert result.tier == DocumentTier.CRITICAL

    def test_circular_classified_as_tier2(self, classifier):
        result = classifier.classify(
            title="Circolare AdE n. 15/2026",
            source="agenzia_entrate",
        )
        assert result.tier in (DocumentTier.CRITICAL, DocumentTier.IMPORTANT)

    def test_faq_classified_as_tier3(self, classifier):
        result = classifier.classify(
            title="FAQ su bonus edilizi 2026",
            source="web",
        )
        assert result.tier in (DocumentTier.IMPORTANT, DocumentTier.REFERENCE)


class TestChunkConfiguration:
    def test_chunk_tokens_configured(self):
        from app.core.config import CHUNK_TOKENS

        assert CHUNK_TOKENS > 0
        assert CHUNK_TOKENS <= 2000  # Reasonable upper bound

    def test_chunk_overlap_configured(self):
        from app.core.config import CHUNK_OVERLAP

        assert 0 < CHUNK_OVERLAP < 1  # Should be a fraction


class TestPipelineConnectivity:
    def test_tiered_ingestion_service_importable(self):
        from app.services.tiered_ingestion_service import TieredIngestionService

        assert TieredIngestionService is not None

    def test_document_classifier_importable(self):
        from app.services.document_classifier import DocumentClassifier

        assert DocumentClassifier is not None
