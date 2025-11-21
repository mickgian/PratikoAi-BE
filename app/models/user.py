"""This file contains the user model for the application."""

from typing import (
    TYPE_CHECKING,
    List,
)

import bcrypt
from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session


class User(BaseModel, table=True):
    """User model for storing user accounts.

    Attributes:
        id: The primary key
        email: User's email (unique)
        hashed_password: Bcrypt hashed password (nullable for OAuth users)
        refresh_token_hash: Hash of the current refresh token (nullable)
        name: User's full name (from OAuth or manual registration)
        avatar_url: URL to user's profile picture (from OAuth)
        provider: Authentication provider ('email', 'google', 'linkedin')
        provider_id: Unique ID from the OAuth provider (nullable)
        created_at: When the user was created (inherited from BaseModel)
        sessions: Relationship to user's chat sessions
    """

    __tablename__ = "user"

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str | None = Field(default=None)  # Nullable for OAuth users
    # Store hash of refresh token for security - allows token revocation
    refresh_token_hash: str | None = Field(default=None, index=True)

    # OAuth and profile fields
    name: str | None = Field(default=None, max_length=255)
    avatar_url: str | None = Field(default=None, max_length=512)
    provider: str = Field(default="email", max_length=50, index=True)  # 'email', 'google', 'linkedin'
    provider_id: str | None = Field(default=None, max_length=255, index=True)  # OAuth provider user ID

    sessions: list["Session"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash.

        Truncates password to 72 bytes to comply with bcrypt limits.
        """
        password_bytes = password.encode("utf-8")[:72]
        return bcrypt.checkpw(password_bytes, self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Truncates password to 72 bytes to comply with bcrypt limits.
        """
        password_bytes = password.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password_bytes, salt).decode("utf-8")

    def set_refresh_token_hash(self, refresh_token: str) -> None:
        """Set the hash of the refresh token.

        Stores a bcrypt hash of the refresh token for secure validation.
        This allows us to revoke refresh tokens by clearing the hash.

        Args:
            refresh_token: The refresh token to hash and store

        Note:
            Truncates token to 72 bytes to comply with bcrypt limits.
        """
        token_bytes = refresh_token.encode("utf-8")[:72]
        salt = bcrypt.gensalt()
        self.refresh_token_hash = bcrypt.hashpw(token_bytes, salt).decode("utf-8")

    def verify_refresh_token(self, refresh_token: str) -> bool:
        """Verify if the provided refresh token matches the stored hash.

        Args:
            refresh_token: The refresh token to verify

        Returns:
            bool: True if the token matches, False otherwise

        Note:
            Truncates token to 72 bytes to comply with bcrypt limits.
        """
        if self.refresh_token_hash is None:
            return False
        token_bytes = refresh_token.encode("utf-8")[:72]
        return bcrypt.checkpw(token_bytes, self.refresh_token_hash.encode("utf-8"))

    def revoke_refresh_token(self) -> None:
        """Revoke the current refresh token by clearing its hash.

        This effectively invalidates all existing refresh tokens for this user.
        """
        self.refresh_token_hash = None


# Avoid circular imports
from app.models.session import Session  # noqa: E402
