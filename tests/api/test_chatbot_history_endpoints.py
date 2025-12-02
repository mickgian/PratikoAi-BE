"""Integration tests for chat history API endpoints.

Tests authentication, authorization, and endpoint functionality for:
- GET /api/v1/chatbot/sessions/{session_id}/messages
- POST /api/v1/chatbot/import-history

NOTE: Skipped in CI - requires real authentication infrastructure.
"""

import pytest

pytest.skip(
    "Chat history endpoint tests require real authentication infrastructure - skipped in CI",
    allow_module_level=True,
)

import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User

client = TestClient(app)


@pytest.fixture
def sample_user():
    """Fixture for sample user."""
    return User(
        id=12345,
        email="test@example.com",
        full_name="Test User",
        hashed_password="hashed_password_here",
    )


@pytest.fixture
def sample_session_id():
    """Fixture for sample session ID."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_token():
    """Fixture for sample JWT token."""
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token"


@pytest.fixture
def auth_headers(sample_token):
    """Fixture for authentication headers."""
    return {"Authorization": f"Bearer {sample_token}"}


class TestGetSessionMessages:
    """Test suite for GET /api/v1/chatbot/sessions/{session_id}/messages endpoint."""

    def test_get_session_messages_unauthenticated(self, sample_session_id):
        """Test endpoint returns 401 when no auth token provided."""
        # Act
        response = client.get(f"/api/v1/chatbot/sessions/{sample_session_id}/messages")

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_session_messages_success(
        self,
        sample_session_id,
        auth_headers,
        sample_user,
    ):
        """Test successful retrieval of session messages."""
        # Arrange
        mock_messages = [
            {
                "id": str(uuid.uuid4()),
                "query": "Test query 1",
                "response": "Test response 1",
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "gpt-4-turbo",
                "tokens_used": 350,
                "cost_cents": 5,
                "response_cached": False,
                "response_time_ms": 1200,
            },
            {
                "id": str(uuid.uuid4()),
                "query": "Test query 2",
                "response": "Test response 2",
                "timestamp": datetime.utcnow().isoformat(),
                "model_used": "gpt-4-turbo",
                "tokens_used": 400,
                "cost_cents": 6,
                "response_cached": True,
                "response_time_ms": 800,
            },
        ]

        # Mock authentication
        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            # Mock session with user_id matching the session owner
            mock_session = AsyncMock()
            mock_session.id = sample_session_id
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            # Mock chat history service
            with patch("app.api.v1.chatbot.chat_history_service.get_session_history") as mock_get_history:
                mock_get_history.return_value = mock_messages

                # Act
                response = client.get(
                    f"/api/v1/chatbot/sessions/{sample_session_id}/messages",
                    headers=auth_headers,
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["query"] == "Test query 1"
        assert data[1]["response_cached"] is True

    @pytest.mark.asyncio
    async def test_get_session_messages_unauthorized_access(
        self,
        sample_session_id,
        auth_headers,
        sample_user,
    ):
        """Test endpoint returns 403 when user tries to access another user's session."""
        # Arrange
        different_user_id = 99999

        # Mock authentication
        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            # Mock session with different user_id
            mock_session = AsyncMock()
            mock_session.id = str(uuid.uuid4())  # Different session
            mock_session.user_id = different_user_id  # Different user
            mock_auth.return_value = mock_session

            # Act
            response = client.get(
                f"/api/v1/chatbot/sessions/{sample_session_id}/messages",
                headers=auth_headers,
            )

        # Assert
        assert response.status_code == 403
        assert "not authorized" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_session_messages_with_pagination(
        self,
        sample_session_id,
        auth_headers,
        sample_user,
    ):
        """Test pagination with limit and offset query parameters."""
        # Arrange
        mock_messages = []

        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            mock_session = AsyncMock()
            mock_session.id = sample_session_id
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            with patch("app.api.v1.chatbot.chat_history_service.get_session_history") as mock_get_history:
                mock_get_history.return_value = mock_messages

                # Act
                response = client.get(
                    f"/api/v1/chatbot/sessions/{sample_session_id}/messages?limit=50&offset=100",
                    headers=auth_headers,
                )

                # Assert
                assert response.status_code == 200
                # Verify pagination params were passed to service
                mock_get_history.assert_called_once_with(
                    session_id=sample_session_id,
                    limit=50,
                    offset=100,
                )

    @pytest.mark.asyncio
    async def test_get_session_messages_empty_result(
        self,
        sample_session_id,
        auth_headers,
        sample_user,
    ):
        """Test endpoint returns empty array when no messages exist."""
        # Arrange
        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            mock_session = AsyncMock()
            mock_session.id = sample_session_id
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            with patch("app.api.v1.chatbot.chat_history_service.get_session_history") as mock_get_history:
                mock_get_history.return_value = []

                # Act
                response = client.get(
                    f"/api/v1/chatbot/sessions/{sample_session_id}/messages",
                    headers=auth_headers,
                )

        # Assert
        assert response.status_code == 200
        assert response.json() == []


class TestImportHistory:
    """Test suite for POST /api/v1/chatbot/import-history endpoint."""

    def test_import_history_unauthenticated(self):
        """Test endpoint returns 401 when no auth token provided."""
        # Act
        response = client.post(
            "/api/v1/chatbot/import-history",
            json={"messages": []},
        )

        # Assert
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_import_history_success(
        self,
        auth_headers,
        sample_user,
        sample_session_id,
    ):
        """Test successful import of chat history from IndexedDB."""
        # Arrange
        import_data = {
            "messages": [
                {
                    "session_id": sample_session_id,
                    "query": "Query from IndexedDB 1",
                    "response": "Response from IndexedDB 1",
                    "timestamp": "2025-11-29T10:00:00Z",
                    "model_used": "gpt-4-turbo",
                    "tokens_used": 350,
                },
                {
                    "session_id": sample_session_id,
                    "query": "Query from IndexedDB 2",
                    "response": "Response from IndexedDB 2",
                    "timestamp": "2025-11-29T11:00:00Z",
                    "model_used": "gpt-4-turbo",
                    "tokens_used": 400,
                },
            ]
        }

        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            mock_session = AsyncMock()
            mock_session.id = sample_session_id
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            with patch("app.api.v1.chatbot.chat_history_service.save_chat_interaction") as mock_save:
                # Mock successful saves
                mock_save.return_value = str(uuid.uuid4())

                # Act
                response = client.post(
                    "/api/v1/chatbot/import-history",
                    headers=auth_headers,
                    json=import_data,
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2
        assert data["skipped_count"] == 0
        assert data["status"] == "success"

    @pytest.mark.asyncio
    async def test_import_history_validation_error(
        self,
        auth_headers,
        sample_user,
    ):
        """Test validation error when required fields missing."""
        # Arrange
        invalid_data = {
            "messages": [
                {
                    "session_id": "missing-query-field",
                    # Missing query and response
                }
            ]
        }

        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            mock_session = AsyncMock()
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            # Act
            response = client.post(
                "/api/v1/chatbot/import-history",
                headers=auth_headers,
                json=invalid_data,
            )

        # Assert
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_import_history_partial_failure(
        self,
        auth_headers,
        sample_user,
        sample_session_id,
    ):
        """Test import with some messages failing (partial success)."""
        # Arrange
        import_data = {
            "messages": [
                {
                    "session_id": sample_session_id,
                    "query": "Valid message 1",
                    "response": "Valid response 1",
                    "timestamp": "2025-11-29T10:00:00Z",
                },
                {
                    "session_id": sample_session_id,
                    "query": "Will fail",
                    "response": "This save will fail",
                    "timestamp": "2025-11-29T11:00:00Z",
                },
                {
                    "session_id": sample_session_id,
                    "query": "Valid message 2",
                    "response": "Valid response 2",
                    "timestamp": "2025-11-29T12:00:00Z",
                },
            ]
        }

        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            mock_session = AsyncMock()
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            call_count = 0

            def save_side_effect(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:
                    raise Exception("Database error")
                return str(uuid.uuid4())

            with patch("app.api.v1.chatbot.chat_history_service.save_chat_interaction") as mock_save:
                mock_save.side_effect = save_side_effect

                # Act
                response = client.post(
                    "/api/v1/chatbot/import-history",
                    headers=auth_headers,
                    json=import_data,
                )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 2
        assert data["skipped_count"] == 1
        assert data["status"] == "partial_success"

    @pytest.mark.asyncio
    async def test_import_history_empty_messages(
        self,
        auth_headers,
        sample_user,
    ):
        """Test import with empty messages array."""
        # Arrange
        import_data = {"messages": []}

        with patch("app.api.v1.auth.get_current_session") as mock_auth:
            mock_session = AsyncMock()
            mock_session.user_id = sample_user.id
            mock_auth.return_value = mock_session

            # Act
            response = client.post(
                "/api/v1/chatbot/import-history",
                headers=auth_headers,
                json=import_data,
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["imported_count"] == 0
        assert data["skipped_count"] == 0
        assert data["status"] == "success"
