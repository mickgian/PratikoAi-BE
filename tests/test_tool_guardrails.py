"""Unit tests for tool guardrails."""

import pytest
from app.core.rag.tool_guardrails import (
    should_execute_tool_call,
    filter_tool_calls,
    MAX_TOOL_CALLS_PER_TURN,
    _generate_tool_call_key
)


class TestToolGuardrails:
    """Test suite for tool calling guardrails."""

    def test_first_tool_call_allowed(self):
        """Test that first tool call is allowed."""
        prev_calls = []
        new_call = {
            "function": {
                "name": "search_kb",
                "arguments": '{"query": "CCNL"}'
            }
        }

        decision = should_execute_tool_call(prev_calls, new_call)

        assert decision.should_execute == True
        assert decision.reason == "passed_guardrails"
        assert decision.tool_name == "search_kb"

    def test_second_tool_call_blocked(self):
        """Test that second tool call is blocked (max 1 per turn)."""
        prev_calls = [{
            "function": {
                "name": "search_kb",
                "arguments": '{"query": "CCNL"}'
            }
        }]
        new_call = {
            "function": {
                "name": "search_ccnl",
                "arguments": '{"query": "metalmeccanici"}'
            }
        }

        decision = should_execute_tool_call(prev_calls, new_call)

        assert decision.should_execute == False
        assert "max_calls_reached" in decision.reason
        assert decision.tool_name == "search_ccnl"

    def test_duplicate_tool_call_blocked(self):
        """Test that duplicate tool call is blocked when using filter."""
        # Two identical calls in the list - should be deduplicated
        tool_calls = [
            {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}},
            {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}  # Duplicate
        ]

        filtered = filter_tool_calls(tool_calls)

        # Should only keep first one, removing duplicate
        assert len(filtered) == 1
        assert filtered[0]["function"]["name"] == "search_kb"

    def test_different_arguments_allowed(self):
        """Test that same tool with different arguments is allowed (if under limit)."""
        prev_calls = []  # Empty to test first call
        new_call = {
            "function": {
                "name": "search_kb",
                "arguments": '{"query": "IVA"}'
            }
        }

        decision = should_execute_tool_call(prev_calls, new_call)

        assert decision.should_execute == True

    def test_filter_tool_calls_max_one(self):
        """Test that filter_tool_calls returns max 1 tool."""
        tool_calls = [
            {"function": {"name": "tool1", "arguments": "{}"}},
            {"function": {"name": "tool2", "arguments": "{}"}},
            {"function": {"name": "tool3", "arguments": "{}"}}
        ]

        filtered = filter_tool_calls(tool_calls)

        assert len(filtered) == 1
        assert filtered[0]["function"]["name"] == "tool1"

    def test_filter_tool_calls_removes_duplicates(self):
        """Test that filter_tool_calls removes duplicates."""
        tool_calls = [
            {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}},
            {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}  # Duplicate
        ]

        filtered = filter_tool_calls(tool_calls)

        assert len(filtered) == 1

    def test_filter_tool_calls_empty_list(self):
        """Test that filter_tool_calls handles empty list."""
        filtered = filter_tool_calls([])

        assert filtered == []

    def test_filter_tool_calls_with_prev_calls(self):
        """Test filter_tool_calls with previous calls."""
        prev_calls = [{
            "function": {"name": "search_kb", "arguments": '{"query": "A"}'}
        }]
        tool_calls = [
            {"function": {"name": "search_ccnl", "arguments": '{"query": "B"}'}}
        ]

        filtered = filter_tool_calls(tool_calls, prev_calls)

        # Already have 1 previous call, so new call should be blocked
        assert len(filtered) == 0

    def test_generate_tool_call_key_consistent(self):
        """Test that _generate_tool_call_key is consistent."""
        call1 = {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}
        call2 = {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}

        key1 = _generate_tool_call_key(call1)
        key2 = _generate_tool_call_key(call2)

        assert key1 == key2

    def test_generate_tool_call_key_different_args(self):
        """Test that _generate_tool_call_key differs for different arguments."""
        call1 = {"function": {"name": "search_kb", "arguments": '{"query": "CCNL"}'}}
        call2 = {"function": {"name": "search_kb", "arguments": '{"query": "IVA"}'}}

        key1 = _generate_tool_call_key(call1)
        key2 = _generate_tool_call_key(call2)

        assert key1 != key2

    def test_generate_tool_call_key_different_names(self):
        """Test that _generate_tool_call_key differs for different tool names."""
        call1 = {"function": {"name": "search_kb", "arguments": '{}'}}
        call2 = {"function": {"name": "search_ccnl", "arguments": '{}'}}

        key1 = _generate_tool_call_key(call1)
        key2 = _generate_tool_call_key(call2)

        assert key1 != key2

    def test_max_tool_calls_per_turn_constant(self):
        """Test that MAX_TOOL_CALLS_PER_TURN is set correctly."""
        assert MAX_TOOL_CALLS_PER_TURN == 1

    def test_invalid_tool_call_format(self):
        """Test handling of invalid tool call format."""
        prev_calls = []
        new_call = {"invalid": "format"}

        # Should handle gracefully
        key = _generate_tool_call_key(new_call)
        assert "unknown|invalid" in key
