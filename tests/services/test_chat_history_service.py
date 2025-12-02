"""Unit tests for ChatHistoryService.

Tests chat history persistence, retrieval, and GDPR compliance.

The ChatHistoryService methods accept an optional `db` parameter for dependency
injection, which allows us to pass mock database sessions directly without
needing to patch the get_db async generator.
"""

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.chat_history_service import ChatHistoryService


@pytest.fixture
def chat_history_service():
    """Fixture for ChatHistoryService instance."""
    return ChatHistoryService()


@pytest.fixture
def sample_user_id():
    """Fixture for sample user ID."""
    return 12345


@pytest.fixture
def sample_session_id():
    """Fixture for sample session ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_query():
    """Fixture for sample user query."""
    return "Come funziona l'IVA in Italia?"


@pytest.fixture
def sample_response():
    """Fixture for sample AI response."""
    return "L'IVA (Imposta sul Valore Aggiunto) e un'imposta indiretta sui consumi..."


@pytest.fixture
def mock_db():
    """Fixture for mock async database session.

    Creates a mock AsyncSession with common methods pre-configured.
    """
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    return db


class TestSaveChatInteraction:
    """Test suite for save_chat_interaction method."""

    @pytest.mark.asyncio
    async def test_save_chat_interaction_success(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
        sample_query,
        sample_response,
        mock_db,
    ):
        """Test successful chat interaction save."""
        # Act - pass mock_db directly via db parameter
        record_id = await chat_history_service.save_chat_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            user_query=sample_query,
            ai_response=sample_response,
            model_used="gpt-4-turbo",
            tokens_used=350,
            cost_cents=5,
            response_time_ms=1200,
            response_cached=False,
            db=mock_db,
        )

        # Assert
        assert record_id is not None
        assert isinstance(record_id, str)
        # Verify UUID format
        uuid.UUID(record_id)
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_chat_interaction_minimal_params(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
        sample_query,
        sample_response,
        mock_db,
    ):
        """Test save with only required parameters."""
        # Act
        record_id = await chat_history_service.save_chat_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            user_query=sample_query,
            ai_response=sample_response,
            db=mock_db,
        )

        # Assert
        assert record_id is not None
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_chat_interaction_with_conversation_id(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
        sample_query,
        sample_response,
        mock_db,
    ):
        """Test save with conversation ID for conversation threading."""
        # Arrange
        conversation_id = str(uuid.uuid4())

        # Act
        record_id = await chat_history_service.save_chat_interaction(
            user_id=sample_user_id,
            session_id=sample_session_id,
            user_query=sample_query,
            ai_response=sample_response,
            conversation_id=conversation_id,
            db=mock_db,
        )

        # Assert
        assert record_id is not None
        call_args = mock_db.execute.call_args
        # The second argument to execute is the params dict
        assert call_args[0][1]["conversation_id"] == conversation_id

    @pytest.mark.asyncio
    async def test_save_chat_interaction_database_error(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
        sample_query,
        sample_response,
    ):
        """Test error handling when database save fails."""
        # Arrange - create mock that raises an exception
        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(side_effect=Exception("Database connection failed"))

        # Act & Assert
        with pytest.raises(Exception, match="Database connection failed"):
            await chat_history_service.save_chat_interaction(
                user_id=sample_user_id,
                session_id=sample_session_id,
                user_query=sample_query,
                ai_response=sample_response,
                db=mock_db,
            )


class TestGetSessionHistory:
    """Test suite for get_session_history method."""

    @pytest.mark.asyncio
    async def test_get_session_history_success(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Test successful retrieval of session history."""
        # Arrange
        mock_rows = [
            (
                str(uuid.uuid4()),
                "Query 1",
                "Response 1",
                datetime.utcnow(),
                "gpt-4-turbo",
                350,
                5,
                False,
                1200,
            ),
            (
                str(uuid.uuid4()),
                "Query 2",
                "Response 2",
                datetime.utcnow(),
                "gpt-4-turbo",
                400,
                6,
                True,
                800,
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act - pass mock_db directly via db parameter
        history = await chat_history_service.get_session_history(
            user_id=sample_user_id,
            session_id=sample_session_id,
            limit=100,
            offset=0,
            db=mock_db,
        )

        # Assert
        assert len(history) == 2
        assert history[0]["query"] == "Query 1"
        assert history[1]["query"] == "Query 2"
        assert history[1]["response_cached"] is True
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session_history_pagination(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Test pagination with limit and offset."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        history = await chat_history_service.get_session_history(
            user_id=sample_user_id,
            session_id=sample_session_id,
            limit=50,
            offset=100,
            db=mock_db,
        )

        # Assert
        assert len(history) == 0
        call_args = mock_db.execute.call_args
        assert call_args[0][1]["limit"] == 50
        assert call_args[0][1]["offset"] == 100

    @pytest.mark.asyncio
    async def test_get_session_history_empty_result(
        self,
        chat_history_service,
        sample_user_id,
        sample_session_id,
    ):
        """Test retrieval when no messages exist."""
        # Arrange
        mock_result = MagicMock()
        mock_result.fetchall.return_value = []

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act
        history = await chat_history_service.get_session_history(
            user_id=sample_user_id,
            session_id=sample_session_id,
            db=mock_db,
        )

        # Assert
        assert len(history) == 0


class TestGetUserHistory:
    """Test suite for get_user_history method."""

    @pytest.mark.asyncio
    async def test_get_user_history_success(
        self,
        chat_history_service,
        sample_user_id,
    ):
        """Test successful retrieval of user history across sessions."""
        # Arrange
        session_id_1 = str(uuid.uuid4())
        session_id_2 = str(uuid.uuid4())

        mock_rows = [
            (
                str(uuid.uuid4()),
                session_id_1,
                "Query 1",
                "Response 1",
                datetime.utcnow(),
                "gpt-4-turbo",
                350,
                5,
            ),
            (
                str(uuid.uuid4()),
                session_id_2,
                "Query 2",
                "Response 2",
                datetime.utcnow(),
                "gpt-4-turbo",
                400,
                6,
            ),
        ]

        mock_result = MagicMock()
        mock_result.fetchall.return_value = mock_rows

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Act - pass mock_db directly via db parameter
        history = await chat_history_service.get_user_history(
            user_id=sample_user_id,
            limit=100,
            offset=0,
            db=mock_db,
        )

        # Assert
        assert len(history) == 2
        assert history[0]["session_id"] == session_id_1
        assert history[1]["session_id"] == session_id_2


class TestDeleteUserHistory:
    """Test suite for delete_user_history method."""

    @pytest.mark.asyncio
    async def test_delete_user_history_success(
        self,
        chat_history_service,
        sample_user_id,
    ):
        """Test successful deletion of all user history."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 42  # Number of deleted records

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act - pass mock_db directly via db parameter
        deleted_count = await chat_history_service.delete_user_history(
            user_id=sample_user_id,
            db=mock_db,
        )

        # Assert
        assert deleted_count == 42
        mock_db.execute.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_history_no_records(
        self,
        chat_history_service,
        sample_user_id,
    ):
        """Test deletion when user has no history."""
        # Arrange
        mock_result = MagicMock()
        mock_result.rowcount = 0

        mock_db = AsyncMock()
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()

        # Act
        deleted_count = await chat_history_service.delete_user_history(
            user_id=sample_user_id,
            db=mock_db,
        )

        # Assert
        assert deleted_count == 0
