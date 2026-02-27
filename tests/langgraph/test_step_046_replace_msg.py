"""TDD Regression Tests for Step 46: Replace System Message.

These tests protect against the P0.7 bug where Step 46 was looking for
'new_system_prompt' but Step 44 stores the prompt as 'system_prompt'.

DEV-007: Critical regression tests for multi-attachment Turn 2 context update.

Bug scenario:
1. Turn 1: User uploads Payslip 10, system prompt created with Payslip 10 context
2. Turn 2: User uploads Payslip 8 + 9, Step 44 builds new system_prompt
3. Step 45 routes to Step 46 (sys_msg_exists=True)
4. BUG: Step 46 looked for ctx["new_system_prompt"] but got None
5. Result: Step 46 skipped replacement, LLM saw only Payslip 10

Fix: Step 46 now checks both "new_system_prompt" and "system_prompt" keys.
"""

from unittest.mock import MagicMock, patch

import pytest


class TestStep46SystemPromptKeyLookup:
    """Test that Step 46 correctly retrieves system_prompt from context.

    P0.7 FIX: Step 46 must check both 'new_system_prompt' and 'system_prompt'
    keys because Step 44 stores the prompt as 'system_prompt'.
    """

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_retrieves_system_prompt_from_ctx(self, mock_timer, mock_log):
        """P0.7 REGRESSION: Step 46 MUST retrieve prompt from ctx['system_prompt'].

        This is the exact key that Step 44 uses to store the built prompt.
        Before P0.7 fix, Step 46 only looked for ctx['new_system_prompt'].
        """
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: Messages with existing system message (Turn 2 scenario)
        messages = [
            MagicMock(role="system", content="Old Turn 1 context about Payslip 10"),
            MagicMock(role="user", content="E queste?"),
        ]

        # Given: Context with system_prompt (as Step 44 stores it)
        ctx = {
            "system_prompt": "New context about Payslip 8 and Payslip 9",  # Step 44's key
            "classification": {"domain": "document_analysis", "confidence": 0.9},
        }

        # When: step_46__replace_msg is called
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: System message should be replaced with new content
        assert result[0].content == "New context about Payslip 8 and Payslip 9", (
            "Step 46 must retrieve and use ctx['system_prompt'] from Step 44"
        )

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_also_accepts_new_system_prompt_key(self, mock_timer, mock_log):
        """Step 46 should still accept 'new_system_prompt' for backward compatibility."""
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: Messages with existing system message
        messages = [
            MagicMock(role="system", content="Old context"),
            MagicMock(role="user", content="Hello"),
        ]

        # Given: Context with new_system_prompt (legacy key)
        ctx = {
            "new_system_prompt": "New context via legacy key",
            "classification": {"domain": "tax", "confidence": 0.8},
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: Should work with legacy key too
        assert result[0].content == "New context via legacy key"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_prefers_new_system_prompt_over_system_prompt(self, mock_timer, mock_log):
        """When both keys exist, new_system_prompt takes precedence."""
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: Messages with existing system message
        messages = [
            MagicMock(role="system", content="Old context"),
            MagicMock(role="user", content="Hello"),
        ]

        # Given: Context with BOTH keys (edge case)
        ctx = {
            "new_system_prompt": "New context (preferred)",
            "system_prompt": "System prompt (fallback)",
            "classification": {"domain": "tax", "confidence": 0.8},
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: new_system_prompt should take precedence
        assert result[0].content == "New context (preferred)"


class TestStep46ReplacementLogic:
    """Test Step 46's system message replacement logic."""

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_replaces_when_all_conditions_met(self, mock_timer, mock_log):
        """Step 46 replaces system message when:
        1. System message exists
        2. Classification is available
        3. New system prompt is provided (via system_prompt key)
        """
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: All conditions met
        messages = [
            MagicMock(role="system", content="Old context"),
            MagicMock(role="user", content="E queste?"),
        ]
        ctx = {
            "system_prompt": "New Turn 2 context with Payslip 8, 9",
            "classification": {"domain": "document_analysis"},
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: Message replaced
        assert result[0].content == "New Turn 2 context with Payslip 8, 9"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_skips_when_no_system_prompt_provided(self, mock_timer, mock_log):
        """Step 46 skips replacement when no system_prompt in context.

        This was the P0.7 bug - Step 46 never found the prompt because
        it was only looking for 'new_system_prompt'.
        """
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: No system_prompt in context
        messages = [
            MagicMock(role="system", content="Old context that should NOT change"),
            MagicMock(role="user", content="E queste?"),
        ]
        ctx = {
            "classification": {"domain": "document_analysis"},
            # Missing both system_prompt and new_system_prompt
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: Original message unchanged
        assert result[0].content == "Old context that should NOT change"

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_skips_when_no_classification(self, mock_timer, mock_log):
        """Step 46 skips replacement when no classification available."""
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: No classification
        messages = [
            MagicMock(role="system", content="Old context"),
            MagicMock(role="user", content="Hello"),
        ]
        ctx = {
            "system_prompt": "New context",
            # Missing classification
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: Original message unchanged
        assert result[0].content == "Old context"


class TestStep46DictMessages:
    """Test Step 46 with dict messages (as used in RAGState)."""

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_step_46_works_with_dict_messages(self, mock_timer, mock_log):
        """Step 46 should work with dict messages (common in RAGState)."""
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: Dict messages (as stored in RAGState)
        messages = [
            {"role": "system", "content": "Old Turn 1 context"},
            {"role": "user", "content": "E queste?"},
        ]
        ctx = {
            "system_prompt": "New Turn 2 context with all attachments",
            "classification": {"domain": "document_analysis", "confidence": 0.85},
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: First message should be replaced (returns Message object)
        assert result[0].content == "New Turn 2 context with all attachments"
        assert result[0].role == "system"


class TestStep46RegressionMultiAttachment:
    """End-to-end regression tests for the multi-attachment Turn 2 bug.

    These tests simulate the exact scenario that was broken:
    Turn 1: Upload Payslip 10
    Turn 2: Upload Payslip 8 + 9, ask "E queste?"
    Expected: LLM sees context with Payslip 8 + 9
    Bug: LLM only saw Payslip 10 (Turn 1 context)
    """

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_turn2_attachment_context_replaces_turn1(self, mock_timer, mock_log):
        """P0.7 CRITICAL: Turn 2 context MUST replace Turn 1 context.

        This is the exact regression test for the bug. Before P0.7,
        Step 46 would skip replacement because it couldn't find the prompt.
        """
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        # Given: Turn 1 system message with Payslip 10 context
        turn1_context = """# Relevant Knowledge Base Context
From your documents:
**>>> NUOVI DOCUMENTI APPENA CARICATI (1): Payslip 10 - Ottobre 2025.pdf <<<**
[DOCUMENTI ALLEGATI ORA] [Documento: Payslip 10 - Ottobre 2025.pdf]
Payslip content for October 2025..."""

        # Given: Turn 2 context with Payslip 8 + 9 (built by Step 44)
        turn2_context = """# Relevant Knowledge Base Context
From your documents:
**>>> NUOVI DOCUMENTI APPENA CARICATI (2): Payslip 8 - Agosto 2025.pdf, Payslip 9 - Settembre 2025.pdf <<<**
[DOCUMENTI ALLEGATI ORA] [Documento: Payslip 8 - Agosto 2025.pdf]
Payslip content for August 2025...
---
[DOCUMENTI ALLEGATI ORA] [Documento: Payslip 9 - Settembre 2025.pdf]
Payslip content for September 2025...
---
[CONTESTO PRECEDENTE] [Documento: Payslip 10 - Ottobre 2025.pdf]
(Previously discussed)"""

        messages = [
            MagicMock(role="system", content=turn1_context),
            MagicMock(role="user", content="Spiegami questa fattura"),
            MagicMock(role="assistant", content="Analysis of Payslip 10..."),
            MagicMock(role="user", content="E queste?"),  # Turn 2 question
        ]

        ctx = {
            "system_prompt": turn2_context,  # Step 44 stores it here
            "classification": {
                "domain": "document_analysis",
                "action": "analyze",
                "confidence": 0.92,
            },
        }

        # When: Step 46 processes Turn 2
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: System message MUST contain Turn 2 context
        system_content = result[0].content

        # Verify Turn 2 documents are present
        assert "Payslip 8 - Agosto 2025" in system_content, "Turn 2 context must include Payslip 8"
        assert "Payslip 9 - Settembre 2025" in system_content, "Turn 2 context must include Payslip 9"
        assert "NUOVI DOCUMENTI APPENA CARICATI (2)" in system_content, "Turn 2 context must show 2 new documents"

        # Verify Turn 1's "NUOVI DOCUMENTI (1)" header is replaced
        assert "NUOVI DOCUMENTI APPENA CARICATI (1): Payslip 10" not in system_content, (
            "Turn 1's header should be replaced with Turn 2's header"
        )

    @patch("app.orchestrators.prompting.rag_step_log")
    @patch("app.orchestrators.prompting.rag_step_timer")
    def test_turn2_preserves_prior_document_in_context(self, mock_timer, mock_log):
        """Turn 2 context should include prior document as CONTESTO PRECEDENTE."""
        from app.orchestrators.prompting import step_46__replace_msg

        # Mock timer context manager
        mock_timer.return_value.__enter__ = MagicMock()
        mock_timer.return_value.__exit__ = MagicMock()

        turn2_context = """From your documents:
**>>> NUOVI DOCUMENTI APPENA CARICATI (2): Payslip 8.pdf, Payslip 9.pdf <<<**
[DOCUMENTI ALLEGATI ORA] [Documento: Payslip 8.pdf]
New upload 1
---
[DOCUMENTI ALLEGATI ORA] [Documento: Payslip 9.pdf]
New upload 2
---
[CONTESTO PRECEDENTE] [Documento: Payslip 10.pdf]
Previously discussed document"""

        messages = [
            MagicMock(role="system", content="Old context"),
            MagicMock(role="user", content="E queste?"),
        ]

        ctx = {
            "system_prompt": turn2_context,
            "classification": {"domain": "document_analysis"},
        }

        # When
        result = step_46__replace_msg(messages=messages, ctx=ctx)

        # Then: Prior document should be marked as CONTESTO PRECEDENTE
        assert "[CONTESTO PRECEDENTE]" in result[0].content
        assert "Payslip 10.pdf" in result[0].content


class TestStep46NodeWrapperIntegration:
    """Test Step 46 node wrapper integration."""

    @pytest.mark.asyncio
    async def test_node_step_46_uses_state_system_prompt(self):
        """Node wrapper passes state['system_prompt'] to orchestrator."""
        from app.core.langgraph.nodes.step_046__replace_msg import node_step_46

        # Given: State with system_prompt from Step 44
        state = {
            "messages": [
                {"role": "system", "content": "Old Turn 1 context"},
                {"role": "user", "content": "E queste?"},
            ],
            "system_prompt": "New Turn 2 context with Payslip 8 and 9",
            "classification": {"domain": "document_analysis", "confidence": 0.9},
        }

        # When: node_step_46 processes state
        result_state = await node_step_46(state)

        # Then: Messages should be updated with new system prompt
        assert result_state.get("sys_msg_replaced") is True, (
            "Step 46 node should mark sys_msg_replaced=True when replacement succeeds"
        )

    @pytest.mark.asyncio
    async def test_node_step_46_skips_without_system_prompt(self):
        """Node wrapper handles missing system_prompt gracefully."""
        from app.core.langgraph.nodes.step_046__replace_msg import node_step_46

        # Given: State WITHOUT system_prompt
        state = {
            "messages": [
                {"role": "system", "content": "Old context"},
                {"role": "user", "content": "Hello"},
            ],
            "classification": {"domain": "tax"},
            # No system_prompt
        }

        # When
        result_state = await node_step_46(state)

        # Then: Should not crash, sys_msg_replaced may be False or None
        # The important thing is it doesn't error
        assert "messages" in result_state
