"""Tests for TOTP 2FA service."""

from unittest.mock import patch

import pyotp
import pytest
from cryptography.fernet import Fernet

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

    def test_serialize_backup_codes(self):
        """Test serializing backup codes to JSON."""
        codes = ["abcd-efgh", "ijkl-mnop"]
        serialized = self.service.serialize_backup_codes(codes)
        assert isinstance(serialized, str)
        assert "abcd-efgh" in serialized

    def test_verify_backup_code_valid(self):
        """Test verifying a valid backup code."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.serialize_backup_codes(codes)
        assert self.service.verify_backup_code(codes[0], codes_json) is True

    def test_verify_backup_code_invalid(self):
        """Test verifying an invalid backup code."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.serialize_backup_codes(codes)
        assert self.service.verify_backup_code("xxxx-yyyy", codes_json) is False

    def test_consume_backup_code(self):
        """Test consuming a backup code removes it from the list."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.serialize_backup_codes(codes)
        updated = self.service.consume_backup_code(codes[0], codes_json)
        assert updated is not None
        assert self.service.verify_backup_code(codes[0], updated) is False
        assert self.service.verify_backup_code(codes[1], updated) is True

    def test_consume_backup_code_invalid(self):
        """Test consuming a non-existent backup code returns None."""
        codes = self.service.generate_backup_codes()
        codes_json = self.service.serialize_backup_codes(codes)
        assert self.service.consume_backup_code("xxxx-yyyy", codes_json) is None


class TestTOTPEncryption:
    """Test Fernet encryption/decryption of TOTP secrets."""

    def setup_method(self):
        """Set up test fixtures with a valid Fernet key."""
        self.fernet_key = Fernet.generate_key().decode()
        self.service = TOTPService()

    def test_encrypt_secret_returns_different_from_plaintext(self):
        """Encrypted secret must differ from plaintext."""
        secret = self.service.generate_secret()
        encrypted = self.service.encrypt_secret(secret, self.fernet_key)
        assert encrypted != secret
        assert isinstance(encrypted, str)

    def test_decrypt_secret_roundtrip(self):
        """Encrypt then decrypt returns the original secret."""
        secret = self.service.generate_secret()
        encrypted = self.service.encrypt_secret(secret, self.fernet_key)
        decrypted = self.service.decrypt_secret(encrypted, self.fernet_key)
        assert decrypted == secret

    def test_decrypt_with_wrong_key_fails(self):
        """Decrypting with a different key raises InvalidToken."""
        from cryptography.fernet import InvalidToken

        secret = self.service.generate_secret()
        encrypted = self.service.encrypt_secret(secret, self.fernet_key)
        wrong_key = Fernet.generate_key().decode()
        with pytest.raises(InvalidToken):
            self.service.decrypt_secret(encrypted, wrong_key)

    def test_encrypt_secret_without_key_raises(self):
        """Encrypting without a key raises ValueError."""
        secret = self.service.generate_secret()
        with pytest.raises(ValueError, match="TOTP_ENCRYPTION_KEY"):
            self.service.encrypt_secret(secret, "")

    def test_decrypt_secret_without_key_raises(self):
        """Decrypting without a key raises ValueError."""
        with pytest.raises(ValueError, match="TOTP_ENCRYPTION_KEY"):
            self.service.decrypt_secret("something", "")
