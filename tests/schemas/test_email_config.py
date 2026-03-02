"""DEV-444: Tests for Email Config schemas.

TDD: Validates request/response schema validation and serialization.
"""

import pytest
from pydantic import ValidationError

from app.schemas.email_config import EmailConfigCreateRequest, EmailConfigResponse


class TestEmailConfigCreateRequest:
    """Tests for create/update request schema."""

    def test_valid_request(self) -> None:
        """Happy path: valid request with all fields."""
        req = EmailConfigCreateRequest(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password="secret",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert req.smtp_host == "smtp.example.com"
        assert req.smtp_port == 587
        assert req.use_tls is True  # default
        assert req.reply_to_email is None  # optional

    def test_default_port_587(self) -> None:
        """Default port should be 587."""
        req = EmailConfigCreateRequest(
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password="secret",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert req.smtp_port == 587

    def test_optional_reply_to(self) -> None:
        """reply_to_email should be optional."""
        req = EmailConfigCreateRequest(
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password="secret",
            from_email="info@studio.it",
            from_name="Studio Rossi",
            reply_to_email="reply@studio.it",
        )
        assert req.reply_to_email == "reply@studio.it"

    def test_missing_required_field_raises(self) -> None:
        """Missing required field should raise ValidationError."""
        with pytest.raises(ValidationError):
            EmailConfigCreateRequest(
                smtp_host="smtp.example.com",
                # missing smtp_username, smtp_password, from_email, from_name
            )


class TestEmailConfigResponse:
    """Tests for response schema."""

    def test_password_redacted_as_has_password(self) -> None:
        """Response should use has_password instead of actual password."""
        resp = EmailConfigResponse(
            id=1,
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            has_password=True,
            use_tls=True,
            from_email="info@studio.it",
            from_name="Studio Rossi",
            is_verified=True,
            is_active=True,
        )
        assert resp.has_password is True
        # Ensure no password field exists in the model
        assert not hasattr(resp, "smtp_password")
        assert not hasattr(resp, "smtp_password_encrypted")

    def test_nullable_fields(self) -> None:
        """Optional fields should default to None."""
        resp = EmailConfigResponse(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            has_password=True,
            use_tls=True,
            from_email="info@studio.it",
            from_name="Studio Rossi",
            is_verified=False,
            is_active=True,
        )
        assert resp.id is None
        assert resp.reply_to_email is None
        assert resp.created_at is None
        assert resp.updated_at is None
