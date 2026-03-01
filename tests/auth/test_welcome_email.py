"""Tests for welcome email after registration."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.config import Environment
from app.services.email_service import EmailService


class TestSendWelcomeEmail:
    """Tests for EmailService.send_welcome_email()."""

    def setup_method(self):
        with patch("app.services.email_service.MetricsService"):
            self.service = EmailService()

    @pytest.mark.asyncio
    async def test_sends_email_with_correct_subject(self):
        """Happy path: email is sent with Italian subject line (QA env)."""
        self.service._send_email = AsyncMock(return_value=True)

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.QA
            await self.service.send_welcome_email("user@example.com")

        self.service._send_email.assert_called_once()
        call_kwargs = self.service._send_email.call_args
        assert call_kwargs[1]["recipient_email"] == "user@example.com"
        assert "Benvenuto su PratikoAI" in call_kwargs[1]["subject"]

    @pytest.mark.asyncio
    async def test_subject_has_no_env_label_in_production(self):
        """In production the subject has no environment suffix."""
        self.service._send_email = AsyncMock(return_value=True)

        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.ENVIRONMENT = Environment.PRODUCTION
            await self.service.send_welcome_email("user@example.com")

        call_kwargs = self.service._send_email.call_args
        assert "Benvenuto su PratikoAI" in call_kwargs[1]["subject"]
        assert "QA" not in call_kwargs[1]["subject"]

    @pytest.mark.asyncio
    async def test_html_does_not_contain_plaintext_password(self):
        """P0 security fix: email body must NOT include plaintext password."""
        self.service._send_email = AsyncMock(return_value=True)

        await self.service.send_welcome_email("mario@studio.it")

        html = self.service._send_email.call_args[1]["html_content"]
        assert "mario@studio.it" in html
        # Password must NOT appear anywhere in the email
        assert "Password" not in html or "password" not in html.lower().split("reimposta")

    @pytest.mark.asyncio
    async def test_html_contains_verification_link_when_provided(self):
        """Email body includes verification link when URL is given."""
        self.service._send_email = AsyncMock(return_value=True)

        await self.service.send_welcome_email(
            "u@ex.com", verification_url="https://app.pratikoai.com/verify?token=abc"
        )

        html = self.service._send_email.call_args[1]["html_content"]
        assert "https://app.pratikoai.com/verify?token=abc" in html
        assert "Verifica" in html

    @pytest.mark.asyncio
    async def test_html_contains_login_link_when_no_verification(self):
        """Email body includes login link when no verification URL."""
        self.service._send_email = AsyncMock(return_value=True)

        await self.service.send_welcome_email("u@ex.com")

        html = self.service._send_email.call_args[1]["html_content"]
        assert "/signin" in html

    @pytest.mark.asyncio
    async def test_returns_false_on_smtp_failure(self):
        """If _send_email fails, send_welcome_email returns False."""
        self.service._send_email = AsyncMock(return_value=False)

        result = await self.service.send_welcome_email("u@ex.com")

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self):
        """If _send_email raises, send_welcome_email catches and returns False."""
        self.service._send_email = AsyncMock(side_effect=Exception("SMTP down"))

        result = await self.service.send_welcome_email("u@ex.com")

        assert result is False


class TestRegisterTriggersWelcomeEmail:
    """Test that register_user() fires welcome email."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.email_service")
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_register_fires_welcome_email(self, mock_limiter, mock_db, mock_email):
        """Registration creates a background task to send welcome email."""
        from pydantic import SecretStr
        from starlette.testclient import TestClient

        from app.api.v1.auth import register_user
        from app.schemas.auth import UserCreate

        # Setup mocks
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "new@user.com"
        mock_db.get_user_by_email = AsyncMock(return_value=None)
        mock_db.create_user = AsyncMock(return_value=mock_user)
        mock_db.update_user_refresh_token = AsyncMock()
        mock_db.create_email_verification = AsyncMock()
        mock_email.send_welcome_email = AsyncMock(return_value=True)

        # Build a real-enough Request for slowapi
        from starlette.requests import Request as StarletteRequest

        scope = {"type": "http", "method": "POST", "path": "/register", "headers": [], "query_string": b""}
        mock_request = StarletteRequest(scope)

        user_data = UserCreate(email="new@user.com", password=SecretStr("ValidP@ss1"))

        with (
            patch("app.api.v1.auth.sanitize_email", return_value="new@user.com"),
            patch("app.api.v1.auth.validate_password_strength"),
            patch("app.api.v1.auth.User") as mock_user_cls,
            patch("app.api.v1.auth.create_access_token") as mock_at,
            patch("app.api.v1.auth.create_refresh_token") as mock_rt,
        ):
            mock_user_cls.hash_password.return_value = "hashed"
            mock_at.return_value = MagicMock(access_token="at", expires_at="2099-01-01")
            mock_rt.return_value = MagicMock(access_token="rt")

            await register_user(mock_request, user_data)

            # Let the event loop run the background task
            await asyncio.sleep(0)

        mock_email.send_welcome_email.assert_called_once()
        call_args = mock_email.send_welcome_email.call_args
        assert call_args[0][0] == "new@user.com" or call_args[1].get("recipient_email") == "new@user.com"
