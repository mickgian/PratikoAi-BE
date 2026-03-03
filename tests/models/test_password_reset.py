"""Tests for PasswordReset model."""

from datetime import UTC, datetime, timedelta

from app.models.password_reset import PasswordReset


class TestPasswordResetModel:
    """Test PasswordReset model definition."""

    def test_create_password_reset(self):
        """Test creating a password reset token."""
        expires = datetime.now(UTC) + timedelta(hours=1)
        reset = PasswordReset(
            user_id=1,
            token_hash="hashed_token_value",
            expires_at=expires,
        )
        assert reset.user_id == 1
        assert reset.token_hash == "hashed_token_value"
        assert reset.used is False
        assert reset.expires_at == expires

    def test_is_expired_false(self):
        """Test token that has not expired."""
        reset = PasswordReset(
            user_id=1,
            token_hash="abc",
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        assert reset.is_expired() is False

    def test_is_expired_true(self):
        """Test token that has expired."""
        reset = PasswordReset(
            user_id=1,
            token_hash="abc",
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        assert reset.is_expired() is True

    def test_defaults(self):
        """Test default values."""
        reset = PasswordReset(
            user_id=1,
            token_hash="abc",
            expires_at=datetime.now(UTC),
        )
        assert reset.used is False
        assert reset.token_prefix == ""

    def test_compute_prefix(self):
        """Test SHA-256 prefix computation is deterministic and 8 chars."""
        prefix = PasswordReset.compute_prefix("test-token-123")
        assert isinstance(prefix, str)
        assert len(prefix) == 8
        # Deterministic: same input gives same output
        assert PasswordReset.compute_prefix("test-token-123") == prefix
        # Different input gives different output
        assert PasswordReset.compute_prefix("other-token") != prefix

    def test_table_name(self):
        """Test table name."""
        assert PasswordReset.__tablename__ == "password_reset"
