"""DEV-442: StudioEmailConfig SQLModel for per-studio custom SMTP configuration.

Stores SMTP credentials with Fernet-encrypted password field.
One config per user (unique constraint on user_id).
Password field is write-only — never returned in API responses or logs.
See ADR-034 for design rationale.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, func
from sqlmodel import Field, SQLModel


class StudioEmailConfig(SQLModel, table=True):  # type: ignore[call-arg]
    """Per-user custom SMTP configuration for branded email sending.

    SMTP password is Fernet-encrypted at rest (key in SMTP_ENCRYPTION_KEY env var).
    Only Pro/Premium plan users can create/update configs (enforced at service level).
    """

    __tablename__ = "studio_email_configs"

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", unique=True, index=True)

    # SMTP settings
    smtp_host: str = Field(max_length=255)
    smtp_port: int = Field(default=587)
    smtp_username: str = Field(max_length=255)
    smtp_password_encrypted: str = Field(max_length=1024)  # Fernet-encrypted
    use_tls: bool = Field(default=True)

    # Sender identity
    from_email: str = Field(max_length=255)
    from_name: str = Field(max_length=255)
    reply_to_email: str | None = Field(default=None, max_length=255)

    # Status
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)

    # Audit timestamps
    created_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
    )  # type: ignore[assignment]
    updated_at: datetime | None = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
    )  # type: ignore[assignment]
