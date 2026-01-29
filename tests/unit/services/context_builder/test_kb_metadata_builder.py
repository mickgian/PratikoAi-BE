"""Tests for KB metadata builder.

DEV-250: Tests for authority_boost exemption from score filtering.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.services.context_builder.kb_metadata_builder import build_kb_sources_metadata


class TestAuthorityBoostExemption:
    """DEV-250: Tests for authority_boost exemption from score filtering."""

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_authority_boost_sources_never_filtered(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Sources with authority_boost > 1.0 should appear regardless of score."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            # Legge with authority_boost from GERARCHIA_FONTI - should NOT be filtered
            {
                "id": "1",
                "title": "LEGGE 199/2025",
                "type": "legge",
                "rrf_score": 0.001,
                "authority_boost": 1.8,
            },
            # Unknown source without boost - SHOULD be filtered (low score)
            {
                "id": "2",
                "title": "Unknown doc",
                "type": "unknown",
                "rrf_score": 0.001,
                "authority_boost": 1.0,
            },
        ]
        result = build_kb_sources_metadata(kb_docs)

        # Legge should appear (authority_boost > 1.0)
        assert any(m["id"] == "1" for m in result)
        # Unknown should NOT appear (authority_boost = 1.0 + low score)
        assert not any(m["id"] == "2" for m in result)

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_circolare_with_boost_not_filtered(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Even circolare has authority_boost=1.3, so should appear."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            {
                "id": "1",
                "title": "Circolare AdE",
                "type": "circolare",
                "rrf_score": 0.002,
                "authority_boost": 1.3,
            },
        ]
        result = build_kb_sources_metadata(kb_docs)
        assert len(result) == 1  # Circolare should appear (boost > 1.0)

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_decreto_with_boost_not_filtered(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Decreto with authority_boost=1.6 should appear."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            {
                "id": "1",
                "title": "DECRETO 2025",
                "type": "decreto",
                "rrf_score": 0.003,
                "authority_boost": 1.6,
            },
        ]
        result = build_kb_sources_metadata(kb_docs)
        assert len(result) == 1  # Decreto should appear (boost > 1.0)

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_interpello_with_boost_not_filtered(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Interpello with authority_boost=1.1 should appear."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            {
                "id": "1",
                "title": "Interpello 123",
                "type": "interpello",
                "rrf_score": 0.002,
                "authority_boost": 1.1,
            },
        ]
        result = build_kb_sources_metadata(kb_docs)
        assert len(result) == 1  # Interpello should appear (boost > 1.0)

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_source_without_boost_filtered_if_low_score(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Sources without authority_boost should be filtered if low score."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            {
                "id": "1",
                "title": "Low relevance doc",
                "type": "web",
                "rrf_score": 0.001,
                # No authority_boost -> defaults to 1.0
            },
        ]
        result = build_kb_sources_metadata(kb_docs)
        assert len(result) == 0  # Should be filtered (no boost + low score)

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_source_without_boost_kept_if_high_score(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Sources without authority_boost pass if score is high enough."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            {
                "id": "1",
                "title": "High relevance doc",
                "type": "web",
                "rrf_score": 0.05,  # Above MIN_FONTI_RELEVANCE_SCORE (0.008)
                # No authority_boost -> defaults to 1.0
            },
        ]
        result = build_kb_sources_metadata(kb_docs)
        assert len(result) == 1  # Should pass (score >= threshold)

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_missing_authority_boost_treated_as_no_boost(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Missing authority_boost defaults to 1.0 (no exemption)."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            {
                "id": "1",
                "title": "Old doc without boost field",
                "type": "unknown",
                "rrf_score": 0.002,
                # authority_boost field missing entirely
            },
        ]
        result = build_kb_sources_metadata(kb_docs)
        assert len(result) == 0  # Should be filtered (defaults to 1.0 = no exemption)


class TestMixedAuthorityDocuments:
    """DEV-250: Tests for mixed authority documents in same batch."""

    @patch("app.services.context_builder.kb_metadata_builder.ParagraphExtractor")
    def test_mixed_authority_filtering(self, mock_extractor: MagicMock) -> None:
        """DEV-250: Mix of high and low authority sources filtered correctly."""
        mock_extractor.return_value.extract_best_paragraph.return_value = None

        kb_docs = [
            # Should PASS: legge with authority_boost
            {
                "id": "1",
                "title": "LEGGE 199/2025",
                "type": "legge",
                "rrf_score": 0.001,
                "authority_boost": 1.8,
            },
            # Should PASS: decreto with authority_boost
            {
                "id": "2",
                "title": "DECRETO 2025",
                "type": "decreto",
                "rrf_score": 0.002,
                "authority_boost": 1.6,
            },
            # Should FAIL: web source with low score
            {
                "id": "3",
                "title": "Blog post",
                "type": "web",
                "rrf_score": 0.001,
                "authority_boost": 1.0,
            },
            # Should PASS: web source with HIGH score
            {
                "id": "4",
                "title": "News article",
                "type": "web",
                "rrf_score": 0.05,
                "authority_boost": 1.0,
            },
            # Should FAIL: no boost + low score
            {
                "id": "5",
                "title": "Random doc",
                "type": "unknown",
                "rrf_score": 0.003,
            },
        ]
        result = build_kb_sources_metadata(kb_docs)

        result_ids = {m["id"] for m in result}
        assert result_ids == {"1", "2", "4"}  # Only these should pass
