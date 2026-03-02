"""Login attempt model for audit trail and account lockout (P1/P2)."""

from datetime import datetime

from sqlmodel import Field

from app.models.base import BaseModel


class LoginAttempt(BaseModel, table=True):  # type: ignore[call-arg]
    """Records every login attempt for audit and lockout logic.

    Attributes:
        id: Auto-increment primary key
        user_id: FK to user (nullable — failed attempts for unknown emails)
        email: The email used in the attempt
        ip_address: Client IP address
        user_agent: Browser/client user agent string
        success: Whether the attempt succeeded
        failure_reason: Why it failed (wrong_password, account_locked, 2fa_failed, etc.)
        created_at: When the attempt occurred (inherited from BaseModel)
    """

    __tablename__ = "login_attempt"

    id: int = Field(default=None, primary_key=True)
    user_id: int | None = Field(default=None, index=True)
    email: str = Field(max_length=255, index=True)
    ip_address: str = Field(default="", max_length=45)
    user_agent: str = Field(default="", max_length=512)
    success: bool = Field(default=False, index=True)
    failure_reason: str | None = Field(default=None, max_length=100)
