"""Tests for graph utilities."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.schemas import Message
from app.utils.graph import dump_messages, prepare_messages


class TestDumpMessages:
    """Test dump_messages function."""

    def test_dump_empty_list(self):
        """Test dumping empty message list."""
        result = dump_messages([])
        assert result == []

    def test_dump_single_message(self):
        """Test dumping single message."""
        message = Message(role="user", content="Hello")
        result = dump_messages([message])

        assert len(result) == 1
        assert isinstance(result[0], dict)
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_dump_multiple_messages(self):
        """Test dumping multiple messages."""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there"),
            Message(role="user", content="How are you?"),
        ]
        result = dump_messages(messages)

        assert len(result) == 3
        assert all(isinstance(msg, dict) for msg in result)
        assert result[0]["content"] == "Hello"
        assert result[1]["content"] == "Hi there"
        assert result[2]["content"] == "How are you?"

    def test_dump_preserves_order(self):
        """Test dumping preserves message order."""
        messages = [
            Message(role="user", content="First"),
            Message(role="assistant", content="Second"),
            Message(role="user", content="Third"),
        ]
        result = dump_messages(messages)

        assert result[0]["content"] == "First"
        assert result[1]["content"] == "Second"
        assert result[2]["content"] == "Third"

    def test_dump_message_with_system_role(self):
        """Test dumping message with system role."""
        message = Message(role="system", content="System prompt")
        result = dump_messages([message])

        assert result[0]["role"] == "system"
        assert result[0]["content"] == "System prompt"


class TestPrepareMessages:
    """Test prepare_messages function."""

    @patch("app.utils.graph._trim_messages")
    @patch("app.utils.graph.settings")
    def test_prepare_messages_basic(self, mock_settings, mock_trim):
        """Test basic message preparation."""
        mock_settings.MAX_TOKENS = 1000

        # Mock trim_messages to return the input
        mock_trim.return_value = [{"role": "user", "content": "Hello"}]

        messages = [Message(role="user", content="Hello")]
        llm = Mock()
        system_prompt = "You are a helpful assistant"

        result = prepare_messages(messages, llm, system_prompt)

        # Should have system message prepended
        assert len(result) >= 1
        assert result[0].role == "system"
        assert result[0].content == system_prompt

    @patch("app.utils.graph._trim_messages")
    @patch("app.utils.graph.settings")
    def test_prepare_messages_calls_trim(self, mock_settings, mock_trim):
        """Test prepare_messages calls trim_messages."""
        mock_settings.MAX_TOKENS = 1000
        mock_trim.return_value = []

        messages = [Message(role="user", content="Test")]
        llm = Mock()
        system_prompt = "System"

        prepare_messages(messages, llm, system_prompt)

        # Verify trim_messages was called
        mock_trim.assert_called_once()
        call_args = mock_trim.call_args

        # Check parameters passed to trim
        assert call_args.kwargs["strategy"] == "last"
        assert call_args.kwargs["token_counter"] == llm
        assert call_args.kwargs["max_tokens"] == 1000
        assert call_args.kwargs["start_on"] == "human"
        assert call_args.kwargs["include_system"] is False
        assert call_args.kwargs["allow_partial"] is False

    @patch("app.utils.graph._trim_messages")
    @patch("app.utils.graph.settings")
    def test_prepare_messages_empty_list(self, mock_settings, mock_trim):
        """Test preparing empty message list."""
        mock_settings.MAX_TOKENS = 1000
        mock_trim.return_value = []

        messages = []
        llm = Mock()
        system_prompt = "System prompt"

        result = prepare_messages(messages, llm, system_prompt)

        # Should still have system message
        assert len(result) == 1
        assert result[0].role == "system"

    @patch("app.utils.graph._trim_messages")
    @patch("app.utils.graph.settings")
    def test_prepare_messages_with_multiple_messages(self, mock_settings, mock_trim):
        """Test preparing multiple messages."""
        mock_settings.MAX_TOKENS = 2000

        mock_trim.return_value = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]
        llm = Mock()
        system_prompt = "Be helpful"

        result = prepare_messages(messages, llm, system_prompt)

        # System message + trimmed messages
        assert len(result) >= 1
        assert result[0].role == "system"
        assert result[0].content == "Be helpful"

    @patch("app.utils.graph._trim_messages")
    @patch("app.utils.graph.settings")
    def test_prepare_messages_respects_max_tokens(self, mock_settings, mock_trim):
        """Test prepare_messages respects MAX_TOKENS setting."""
        custom_max_tokens = 5000
        mock_settings.MAX_TOKENS = custom_max_tokens
        mock_trim.return_value = []

        messages = [Message(role="user", content="Test")]
        llm = Mock()

        prepare_messages(messages, llm, "System")

        # Verify max_tokens was passed correctly
        call_args = mock_trim.call_args
        assert call_args.kwargs["max_tokens"] == custom_max_tokens

    @patch("app.utils.graph._trim_messages")
    @patch("app.utils.graph.settings")
    def test_prepare_messages_system_always_first(self, mock_settings, mock_trim):
        """Test system message is always first."""
        mock_settings.MAX_TOKENS = 1000

        mock_trim.return_value = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
        ]

        messages = [
            Message(role="user", content="User message"),
            Message(role="assistant", content="Assistant message"),
        ]
        llm = Mock()
        system_prompt = "System instructions"

        result = prepare_messages(messages, llm, system_prompt)

        # First message must be system
        assert result[0].role == "system"
        assert result[0].content == "System instructions"
