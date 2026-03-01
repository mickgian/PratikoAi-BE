"""Tests for TOTP 2FA service."""

import pyotp
import pytest

from app.services.totp_service import TOTPService


class TestTOTPService:
    """Test TOTP service functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = TOTPService()

    def test_generate_secret(self):
        """Test generating a TOTP secret."""
        secret = self.service.generate_secret()
        assert isinstance(secret, str)
        assert len(secret) == 32  # base32 encoded

    def test_generate_provisioning_uri(self):
        """Test generating a provisioning URI for QR codes."""
        secret = self.service.generate_secret()
        uri = self.service.get_provisioning_uri(
            secret=secret,
            email="test@example.com",
        )
        assert uri.startswith("otpauth://totp/")
        assert "PratikoAI" in uri
        assert "test%40example.com" in uri or "test@example.com" in uri

    def test_verify_valid_code(self):
        """Test verifying a valid TOTP code."""
        secret = self.service.generate_secret()
        totp = pyotp.TOTP(secret)
        code = totp.now()
        assert self.service.verify_code(secret, code) is True

    def test_verify_invalid_code(self):
        """Test verifying an invalid TOTP code."""
        secret = self.service.generate_secret()
        assert self.service.verify_code(secret, "000000") is False

    def test_verify_code_wrong_length(self):
        """Test verifying code with wrong length."""
        secret = self.service.generate_secret()
        assert self.service.verify_code(secret, "123") is False

    def test_generate_backup_codes(self):
        """Test generating backup codes."""
        codes = self.service.generate_backup_codes()
        assert len(codes) == 8
        for code in codes:
            assert len(code) == 9  # 8 chars + 1 dash: xxxx-xxxx
            assert "-" in code

    def test_generate_email_otp(self):
        """Test generating an email OTP code."""
        code = self.service.generate_email_otp()
        assert isinstance(code, str)
        assert len(code) == 6
        assert code.isdigit()

    def test_hash_backup_codes(self):
        """Test serializing backup codes to JSON."""
        codes = ["abcd-efgh", "ijkl-mnop"]
        serialized = self.service.hash_backup_codes(codes)
        assert isinstance(serialized, str)
        assert "abcd-efgh" in serialized

    def test_verify_backup_code_valid(self):
        """Test verifying a valid backup code."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.hash_backup_codes(codes)
        assert self.service.verify_backup_code(codes[0], codes_json) is True

    def test_verify_backup_code_invalid(self):
        """Test verifying an invalid backup code."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.hash_backup_codes(codes)
        assert self.service.verify_backup_code("xxxx-yyyy", codes_json) is False

    def test_consume_backup_code(self):
        """Test consuming a backup code removes it from the list."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.hash_backup_codes(codes)
        updated = self.service.consume_backup_code(codes[0], codes_json)
        assert updated is not None
        assert self.service.verify_backup_code(codes[0], updated) is False
        assert self.service.verify_backup_code(codes[1], updated) is True

    def test_consume_backup_code_invalid(self):
        """Test consuming a non-existent backup code returns None."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.hash_backup_codes(codes)
        assert self.service.consume_backup_code("xxxx-yyyy", codes_json) is None
