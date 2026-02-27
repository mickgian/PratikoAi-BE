"""TDD Tests for Step 45: Check System Message.

These tests verify that Step 45 returns the correct key name 'sys_msg_exists'
to prevent regression where Turn 2 documents are ignored because the system
prompt is never replaced.

DEV-007: Written BEFORE the fix to ensure TDD approach.
"""

import pytest


class TestStep45KeyName:
    """Test that Step 45 orchestrator returns correct key names."""

    def test_step_45_returns_sys_msg_exists_key(self):
        """Step 45 MUST return 'sys_msg_exists' key, not 'system_exists'.

        This is the critical test - the bug was that orchestrator returned
        'system_exists' but node wrapper expected 'sys_msg_exists'.
        """
        from app.orchestrators.prompting import step_45__check_sys_msg

        # Given: Messages with existing system message
        messages = [{"role": "system", "content": "You are an assistant"}]

        # When: step_45__check_sys_msg is called (sync function)
        result = step_45__check_sys_msg(messages=messages, ctx={})

        # Then: Result contains 'sys_msg_exists' key (NOT 'system_exists')
        assert "sys_msg_exists" in result, "Must return 'sys_msg_exists' key"
        assert result["sys_msg_exists"] is True

    def test_step_45_detects_system_message_exists(self):
        """Step 45 should detect when system message exists."""
        from app.orchestrators.prompting import step_45__check_sys_msg

        # Given: Messages WITH system message
        messages = [
            {"role": "system", "content": "System prompt"},
            {"role": "user", "content": "Hello"},
        ]

        # When (sync function)
        result = step_45__check_sys_msg(messages=messages, ctx={})

        # Then
        assert result["sys_msg_exists"] is True

    def test_step_45_detects_no_system_message(self):
        """Step 45 should detect when NO system message exists."""
        from app.orchestrators.prompting import step_45__check_sys_msg

        # Given: Messages WITHOUT system message
        messages = [{"role": "user", "content": "Hello"}]

        # When (sync function)
        result = step_45__check_sys_msg(messages=messages, ctx={})

        # Then
        assert result["sys_msg_exists"] is False


class TestStep45NodeWrapper:
    """Test the node wrapper propagates state correctly."""

    @pytest.mark.asyncio
    async def test_node_step_45_sets_sys_msg_exists_in_state(self):
        """Node wrapper should set sys_msg_exists in state for router."""
        from app.core.langgraph.nodes.step_045__check_sys_msg import node_step_45

        # Given: State with existing system message
        state = {
            "messages": [
                {"role": "system", "content": "Context about Payslip 10..."},
                {"role": "user", "content": "Spiegami questa fattura"},
            ],
        }

        # When: node_step_45 processes state
        result_state = await node_step_45(state)

        # Then: sys_msg_exists should be True in state
        assert (
            result_state.get("sys_msg_exists") is True
        ), "Node wrapper must set sys_msg_exists=True when system message exists"


class TestStep45RegressionMultipleAttachments:
    """Regression tests for the multiple attachments bug.

    Bug: User uploads Payslip 8+9 in Turn 2, but LLM only sees Turn 1's
    context because system prompt was never replaced.
    """

    @pytest.mark.asyncio
    async def test_turn2_triggers_replace_path(self):
        """Turn 2 should trigger ReplaceMsg path when system message exists.

        The bug was that sys_msg_exists was always False, causing InsertMsg
        to skip (since system already exists), leaving old Turn 1 context.
        """
        from app.core.langgraph.nodes.step_045__check_sys_msg import node_step_45

        # Given: State simulating Turn 2 (system message already exists from Turn 1)
        state = {
            "messages": [
                {"role": "system", "content": "Old context about Payslip 10..."},
                {"role": "user", "content": "Spiegami questa fattura"},
                {"role": "assistant", "content": "Analysis of Payslip 10..."},
                {"role": "user", "content": "E queste?"},  # Turn 2
            ],
            "context": "New context about Payslip 8 and Payslip 9...",
        }

        # When: node_step_45 processes state
        result_state = await node_step_45(state)

        # Then: sys_msg_exists should be True, triggering ReplaceMsg path
        assert (
            result_state.get("sys_msg_exists") is True
        ), "Must detect existing system message to trigger ReplaceMsg path"
