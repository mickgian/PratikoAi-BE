"""Tests for new auth endpoints (P0-P3): password reset, email verification, 2FA, lockout."""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.requests import Request as StarletteRequest


def _make_request(method: str = "POST", path: str = "/test") -> StarletteRequest:
    """Helper to build a mock Starlette request for slowapi."""
    scope = {"type": "http", "method": method, "path": path, "headers": [], "query_string": b""}
    return StarletteRequest(scope)


# --- P0: Password Reset ---


class TestPasswordResetRequest:
    """Test POST /auth/password-reset/request."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.email_service")
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_request_reset_sends_email(self, _limiter, mock_db, mock_email):
        """Happy path: reset request sends email with reset link."""
        from app.api.v1.auth import request_password_reset
        from app.schemas.auth import PasswordResetRequest

        mock_user = MagicMock(id=1, email="test@example.com")
        mock_db.get_user_by_email = AsyncMock(return_value=mock_user)
        mock_db.create_password_reset_token = AsyncMock()
        mock_email.send_password_reset_email = AsyncMock(return_value=True)

        req = _make_request()
        data = PasswordResetRequest(email="test@example.com")
        result = await request_password_reset(req, data)

        assert result.message  # Should return a success message
        mock_email.send_password_reset_email.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.email_service")
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_request_reset_unknown_email_still_returns_ok(self, _limiter, mock_db, mock_email):
        """Security: unknown emails get same response (no user enumeration)."""
        from app.api.v1.auth import request_password_reset
        from app.schemas.auth import PasswordResetRequest

        mock_db.get_user_by_email = AsyncMock(return_value=None)

        req = _make_request()
        data = PasswordResetRequest(email="unknown@example.com")
        result = await request_password_reset(req, data)

        assert result.message
        mock_email.send_password_reset_email.assert_not_called()


class TestPasswordResetConfirm:
    """Test POST /auth/password-reset/confirm."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_confirm_reset_with_valid_token(self, _limiter, mock_db):
        """Happy path: valid token resets password."""
        from pydantic import SecretStr

        from app.api.v1.auth import confirm_password_reset
        from app.schemas.auth import PasswordResetConfirm

        mock_reset = MagicMock()
        mock_reset.user_id = 1
        mock_reset.used = False
        mock_reset.is_expired.return_value = False
        mock_db.get_password_reset_by_token = AsyncMock(return_value=mock_reset)
        mock_db.update_user_password = AsyncMock()
        mock_db.mark_password_reset_used = AsyncMock()

        req = _make_request()
        data = PasswordResetConfirm(token="valid-token", new_password=SecretStr("NewStr0ng!Pass"))
        result = await confirm_password_reset(req, data)

        assert result.message
        mock_db.update_user_password.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_confirm_reset_expired_token_rejected(self, _limiter, mock_db):
        """Expired token is rejected."""
        from pydantic import SecretStr

        from app.api.v1.auth import confirm_password_reset
        from app.schemas.auth import PasswordResetConfirm

        mock_reset = MagicMock()
        mock_reset.used = False
        mock_reset.is_expired.return_value = True
        mock_db.get_password_reset_by_token = AsyncMock(return_value=mock_reset)

        req = _make_request()
        data = PasswordResetConfirm(token="expired", new_password=SecretStr("NewStr0ng!Pass"))
        with pytest.raises(HTTPException):
            await confirm_password_reset(req, data)


# --- P0: Email Verification ---


class TestEmailVerification:
    """Test POST /auth/verify-email."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_verify_valid_token(self, _limiter, mock_db):
        """Happy path: valid token verifies email."""
        from app.api.v1.auth import verify_email
        from app.schemas.auth import EmailVerificationRequest

        mock_verification = MagicMock()
        mock_verification.user_id = 1
        mock_verification.used = False
        mock_verification.is_expired.return_value = False
        mock_db.get_email_verification_by_token = AsyncMock(return_value=mock_verification)
        mock_db.mark_user_email_verified = AsyncMock()
        mock_db.mark_email_verification_used = AsyncMock()

        req = _make_request()
        data = EmailVerificationRequest(token="valid-token")
        result = await verify_email(req, data)

        assert result.message
        mock_db.mark_user_email_verified.assert_called_once_with(1)

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_verify_expired_token_rejected(self, _limiter, mock_db):
        """Expired verification token is rejected."""
        from app.api.v1.auth import verify_email
        from app.schemas.auth import EmailVerificationRequest

        mock_verification = MagicMock()
        mock_verification.used = False
        mock_verification.is_expired.return_value = True
        mock_db.get_email_verification_by_token = AsyncMock(return_value=mock_verification)

        req = _make_request()
        data = EmailVerificationRequest(token="expired")
        with pytest.raises(HTTPException):
            await verify_email(req, data)


# --- P1: Account Lockout ---


class TestAccountLockout:
    """Test that login enforces account lockout."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_locked_account_returns_403(self, _limiter, mock_db):
        """Locked account is rejected even with correct credentials."""
        from app.api.v1.auth import login

        mock_user = MagicMock()
        mock_user.email = "locked@example.com"
        mock_user.account_locked_until = datetime.now(UTC) + timedelta(minutes=15)
        mock_user.failed_login_attempts = 5
        mock_user.verify_password.return_value = True
        mock_db.get_user_by_email = AsyncMock(return_value=mock_user)
        mock_db.record_login_attempt = AsyncMock()

        req = _make_request()
        with pytest.raises(Exception) as exc_info:
            await login(
                req, username="locked@example.com", password="Valid1!", remember_me=False, grant_type="password"
            )
        # Should be 423 Locked or 403 Forbidden
        assert exc_info.value.status_code in (403, 423)


# --- P2: TOTP 2FA Setup ---


class TestTOTPSetup:
    """Test 2FA setup endpoints."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    async def test_setup_2fa_returns_secret_and_qr(self, mock_db):
        """Setup returns TOTP secret, provisioning URI, and backup codes."""
        from app.api.v1.auth import setup_2fa

        mock_user = MagicMock(id=1, email="test@example.com", totp_enabled=False)
        mock_db.create_totp_device = AsyncMock()

        result = await setup_2fa(mock_user)

        assert result.secret
        assert result.provisioning_uri.startswith("otpauth://totp/")
        assert len(result.backup_codes) == 8

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    async def test_setup_2fa_rejected_when_already_enabled(self, mock_db):
        """Cannot setup 2FA if already enabled."""
        from app.api.v1.auth import setup_2fa

        mock_user = MagicMock(id=1, email="test@example.com", totp_enabled=True)

        with pytest.raises(HTTPException):
            await setup_2fa(mock_user)


# --- P2: Login with 2FA ---


class TestLoginWith2FA:
    """Test that login returns 2FA challenge when TOTP is enabled."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    @patch("app.api.v1.auth.limiter")
    async def test_login_with_2fa_enabled_returns_challenge(self, _limiter, mock_db):
        """When user has 2FA, login returns requires_2fa=True."""
        from app.api.v1.auth import login

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "2fa@example.com"
        mock_user.totp_enabled = True
        mock_user.account_locked_until = None
        mock_user.failed_login_attempts = 0
        mock_user.verify_password.return_value = True
        mock_db.get_user_by_email = AsyncMock(return_value=mock_user)
        mock_db.record_login_attempt = AsyncMock()

        req = _make_request()
        result = await login(
            req, username="2fa@example.com", password="Valid1!", remember_me=False, grant_type="password"
        )

        assert result.requires_2fa is True
        assert result.two_factor_token != ""
        assert result.access_token == ""


# --- P3: Session Limits ---


class TestSessionLimits:
    """Test concurrent session limits."""

    @pytest.mark.asyncio
    @patch("app.api.v1.auth.db_service")
    async def test_session_creation_respects_limit(self, mock_db):
        """Session creation fails when limit is reached."""
        from app.api.v1.auth import create_session

        mock_user = MagicMock(id=1)
        # Return 5 existing sessions (at limit)
        mock_db.get_user_sessions = AsyncMock(return_value=[MagicMock() for _ in range(5)])

        with pytest.raises(Exception) as exc_info:
            await create_session(mock_user)
        assert exc_info.value.status_code == 429
