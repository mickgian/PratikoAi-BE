"""TDD Tests for Page Refresh Persistence Bug.

These tests verify that conversation messages are MERGED in checkpoint,
not REPLACED, to prevent Turn 2 content corruption after page refresh.

DEV-007: Written BEFORE the fix to ensure TDD approach.

BUG: After page refresh:
- Turn 2's user message "E queste?" becomes "Spiegami questa fattura" (Turn 1's text!)
- Turn 2's assistant response shows PII placeholders
- Turn 2's response shows Payslip 10 instead of Payslip 8+9

ROOT CAUSE: RAGState.messages has no reducer, causing checkpoint to
REPLACE messages instead of MERGING them.

FIX: Add custom merge_messages reducer to RAGState.
"""

import pytest


class TestMergeMessagesReducer:
    """Test the merge_messages reducer function."""

    def test_merge_messages_exists(self):
        """merge_messages function must exist in types module."""
        from app.core.langgraph.types import merge_messages

        assert callable(merge_messages), "merge_messages must be a callable function"

    def test_merge_messages_with_none_existing(self):
        """When existing is None, return new messages."""
        from app.core.langgraph.types import merge_messages

        new_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = merge_messages(None, new_messages)

        assert result == new_messages

    def test_merge_messages_with_none_new(self):
        """When new is None, return existing messages."""
        from app.core.langgraph.types import merge_messages

        existing_messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        result = merge_messages(existing_messages, None)

        assert result == existing_messages

    def test_merge_messages_appends_new(self):
        """New messages should be appended to existing."""
        from app.core.langgraph.types import merge_messages

        existing = [
            {"role": "user", "content": "Spiegami questa fattura"},
            {"role": "assistant", "content": "Analysis of Payslip 10..."},
        ]

        new = [
            {"role": "user", "content": "Spiegami questa fattura"},
            {"role": "assistant", "content": "Analysis of Payslip 10..."},
            {"role": "user", "content": "E queste?"},  # NEW message
        ]

        result = merge_messages(existing, new)

        # Should contain all messages, with "E queste?" appended
        assert len(result) == 3
        assert result[0]["content"] == "Spiegami questa fattura"
        assert result[1]["content"] == "Analysis of Payslip 10..."
        assert result[2]["content"] == "E queste?"

    def test_merge_messages_deduplicates_by_role_and_content(self):
        """Messages with same (role, content) should not be duplicated."""
        from app.core.langgraph.types import merge_messages

        existing = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]

        new = [
            {"role": "user", "content": "Hello"},  # Duplicate
            {"role": "assistant", "content": "Hi"},  # Duplicate
            {"role": "user", "content": "How are you?"},  # New
        ]

        result = merge_messages(existing, new)

        # Should have 3 messages, not 5 (duplicates removed)
        assert len(result) == 3
        contents = [m["content"] for m in result]
        assert contents == ["Hello", "Hi", "How are you?"]


class TestMergeMessagesRegressionScenarios:
    """Regression tests for specific user scenarios."""

    def test_turn2_user_message_preserved(self):
        """Turn 2's user message 'E queste?' must not become 'Spiegami questa fattura'.

        This is THE critical regression test for the page refresh bug.
        """
        from app.core.langgraph.types import merge_messages

        # Turn 1 state in checkpoint
        turn1_checkpoint = [
            {"role": "user", "content": "Spiegami questa fattura"},
            {"role": "assistant", "content": "Analysis of Payslip 10..."},
        ]

        # Turn 2 adds new messages
        turn2_messages = [
            {"role": "user", "content": "Spiegami questa fattura"},
            {"role": "assistant", "content": "Analysis of Payslip 10..."},
            {"role": "user", "content": "E queste?"},  # Turn 2 user message
            {"role": "assistant", "content": "Analysis of Payslip 8 and 9..."},  # Turn 2 response
        ]

        result = merge_messages(turn1_checkpoint, turn2_messages)

        # Verify Turn 2's user message is preserved
        user_messages = [m["content"] for m in result if m["role"] == "user"]
        assert "E queste?" in user_messages, (
            f"Turn 2's user message 'E queste?' must be preserved! Got: {user_messages}"
        )

    def test_turn2_assistant_response_preserved(self):
        """Turn 2's assistant response about Payslip 8+9 must be preserved."""
        from app.core.langgraph.types import merge_messages

        turn1_checkpoint = [
            {"role": "user", "content": "Spiegami questa fattura"},
            {"role": "assistant", "content": "Analysis of Payslip 10..."},
        ]

        turn2_messages = [
            {"role": "user", "content": "Spiegami questa fattura"},
            {"role": "assistant", "content": "Analysis of Payslip 10..."},
            {"role": "user", "content": "E queste?"},
            {"role": "assistant", "content": "Analysis of Payslip 8 and 9..."},
        ]

        result = merge_messages(turn1_checkpoint, turn2_messages)

        # Verify Turn 2's assistant response is preserved
        assistant_messages = [m["content"] for m in result if m["role"] == "assistant"]
        assert "Analysis of Payslip 8 and 9..." in assistant_messages, (
            f"Turn 2's response must be preserved! Got: {assistant_messages}"
        )

    def test_messages_not_replaced_entirely(self):
        """Existing messages must not be REPLACED by new messages."""
        from app.core.langgraph.types import merge_messages

        existing = [
            {"role": "user", "content": "Original message 1"},
            {"role": "assistant", "content": "Original response 1"},
        ]

        # If reducer is broken (no merge), this would REPLACE existing
        new = [
            {"role": "user", "content": "New message only"},
        ]

        result = merge_messages(existing, new)

        # Original messages must still be present
        contents = [m["content"] for m in result]
        assert "Original message 1" in contents, "Existing messages must be preserved"
        assert "Original response 1" in contents, "Existing messages must be preserved"
        assert "New message only" in contents, "New messages must be added"


class TestRAGStateHasMergeMessagesReducer:
    """Test that RAGState uses the merge_messages reducer."""

    def test_ragstate_messages_has_annotated_reducer(self):
        """RAGState.messages must be Annotated with merge_messages reducer."""
        from typing import Annotated, get_args, get_origin, get_type_hints

        from app.core.langgraph.types import RAGState, merge_messages

        # Get the type hints for RAGState
        hints = get_type_hints(RAGState, include_extras=True)

        assert "messages" in hints, "RAGState must have 'messages' field"

        messages_type = hints["messages"]

        # Check if it's Annotated
        origin = get_origin(messages_type)
        assert origin is Annotated, f"RAGState.messages must be Annotated, got: {messages_type}"

        # Check if merge_messages is in the annotations
        args = get_args(messages_type)
        # args[0] is the base type (list[dict])
        # args[1:] are the annotations
        annotations = args[1:]

        assert merge_messages in annotations, (
            f"RAGState.messages must be annotated with merge_messages reducer. Got annotations: {annotations}"
        )
