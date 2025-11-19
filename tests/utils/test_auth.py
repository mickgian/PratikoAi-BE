"""Tests for authentication utilities."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from app.schemas.auth import Token
from app.utils.auth import (
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    verify_token,
)


class TestCreateAccessToken:
    """Test create_access_token function."""

    @patch("app.utils.auth.settings")
    def test_create_access_token_default_expiration(self, mock_settings):
        """Test creating access token with default expiration."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2

        token = create_access_token("thread-123")

        assert isinstance(token, Token)
        assert token.access_token is not None
        assert token.expires_at is not None

    @patch("app.utils.auth.settings")
    def test_create_access_token_custom_expiration(self, mock_settings):
        """Test creating access token with custom expiration."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"

        expires_delta = timedelta(hours=1)
        token = create_access_token("thread-123", expires_delta=expires_delta)

        assert isinstance(token, Token)
        # Expiration should be approximately 1 hour from now
        time_until_expiry = (token.expires_at - datetime.now(UTC)).total_seconds()
        assert 3500 < time_until_expiry < 3700  # ~1 hour with tolerance

    @patch("app.utils.auth.settings")
    def test_access_token_is_string(self, mock_settings):
        """Test access token is a string."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2

        token = create_access_token("thread-123")

        assert isinstance(token.access_token, str)
        assert len(token.access_token) > 0


class TestCreateRefreshToken:
    """Test create_refresh_token function."""

    @patch("app.utils.auth.settings")
    def test_create_refresh_token_default_expiration(self, mock_settings):
        """Test creating refresh token with default expiration."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

        token = create_refresh_token(user_id=1)

        assert isinstance(token, Token)
        assert token.access_token is not None
        assert token.expires_at is not None

    @patch("app.utils.auth.settings")
    def test_create_refresh_token_custom_expiration(self, mock_settings):
        """Test creating refresh token with custom expiration."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"

        expires_delta = timedelta(days=30)
        token = create_refresh_token(user_id=1, expires_delta=expires_delta)

        assert isinstance(token, Token)
        # Expiration should be approximately 30 days from now
        time_until_expiry = (token.expires_at - datetime.now(UTC)).total_seconds()
        assert 29.9 * 24 * 3600 < time_until_expiry < 30.1 * 24 * 3600

    @patch("app.utils.auth.settings")
    def test_refresh_token_is_string(self, mock_settings):
        """Test refresh token is a string."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

        token = create_refresh_token(user_id=1)

        assert isinstance(token.access_token, str)
        assert len(token.access_token) > 0


class TestVerifyToken:
    """Test verify_token function."""

    @patch("app.utils.auth.settings")
    def test_verify_valid_access_token(self, mock_settings):
        """Test verifying valid access token."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2

        token = create_access_token("thread-123")
        thread_id = verify_token(token.access_token)

        assert thread_id == "thread-123"

    @patch("app.utils.auth.settings")
    def test_verify_token_empty_string(self, mock_settings):
        """Test verifying empty token raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            verify_token("")

    @patch("app.utils.auth.settings")
    def test_verify_token_none(self, mock_settings):
        """Test verifying None token raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            verify_token(None)

    @patch("app.utils.auth.settings")
    def test_verify_token_invalid_format(self, mock_settings):
        """Test verifying token with invalid format."""
        with pytest.raises(ValueError, match="invalid"):
            verify_token("not-a-jwt-token")

    @patch("app.utils.auth.settings")
    def test_verify_token_malformed_jwt(self, mock_settings):
        """Test verifying malformed JWT."""
        with pytest.raises(ValueError, match="invalid"):
            verify_token("a.b")  # Only 2 segments

    @patch("app.utils.auth.settings")
    def test_verify_expired_token_returns_none(self, mock_settings):
        """Test verifying expired token returns None."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"

        # Create token that expires immediately
        token = create_access_token("thread-123", expires_delta=timedelta(seconds=-1))
        result = verify_token(token.access_token)

        assert result is None

    @patch("app.utils.auth.settings")
    def test_verify_refresh_token_as_access_returns_none(self, mock_settings):
        """Test refresh token used as access token returns None."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

        refresh_token = create_refresh_token(user_id=1)
        result = verify_token(refresh_token.access_token)

        assert result is None  # Should reject refresh tokens


class TestVerifyRefreshToken:
    """Test verify_refresh_token function."""

    @patch("app.utils.auth.settings")
    def test_verify_valid_refresh_token(self, mock_settings):
        """Test verifying valid refresh token."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

        token = create_refresh_token(user_id=42)
        user_id = verify_refresh_token(token.access_token)

        assert user_id == 42

    @patch("app.utils.auth.settings")
    def test_verify_refresh_token_empty_string(self, mock_settings):
        """Test verifying empty refresh token raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            verify_refresh_token("")

    @patch("app.utils.auth.settings")
    def test_verify_refresh_token_none(self, mock_settings):
        """Test verifying None refresh token raises ValueError."""
        with pytest.raises(ValueError, match="non-empty string"):
            verify_refresh_token(None)

    @patch("app.utils.auth.settings")
    def test_verify_refresh_token_invalid_format(self, mock_settings):
        """Test verifying refresh token with invalid format."""
        with pytest.raises(ValueError, match="invalid"):
            verify_refresh_token("not-a-jwt")

    @patch("app.utils.auth.settings")
    def test_verify_access_token_as_refresh_returns_none(self, mock_settings):
        """Test access token used as refresh token returns None."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2

        access_token = create_access_token("thread-123")
        result = verify_refresh_token(access_token.access_token)

        assert result is None  # Should reject access tokens

    @patch("app.utils.auth.settings")
    def test_verify_expired_refresh_token_returns_none(self, mock_settings):
        """Test verifying expired refresh token returns None."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"

        # Create refresh token that expires immediately
        token = create_refresh_token(user_id=1, expires_delta=timedelta(seconds=-1))
        result = verify_refresh_token(token.access_token)

        assert result is None


class TestTokenSecurity:
    """Test token security features."""

    @patch("app.utils.auth.settings")
    def test_tokens_have_jti(self, mock_settings):
        """Test tokens include JTI (JWT ID) for tracking."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2

        from jose import jwt

        token = create_access_token("thread-123")
        payload = jwt.decode(token.access_token, "test-secret-key", algorithms=["HS256"])

        assert "jti" in payload

    @patch("app.utils.auth.settings")
    def test_access_and_refresh_tokens_different(self, mock_settings):
        """Test access and refresh tokens are different."""
        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2
        mock_settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

        access_token = create_access_token("thread-123")
        refresh_token = create_refresh_token(user_id=1)

        assert access_token.access_token != refresh_token.access_token

    @patch("app.utils.auth.settings")
    def test_same_input_produces_different_tokens(self, mock_settings):
        """Test same input produces different tokens (due to timestamps)."""
        import time

        mock_settings.JWT_SECRET_KEY = "test-secret-key"
        mock_settings.JWT_ALGORITHM = "HS256"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS = 2

        token1 = create_access_token("thread-123")
        time.sleep(0.01)  # Small delay
        token2 = create_access_token("thread-123")

        assert token1.access_token != token2.access_token
