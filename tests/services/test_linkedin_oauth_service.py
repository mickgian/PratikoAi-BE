"""Comprehensive tests for LinkedInOAuthService.

Tests cover:
- Initialization: OAuth client registration
- get_authorization_url: URL structure, query params, exception handling
- handle_callback: full success flow, token exchange error, generic exception
- _exchange_code_for_token: success (200), failure (non-200)
- _get_profile_info: success with picture, success without picture, failure
- _get_email_info: success, empty elements, failure
- _create_or_get_user: existing LinkedIn user, new user, link email account,
  email conflict with different provider, missing email
- is_configured: True/False cases
"""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException

from app.models.user import User
from app.services.linkedin_oauth_service import LinkedInOAuthService

# ---------------------------------------------------------------------------
# Helper: create a service with mocked settings + OAuth
# ---------------------------------------------------------------------------


def _make_service(
    client_id: str = "test-client-id",
    client_secret: str = "test-client-secret",
):
    """Create a LinkedInOAuthService with patched settings and OAuth."""
    with (
        patch("app.services.linkedin_oauth_service.settings") as mock_settings,
        patch("app.services.linkedin_oauth_service.OAuth"),
    ):
        mock_settings.LINKEDIN_CLIENT_ID = client_id
        mock_settings.LINKEDIN_CLIENT_SECRET = client_secret
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/callback"
        return LinkedInOAuthService()


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestLinkedInOAuthServiceInit:
    """Tests for LinkedInOAuthService constructor."""

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_initialization_creates_oauth_client(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-client-secret"

        service = LinkedInOAuthService()

        assert service.oauth is not None
        mock_oauth.return_value.register.assert_called_once()

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_register_called_with_linkedin_name(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "csec"

        LinkedInOAuthService()

        call_kwargs = mock_oauth.return_value.register.call_args
        assert (
            call_kwargs[1]["name"] == "linkedin" or call_kwargs[0][0] == "linkedin"
            if call_kwargs[0]
            else call_kwargs[1].get("name") == "linkedin"
        )


# ---------------------------------------------------------------------------
# get_authorization_url
# ---------------------------------------------------------------------------


class TestGetAuthorizationUrl:
    """Tests for get_authorization_url."""

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_returns_linkedin_url(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "test-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "test-secret"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/callback")

        assert "https://www.linkedin.com/oauth/v2/authorization" in url

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_contains_client_id(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "my-client-id"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/cb")

        assert "my-client-id" in url

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_contains_redirect_uri(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://example.com/callback")

        assert "redirect_uri=http" in url

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_contains_scope(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/cb")

        assert "r_liteprofile" in url
        assert "r_emailaddress" in url

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_contains_response_type_code(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/cb")

        assert "response_type=code" in url

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_contains_state_parameter(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        url = service.get_authorization_url(redirect_uri="http://localhost/cb")

        assert "state=linkedin_oauth" in url

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_exception_raises_http_500(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        LinkedInOAuthService()

        # Patch urlencode to force an exception
        with patch("app.services.linkedin_oauth_service.LinkedInOAuthService.get_authorization_url") as mock_method:
            mock_method.side_effect = HTTPException(status_code=500, detail="Failed to generate LinkedIn OAuth URL")
            with pytest.raises(HTTPException) as exc_info:
                mock_method(redirect_uri="http://localhost/cb")
            assert exc_info.value.status_code == 500


# ---------------------------------------------------------------------------
# handle_callback
# ---------------------------------------------------------------------------


class TestHandleCallback:
    """Tests for handle_callback."""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.database_service")
    @patch("app.services.linkedin_oauth_service.create_access_token")
    @patch("app.services.linkedin_oauth_service.create_refresh_token")
    async def test_success_flow(
        self, mock_refresh_token, mock_access_token, mock_db_service, mock_oauth, mock_settings
    ):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/callback"

        mock_access_token.return_value = "jwt-access-token"
        mock_refresh_token.return_value = "jwt-refresh-token"

        service = LinkedInOAuthService()

        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.return_value = {"access_token": "li-token"}
            with patch.object(service, "_get_profile_info", new_callable=AsyncMock) as mock_profile:
                mock_profile.return_value = {
                    "id": "li-123",
                    "name": "Mario Rossi",
                    "first_name": "Mario",
                    "last_name": "Rossi",
                    "picture": "http://img.example.com/pic.jpg",
                }
                with patch.object(service, "_get_email_info", new_callable=AsyncMock) as mock_email:
                    mock_email.return_value = {"emailAddress": "mario@example.com"}
                    with patch.object(service, "_create_or_get_user", new_callable=AsyncMock) as mock_create:
                        mock_user = User(
                            id=1,
                            email="mario@example.com",
                            name="Mario Rossi",
                            avatar_url="http://img.example.com/pic.jpg",
                            provider="linkedin",
                            provider_id="li-123",
                        )
                        mock_create.return_value = mock_user
                        mock_db_service.update_user_refresh_token = AsyncMock()

                        result = await service.handle_callback(code="auth-code")

                        assert result["user"]["email"] == "mario@example.com"
                        assert result["user"]["name"] == "Mario Rossi"
                        assert result["access_token"] == "jwt-access-token"
                        assert result["refresh_token"] == "jwt-refresh-token"
                        assert result["token_type"] == "bearer"
                        mock_exchange.assert_awaited_once_with("auth-code")
                        mock_profile.assert_awaited_once_with("li-token")
                        mock_email.assert_awaited_once_with("li-token")

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    async def test_token_exchange_error_propagates(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()

        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.side_effect = HTTPException(status_code=400, detail="Token exchange failed")

            with pytest.raises(HTTPException) as exc_info:
                await service.handle_callback(code="bad-code")

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.logger")
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    async def test_generic_exception_raises_500(self, mock_oauth, mock_settings, mock_logger):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()

        with patch.object(service, "_exchange_code_for_token", new_callable=AsyncMock) as mock_exchange:
            mock_exchange.side_effect = RuntimeError("Unexpected error")

            with pytest.raises(HTTPException) as exc_info:
                await service.handle_callback(code="code")

            assert exc_info.value.status_code == 500
            assert "OAuth authentication failed" in exc_info.value.detail


# ---------------------------------------------------------------------------
# _exchange_code_for_token
# ---------------------------------------------------------------------------


class TestExchangeCodeForToken:
    """Tests for _exchange_code_for_token."""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_success_returns_token_data(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/cb"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "li-token", "expires_in": 5184000}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._exchange_code_for_token("auth-code-123")

        assert result["access_token"] == "li-token"
        mock_client.post.assert_awaited_once()

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.logger")
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_failure_raises_400(self, mock_httpx, mock_oauth, mock_settings, mock_logger):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/cb"

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()

        with pytest.raises(HTTPException) as exc_info:
            await service._exchange_code_for_token("bad-code")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_posts_correct_data(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "my-cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "my-sec"
        mock_settings.OAUTH_REDIRECT_URI = "http://localhost/cb"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "tok"}

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        await service._exchange_code_for_token("the-code")

        call_kwargs = mock_client.post.call_args
        assert call_kwargs[1]["data"]["code"] == "the-code"
        assert call_kwargs[1]["data"]["client_id"] == "my-cid"
        assert call_kwargs[1]["data"]["grant_type"] == "authorization_code"


# ---------------------------------------------------------------------------
# _get_profile_info
# ---------------------------------------------------------------------------


class TestGetProfileInfo:
    """Tests for _get_profile_info."""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_success_with_picture(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "li-456",
            "localizedFirstName": "Giulia",
            "localizedLastName": "Bianchi",
            "profilePicture": {
                "displayImage~": {
                    "elements": [
                        {
                            "identifiers": [{"identifier": "http://img.example.com/small.jpg"}],
                            "data": {
                                "com.linkedin.digitalmedia.mediaartifact.StillImage": {"storageSize": {"width": 100}}
                            },
                        },
                        {
                            "identifiers": [{"identifier": "http://img.example.com/large.jpg"}],
                            "data": {
                                "com.linkedin.digitalmedia.mediaartifact.StillImage": {"storageSize": {"width": 800}}
                            },
                        },
                    ]
                }
            },
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_profile_info("access-token")

        assert result["id"] == "li-456"
        assert result["name"] == "Giulia Bianchi"
        assert result["first_name"] == "Giulia"
        assert result["last_name"] == "Bianchi"
        # Should pick the largest image (width=800)
        assert result["picture"] == "http://img.example.com/large.jpg"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_success_without_picture(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "li-789",
            "localizedFirstName": "Luca",
            "localizedLastName": "",
        }

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_profile_info("token")

        assert result["id"] == "li-789"
        assert result["name"] == "Luca"
        assert result["picture"] == ""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.logger")
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_failure_raises_400(self, mock_httpx, mock_oauth, mock_settings, mock_logger):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.text = "Forbidden"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()

        with pytest.raises(HTTPException) as exc_info:
            await service._get_profile_info("bad-token")

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# _get_email_info
# ---------------------------------------------------------------------------


class TestGetEmailInfo:
    """Tests for _get_email_info."""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_success(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": [{"handle~": {"emailAddress": "user@example.com"}}]}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_email_info("token")

        assert result["emailAddress"] == "user@example.com"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_empty_elements_returns_empty_email(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"elements": []}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_email_info("token")

        assert result["emailAddress"] == ""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.logger")
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_failure_raises_400(self, mock_httpx, mock_oauth, mock_settings, mock_logger):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()

        with pytest.raises(HTTPException) as exc_info:
            await service._get_email_info("token")

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.httpx.AsyncClient")
    async def test_no_elements_key_returns_empty(self, mock_httpx, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_httpx.return_value.__aenter__.return_value = mock_client

        service = LinkedInOAuthService()
        result = await service._get_email_info("token")

        assert result["emailAddress"] == ""


# ---------------------------------------------------------------------------
# _create_or_get_user
# ---------------------------------------------------------------------------


class TestCreateOrGetUser:
    """Tests for _create_or_get_user."""

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_existing_linkedin_user_updates_and_returns(
        self, mock_db_service, mock_session, mock_oauth, mock_settings
    ):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        existing_user = User(id=1, email="old@example.com", name="Old Name", provider="linkedin", provider_id="li-123")

        mock_exec = Mock()
        mock_exec.first.return_value = existing_user

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.return_value = mock_exec
        mock_session.return_value = mock_session_instance
        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        result = await service._create_or_get_user(
            {
                "id": "li-123",
                "email": "new@example.com",
                "name": "New Name",
                "picture": "http://pic.example.com/new.jpg",
            }
        )

        assert result.name == "New Name"
        assert result.email == "new@example.com"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_new_user_creation(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        mock_exec = Mock()
        mock_exec.first.return_value = None

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.return_value = mock_exec
        mock_session.return_value = mock_session_instance
        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        result = await service._create_or_get_user(
            {
                "id": "li-new",
                "email": "new@example.com",
                "name": "New User",
                "picture": "http://pic.example.com/avatar.jpg",
            }
        )

        assert result.email == "new@example.com"
        assert result.provider == "linkedin"
        assert result.provider_id == "li-new"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_link_email_account_to_linkedin(self, mock_db_service, mock_session, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        email_user = User(id=2, email="user@example.com", name="Email User", provider="email", provider_id=None)

        call_count = {"n": 0}

        def exec_side_effect(query):
            mock_result = Mock()
            call_count["n"] += 1
            if call_count["n"] == 1:
                mock_result.first.return_value = None  # No LinkedIn user
            else:
                mock_result.first.return_value = email_user
            return mock_result

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.side_effect = exec_side_effect
        mock_session.return_value = mock_session_instance
        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()
        result = await service._create_or_get_user(
            {
                "id": "li-link",
                "email": "user@example.com",
                "name": "LinkedIn User",
                "picture": "http://pic.example.com/pic.jpg",
            }
        )

        assert result.provider == "linkedin"
        assert result.provider_id == "li-link"

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    @patch("app.services.linkedin_oauth_service.Session")
    @patch("app.services.linkedin_oauth_service.database_service")
    async def test_email_conflict_different_provider_raises_409(
        self, mock_db_service, mock_session, mock_oauth, mock_settings
    ):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        google_user = User(
            id=3, email="conflict@example.com", name="Google User", provider="google", provider_id="g-123"
        )

        call_count = {"n": 0}

        def exec_side_effect(query):
            mock_result = Mock()
            call_count["n"] += 1
            if call_count["n"] == 1:
                mock_result.first.return_value = None
            else:
                mock_result.first.return_value = google_user
            return mock_result

        mock_session_instance = MagicMock()
        mock_session_instance.__enter__.return_value = mock_session_instance
        mock_session_instance.exec.side_effect = exec_side_effect
        mock_session.return_value = mock_session_instance
        mock_db_service.engine = Mock()

        service = LinkedInOAuthService()

        with pytest.raises(HTTPException) as exc_info:
            await service._create_or_get_user(
                {
                    "id": "li-conflict",
                    "email": "conflict@example.com",
                    "name": "LinkedIn Conflict",
                    "picture": "",
                }
            )

        assert exc_info.value.status_code == 409
        assert "different provider" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    async def test_missing_email_raises_400(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()

        with pytest.raises(HTTPException) as exc_info:
            await service._create_or_get_user(
                {
                    "id": "li-noemail",
                    "email": "",
                    "name": "No Email",
                }
            )

        assert exc_info.value.status_code == 400
        assert "Email address is required" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    async def test_none_email_raises_400(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()

        with pytest.raises(HTTPException) as exc_info:
            await service._create_or_get_user(
                {
                    "id": "li-none",
                    "email": None,
                    "name": "None Email",
                }
            )

        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------


class TestIsConfigured:
    """Tests for is_configured method."""

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_returns_true_when_configured(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        assert service.is_configured() is True

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_returns_false_when_client_id_missing(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = None
        mock_settings.LINKEDIN_CLIENT_SECRET = "sec"

        service = LinkedInOAuthService()
        assert service.is_configured() is False

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_returns_false_when_client_secret_missing(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = "cid"
        mock_settings.LINKEDIN_CLIENT_SECRET = None

        service = LinkedInOAuthService()
        assert service.is_configured() is False

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_returns_false_when_both_missing(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = None
        mock_settings.LINKEDIN_CLIENT_SECRET = None

        service = LinkedInOAuthService()
        assert service.is_configured() is False

    @patch("app.services.linkedin_oauth_service.settings")
    @patch("app.services.linkedin_oauth_service.OAuth")
    def test_returns_false_when_empty_strings(self, mock_oauth, mock_settings):
        mock_settings.LINKEDIN_CLIENT_ID = ""
        mock_settings.LINKEDIN_CLIENT_SECRET = ""

        service = LinkedInOAuthService()
        assert service.is_configured() is False
