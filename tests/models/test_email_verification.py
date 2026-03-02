"""Tests for EmailVerification model."""

from datetime import UTC, datetime, timedelta

from app.models.email_verification import EmailVerification


class TestEmailVerificationModel:
    """Test EmailVerification model definition."""

    def test_create_email_verification(self):
        """Test creating an email verification token."""
        expires = datetime.now(UTC) + timedelta(hours=24)
        verification = EmailVerification(
            user_id=1,
            token="abc123token",
            expires_at=expires,
        )
        assert verification.user_id == 1
        assert verification.token == "abc123token"
        assert verification.used is False
        assert verification.expires_at == expires

    def test_is_expired_false(self):
        """Test token that has not expired."""
        verification = EmailVerification(
            user_id=1,
            token="abc",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        assert verification.is_expired() is False

    def test_is_expired_true(self):
        """Test token that has expired."""
        verification = EmailVerification(
            user_id=1,
            token="abc",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert verification.is_expired() is True

    def test_defaults(self):
        """Test default values."""
        verification = EmailVerification(
            user_id=1,
            token="abc",
            expires_at=datetime.now(UTC),
        )
        assert verification.used is False

    def test_table_name(self):
        """Test table name."""
        assert EmailVerification.__tablename__ == "email_verification"
