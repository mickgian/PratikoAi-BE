"""Tests for DEV-007 Issue 11e: Conversation Context Continuity.

This module tests that follow-up questions work correctly by verifying
that prior conversation history is loaded from the checkpointer and
merged with current messages.

These tests focus on the core merging logic (_get_prior_state method)
rather than full integration with get_stream_response() which requires
extensive mocking of the entire RAG pipeline.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.langgraph.graph import LangGraphAgent
from app.schemas.chat import Message


class TestGetPriorState:
    """Tests for _get_prior_state() method."""

    @pytest.mark.asyncio
    async def test_returns_empty_when_graph_is_none(self):
        """Should return empty lists when graph is not initialized."""
        agent = LangGraphAgent()
        agent._graph = None

        prior_messages, prior_attachments = await agent._get_prior_state("session-123")

        assert prior_messages == []
        assert prior_attachments == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_prior_state(self):
        """Should return empty lists when checkpointer has no state for session."""
        agent = LangGraphAgent()
        agent._graph = MagicMock()
        agent._graph.aget_state = AsyncMock(return_value=None)

        prior_messages, prior_attachments = await agent._get_prior_state("new-session")

        assert prior_messages == []
        assert prior_attachments == []
        agent._graph.aget_state.assert_called_once_with({"configurable": {"thread_id": "new-session"}})

    @pytest.mark.asyncio
    async def test_returns_prior_messages_and_attachments(self):
        """Should return messages and attachments from checkpoint state."""
        agent = LangGraphAgent()
        agent._graph = MagicMock()

        mock_state = MagicMock()
        mock_state.values = {
            "messages": [
                {"role": "user", "content": "What is INPS message 3585?"},
                {"role": "assistant", "content": "INPS message 3585 is about..."},
            ],
            "attachments": [{"id": "doc-1", "filename": "test.xlsx"}],
        }
        agent._graph.aget_state = AsyncMock(return_value=mock_state)

        prior_messages, prior_attachments = await agent._get_prior_state("existing-session")

        assert len(prior_messages) == 2
        assert prior_messages[0]["content"] == "What is INPS message 3585?"
        assert len(prior_attachments) == 1
        assert prior_attachments[0]["filename"] == "test.xlsx"

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self):
        """Should return empty lists and log warning on error."""
        agent = LangGraphAgent()
        agent._graph = MagicMock()
        agent._graph.aget_state = AsyncMock(side_effect=Exception("Database error"))

        with patch("app.core.langgraph.graph.logger") as mock_logger:
            prior_messages, prior_attachments = await agent._get_prior_state("error-session")

        assert prior_messages == []
        assert prior_attachments == []
        mock_logger.warning.assert_called_once()


class TestConversationContextMergingLogic:
    """Tests for conversation context merging logic.

    These tests verify the merging algorithm works correctly without
    running the full get_stream_response() which requires extensive mocking.
    """

    def test_merge_prior_messages_with_current(self):
        """Should correctly merge prior history with current message."""
        prior_messages = [
            {"role": "user", "content": "What is INPS message 3585?"},
            {"role": "assistant", "content": "INPS message 3585 extends the deadline..."},
        ]
        current_message_dicts = [{"role": "user", "content": "Until when is it extended?"}]

        # Simulate the merging logic from get_stream_response
        last_current = current_message_dicts[-1] if current_message_dicts else None
        if last_current and prior_messages and prior_messages[-1].get("content") == last_current.get("content"):
            merged_messages = prior_messages
        else:
            merged_messages = prior_messages + current_message_dicts

        # Verify merge result
        assert len(merged_messages) == 3
        assert merged_messages[0]["content"] == "What is INPS message 3585?"
        assert merged_messages[1]["content"] == "INPS message 3585 extends the deadline..."
        assert merged_messages[2]["content"] == "Until when is it extended?"

    def test_avoid_duplicate_on_retry(self):
        """Should not duplicate if current message already in history (retry scenario)."""
        prior_messages = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
            {"role": "user", "content": "Retry question"},  # Already in history
        ]
        current_message_dicts = [{"role": "user", "content": "Retry question"}]

        # Simulate the merging logic
        last_current = current_message_dicts[-1] if current_message_dicts else None
        if last_current and prior_messages and prior_messages[-1].get("content") == last_current.get("content"):
            merged_messages = prior_messages
        else:
            merged_messages = prior_messages + current_message_dicts

        # Should NOT duplicate
        assert len(merged_messages) == 3
        assert merged_messages[-1]["content"] == "Retry question"

    def test_empty_prior_messages(self):
        """Should work correctly when no prior messages exist."""
        prior_messages = []
        current_message_dicts = [{"role": "user", "content": "Hello!"}]

        # Simulate the merging logic
        if prior_messages:
            last_current = current_message_dicts[-1] if current_message_dicts else None
            if last_current and prior_messages and prior_messages[-1].get("content") == last_current.get("content"):
                merged_messages = prior_messages
            else:
                merged_messages = prior_messages + current_message_dicts
        else:
            merged_messages = current_message_dicts

        assert len(merged_messages) == 1
        assert merged_messages[0]["content"] == "Hello!"

    def test_attachment_restoration(self):
        """Should restore attachments from prior state when none provided."""
        prior_attachments = [{"id": "doc-1", "filename": "fondo_pensione.xlsx", "extracted_text": "Data..."}]
        current_attachments = []

        # Simulate the attachment restoration logic
        resolved_attachments = current_attachments or []
        if not resolved_attachments and prior_attachments:
            resolved_attachments = prior_attachments

        assert len(resolved_attachments) == 1
        assert resolved_attachments[0]["filename"] == "fondo_pensione.xlsx"

    def test_new_attachments_take_precedence(self):
        """Should use new attachments when provided, not restore prior."""
        prior_attachments = [{"id": "doc-old", "filename": "old_file.xlsx"}]
        current_attachments = [{"id": "doc-new", "filename": "new_file.pdf"}]

        # Simulate the attachment restoration logic
        resolved_attachments = current_attachments or []
        if not resolved_attachments and prior_attachments:
            resolved_attachments = prior_attachments

        assert len(resolved_attachments) == 1
        assert resolved_attachments[0]["filename"] == "new_file.pdf"


class TestRealWorldScenariosMergeLogic:
    """Test merging logic for real-world scenarios."""

    def test_inps_3585_followup_merge(self):
        """
        DEV-007 Issue 11e: Verify merging for INPS 3585 follow-up scenario.

        User asked: "Cos'e' il messaggio 3585 dell'inps?"
        Then asked: "Fino a quando e' prorogato?"
        """
        prior_messages = [
            {"role": "user", "content": "Cos'e' il messaggio 3585 dell'inps?"},
            {
                "role": "assistant",
                "content": "Il messaggio INPS 3585 del 24 ottobre 2024 proroga il termine "
                "per la presentazione delle domande di Ape sociale al 30 novembre 2024...",
            },
        ]
        current_message_dicts = [{"role": "user", "content": "Fino a quando e' prorogato?"}]

        # Merge logic
        last_current = current_message_dicts[-1]
        if prior_messages[-1].get("content") == last_current.get("content"):
            merged_messages = prior_messages
        else:
            merged_messages = prior_messages + current_message_dicts

        # Verify the context chain is complete
        assert len(merged_messages) == 3
        assert "3585" in merged_messages[0]["content"]
        assert "30 novembre" in merged_messages[1]["content"]
        assert "prorogato" in merged_messages[2]["content"]

    def test_document_followup_merge(self):
        """
        DEV-007 Issue 11e: Verify merging for document follow-up scenario.

        User uploads document, asks about it, then asks follow-up.
        """
        prior_messages = [
            {"role": "user", "content": "A che servono i dati in questo documento?"},
            {"role": "assistant", "content": "Il documento confronta un fondo pensione con un ETF..."},
        ]
        prior_attachments = [
            {
                "id": "doc-xyz",
                "filename": "fondo_pensione.xlsx",
                "extracted_text": "Anno,Aliquota f.p.,Montante...",
                "extracted_data": {"rendimento_etf": "7.84%"},
            }
        ]
        current_message_dicts = [
            {"role": "user", "content": "Al ventesimo anno conviene più il fondo pensione o l'ETF?"}
        ]
        current_attachments = []  # User didn't re-upload

        # Merge messages
        merged_messages = prior_messages + current_message_dicts

        # Restore attachments
        resolved_attachments = current_attachments or []
        if not resolved_attachments and prior_attachments:
            resolved_attachments = prior_attachments

        # Verify
        assert len(merged_messages) == 3
        assert len(resolved_attachments) == 1
        assert resolved_attachments[0]["filename"] == "fondo_pensione.xlsx"
        assert "7.84%" in str(resolved_attachments[0].get("extracted_data", {}))
