"""Integration tests for chat history full flow.

Tests the complete chat history workflow: save → retrieve → export → delete
using a real database with proper fixtures.
"""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from app.models.data_export import QueryHistory
from app.models.user import User
from app.services.chat_history_service import ChatHistoryService


class TestChatHistoryIntegration:
    """Integration tests for chat history service with real database."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_chat_interaction(self, test_db, test_user, test_session_id):
        """Test saving a chat interaction and retrieving it from the database."""
        # Arrange
        service = ChatHistoryService()
        user_query = "What is IVA in Italy?"
        ai_response = "IVA (Imposta sul Valore Aggiunto) is the Italian Value-Added Tax."

        # Act - Save chat interaction
        record_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query=user_query,
            ai_response=ai_response,
            db=test_db,
            model_used="gpt-4-turbo",
            tokens_used=150,
            cost_cents=2,
            response_time_ms=1200,
            response_cached=False,
        )

        # Assert - Verify record was saved
        assert record_id is not None
        assert isinstance(record_id, str)

        # Verify record in database
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.id == uuid.UUID(record_id)))
        saved_record = result.scalar_one_or_none()

        assert saved_record is not None
        assert saved_record.user_id == test_user.id
        assert saved_record.session_id == test_session_id
        assert saved_record.query == user_query
        assert saved_record.response == ai_response
        assert saved_record.model_used == "gpt-4-turbo"
        assert saved_record.tokens_used == 150
        assert saved_record.cost_cents == 2
        assert saved_record.response_cached is False

    @pytest.mark.asyncio
    async def test_retrieve_session_history(self, test_db, test_user, sample_chat_messages):
        """Test retrieving chat history for a session."""
        # Arrange
        service = ChatHistoryService()
        session_id = (
            await test_db.execute(select(QueryHistory.session_id).where(QueryHistory.user_id == test_user.id).limit(1))
        ).scalar_one()

        # Act - Retrieve session history
        messages = await service.get_session_history(user_id=test_user.id, session_id=session_id, limit=10, db=test_db)

        # Assert
        assert len(messages) == 3
        assert messages[0]["query"] == "What is IVA in Italy?"
        assert messages[1]["query"] == "How much is the standard IVA rate?"
        assert messages[2]["query"] == "Are there reduced IVA rates?"

        # Verify messages have all required fields
        for msg in messages:
            assert "id" in msg
            assert "query" in msg
            assert "response" in msg
            assert "timestamp" in msg
            assert "model_used" in msg
            assert "tokens_used" in msg

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, test_db, test_user, sample_chat_messages):
        """Test retrieving list of user sessions."""
        # Arrange
        service = ChatHistoryService()

        # Act
        sessions = await service.get_user_sessions(user_id=test_user.id, db=test_db)

        # Assert
        assert len(sessions) >= 1
        assert "session_id" in sessions[0]
        assert "message_count" in sessions[0]
        assert "last_message_at" in sessions[0]
        assert sessions[0]["message_count"] == 3

    @pytest.mark.asyncio
    async def test_delete_session(self, test_db, test_user, test_session_id):
        """Test deleting a chat session."""
        # Arrange
        service = ChatHistoryService()

        # Create a message
        await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="Test query",
            ai_response="Test response",
            db=test_db,
        )

        # Act - Delete session
        deleted_count = await service.delete_session(user_id=test_user.id, session_id=test_session_id, db=test_db)

        # Assert
        assert deleted_count > 0

        # Verify session is deleted
        result = await test_db.execute(
            select(QueryHistory).where(
                QueryHistory.user_id == test_user.id, QueryHistory.session_id == test_session_id
            )
        )
        remaining_messages = result.scalars().all()
        assert len(remaining_messages) == 0

    @pytest.mark.asyncio
    async def test_cascade_delete_on_user_deletion(self, test_db, test_user, sample_chat_messages):
        """Test that chat history is CASCADE deleted when user is deleted (GDPR compliance)."""
        # Arrange - Verify messages exist
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.user_id == test_user.id))
        messages_before = result.scalars().all()
        assert len(messages_before) == 3

        # Act - Delete user (should CASCADE delete chat history)
        await test_db.delete(test_user)
        await test_db.commit()

        # Assert - Verify chat history deleted
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.user_id == test_user.id))
        messages_after = result.scalars().all()
        assert len(messages_after) == 0

    @pytest.mark.asyncio
    async def test_conversation_threading(self, test_db, test_user, test_session_id):
        """Test conversation threading with conversation_id."""
        # Arrange
        service = ChatHistoryService()
        conversation_id = str(uuid.uuid4())

        # Act - Create multiple messages in same conversation
        _msg1_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="What is IVA?",
            ai_response="IVA is Value-Added Tax.",
            conversation_id=conversation_id,
            db=test_db,
        )

        _msg2_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="What's the rate?",
            ai_response="The standard rate is 22%.",
            conversation_id=conversation_id,
            db=test_db,
        )

        # Assert - Verify both messages share conversation_id
        result = await test_db.execute(
            select(QueryHistory).where(QueryHistory.conversation_id == uuid.UUID(conversation_id))
        )
        conversation_messages = result.scalars().all()
        assert len(conversation_messages) == 2
        assert all(str(msg.conversation_id) == conversation_id for msg in conversation_messages)

    @pytest.mark.asyncio
    async def test_italian_content_tracking(self, test_db, test_user, test_session_id):
        """Test tracking of Italian content in queries."""
        # Arrange
        service = ChatHistoryService()

        # Act - Save message with italian_content flag
        record_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="Come funziona l'IVA?",
            ai_response="L'IVA funziona così...",
            italian_content=True,
            db=test_db,
        )

        # Assert - Verify italian_content flag saved
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.id == uuid.UUID(record_id)))
        message = result.scalar_one()
        assert message.italian_content is True

    @pytest.mark.asyncio
    async def test_query_type_categorization(self, test_db, test_user, test_session_id):
        """Test query type categorization (tax_question, legal_question, etc.)."""
        # Arrange
        service = ChatHistoryService()

        # Act - Save message with query_type
        record_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="How do I calculate IVA?",
            ai_response="To calculate IVA...",
            query_type="tax_calculation",
            db=test_db,
        )

        # Assert - Verify query_type saved
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.id == uuid.UUID(record_id)))
        message = result.scalar_one()
        assert message.query_type == "tax_calculation"

    @pytest.mark.asyncio
    async def test_response_caching_tracking(self, test_db, test_user, test_session_id):
        """Test tracking of cached responses."""
        # Arrange
        service = ChatHistoryService()

        # Act - Save cached response
        record_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="What is IVA?",
            ai_response="IVA is Value-Added Tax.",
            response_cached=True,
            response_time_ms=50,  # Faster due to cache
            db=test_db,
        )

        # Assert - Verify caching metadata
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.id == uuid.UUID(record_id)))
        message = result.scalar_one()
        assert message.response_cached is True
        assert message.response_time_ms == 50

    @pytest.mark.asyncio
    async def test_usage_tracking(self, test_db, test_user, test_session_id):
        """Test tracking of tokens and cost."""
        # Arrange
        service = ChatHistoryService()

        # Act - Save with usage data
        record_id = await service.save_chat_interaction(
            user_id=test_user.id,
            session_id=test_session_id,
            user_query="Complex tax question...",
            ai_response="Detailed tax answer...",
            model_used="gpt-4-turbo",
            tokens_used=500,
            cost_cents=10,
            db=test_db,
        )

        # Assert - Verify usage tracking
        result = await test_db.execute(select(QueryHistory).where(QueryHistory.id == uuid.UUID(record_id)))
        message = result.scalar_one()
        assert message.model_used == "gpt-4-turbo"
        assert message.tokens_used == 500
        assert message.cost_cents == 10
