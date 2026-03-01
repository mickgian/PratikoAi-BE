"""Email verification token model (P0)."""

from datetime import UTC, datetime

from sqlmodel import Field

from app.models.base import BaseModel


class EmailVerification(BaseModel, table=True):  # type: ignore[call-arg]
    """Stores email verification tokens sent after registration.

    Attributes:
        id: Auto-increment primary key
        user_id: FK to user
        token: Unique verification token (URL-safe)
        expires_at: When the token expires (24 hours from creation)
        used: Whether the token has been consumed
        created_at: Inherited from BaseModel
    """

    __tablename__ = "email_verification"

    id: int = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    token: str = Field(unique=True, index=True, max_length=255)
    expires_at: datetime = Field()
    used: bool = Field(default=False)

    def is_expired(self) -> bool:
        """Check if the verification token has expired."""
        return datetime.now(UTC) > self.expires_at.replace(tzinfo=UTC)
