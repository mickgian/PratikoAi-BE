"""DEV-442: Tests for StudioEmailConfig SQLModel.

TDD RED phase: Tests written FIRST before implementation.
Tests model creation, defaults, encryption round-trip, and constraints.
"""

import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from app.models.studio_email_config import StudioEmailConfig


class TestStudioEmailConfigModel:
    """Test StudioEmailConfig model creation and defaults."""

    def test_create_valid_config(self) -> None:
        """Happy path: create config with all required fields."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user@example.com",
            smtp_password_encrypted="encrypted_password_data",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.user_id == 1
        assert config.smtp_host == "smtp.example.com"
        assert config.smtp_port == 587
        assert config.smtp_username == "user@example.com"
        assert config.smtp_password_encrypted == "encrypted_password_data"
        assert config.from_email == "info@studio.it"
        assert config.from_name == "Studio Rossi"

    def test_default_tls_true(self) -> None:
        """Default: use_tls=True."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.use_tls is True

    def test_default_is_verified_false(self) -> None:
        """Default: is_verified=False."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.is_verified is False

    def test_default_is_active_true(self) -> None:
        """Default: is_active=True."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.is_active is True

    def test_default_port_587(self) -> None:
        """Default: smtp_port=587."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.smtp_port == 587

    def test_nullable_reply_to(self) -> None:
        """reply_to_email is optional (nullable)."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.reply_to_email is None

    def test_reply_to_set(self) -> None:
        """reply_to_email can be set."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
            reply_to_email="reply@studio.it",
        )
        assert config.reply_to_email == "reply@studio.it"

    def test_password_encryption_round_trip(self) -> None:
        """Fernet encryption: encrypt then decrypt should return original."""
        key = Fernet.generate_key()
        f = Fernet(key)
        original_password = "my_secret_smtp_password_123!"
        encrypted = f.encrypt(original_password.encode()).decode()
        decrypted = f.decrypt(encrypted.encode()).decode()
        assert decrypted == original_password

    def test_tablename(self) -> None:
        """Table name should be studio_email_configs."""
        assert StudioEmailConfig.__tablename__ == "studio_email_configs"

    def test_id_none_by_default(self) -> None:
        """ID should be None before DB insert."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
        )
        assert config.id is None

    def test_custom_port(self) -> None:
        """Custom port (e.g. 465 for SSL) should be accepted."""
        config = StudioEmailConfig(
            user_id=1,
            smtp_host="smtp.example.com",
            smtp_port=465,
            smtp_username="user@example.com",
            smtp_password_encrypted="enc",
            from_email="info@studio.it",
            from_name="Studio Rossi",
            use_tls=False,
        )
        assert config.smtp_port == 465
        assert config.use_tls is False
