"""Tests for TOTPDevice model."""

from datetime import UTC, datetime

from app.models.totp_device import TOTPDevice


class TestTOTPDeviceModel:
    """Test TOTPDevice model definition."""

    def test_create_totp_device(self):
        """Test creating a TOTP device."""
        device = TOTPDevice(
            user_id=1,
            secret_encrypted="encrypted_secret_here",
            name="Google Authenticator",
            confirmed=False,
        )
        assert device.user_id == 1
        assert device.secret_encrypted == "encrypted_secret_here"
        assert device.name == "Google Authenticator"
        assert device.confirmed is False

    def test_defaults(self):
        """Test default values."""
        device = TOTPDevice(
            user_id=1,
            secret_encrypted="enc",
        )
        assert device.confirmed is False
        assert device.name == "Autenticatore"
        assert device.backup_codes_json is None

    def test_table_name(self):
        """Test table name."""
        assert TOTPDevice.__tablename__ == "totp_device"
