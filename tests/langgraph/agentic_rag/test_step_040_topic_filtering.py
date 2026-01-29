"""DEV-245 Phase 5.5: Tests for topic keyword web filtering in step_040.

Tests that web results are filtered to require ALL topic keywords match,
preventing "rottamazione ter" results when topic is "rottamazione quinquies".

DEV-250: Updated imports to use app.services.context_builder module.
"""

import pytest

from app.services.context_builder import is_web_source_topic_relevant as _is_web_source_topic_relevant


class TestTopicKeywordWebFiltering:
    """DEV-245 Phase 5.5: Topic keyword filtering tests."""

    def test_filters_wrong_rottamazione_version(self):
        """'Rottamazione ter' should NOT pass filter when topic is 'rottamazione quinquies'."""
        doc = {
            "title": "Rottamazione Ter 2024 - Guida Completa",
            "content": "La rottamazione ter permette di sanare i debiti fiscali...",
            "source_name": "Rottamazione Ter 2024",
        }
        query_keywords = ["rottamazione", "quinquies", "irap", "sicilia"]
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should fail: missing "quinquies" in title/content
        assert result is False

    def test_passes_correct_rottamazione_version(self):
        """'Rottamazione quinquies' should pass filter."""
        doc = {
            "title": "Rottamazione Quinquies IRAP Sicilia 2026",
            "content": "La rottamazione quinquies prevede l'inclusione dell'IRAP...",
            "source_name": "Rottamazione Quinquies IRAP",
        }
        query_keywords = ["rottamazione", "quinquies", "irap", "sicilia"]
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: both "rottamazione" and "quinquies" present
        assert result is True

    def test_no_topic_keywords_fallback_to_any_match(self):
        """Without topic_keywords, fallback to any() match (existing behavior)."""
        doc = {
            "title": "Rottamazione Ter 2024",
            "content": "Guida alla rottamazione ter...",
        }
        query_keywords = ["rottamazione", "ter"]
        topic_keywords = None

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: fallback to any keyword matches
        assert result is True

    def test_empty_topic_keywords_list_fallback(self):
        """Empty topic_keywords list should fallback to any() match."""
        doc = {
            "title": "IRAP Sicilia 2026",
            "content": "Le novità sull'IRAP in Sicilia...",
        }
        query_keywords = ["irap", "sicilia"]
        topic_keywords = []

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: empty list triggers fallback
        assert result is True

    def test_single_topic_keyword_fallback(self):
        """Single topic keyword should fallback to any() match (need 2+ for strict)."""
        doc = {
            "title": "IRAP overview 2026",
            "content": "All about IRAP...",
        }
        query_keywords = ["irap", "sicilia"]
        topic_keywords = ["irap"]  # Only 1 topic keyword

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: only 1 topic keyword, fallback to any() match
        assert result is True

    def test_topic_keywords_case_insensitive(self):
        """Topic keyword matching should be case-insensitive."""
        doc = {
            "title": "ROTTAMAZIONE QUINQUIES - Guida",
            "content": "La ROTTAMAZIONE QUINQUIES prevede...",
        }
        query_keywords = ["rottamazione", "quinquies"]
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: case-insensitive matching
        assert result is True

    def test_topic_keyword_in_content_not_title(self):
        """Topic keywords can be in content, not just title."""
        doc = {
            "title": "Novità fiscali 2026",
            "content": "Le ultime novità sulla rottamazione quinquies includono...",
        }
        query_keywords = ["rottamazione", "quinquies", "novità"]
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: topic keywords in content
        assert result is True

    def test_invalid_topic_keywords_type_string(self):
        """String topic_keywords should fallback to any() match (type safety)."""
        doc = {
            "title": "Rottamazione Ter 2024",
            "content": "Guida alla rottamazione ter...",
        }
        query_keywords = ["rottamazione", "ter"]
        topic_keywords = "rottamazione"  # Invalid type: string instead of list

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: invalid type triggers fallback
        assert result is True

    def test_invalid_topic_keywords_type_dict(self):
        """Dict topic_keywords should fallback to any() match (type safety)."""
        doc = {
            "title": "Rottamazione Ter 2024",
            "content": "Guida alla rottamazione ter...",
        }
        query_keywords = ["rottamazione", "ter"]
        topic_keywords = {"rottamazione": True}  # Invalid type: dict instead of list

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: invalid type triggers fallback
        assert result is True

    def test_filters_bollo_auto_irrelevant_result(self):
        """Q5 regression test: 'bollo auto' should NOT pass when topic is 'rottamazione quinquies'."""
        doc = {
            "title": "Rottamazione bollo auto Sicilia 2022",
            "content": "La legge regionale n. 16 del 10 agosto 2022 prevede la rottamazione del bollo auto...",
        }
        query_keywords = ["rottamazione", "quinquies", "irap", "sicilia", "regione"]
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should fail: missing "quinquies" - this is bollo auto, not rottamazione quinquies
        assert result is False

    def test_no_query_keywords_with_topic_keywords_filters(self):
        """DEV-245 Phase 5.5 FIX: Topic filter runs even with empty query_keywords."""
        doc = {
            "title": "Rottamazione Ter 2024 - Sicilia",
            "content": "La rottamazione ter in Sicilia...",
        }
        query_keywords = []  # Empty!
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should FAIL - missing "quinquies" (topic filter must run before early return)
        assert result is False

    def test_no_query_keywords_without_topic_keywords_returns_true(self):
        """Without topic_keywords, empty query_keywords should return True."""
        doc = {
            "title": "Any document",
            "content": "Any content...",
        }
        query_keywords = []
        topic_keywords = None  # No topic filter

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should pass: no filtering at all
        assert result is True

    def test_all_topic_keywords_must_match(self):
        """ALL topic keywords must be present, not just some."""
        doc = {
            "title": "Rottamazione quater IRAP Sicilia",  # "quater" not "quinquies"
            "content": "La rottamazione quater prevede...",
        }
        query_keywords = ["rottamazione", "quinquies", "irap", "sicilia"]
        topic_keywords = ["rottamazione", "quinquies"]

        result = _is_web_source_topic_relevant(doc, query_keywords, topic_keywords)

        # Should fail: has "rottamazione" but not "quinquies"
        assert result is False


class TestTopicKeywordIntegration:
    """Integration tests for topic keyword flow through step_040."""

    @pytest.mark.asyncio
    async def test_topic_keywords_passed_to_prefilter(self):
        """Topic keywords should be read from state and used for pre-filtering."""
        # This tests the integration in node_step_40()
        # We can't easily unit test this without mocking the full state
        # so this is a placeholder for manual verification
        pass

    @pytest.mark.asyncio
    async def test_topic_keywords_passed_to_fonti_filter(self):
        """Topic keywords should be used for Fonti section filtering too."""
        # Placeholder for manual verification
        pass
