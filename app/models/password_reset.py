"""Password reset token model (P0)."""

from datetime import UTC, datetime

from sqlmodel import Field

from app.models.base import BaseModel


class PasswordReset(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores password reset tokens.

    Attributes:
        id: Auto-increment primary key
        user_id: FK to user
        token_hash: Bcrypt hash of the reset token (never store plaintext)
        expires_at: When the token expires (1 hour from creation)
        used: Whether the token has been consumed
        created_at: Inherited from BaseModel
    """

    __tablename__ = "password_reset"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    token_hash: str = Field(max_length=255)
    expires_at: datetime = Field()
    used: bool = Field(default=False)

    def is_expired(self) -> bool:
        """Check if the reset token has expired."""
        return datetime.now(UTC) > self.expires_at.replace(tzinfo=UTC)
