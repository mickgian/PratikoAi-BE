"""TDD Tests for KnowledgeSearchService Conversation Context Formatting.

DEV-251 Part 2: Tests for _format_recent_conversation helper method.

Tests written BEFORE implementation following TDD RED-GREEN-REFACTOR methodology.
Coverage Target: 80%+ for new code.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.knowledge_search_service import KnowledgeSearchService

# =============================================================================
# Tests: _format_recent_conversation Helper Method (DEV-251)
# =============================================================================


class TestFormatRecentConversation:
    """Test the _format_recent_conversation helper method."""

    @pytest.fixture
    def service(self):
        """Create a KnowledgeSearchService instance with mocked dependencies."""
        mock_db = MagicMock()
        return KnowledgeSearchService(db_session=mock_db)

    def test_format_empty_messages_returns_none(self, service):
        """DEV-251: Empty messages list should return None."""
        result = service._format_recent_conversation([])
        assert result is None

    def test_format_none_messages_returns_none(self, service):
        """DEV-251: None messages should return None."""
        result = service._format_recent_conversation(None)
        assert result is None

    def test_format_single_user_message(self, service):
        """DEV-251: Single user message should be formatted correctly."""
        messages = [{"role": "user", "content": "parlami della rottamazione quinquies"}]
        result = service._format_recent_conversation(messages)

        assert result is not None
        assert "user:" in result.lower()
        assert "rottamazione" in result.lower()

    def test_format_user_and_assistant_message(self, service):
        """DEV-251: User and assistant messages should both be included."""
        messages = [
            {"role": "user", "content": "parlami della rottamazione quinquies"},
            {
                "role": "assistant",
                "content": "La rottamazione quinquies riguarda l'IRAP e altri tributi...",
            },
        ]
        result = service._format_recent_conversation(messages)

        assert result is not None
        assert "user:" in result.lower()
        assert "assistant:" in result.lower()
        assert "IRAP" in result

    def test_format_truncates_to_last_3_turns(self, service):
        """DEV-251: Should only include last 3 turns (6 messages max)."""
        messages = [
            {"role": "user", "content": "Message 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Message 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Message 3"},
            {"role": "assistant", "content": "Response 3"},
            {"role": "user", "content": "Message 4"},
            {"role": "assistant", "content": "Response 4"},
        ]
        result = service._format_recent_conversation(messages)

        # Should only have last 6 messages (3 turns)
        # Message 1 and Response 1 should be excluded
        assert "Message 1" not in result
        assert "Response 1" not in result
        # Recent messages should be included
        assert "Message 4" in result
        assert "Response 4" in result

    def test_format_truncates_long_content(self, service):
        """DEV-251: Long message content should be truncated to 200 chars."""
        long_content = "A" * 500  # 500 characters
        messages = [{"role": "assistant", "content": long_content}]

        result = service._format_recent_conversation(messages)

        # Content should be truncated (200 chars per message)
        # The result should not contain all 500 'A's
        assert result is not None
        assert len(result) < 500

    def test_format_skips_non_dict_messages(self, service):
        """DEV-251: Non-dict messages should be skipped gracefully."""
        messages = [
            {"role": "user", "content": "valid message"},
            "invalid string message",
            None,
            123,
            {"role": "assistant", "content": "another valid"},
        ]
        result = service._format_recent_conversation(messages)

        # Should include valid messages, skip invalid ones
        assert result is not None
        assert "valid message" in result
        assert "another valid" in result

    def test_format_skips_system_messages(self, service):
        """DEV-251: System role messages should be skipped."""
        messages = [
            {"role": "system", "content": "You are an assistant"},
            {"role": "user", "content": "user question"},
            {"role": "assistant", "content": "assistant response"},
        ]
        result = service._format_recent_conversation(messages)

        # Should skip system message
        assert result is not None
        assert "system:" not in result.lower()
        assert "user:" in result.lower()

    def test_format_handles_missing_content_key(self, service):
        """DEV-251: Messages without content key should be skipped."""
        messages = [
            {"role": "user"},  # Missing content
            {"role": "assistant", "content": "valid response"},
        ]
        result = service._format_recent_conversation(messages)

        assert result is not None
        assert "valid response" in result

    def test_format_handles_empty_content(self, service):
        """DEV-251: Messages with empty content should be skipped."""
        messages = [
            {"role": "user", "content": ""},
            {"role": "assistant", "content": "valid response"},
        ]
        result = service._format_recent_conversation(messages)

        assert result is not None
        # Empty user message should be skipped
        # Only assistant message should be present
        lines = [line for line in result.split("\n") if line.strip()]
        assert len(lines) >= 1

    def test_format_preserves_tax_acronyms(self, service):
        """DEV-251: Tax acronyms (IRAP, IMU, IVA) should be preserved in output."""
        messages = [
            {
                "role": "assistant",
                "content": "L'IRAP (Imposta Regionale sulle Attività Produttive) e l'IMU...",
            }
        ]
        result = service._format_recent_conversation(messages)

        assert "IRAP" in result
        assert "IMU" in result

    def test_format_with_custom_max_turns(self, service):
        """DEV-251: Should respect custom max_turns parameter."""
        messages = [
            {"role": "user", "content": "Turn 1"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Turn 2"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Turn 3"},
            {"role": "assistant", "content": "Response 3"},
        ]

        # With max_turns=1, should only include last 2 messages
        result = service._format_recent_conversation(messages, max_turns=1)

        assert "Turn 3" in result
        assert "Response 3" in result
        # Earlier messages should be excluded
        assert "Turn 1" not in result

    def test_format_returns_joined_string(self, service):
        """DEV-251: Result should be newline-joined string."""
        messages = [
            {"role": "user", "content": "question"},
            {"role": "assistant", "content": "answer"},
        ]
        result = service._format_recent_conversation(messages)

        # Should contain newlines
        assert "\n" in result
        # Should have role prefixes
        assert "user:" in result.lower()
        assert "assistant:" in result.lower()
