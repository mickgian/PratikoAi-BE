"""Tests for Google OAuth service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.google_oauth_service import GoogleOAuthService


class TestGoogleOAuthService:
    """Test GoogleOAuthService class."""

    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    def test_initialization(self, mock_oauth, mock_settings):
        """Test GoogleOAuthService initialization."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-client-secret"

        service = GoogleOAuthService()

        assert service.oauth is not None
        mock_oauth.return_value.register.assert_called_once()

    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    def test_get_authorization_url(self, mock_oauth, mock_settings):
        """Test authorization URL generation."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        service = GoogleOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/callback")

        assert "https://accounts.google.com/o/oauth2/auth" in url
        assert "test-client-id" in url
        assert "redirect_uri=http" in url
        assert "scope=openid" in url

    @pytest.mark.asyncio
    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    @patch("app.services.google_oauth_service.database_service")
    @patch("app.services.google_oauth_service.create_access_token")
    @patch("app.services.google_oauth_service.create_refresh_token")
    async def test_handle_callback_new_user(
        self, mock_refresh_token, mock_access_token, mock_db_service, mock_oauth, mock_settings
    ):
        """Test OAuth callback with new user creation."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/callback"

        mock_access_token.return_value = "access-token-123"
        mock_refresh_token.return_value = "refresh-token-123"

        service = GoogleOAuthService()

        # Mock token exchange
        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = {"access_token": "google-token"}

            # Mock user info retrieval
            with patch.object(service, "_get_user_info", new_callable=AsyncMock) as mock_user_info:
                mock_user_info.return_value = {
                    "id": "google-123",
                    "email": "test@example.com",
                    "name": "Test User",
                    "picture": "http://example.com/avatar.jpg",
                }

                # Mock user creation
                with patch.object(service, "_create_or_get_user", new_callable=AsyncMock) as mock_create_user:
                    mock_user = User(
                        id=1,
                        email="test@example.com",
                        name="Test User",
                        avatar_url="http://example.com/avatar.jpg",
                        provider="google",
                        provider_id="google-123",
                    )
                    mock_create_user.return_value = mock_user

                    mock_db_service.update_user_refresh_token = AsyncMock()

                    result = await service.handle_callback(code="auth-code-123")

                    assert result["user"]["email"] == "test@example.com"
                    assert result["access_token"] == "access-token-123"
                    assert result["refresh_token"] == "refresh-token-123"
                    assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    async def test_handle_callback_token_exchange_error(self, mock_oauth, mock_settings):
        """Test OAuth callback with token exchange error."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        service = GoogleOAuthService()

        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.side_effect = HTTPException(status_code=400, detail="Token exchange failed")

            with pytest.raises(HTTPException) as exc_info:
                await service.handle_callback(code="auth-code-123")

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    @patch("app.services.google_oauth_service.httpx.AsyncClient")
    async def test_exchange_code_for_token_success(self, mock_httpx, mock_oauth, mock_settings):
        """Test successful authorization code exchange."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/callback"

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "google-token", "expires_in": 3600}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = GoogleOAuthService()
        result = await service._exchange_code_for_token("auth-code-123")

        assert result["access_token"] == "google-token"

    @pytest.mark.asyncio
    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    @patch("app.services.google_oauth_service.httpx.AsyncClient")
    async def test_get_user_info_success(self, mock_httpx, mock_oauth, mock_settings):
        """Test successful user info retrieval."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "google-123", "email": "test@example.com", "name": "Test User"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = GoogleOAuthService()
        result = await service._get_user_info("google-access-token")

        assert result["email"] == "test@example.com"
        assert result["id"] == "google-123"

    @pytest.mark.asyncio
    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    @patch("app.services.google_oauth_service.Session")
    @patch("app.services.google_oauth_service.database_service")
    async def test_create_or_get_user_existing(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        """Test getting existing user."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        existing_user = User(
            id=1, email="test@example.com", name="Test User", provider="google", provider_id="google-123"
        )

        # Mock session and query
        mock_exec = Mock()
        mock_exec.first.return_value = existing_user

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.return_value = mock_exec
        mock_session.return_value = mock_session_instance

        mock_db_service.engine = Mock()

        service = GoogleOAuthService()
        user_info = {"id": "google-123", "email": "test@example.com", "name": "Test User Updated"}

        result = await service._create_or_get_user(user_info)

        assert result.email == "test@example.com"
        assert result.name == "Test User Updated"  # Should be updated

    @pytest.mark.asyncio
    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    @patch("app.services.google_oauth_service.Session")
    @patch("app.services.google_oauth_service.database_service")
    async def test_create_or_get_user_new(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        """Test creating new user."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        # Mock session to return None (user doesn't exist)
        mock_exec = Mock()
        mock_exec.first.return_value = None

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.return_value = mock_exec
        mock_session.return_value = mock_session_instance

        mock_db_service.engine = Mock()

        service = GoogleOAuthService()
        user_info = {
            "id": "google-456",
            "email": "newuser@example.com",
            "name": "New User",
            "picture": "http://example.com/pic.jpg",
        }

        result = await service._create_or_get_user(user_info)

        assert result.email == "newuser@example.com"
        assert result.provider == "google"
        assert result.provider_id == "google-456"

    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    def test_is_configured_true(self, mock_oauth, mock_settings):
        """Test OAuth configuration check when configured."""
        mock_settings.GOOGLE_CLIENT_ID = "test-client-id"
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        service = GoogleOAuthService()

        assert service.is_configured() is True

    @patch("app.services.google_oauth_service.settings")
    @patch("app.services.google_oauth_service.OAuth")
    def test_is_configured_false(self, mock_oauth, mock_settings):
        """Test OAuth configuration check when not configured."""
        mock_settings.GOOGLE_CLIENT_ID = None
        mock_settings.GOOGLE_CLIENT_SECRET = "test-secret"

        service = GoogleOAuthService()

        assert service.is_configured() is False
