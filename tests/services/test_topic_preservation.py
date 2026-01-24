"""DEV-245 Phase 5.3: Tests for topic preservation in long conversations.

Tests that topic_keywords from state are used for keyword ordering,
ensuring the main conversation topic is never lost (even at Q4+).
"""

import pytest

from app.services.parallel_retrieval import ParallelRetrievalService


class TestTopicPreservationParallelRetrieval:
    """Test topic keyword usage in ParallelRetrievalService."""

    @pytest.fixture
    def service(self):
        """Create service with mock dependencies."""
        return ParallelRetrievalService(
            search_service=None,  # Not needed for keyword extraction tests
            embedding_service=None,
        )

    def test_uses_topic_keywords_when_provided(self, service):
        """Should use topic_keywords from state as context keywords."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"
        topic_keywords = ["rottamazione", "quinquies"]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords=topic_keywords,
        )

        # Topic keywords should come first
        assert result[0] == "rottamazione"
        assert result[1] == "quinquies"
        # New keyword should come last
        assert "irap" in result

    def test_topic_keywords_order_is_context_first(self, service):
        """Topic keywords should appear before query-only keywords."""
        query = "e l'irap? E l'imu?"
        topic_keywords = ["rottamazione", "quinquies"]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords=topic_keywords,
        )

        # Get indices
        rottamazione_idx = result.index("rottamazione") if "rottamazione" in result else 999
        quinquies_idx = result.index("quinquies") if "quinquies" in result else 999
        irap_idx = result.index("irap") if "irap" in result else -1
        imu_idx = result.index("imu") if "imu" in result else -1

        # Context keywords first
        if irap_idx != -1:
            assert rottamazione_idx < irap_idx
        if imu_idx != -1:
            assert quinquies_idx < imu_idx

    def test_fallback_to_messages_without_topic_keywords(self, service):
        """Should fallback to message-based extraction if no topic_keywords."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"
        messages = [
            {"role": "user", "content": "parlami della rottamazione quinquies"},
            {
                "role": "assistant",
                "content": "La rottamazione quinquies è una definizione agevolata dei debiti fiscali.",
            },
            {"role": "user", "content": query},
        ]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=messages,
            topic_keywords=None,  # No topic keywords
        )

        # Should still work (fallback path)
        assert "rottamazione" in result
        assert "quinquies" in result

    def test_preserves_context_at_fourth_question(self, service):
        """Original topic should be preserved in 4th+ follow-up.

        This is the key bug fix: without topic_keywords, messages[-4:]
        would lose the original topic at Q4.
        """
        # Q4: "per quanto riguarda l'irap, ci deve essere un accordo con le regioni?"
        query = "IRAP accordo regioni rottamazione"
        topic_keywords = ["rottamazione", "quinquies"]  # From Q1

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,  # With topic_keywords, messages aren't needed
            topic_keywords=topic_keywords,
        )

        # Original topic should STILL be in context keywords
        assert "rottamazione" in result
        assert "quinquies" in result
        # New keywords from Q4 should also be present
        assert "irap" in result
        assert "accordo" in result or "regioni" in result

    def test_handles_empty_topic_keywords(self, service):
        """Should gracefully handle empty topic_keywords list."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords=[],  # Empty list
        )

        # Should still extract keywords from query
        assert len(result) > 0
        assert "irap" in result or "rottamazione" in result

    def test_query_keywords_not_duplicated(self, service):
        """Keywords appearing in both query and topic should not be duplicated."""
        query = "rottamazione quinquies irap"
        topic_keywords = ["rottamazione", "quinquies"]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords=topic_keywords,
        )

        # Count occurrences
        rottamazione_count = result.count("rottamazione")
        assert rottamazione_count == 1

    def test_handles_invalid_topic_keywords_string(self, service):
        """DEV-245 Phase 5.4: Should gracefully handle string instead of list."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords="rottamazione",  # type: ignore[arg-type]
        )

        # Should fallback to query extraction (not crash, not use char-by-char)
        assert len(result) > 0
        # Should NOT have individual characters from "rottamazione"
        assert "r" not in result
        assert "o" not in result

    def test_handles_invalid_topic_keywords_dict(self, service):
        """DEV-245 Phase 5.4: Should gracefully handle dict instead of list."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords={"rottamazione": True},  # type: ignore[arg-type]
        )

        # Should fallback to query extraction (not crash)
        assert len(result) > 0
        assert "irap" in result or "rottamazione" in result


class TestTopicPreservationWebVerification:
    """Test topic keyword usage in WebVerificationService."""

    @pytest.fixture
    def service(self):
        """Create web verification service."""
        from app.services.web_verification import WebVerificationService

        return WebVerificationService()

    def test_uses_topic_keywords_when_provided(self, service):
        """Should use topic_keywords from state as context keywords."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"
        topic_keywords = ["rottamazione", "quinquies"]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords=topic_keywords,
        )

        # Topic keywords should come first
        assert result[0] == "rottamazione"
        assert result[1] == "quinquies"
        # New keyword should come last
        assert "irap" in result

    def test_skips_newest_assistant_in_fallback(self, service):
        """In fallback mode, should skip newest assistant message.

        This is the Phase 3.9.3 behavior that should still work.
        """
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"
        messages = [
            {"role": "user", "content": "parlami della rottamazione quinquies"},
            {"role": "assistant", "content": "La rottamazione quinquies è una definizione agevolata."},
            {"role": "user", "content": "e l'irap?"},
            # This is the NEW response - should be SKIPPED
            {"role": "assistant", "content": "L'IRAP può essere inclusa nella rottamazione quinquies."},
        ]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=messages,
            topic_keywords=None,  # No topic keywords, uses fallback
        )

        # Context should come from assistant1 (not assistant2)
        # Result should have rottamazione/quinquies first (from context)
        assert "rottamazione" in result
        assert "quinquies" in result

    def test_topic_keywords_override_fallback(self, service):
        """Topic keywords should override message-based extraction."""
        query = "accordo regioni irap"
        topic_keywords = ["rottamazione", "quinquies"]
        messages = [
            {"role": "assistant", "content": "Something completely different without keywords."},
        ]

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=messages,
            topic_keywords=topic_keywords,
        )

        # Should use topic_keywords, not message content
        assert "rottamazione" in result
        assert "quinquies" in result

    def test_handles_invalid_topic_keywords_string(self, service):
        """DEV-245 Phase 5.4: Should gracefully handle string instead of list."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords="rottamazione",  # type: ignore[arg-type]
        )

        # Should fallback to query extraction (not crash, not use char-by-char)
        assert len(result) > 0
        # Should NOT have individual characters from "rottamazione"
        assert "r" not in result
        assert "o" not in result

    def test_handles_invalid_topic_keywords_dict(self, service):
        """DEV-245 Phase 5.4: Should gracefully handle dict instead of list."""
        query = "L'IRAP può essere inclusa nella rottamazione quinquies?"

        result = service._extract_search_keywords_with_context(
            query=query,
            messages=None,
            topic_keywords={"rottamazione": True},  # type: ignore[arg-type]
        )

        # Should fallback to query extraction (not crash)
        assert len(result) > 0
        assert "irap" in result or "rottamazione" in result
