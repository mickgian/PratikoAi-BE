"""DEV-245 Phase 5.3: Tests for topic keyword extraction in step_034a.

Tests that conversation topics are extracted on first query and persisted
for long conversation support (prevents context loss at Q4+).
"""

import pytest

# Import the function we're testing
from app.core.langgraph.nodes.step_034a__llm_router import _extract_topic_keywords


class TestExtractTopicKeywords:
    """Test topic keyword extraction from first query."""

    def test_extracts_main_topic_keywords(self):
        """Should extract significant keywords from query."""
        query = "parlami della rottamazione quinquies"
        result = _extract_topic_keywords(query)

        assert "rottamazione" in result
        assert "quinquies" in result

    def test_filters_stop_words(self):
        """Should filter out Italian stop words."""
        query = "cosa è la rottamazione quinquies e come funziona"
        result = _extract_topic_keywords(query)

        # Stop words should be filtered
        assert "cosa" not in result
        assert "come" not in result
        # "funziona" is a valid keyword (not a stop word)

        # Topic keywords should remain
        assert "rottamazione" in result
        assert "quinquies" in result

    def test_filters_request_words(self):
        """Should filter generic request words like 'parlami', 'dimmi'."""
        query = "parlami della rottamazione quinquies"
        result = _extract_topic_keywords(query)

        # Request words should be filtered
        assert "parlami" not in result

        # Topic keywords should remain
        assert "rottamazione" in result
        assert "quinquies" in result

    def test_returns_max_five_keywords(self):
        """Should cap at 5 keywords maximum."""
        query = "spiegami la rottamazione quinquies per debiti fiscali irap contributi inps iva"
        result = _extract_topic_keywords(query)

        assert len(result) <= 5

    def test_preserves_keyword_order(self):
        """Should preserve order of keywords as they appear in query."""
        query = "rottamazione quinquies irap"
        result = _extract_topic_keywords(query)

        # Ensure order is preserved
        rottamazione_idx = result.index("rottamazione")
        quinquies_idx = result.index("quinquies")
        irap_idx = result.index("irap")

        assert rottamazione_idx < quinquies_idx < irap_idx

    def test_handles_empty_query(self):
        """Should return empty list for empty query."""
        result = _extract_topic_keywords("")
        assert result == []

    def test_handles_query_with_only_stop_words(self):
        """Should return empty list if only stop words."""
        query = "cosa è il di della"
        result = _extract_topic_keywords(query)
        assert result == []

    def test_filters_short_words(self):
        """Should filter words shorter than 3 characters."""
        query = "la rottamazione e quinquies"
        result = _extract_topic_keywords(query)

        # Short words should be filtered
        assert "la" not in result
        assert "e" not in result

        # Topic keywords should remain
        assert "rottamazione" in result
        assert "quinquies" in result

    def test_case_insensitive(self):
        """Should normalize to lowercase."""
        query = "ROTTAMAZIONE Quinquies IRAP"
        result = _extract_topic_keywords(query)

        # All should be lowercase
        assert "rottamazione" in result
        assert "quinquies" in result
        assert "irap" in result

    def test_removes_punctuation(self):
        """Should handle punctuation correctly."""
        query = "rottamazione quinquies, irap?"
        result = _extract_topic_keywords(query)

        assert "rottamazione" in result
        assert "quinquies" in result
        assert "irap" in result

    def test_removes_duplicates(self):
        """Should not include duplicate keywords."""
        query = "rottamazione rottamazione quinquies"
        result = _extract_topic_keywords(query)

        # Count occurrences
        rottamazione_count = result.count("rottamazione")
        assert rottamazione_count == 1

    def test_specific_fiscal_terms(self):
        """Should correctly extract Italian fiscal terms."""
        query = "cosa sono i contributi previdenziali INPS nella rottamazione"
        result = _extract_topic_keywords(query)

        assert "contributi" in result
        assert "previdenziali" in result
        assert "inps" in result
        assert "rottamazione" in result
