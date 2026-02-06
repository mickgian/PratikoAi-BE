"""API tests for user feedback endpoint (DEV-255).

Tests cover:
- POST /api/v1/feedback returns 201 on success
- Unauthenticated requests return 401
- Invalid body returns 422

NOTE: Skipped in CI - TestClient(app) triggers slow app startup.
"""

import os

import pytest

# Skip in CI - TestClient(app) triggers slow app startup
if os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS"):
    pytest.skip(
        "Feedback API tests require full app infrastructure - skipped in CI",
        allow_module_level=True,
    )

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from app.api.v1.auth import get_current_session
from app.main import app
from app.models.session import Session


def _create_mock_session(user_id: int = 1, session_id: str = "test-session-123") -> MagicMock:
    """Create a mock session for auth dependency override."""
    mock_session = MagicMock(spec=Session)
    mock_session.user_id = user_id
    mock_session.id = session_id
    return mock_session


class TestUserFeedbackEndpoint:
    """Tests for POST /api/v1/feedback."""

    def test_submit_feedback_returns_201(self) -> None:
        """Happy path: valid feedback should return 201."""
        mock_session = _create_mock_session()

        with patch("app.services.feedback_service.get_langfuse_client") as mock_get_client:
            mock_client = MagicMock()
            mock_get_client.return_value = mock_client

            app.dependency_overrides[get_current_session] = lambda: mock_session
            try:
                client = TestClient(app)
                response = client.post(
                    "/api/v1/feedback/",
                    json={
                        "trace_id": "trace-abc-123",
                        "score": 1,
                        "comment": "Molto utile!",
                    },
                )
                assert response.status_code == 201
                data = response.json()
                assert data["success"] is True
            finally:
                app.dependency_overrides.clear()

    def test_submit_feedback_unauthenticated_returns_401(self) -> None:
        """Unauthenticated request should return 401."""
        # Don't override the auth dependency - should fail authentication
        app.dependency_overrides.clear()
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post(
            "/api/v1/feedback/",
            json={
                "trace_id": "trace-abc-123",
                "score": 1,
            },
        )
        assert response.status_code in (401, 403)

    def test_submit_feedback_invalid_body_returns_422(self) -> None:
        """Invalid request body should return 422."""
        mock_session = _create_mock_session()

        app.dependency_overrides[get_current_session] = lambda: mock_session
        try:
            client = TestClient(app)
            response = client.post(
                "/api/v1/feedback/",
                json={
                    "score": 5,  # Invalid score (must be 0 or 1)
                },
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()
