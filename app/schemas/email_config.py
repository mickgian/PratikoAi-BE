"""DEV-444: Schemas for Studio Email Config API.

Request and response schemas for email configuration endpoints.
Password field is write-only — never returned in responses.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class EmailConfigCreateRequest(BaseModel):
    """Request to create/update SMTP configuration."""

    smtp_host: str = Field(max_length=255, description="Server SMTP (es. smtp.gmail.com)")
    smtp_port: int = Field(default=587, description="Porta SMTP (25, 465, 587)")
    smtp_username: str = Field(max_length=255, description="Username SMTP")
    smtp_password: str = Field(max_length=255, description="Password SMTP (verrà cifrata)")
    use_tls: bool = Field(default=True, description="Usa TLS per la connessione")
    from_email: str = Field(max_length=255, description="Indirizzo email mittente")
    from_name: str = Field(max_length=255, description="Nome mittente")
    reply_to_email: str | None = Field(default=None, max_length=255, description="Indirizzo reply-to (opzionale)")


class EmailConfigResponse(BaseModel):
    """Response with SMTP config (password redacted)."""

    id: int | None = None
    user_id: int
    smtp_host: str
    smtp_port: int
    smtp_username: str
    has_password: bool = Field(description="Indica se una password è configurata")
    use_tls: bool
    from_email: str
    from_name: str
    reply_to_email: str | None = None
    is_verified: bool
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
