"""Tests for LinkedIn OAuth service."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.linkedin_oauth_service import LinkedInOAuthService


class TestLinkedInOAuthService:
    """Test LinkedInOAuthService class."""

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_initialization(self, mock_oauth, mock_settings):
        """Test LinkedIn OAuth service initialization."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-client-secret"

        service = LinkedInOAuthService()

        assert service.oauth is not None
        mock_oauth.return_value.register.assert_called_once()

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_get_authorization_url(self, mock_oauth, mock_settings):
        """Test authorization URL generation."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/callback")

        assert "https://www.linkedin.com/oauth/v2/authorization" in url
        assert "test-client-id" in url
        assert "redirect_uri=http" in url
        assert "scope=r_liteprofile" in url

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.database_service")
    @patch("app.services.linkedin_oauth_service.create_access_token")
    @patch("app.services.linkedin_oauth_service.create_refresh_token")
    async def test_handle_callback_new_user(
        self, mock_refresh_token, mock_access_token, mock_db_service, mock_oauth, mock_settings
    ):
        """Test OAuth callback with new user creation."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/callback"

        mock_access_token.return_value = "access-token-123"
        mock_refresh_token.return_value = "refresh-token-123"

        service = LinkedInOAuthService()

        # Mock token exchange
        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = {"access_token": "linkedin-token"}

            # Mock profile info retrieval
            with patch.object(service, "_get_profile_info", new_callable=AsyncMock) as mock_profile:
                mock_profile.return_value = {
                    "id": "linkedin-123",
                    "name": "Test User",
                    "first_name": "Test",
                    "last_name": "User",
                    "picture": "http://example.com/avatar.jpg",
                }

                # Mock email info retrieval
                with patch.object(service, "_get_email_info", new_callable=AsyncMock) as mock_email:
                    mock_email.return_value = {"emailAddress": "test@example.com"}

                    # Mock user creation
                    with patch.object(service, "_create_or_get_user", new_callable=AsyncMock) as mock_create_user:
                        mock_user = User(
                            id=1,
                            email="test@example.com",
                            name="Test User",
                            avatar_url="http://example.com/avatar.jpg",
                            provider="linkedin",
                            provider_id="linkedin-123",
                        )
                        mock_create_user.return_value = mock_user

                        mock_db_service.update_user_refresh_token = AsyncMock()

                        result = await service.handle_callback(code="auth-code-123")

                        assert result["user"]["email"] == "test@example.com"
                        assert result["access_token"] == "access-token-123"
                        assert result["refresh_token"] == "refresh-token-123"
                        assert result["token_type"] == "bearer"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    async def test_handle_callback_token_exchange_error(self, mock_oauth, mock_settings):
        """Test OAuth callback with token exchange error."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        service = LinkedInOAuthService()

        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.side_effect = HTTPException(status_code=400, detail="Token exchange failed")

            with pytest.raises(HTTPException) as exc_info:
                await service.handle_callback(code="auth-code-123")

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_exchange_code_for_token_success(self, mock_httpx, mock_oauth, mock_settings):
        """Test successful authorization code exchange."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/callback"

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "linkedin-token", "expires_in": 5184000}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._exchange_code_for_token("auth-code-123")

        assert result["access_token"] == "linkedin-token"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_get_profile_info_success(self, mock_httpx, mock_oauth, mock_settings):
        """Test successful profile info retrieval."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "linkedin-123",
            "localizedFirstName": "Test",
            "localizedLastName": "User",
            "profilePicture": {
                "displayImage~": {
                    "elements": [
                        {
                            "identifiers": [{"identifier": "http://example.com/pic.jpg"}],
                            "data": {
                                "com.linkedin.digitalmedia.mediaartifact.StillImage": {"storageSize": {"width": 400}}
                            },
                        }
                    ]
                }
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_profile_info("linkedin-access-token")

        assert result["name"] == "Test User"
        assert result["id"] == "linkedin-123"
        assert result["picture"] == "http://example.com/pic.jpg"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_get_email_info_success(self, mock_httpx, mock_oauth, mock_settings):
        """Test successful email info retrieval."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        # Mock httpx response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": [{"handle~": {"emailAddress": "test@example.com"}}]}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_email_info("linkedin-access-token")

        assert result["emailAddress"] == "test@example.com"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_create_or_get_user_existing(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        """Test getting existing LinkedIn user."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        existing_user = User(
            id=1, email="test@example.com", name="Test User", provider="linkedin", provider_id="linkedin-123"
        )

        # Mock session and query
        mock_exec = Mock()
        mock_exec.first.return_value = existing_user

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.return_value = mock_exec
        mock_session.return_value = mock_session_instance

        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        user_info = {
            "id": "linkedin-123",
            "email": "test@example.com",
            "name": "Test User Updated",
            "picture": "http://example.com/new.jpg",
        }

        result = await service._create_or_get_user(user_info)

        assert result.email == "test@example.com"
        assert result.name == "Test User Updated"  # Should be updated

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_create_or_get_user_new(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        """Test creating new LinkedIn user."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        # Mock session to return None (user doesn't exist)
        mock_exec = Mock()
        mock_exec.first.return_value = None

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.return_value = mock_exec
        mock_session.return_value = mock_session_instance

        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        user_info = {
            "id": "linkedin-456",
            "email": "newuser@example.com",
            "name": "New User",
            "picture": "http://example.com/pic.jpg",
        }

        result = await service._create_or_get_user(user_info)

        assert result.email == "newuser@example.com"
        assert result.provider == "linkedin"
        assert result.provider_id == "linkedin-456"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_create_or_get_user_link_email_account(
        self, mock_db_service, mock_session, mock_oauth, mock_settings
    ):
        """Test linking existing email account to LinkedIn."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        # Existing user with email provider
        existing_email_user = User(
            id=1, email="test@example.com", name="Email User", provider="email", provider_id=None
        )

        # Mock session - first query returns None (no LinkedIn user), second returns email user
        def exec_side_effect(query):
            mock_result = Mock()
            # First call: check for LinkedIn user
            if not hasattr(exec_side_effect, "call_count"):
                exec_side_effect.call_count = 0
            exec_side_effect.call_count += 1

            if exec_side_effect.call_count == 1:
                mock_result.first.return_value = None  # No LinkedIn user
            else:
                mock_result.first.return_value = existing_email_user  # Email user exists
            return mock_result

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.side_effect = exec_side_effect
        mock_session.return_value = mock_session_instance

        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        user_info = {
            "id": "linkedin-456",
            "email": "test@example.com",
            "name": "LinkedIn User",
            "picture": "http://example.com/pic.jpg",
        }

        result = await service._create_or_get_user(user_info)

        assert result.provider == "linkedin"
        assert result.provider_id == "linkedin-456"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_create_or_get_user_email_conflict(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        """Test user creation with email conflict (different OAuth provider)."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        # Existing user with Google provider
        existing_google_user = User(
            id=1, email="test@example.com", name="Google User", provider="google", provider_id="google-123"
        )

        # Mock session - first query returns None (no LinkedIn user), second returns Google user
        def exec_side_effect(query):
            mock_result = Mock()
            if not hasattr(exec_side_effect, "call_count"):
                exec_side_effect.call_count = 0
            exec_side_effect.call_count += 1

            if exec_side_effect.call_count == 1:
                mock_result.first.return_value = None  # No LinkedIn user
            else:
                mock_result.first.return_value = existing_google_user  # Google user exists
            return mock_result

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.side_effect = exec_side_effect
        mock_session.return_value = mock_session_instance

        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        user_info = {
            "id": "linkedin-456",
            "email": "test@example.com",
            "name": "LinkedIn User",
            "picture": "http://example.com/pic.jpg",
        }

        with pytest.raises(HTTPException) as exc_info:
            await service._create_or_get_user(user_info)

        assert exc_info.value.status_code == 409
        assert "different provider" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    async def test_create_or_get_user_no_email(self, mock_oauth, mock_settings):
        """Test user creation fails without email."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        service = LinkedInOAuthService()
        user_info = {"id": "linkedin-456", "email": "", "name": "No Email User"}

        with pytest.raises(HTTPException) as exc_info:
            await service._create_or_get_user(user_info)

        assert exc_info.value.status_code == 400
        assert "Email address is required" in exc_info.value.detail

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_is_configured_true(self, mock_oauth, mock_settings):
        """Test OAuth configuration check when configured."""
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        service = LinkedInOAuthService()

        assert service.is_configured() is True

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_is_configured_false(self, mock_oauth, mock_settings):
        """Test OAuth configuration check when not configured."""
        mock_settings.LINKEDIN_CLIENT_ID = None
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        service = LinkedInOAuthService()

        assert service.is_configured() is False
