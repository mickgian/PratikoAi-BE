"""Password reset token model (P0)."""

import hashlib
from datetime import UTC, datetime

from sqlmodel import Field

from app.models.base import BaseModel


class PasswordReset(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores password reset tokens.

    Attributes:
        id: Auto-increment primary key
        user_id: FK to user
        token_hash: Bcrypt hash of the reset token (never store plaintext)
        token_prefix: SHA-256 prefix (8 hex chars) for O(1) lookup
        expires_at: When the token expires (1 hour from creation)
        used: Whether the token has been consumed
        created_at: Inherited from BaseModel
    """

    __tablename__ = "password_reset"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    token_hash: str = Field(max_length=255)
    token_prefix: str = Field(default="", max_length=8, index=True)
    expires_at: datetime = Field()
    used: bool = Field(default=False)

    @staticmethod
    def compute_prefix(token: str) -> str:
        """Compute a SHA-256 prefix from a raw token for indexed lookup.

        Returns the first 8 hex characters of the SHA-256 hash.
        This provides ~4 billion possible prefixes, making collisions
        extremely rare for practical reset token volumes.
        """
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:8]

    def is_expired(self) -> bool:
        """Check if the reset token has expired."""
        return datetime.now(UTC) > self.expires_at.replace(tzinfo=UTC)
