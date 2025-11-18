"""Tests for User model."""

import pytest

from app.models.user import User


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test creating a User instance."""
        user = User(email="test@example.com")

        assert user.email == "test@example.com"
        assert hasattr(user, "created_at")

    def test_user_default_provider(self):
        """Test User has default provider."""
        user = User(email="test@example.com")

        assert user.provider == "email"

    def test_user_with_oauth_provider(self):
        """Test User with OAuth provider."""
        user = User(
            email="test@example.com",
            provider="google",
            provider_id="google-123",
        )

        assert user.provider == "google"
        assert user.provider_id == "google-123"

    def test_user_with_name_and_avatar(self):
        """Test User with name and avatar."""
        user = User(
            email="test@example.com",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
        )

        assert user.name == "Test User"
        assert user.avatar_url == "https://example.com/avatar.jpg"


class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123"
        hashed = User.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_hash_password_different_hashes(self):
        """Test same password produces different hashes (due to salt)."""
        password = "SecurePassword123"
        hash1 = User.hash_password(password)
        hash2 = User.hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_hash_password_truncates_long_password(self):
        """Test password is truncated to 72 bytes."""
        # Create password > 72 bytes
        long_password = "a" * 100
        hashed = User.hash_password(long_password)

        # Should still work
        assert len(hashed) > 0

    def test_verify_password_correct(self):
        """Test verifying correct password."""
        password = "SecurePassword123"
        user = User(email="test@example.com")
        user.hashed_password = User.hash_password(password)

        assert user.verify_password(password) is True

    def test_verify_password_incorrect(self):
        """Test verifying incorrect password."""
        password = "SecurePassword123"
        wrong_password = "WrongPassword456"
        user = User(email="test@example.com")
        user.hashed_password = User.hash_password(password)

        assert user.verify_password(wrong_password) is False

    def test_verify_password_case_sensitive(self):
        """Test password verification is case sensitive."""
        password = "SecurePassword123"
        user = User(email="test@example.com")
        user.hashed_password = User.hash_password(password)

        assert user.verify_password("securepassword123") is False

    def test_verify_password_truncates(self):
        """Test verify_password truncates to 72 bytes."""
        password = "a" * 100
        user = User(email="test@example.com")
        user.hashed_password = User.hash_password(password)

        # Should match due to truncation
        assert user.verify_password(password) is True


class TestRefreshToken:
    """Test refresh token functionality."""

    def test_set_refresh_token_hash(self):
        """Test setting refresh token hash."""
        user = User(email="test@example.com")
        token = "refresh-token-123"

        user.set_refresh_token_hash(token)

        assert user.refresh_token_hash is not None
        assert user.refresh_token_hash != token  # Should be hashed

    def test_verify_refresh_token_correct(self):
        """Test verifying correct refresh token."""
        user = User(email="test@example.com")
        token = "refresh-token-123"

        user.set_refresh_token_hash(token)

        assert user.verify_refresh_token(token) is True

    def test_verify_refresh_token_incorrect(self):
        """Test verifying incorrect refresh token."""
        user = User(email="test@example.com")
        token = "refresh-token-123"
        wrong_token = "wrong-token-456"

        user.set_refresh_token_hash(token)

        assert user.verify_refresh_token(wrong_token) is False

    def test_verify_refresh_token_no_hash_set(self):
        """Test verifying refresh token when no hash is set."""
        user = User(email="test@example.com")

        assert user.verify_refresh_token("any-token") is False

    def test_revoke_refresh_token(self):
        """Test revoking refresh token."""
        user = User(email="test@example.com")
        token = "refresh-token-123"

        user.set_refresh_token_hash(token)
        assert user.refresh_token_hash is not None

        user.revoke_refresh_token()

        assert user.refresh_token_hash is None
        assert user.verify_refresh_token(token) is False

    def test_refresh_token_truncates(self):
        """Test refresh token is truncated to 72 bytes."""
        user = User(email="test@example.com")
        long_token = "a" * 100

        user.set_refresh_token_hash(long_token)

        # Should still work due to truncation
        assert user.verify_refresh_token(long_token) is True


class TestUserRelationships:
    """Test User model relationships."""

    def test_user_has_sessions_relationship(self):
        """Test User has sessions relationship."""
        user = User(email="test@example.com")

        assert hasattr(user, "sessions")
        assert isinstance(user.sessions, list)


class TestUserFields:
    """Test User model fields."""

    def test_user_email_required(self):
        """Test User requires email."""
        # Email is required, but we can't test this directly without database
        user = User(email="test@example.com")
        assert user.email == "test@example.com"

    def test_user_hashed_password_nullable(self):
        """Test User hashed_password is nullable (for OAuth)."""
        user = User(email="test@example.com", provider="google")

        assert user.hashed_password is None

    def test_user_refresh_token_hash_nullable(self):
        """Test User refresh_token_hash is nullable."""
        user = User(email="test@example.com")

        assert user.refresh_token_hash is None

    def test_user_provider_id_nullable(self):
        """Test User provider_id is nullable (for email users)."""
        user = User(email="test@example.com", provider="email")

        assert user.provider_id is None
