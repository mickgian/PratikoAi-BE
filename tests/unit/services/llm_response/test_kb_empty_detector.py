"""Tests for KB empty detection functions."""

import pytest

from app.services.llm_response.kb_empty_detector import check_kb_empty_and_inject_warning


class TestCheckKbEmptyAndInjectWarning:
    """Tests for check_kb_empty_and_inject_warning function."""

    def test_injects_warning_when_kb_sources_empty(self):
        """Happy path: injects warning when no KB sources found."""
        state = {
            "kb_sources_metadata": [],
            "context": "",
            "messages": [{"role": "user", "content": "Test query"}],
            "request_id": "test-123",
        }

        result = check_kb_empty_and_inject_warning(state)

        assert result is True
        assert "kb_empty_warning" in state
        assert "KNOWLEDGE BASE VUOTA" in state["kb_empty_warning"]

    def test_injects_warning_when_kb_context_minimal(self):
        """Injects warning when KB context is too short (<200 chars)."""
        state = {
            "kb_sources_metadata": [{"id": 1}],
            "context": "Short context",  # Less than 200 chars
            "messages": [],
            "request_id": "test-123",
        }

        result = check_kb_empty_and_inject_warning(state)

        assert result is True
        assert "kb_empty_warning" in state

    def test_no_warning_when_kb_has_sufficient_content(self):
        """No warning when KB has sources and sufficient context."""
        state = {
            "kb_sources_metadata": [{"id": 1}, {"id": 2}],
            "context": "A" * 250,  # More than 200 chars
            "messages": [],
            "request_id": "test-123",
        }

        result = check_kb_empty_and_inject_warning(state)

        assert result is False
        assert "kb_empty_warning" not in state

    def test_falls_back_to_kb_context_key(self):
        """Uses kb_context key when context is empty."""
        state = {
            "kb_sources_metadata": [],
            "kb_context": "Some context from kb_context key",
            "messages": [],
            "request_id": "test-123",
        }

        result = check_kb_empty_and_inject_warning(state)

        assert result is True  # Still empty because kb_context < 200 chars

    def test_extracts_user_message_from_messages(self):
        """Extracts user query from messages list for logging."""
        state = {
            "kb_sources_metadata": [],
            "context": "",
            "messages": [
                {"role": "assistant", "content": "Hello"},
                {"role": "user", "content": "What is the tax rate?"},
            ],
            "request_id": "test-123",
        }

        result = check_kb_empty_and_inject_warning(state)

        assert result is True
        # Warning should be injected (testing side effect)
        assert "kb_context" in state

    def test_uses_user_message_field_if_present(self):
        """Uses user_message field directly if available."""
        state = {
            "kb_sources_metadata": [],
            "context": "",
            "user_message": "Direct user query",
            "messages": [],
            "request_id": "test-123",
        }

        result = check_kb_empty_and_inject_warning(state)

        assert result is True

    def test_warning_prepended_to_kb_context(self):
        """Warning is prepended to existing kb_context."""
        state = {
            "kb_sources_metadata": [],
            "context": "Original short context",
            "messages": [],
            "request_id": "test-123",
        }

        check_kb_empty_and_inject_warning(state)

        assert state["kb_context"].startswith("\n⚠️⚠️⚠️")
        assert "Original short context" in state["kb_context"]

    def test_does_not_overwrite_context_key(self):
        """Does not overwrite state['context'] - preserves KB chunks."""
        original_context = "A" * 50  # Short context triggers warning
        state = {
            "kb_sources_metadata": [],
            "context": original_context,
            "messages": [],
            "request_id": "test-123",
        }

        check_kb_empty_and_inject_warning(state)

        # context should NOT be overwritten (per DEV-242 Phase 10)
        assert state["context"] == original_context
